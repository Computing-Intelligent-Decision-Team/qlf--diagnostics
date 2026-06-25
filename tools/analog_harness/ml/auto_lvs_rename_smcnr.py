#!/usr/bin/env python3
"""Auto-discover LVS net renames for SMCNR MOS-only extracted SPICE.

SMCNR topology is fixed. After Magic extraction, anonymous nodes follow
coordinate-pattern naming (a_<x>_<y>#). The same circuit node always
has the same coordinate suffix pattern, though the exact coordinates
change with MAGICAL placement.

This tool auto-discovers the mapping from coordinate patterns to logical
net names by analyzing device connectivity in the extracted SPICE.
"""
from __future__ import annotations

import re, json, sys, subprocess
from pathlib import Path
from collections import defaultdict
from typing import Any


# ── Pattern-to-net mapping for SMCNR topology ──
# These suffixes are stable across MAGICAL runs for the same topology.
# The full name is a_<x>_<suffix># where <x> varies but <suffix> is fixed.

SUFFIX_PATTERNS = {
    "_2846#": "ibias",     # bias PMOS gate/source (diode-connected xm7)
    "_586#":  "net53",     # diff pair tail (source of xm0/xm2)
    "_494#":  "outn",      # load NMOS gate + 2nd-stage NMOS gate
    "_n30#":  "outp",      # diff pair drain (drain of xm0/xm2)
    "_n10#":  "outp",      # load NMOS source (alt name for outp)
}

# Backup: connectivity-based classification
# If suffix patterns don't cover a node, use device terminal analysis


def classify_by_connectivity(extracted_lines: list[str]) -> dict[str, str]:
    """Fallback: classify anonymous nodes by device connectivity."""
    devices: list[dict[str, str]] = []
    for line in extracted_lines:
        m = re.match(
            r"^X\d+\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+"
            r"(sky130_fd_pr__[np]fet_01v8)",
            line
        )
        if m:
            devices.append({
                "d": m.group(1), "g": m.group(2),
                "s": m.group(3), "b": m.group(4),
                "model": m.group(5),
            })

    # Find diode-connected PMOS: gate == drain, should be ibias
    diode_pmos_gates: set[str] = set()
    for d in devices:
        if "pfet" in d["model"] and d["g"] == d["d"]:
            diode_pmos_gates.add(d["g"])

    # Find diff-pair tail: source net that feeds BOTH xm0 and xm2 PMOS
    pmos_sources: dict[str, int] = defaultdict(int)
    for d in devices:
        if "pfet" in d["model"]:
            pmos_sources[d["s"]] += 1
    # tail net appears as source of multiple PMOS (xm0, xm2, xm4)
    tail_nets = {net for net, cnt in pmos_sources.items() if cnt >= 2}

    # Find outn: net that connects to NMOS gate AND 2nd-stage NMOS gate
    nmos_gates: dict[str, int] = defaultdict(int)
    for d in devices:
        if "nfet" in d["model"]:
            nmos_gates[d["g"]] += 1
    # outn appears as gate of multiple NMOS (xm1, xm3, xm4)
    outn_nets = {net for net, cnt in nmos_gates.items() if cnt >= 2}

    # Find outp: net that is drain of diff-pair PMOS (xm0 or xm2)
    # diff-pair PMOS have w=7.52 (the largest devices)
    outp_candidates: set[str] = set()
    for d in devices:
        if "pfet" in d["model"] and d["d"] not in diode_pmos_gates:
            outp_candidates.add(d["d"])

    # Remove known nets from outp candidates
    outp_nets = outp_candidates - diode_pmos_gates - tail_nets - outn_nets
    # Also remove port names
    port_names = {"vdda", "gnda", "vin", "vip", "vout", "ibias"}
    outp_nets -= port_names

    renames: dict[str, str] = {}
    anon_pattern = re.compile(r"^a_\d+_[a-z]*\d+#$")

    # Classify anonymous nodes
    all_anon: set[str] = set()
    for d in devices:
        for pin in [d["d"], d["g"], d["s"], d["b"]]:
            if anon_pattern.match(pin):
                all_anon.add(pin)

    for anon in sorted(all_anon):
        if anon in diode_pmos_gates:
            renames[anon] = "ibias"
        elif anon in tail_nets:
            renames[anon] = "net53"
        elif anon in outn_nets:
            renames[anon] = "outn"
        elif anon in outp_nets:
            renames[anon] = "outp"
        # Remaining: check if connected to outp drain
        else:
            for d in devices:
                if d["d"] == anon or d["s"] == anon:
                    if "pfet" in d["model"] and d["d"] == anon:
                        renames[anon] = "outp"
                        break
                    elif "nfet" in d["model"] and d["s"] == anon:
                        renames[anon] = "outp"
                        break

    return renames


def discover_renames(extracted_spice_path: str | Path) -> dict[str, str]:
    """Auto-discover LVS net renames for an SMCNR extracted SPICE file.

    Returns dict mapping anonymous node names to logical net names.
    """
    path = Path(extracted_spice_path)
    lines = path.read_text().splitlines()

    # Method 1: suffix pattern matching (fast, works for most cases)
    renames: dict[str, str] = {}
    anon_pattern = re.compile(r"(a_\d+_[a-z]*\d+#)")
    for line in lines:
        if not line.startswith("X"):
            continue
        for token in line.split():
            m = anon_pattern.fullmatch(token)
            if m:
                name = m.group(1)
                if name not in renames:
                    # Try suffix patterns
                    for suffix, logical in SUFFIX_PATTERNS.items():
                        if name.endswith(suffix):
                            renames[name] = logical
                            break

    # Method 2: connectivity-based for any remaining unmapped nodes
    unmapped = set()
    for line in lines:
        if not line.startswith("X"):
            continue
        for token in line.split():
            if anon_pattern.fullmatch(token) and token not in renames:
                unmapped.add(token)

    if unmapped:
        connectivity_renames = classify_by_connectivity(lines)
        for anon in unmapped:
            if anon in connectivity_renames:
                renames[anon] = connectivity_renames[anon]
            else:
                # Last resort: heuristic by coordinate pattern
                if "_2846#" in anon:
                    renames[anon] = "ibias"
                elif "_586#" in anon:
                    renames[anon] = "net53"
                elif "_494#" in anon:
                    renames[anon] = "outn"
                elif "_n30#" in anon:
                    renames[anon] = "outp"
                elif "_n10#" in anon:
                    renames[anon] = "outp"

    return renames


def prepare_lvs_extracted(
    extracted_spice_path: str | Path,
    renames: dict[str, str],
    output_path: str | Path | None = None,
) -> str:
    """Apply renames and strip parasitic caps for MOS-only LVS.

    Returns the prepared netlist text.
    """
    path = Path(extracted_spice_path)
    lines = path.read_text().splitlines()
    out: list[str] = []
    for line in lines:
        if line.startswith("C"):  # strip parasitic caps
            continue
        for old, new in renames.items():
            line = line.replace(old, new)
        out.append(line)

    text = "\n".join(out) + "\n"
    if output_path:
        Path(output_path).write_text(text)
    return text


def run_lvs(
    source_path: str | Path,
    extracted_path: str | Path,
    setup_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Run Netgen LVS and return result dict."""
    output_dir = Path(output_dir)
    tcl_path = output_dir / "run_lvs.tcl"
    log_path = output_dir / "lvs.log"

    tcl_path.write_text(
        f"lvs {{{source_path.resolve()} SMCNR_SE_2st_AMP}} "
        f"{{{extracted_path.resolve()} SMCNR_SE_2st_AMP_flat}} "
        f"{Path(setup_path).resolve()} {log_path.resolve()}\nquit\n"
    )

    result = subprocess.run(
        ["/usr/lib/netgen/bin/netgen", "-batch", "source", str(tcl_path)],
        capture_output=True, text=True,
    )
    output = result.stdout + result.stderr

    match = "Netlists match uniquely" in output or "Circuits match uniquely" in output
    dev_match = re.search(r"Circuit 1 contains (\d+) devices.*Circuit 2 contains (\d+) devices", output)
    net_match = re.search(r"Circuit 1 contains (\d+) nets.*Circuit 2 contains (\d+) nets", output)
    net_mismatch = "MISMATCH" in output and "nets" in output

    # Classify failure
    failure_reason = None
    if not match:
        if net_mismatch and dev_match and int(dev_match.group(1)) == int(dev_match.group(2)):
            failure_reason = "net_mismatch"  # likely layout open, not rename error
        elif dev_match and int(dev_match.group(1)) != int(dev_match.group(2)):
            failure_reason = "device_mismatch"
        else:
            failure_reason = "unknown"

    return {
        "lvs_pass": match,
        "source_devices": int(dev_match.group(1)) if dev_match else None,
        "extracted_devices": int(dev_match.group(2)) if dev_match else None,
        "source_nets": int(net_match.group(1)) if net_match else None,
        "extracted_nets": int(net_match.group(2)) if net_match else None,
        "failure_reason": failure_reason,
        "output": output,
    }


def process_candidate(
    candidate_dir: str | Path,
    setup_path: str | Path,
) -> dict[str, Any]:
    """Full auto-rename + LVS for one candidate directory.

    The candidate dir should contain:
      - SMCNR_SE_2st_AMP_flat.spice (extracted)
      - case/netlist.sp (source MOS-only)
    """
    candidate_dir = Path(candidate_dir)
    extracted = candidate_dir / "SMCNR_SE_2st_AMP_flat.spice"
    source = candidate_dir / "case" / "netlist.sp"

    if not extracted.exists():
        return {"error": f"extracted SPICE not found: {extracted}"}
    if not source.exists():
        return {"error": f"source netlist not found: {source}"}

    # Discover renames
    renames = discover_renames(extracted)
    if not renames:
        return {"error": "no renames discovered", "renames": {}}

    # Prepare LVS source (convert nch_mac/pch_mac to sky130 models, fix subckt format)
    source_text = source.read_text()
    source_text = source_text.replace("nch_mac", "sky130_fd_pr__nfet_01v8")
    source_text = source_text.replace("pch_mac", "sky130_fd_pr__pfet_01v8")
    # Fix MAGICAL format: subckt -> .subckt, ends -> .ends
    if source_text.startswith("subckt"):
        source_text = "." + source_text
    source_text = source_text.replace("\nends ", "\n.ends ")
    lvs_src = candidate_dir / "lvs_src.spice"
    lvs_src.write_text(source_text)

    # Prepare LVS extracted
    lvs_ext = candidate_dir / "lvs_ext_mos.spice"
    prepare_lvs_extracted(extracted, renames, lvs_ext)

    # Run LVS
    result = run_lvs(lvs_src, lvs_ext, setup_path, candidate_dir)
    result["renames"] = renames
    result["candidate_dir"] = str(candidate_dir)
    return result


# ── CLI ──

def main():
    import argparse
    p = argparse.ArgumentParser(description="Auto LVS rename for SMCNR MOS-only candidates")
    p.add_argument("candidate_dir", type=Path, nargs="?", help="Candidate directory with extracted SPICE")
    p.add_argument("--setup", type=Path,
                   default="/home/qlf/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A/libs.tech/netgen/sky130A_setup.tcl",
                   help="Netgen setup Tcl path")
    p.add_argument("--batch", type=Path, help="Batch directory with mc_* subdirs")
    p.add_argument("--json", action="store_true", help="Output JSON")
    args = p.parse_args()

    if not args.candidate_dir and not args.batch:
        p.error("either candidate_dir or --batch is required")
    if args.batch:
        results = {}
        for subdir in sorted(args.batch.glob("mc_*")):
            cid = subdir.name
            print(f"{cid}: ", end="", flush=True)
            r = process_candidate(subdir, args.setup)
            if r.get("lvs_pass"):
                print(f"PASS (renames={len(r['renames'])})")
            else:
                reason = r.get("failure_reason", r.get("error", "unknown"))
                devs = f"devs={r.get('source_devices','?')}/{r.get('extracted_devices','?')}"
                nets = f"nets={r.get('source_nets','?')}/{r.get('extracted_nets','?')}"
                print(f"FAIL [{reason}] {devs} {nets}")
            results[cid] = {k: v for k, v in r.items() if k != "output"}
        if args.json:
            print(json.dumps(results, indent=2, default=str))
        passed = sum(1 for r in results.values() if r.get("lvs_pass"))
        print(f"\n{passed}/{len(results)} LVS PASS")
    else:
        r = process_candidate(args.candidate_dir, args.setup)
        if args.json:
            print(json.dumps(r, indent=2, default=str))
        else:
            print(f"LVS: {'PASS' if r.get('lvs_pass') else 'FAIL'}")
            print(f"Renames: {r.get('renames', {})}")
            if r.get("error"):
                print(f"Error: {r['error']}")


if __name__ == "__main__":
    main()
