#!/usr/bin/env python3
"""Prepare a native Sky130 passive retarget LVS trial.

This trial is stricter than the formal R/C abstraction flow.  It keeps Sky130
PDK passive subcircuit names such as ``sky130_fd_pr__res_xhigh_po`` and only
claims full native passive LVS when every source passive has a native extracted
PDK device representation.  For the current SMC flow this usually proves the
segmented resistor chain and explicitly fails the MOM capacitor native-device
gate.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


RES_MODEL_RE = re.compile(r"\bsky130_fd_pr__res_[A-Za-z0-9_]+\b")
CAP_MODEL_RE = re.compile(r"\bsky130_fd_pr__cap_[A-Za-z0-9_]+\b")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare native Sky130 passive retarget LVS netlists.")
    parser.add_argument("--packet-json", type=Path, required=True)
    parser.add_argument("--candidate-extracted", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--sky130a", help="sky130A PDK root for Netgen setup.")
    parser.add_argument("--wsl-distro", help="WSL distro used to run netgen-lvs on Windows.")
    parser.add_argument("--run-netgen", action="store_true")
    return parser.parse_args()


def _fs_path(path: Path) -> Path:
    if os.name != "nt":
        return path
    text = str(path.resolve() if not path.is_absolute() else path)
    if text.startswith("\\\\?\\"):
        return Path(text)
    if text.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + text.lstrip("\\"))
    return Path("\\\\?\\" + text)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(_fs_path(path).read_text(encoding="utf-8"))


def source_passive_instances(packet: dict[str, Any]) -> list[str]:
    coverage = packet.get("source_instance_coverage", {})
    if isinstance(coverage, dict) and isinstance(coverage.get("source_instances"), list):
        return [str(item) for item in coverage["source_instances"]]
    instances: list[str] = []
    for item in packet.get("candidates", []):
        if isinstance(item, dict) and item.get("source_instance"):
            instances.append(str(item["source_instance"]))
    return sorted(set(instances))


def resistor_chain_candidate(packet: dict[str, Any]) -> dict[str, Any] | None:
    for item in packet.get("candidates", []):
        if not isinstance(item, dict):
            continue
        if item.get("candidate_type") != "segmented_resistor_chain_source_equivalent":
            continue
        chain = item.get("chain", {})
        devices = chain.get("devices") if isinstance(chain, dict) else None
        if isinstance(devices, list) and devices:
            return item
    return None


def native_capacitor_candidates(packet: dict[str, Any], extracted_lines: list[str]) -> list[dict[str, Any]]:
    source_caps = [
        item
        for item in packet.get("candidates", [])
        if isinstance(item, dict) and item.get("candidate_type") == "plate_coupling_capacitor_source_equivalent"
    ]
    if not source_caps:
        return []
    native_lines = []
    for line in extracted_lines:
        tokens = line.strip().split()
        model_index = next(
            (idx for idx, token in enumerate(tokens) if CAP_MODEL_RE.fullmatch(token)),
            None,
        )
        if len(tokens) >= 4 and model_index is not None and model_index >= 3:
            native_lines.append(
                {
                    "line": line.strip(),
                    "tokens": tokens,
                    "model_index": model_index,
                    "model": tokens[model_index],
                    "terminals": tokens[1:model_index],
                    "params": tokens[model_index + 1 :],
                }
            )
    if not native_lines:
        return []
    results: list[dict[str, Any]] = []
    for cap in source_caps:
        terminals = set(str(term) for term in cap.get("electrical_terminals", []))
        matches = [
            item
            for item in native_lines
            if terminals.issubset(set(item.get("terminals", [])))
        ]
        if matches:
            results.append(
                {
                    "source_instance": cap.get("source_instance"),
                    "source_model": cap.get("source_model"),
                    "electrical_terminals": cap.get("electrical_terminals"),
                    "native_extracted_devices": matches,
                }
            )
    return results


def chain_device_line(device: dict[str, Any], index: int) -> str:
    terminals = [str(term) for term in device.get("terminals", [])]
    model = str(device.get("model", ""))
    if len(terminals) < 3 or not RES_MODEL_RE.fullmatch(model):
        raise ValueError(f"invalid native resistor chain device at index {index}: {device}")
    return " ".join([f"XNR{index}", terminals[0], terminals[1], terminals[2], model, "w=0.4", "l=4"])


def resistor_chain_lines(chain_candidate: dict[str, Any]) -> list[str]:
    chain = chain_candidate.get("chain", {})
    devices = chain.get("devices") if isinstance(chain, dict) else None
    if not isinstance(devices, list):
        return []
    return [chain_device_line(device, idx) for idx, device in enumerate(devices)]


def cap_device_lines(cap_candidates: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    source_lines: list[str] = []
    candidate_lines: list[str] = []
    for idx, cap in enumerate(cap_candidates):
        matches = cap.get("native_extracted_devices") or []
        if not matches:
            continue
        match = matches[0]
        model = str(match.get("model") or "")
        if not CAP_MODEL_RE.fullmatch(model):
            continue
        source_terms = [str(term) for term in cap.get("electrical_terminals", [])]
        candidate_terms = [str(term) for term in match.get("terminals", [])]
        if len(source_terms) < 2 or len(candidate_terms) < 2:
            continue
        params = [str(param) for param in match.get("params", [])]
        source_lines.append(" ".join([f"XNC{idx}", *source_terms, model, *params]))
        candidate_lines.append(" ".join([f"XNC{idx}", *candidate_terms, model, *params]))
    return source_lines, candidate_lines


def native_passive_ports(
    *,
    resistor_candidate: dict[str, Any] | None,
    cap_candidates: list[dict[str, Any]],
) -> list[str]:
    ports: list[str] = []
    if resistor_candidate:
        for term in resistor_candidate.get("source_terminals", []):
            if str(term) not in ports:
                ports.append(str(term))
    for cap in cap_candidates:
        for term in cap.get("electrical_terminals", []):
            if str(term) not in ports:
                ports.append(str(term))
    return ports


def write_native_netlist(path: Path, *, subckt: str, ports: list[str], body_lines: list[str]) -> None:
    _fs_path(path.parent).mkdir(parents=True, exist_ok=True)
    lines = [
        "* Native Sky130 passive retarget trial netlist.",
        "* Keeps extracted Sky130 passive subcircuit models; not a primitive R/C collapse.",
        ".subckt " + " ".join([subckt] + ports),
        *body_lines,
        ".ends " + subckt,
        "",
    ]
    _fs_path(path).write_text("\n".join(lines), encoding="utf-8")


def _wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    if drive:
        rest = str(resolved)[3:].replace("\\", "/")
        return f"/mnt/{drive}/{rest}"
    return str(resolved).replace("\\", "/")


def _path_for_netgen(path: Path | str, *, wsl: bool) -> str:
    if isinstance(path, Path):
        return _wsl_path(path) if wsl else str(path)
    text = str(path)
    if wsl and re.match(r"^[A-Za-z]:", text):
        return _wsl_path(Path(text))
    return text.replace("\\", "/") if wsl else text


def run_netgen(
    *,
    source_netlist: Path,
    source_top: str,
    candidate_netlist: Path,
    candidate_top: str,
    sky130a: str,
    report: Path,
    log: Path,
    wsl_distro: str | None,
) -> dict[str, Any]:
    setup = str(Path(sky130a) / "libs.tech" / "netgen" / "sky130A_setup.tcl")
    use_wsl = os.name == "nt" and shutil.which("wsl") is not None and wsl_distro is not None
    tcl = report.with_suffix(report.suffix + ".tcl")
    _fs_path(report.parent).mkdir(parents=True, exist_ok=True)
    _fs_path(tcl).write_text(
        "\n".join(
            [
                "lvs "
                + " ".join(
                    [
                        "{" + _path_for_netgen(source_netlist, wsl=use_wsl) + f" {source_top}" + "}",
                        "{" + _path_for_netgen(candidate_netlist, wsl=use_wsl) + f" {candidate_top}" + "}",
                        "{" + _path_for_netgen(setup, wsl=use_wsl) + "}",
                        "{" + _path_for_netgen(report, wsl=use_wsl) + "}",
                    ]
                ),
                "quit",
                "",
            ]
        ),
        encoding="ascii",
    )
    if use_wsl:
        tcl_text = shlex.quote(_path_for_netgen(tcl, wsl=True))
        log_text = shlex.quote(_path_for_netgen(log, wsl=True))
        command = (
            f"if [ -x /usr/bin/netgen-lvs ]; then /usr/bin/netgen-lvs -batch source {tcl_text} > {log_text} 2>&1; "
            f"elif command -v netgen-lvs >/dev/null 2>&1; then netgen-lvs -batch source {tcl_text} > {log_text} 2>&1; "
            "else echo 'netgen-lvs missing' >&2; exit 127; fi; "
        )
        cmd = ["wsl", "-d", str(wsl_distro), "--", "bash", "-lc", command]
    else:
        netgen = shutil.which("netgen-lvs") or shutil.which("netgen")
        if not netgen:
            return {"status": "skipped", "reason": "netgen-lvs not found", "returncode": None}
        cmd = [netgen, "-batch", "source", str(tcl)]
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if not use_wsl:
        _fs_path(log).write_text(result.stdout or "", encoding="utf-8")
    return {
        "status": "pass" if result.returncode == 0 else "fail",
        "returncode": result.returncode,
        "report": str(report),
        "log": str(log),
        "tcl": str(tcl),
        "stdout": result.stdout or "",
    }


def build_trial(
    *,
    packet_json: Path,
    candidate_extracted: Path,
    out_dir: Path,
    prefix: str,
) -> dict[str, Any]:
    packet = load_json(packet_json)
    extracted_lines = _fs_path(candidate_extracted).read_text(encoding="utf-8", errors="replace").splitlines()
    resistor = resistor_chain_candidate(packet)
    cap_native = native_capacitor_candidates(packet, extracted_lines)
    chain_lines = resistor_chain_lines(resistor) if resistor else []
    cap_source_lines, cap_candidate_lines = cap_device_lines(cap_native)
    ports = native_passive_ports(resistor_candidate=resistor, cap_candidates=cap_native)
    if "gnda" not in ports and any(" gnda " in f" {line} " for line in chain_lines):
        ports.append("gnda")

    source_top = f"{prefix}_source_native_passive"
    candidate_top = f"{prefix}_candidate_native_passive"
    source_netlist = out_dir / f"{prefix}_source_native_passive.spice"
    candidate_netlist = out_dir / f"{prefix}_candidate_native_passive.spice"
    write_native_netlist(
        source_netlist,
        subckt=source_top,
        ports=ports,
        body_lines=[*chain_lines, *cap_source_lines],
    )
    write_native_netlist(
        candidate_netlist,
        subckt=candidate_top,
        ports=ports,
        body_lines=[*chain_lines, *cap_candidate_lines],
    )

    source_instances = source_passive_instances(packet)
    resistor_source = resistor.get("source_instance") if resistor else None
    cap_sources = [str(item.get("source_instance")) for item in cap_native]
    missing_native = [
        instance
        for instance in source_instances
        if instance != resistor_source and instance not in cap_sources
    ]
    return {
        "schema_version": "sky130_native_passive_retarget_trial.v1",
        "status": "native_passive_retarget_incomplete" if missing_native else "native_passive_retarget_ready",
        "source_passive_instances": source_instances,
        "source_native_passive_netlist": str(source_netlist),
        "candidate_native_passive_netlist": str(candidate_netlist),
        "source_top": source_top,
        "candidate_top": candidate_top,
        "native_resistor_chain_status": "pass" if chain_lines else "fail",
        "native_resistor_chain_source_instance": resistor_source,
        "native_resistor_chain_device_count": len(chain_lines),
        "native_resistor_chain_model": None
        if not resistor
        else sorted(set(resistor.get("chain", {}).get("device_models", []))),
        "native_capacitor_device_recognition_status": "pass" if cap_native else "fail",
        "native_capacitor_devices": cap_native,
        "native_capacitor_device_count": len(cap_candidate_lines),
        "missing_native_source_passive_instances": missing_native,
        "full_native_passive_lvs_ready": not missing_native and bool(chain_lines or cap_candidate_lines),
        "full_native_passive_lvs_proven": False,
    }


def write_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Native Sky130 Passive Retarget LVS Trial",
        "",
        f"- Status: `{summary.get('status')}`",
        f"- Native resistor chain status: `{summary.get('native_resistor_chain_status')}`",
        f"- Native resistor chain device count: `{summary.get('native_resistor_chain_device_count')}`",
        f"- Native capacitor device recognition status: `{summary.get('native_capacitor_device_recognition_status')}`",
        f"- Native capacitor device count: `{summary.get('native_capacitor_device_count')}`",
        f"- Missing native source passive instances: `{summary.get('missing_native_source_passive_instances')}`",
        f"- Full native passive LVS ready: `{summary.get('full_native_passive_lvs_ready')}`",
        f"- Full native passive LVS proven: `{summary.get('full_native_passive_lvs_proven')}`",
        "",
        "## Artifacts",
        "",
        f"- Source native passive netlist: `{summary.get('source_native_passive_netlist')}`",
        f"- Candidate native passive netlist: `{summary.get('candidate_native_passive_netlist')}`",
        "",
    ]
    if summary.get("native_passive_netgen"):
        lines.extend(
            [
                "## Native Passive Netgen",
                "",
                f"- Status: `{summary['native_passive_netgen'].get('status')}`",
                f"- Report: `{summary['native_passive_netgen'].get('report')}`",
                f"- Log: `{summary['native_passive_netgen'].get('log')}`",
                "",
            ]
        )
    elif summary.get("native_resistor_chain_netgen"):
        lines.extend(
            [
                "## Resistor Chain Netgen",
                "",
                f"- Status: `{summary['native_resistor_chain_netgen'].get('status')}`",
                f"- Report: `{summary['native_resistor_chain_netgen'].get('report')}`",
                f"- Log: `{summary['native_resistor_chain_netgen'].get('log')}`",
                "",
            ]
        )
    if summary.get("native_capacitor_device_recognition_status") != "pass":
        lines.extend(
            [
                "## Native Capacitor Blocker",
                "",
                "The candidate extraction did not contain a Sky130 native capacitor device "
                "such as `sky130_fd_pr__cap_mim_m3_1` or `sky130_fd_pr__cap_mim_m3_2` "
                "for the source capacitor. Existing evidence remains plate-coupling PEX, "
                "not native LVS device recognition.",
                "",
            ]
        )
    _fs_path(path.parent).mkdir(parents=True, exist_ok=True)
    _fs_path(path).write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    summary = build_trial(
        packet_json=args.packet_json,
        candidate_extracted=args.candidate_extracted,
        out_dir=args.out_dir,
        prefix=args.prefix,
    )
    if args.run_netgen and args.sky130a and summary.get("native_resistor_chain_status") == "pass":
        netgen = run_netgen(
            source_netlist=Path(str(summary["source_native_passive_netlist"])),
            source_top=str(summary["source_top"]),
            candidate_netlist=Path(str(summary["candidate_native_passive_netlist"])),
            candidate_top=str(summary["candidate_top"]),
            sky130a=str(args.sky130a),
            report=args.out_dir / f"{args.prefix}_native_resistor_chain_netgen.out",
            log=args.out_dir / f"{args.prefix}_native_resistor_chain_netgen.log",
            wsl_distro=args.wsl_distro,
        )
        netgen_record = {
            key: value for key, value in netgen.items() if key != "stdout"
        }
        summary["native_passive_netgen"] = netgen_record
        summary["native_passive_netgen_status"] = netgen.get("status")
        summary["native_resistor_chain_netgen"] = netgen_record
        summary["native_resistor_chain_netgen_status"] = netgen.get("status")
        summary["full_native_passive_lvs_proven"] = bool(
            summary.get("full_native_passive_lvs_ready") and netgen.get("status") == "pass"
        )
    _fs_path(args.summary_json.parent).mkdir(parents=True, exist_ok=True)
    _fs_path(args.summary_json).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(args.report, summary)
    print(f"native_resistor_chain_status={summary['native_resistor_chain_status']}")
    print(f"native_capacitor_device_recognition_status={summary['native_capacitor_device_recognition_status']}")
    print(f"full_native_passive_lvs_proven={summary['full_native_passive_lvs_proven']}")
    return 0 if summary["native_resistor_chain_status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
