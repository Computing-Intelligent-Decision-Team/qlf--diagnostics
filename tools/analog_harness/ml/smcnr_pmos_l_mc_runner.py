#!/usr/bin/env python3
"""Run deterministic SMCNR PMOS-L Monte Carlo batches.

The runner intentionally stays inside the established AnalogHarness evidence
boundary: MOS-only projection, Magic extraction, auto LVS rename, Netgen LVS,
and PEX parsing.  It does not create training-positive samples.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.analog_harness.ml.auto_lvs_rename_smcnr import (
    discover_renames,
    prepare_lvs_extracted,
    run_lvs,
)
from tools.analog_harness.ml.parasitic_dataset import parse_extracted_spice


TOP_CELL = "SMCNR_SE_2st_AMP"
STATE_PATH = REPO / "reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/state.json"
MAGIC_BIN = Path("/home/qlf/IOT/scripts/env/bin/magic")
PDK_ROOT = Path("/home/qlf/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9")
SETUP_TCL = PDK_ROOT / "sky130A/libs.tech/netgen/sky130A_setup.tcl"
MAGICRC = REPO / "third_party/analoggym_grpo/simulation_files/sky130_pdk/libs.tech/magic/sky130A.magicrc"

AXES = {
    "bias_pmos_l": ("xm7", "xm6"),
    "second_stage_pmos_l": ("xm5",),
}
FACTORS = (0.95, 0.96, 0.97, 0.98, 0.99, 1.005, 1.01, 1.015, 1.02, 1.025, 1.03, 1.04, 1.05)


@dataclass
class CandidateResult:
    sample_id: str
    axis: str
    factor: float
    seed: int
    status: str
    accepted: bool
    failed_stage: str | None = None
    failure_reason: str | None = None
    drc_count: int | None = None
    equiv_count: int | None = None
    pex_caps: int = 0
    pex_total_cap_ff: float = 0.0
    lvs_pass: bool = False
    source_devices: int | None = None
    extracted_devices: int | None = None
    source_nets: int | None = None
    extracted_nets: int | None = None
    renames: dict[str, str] | None = None
    candidate_dir: str = ""
    spice_path: str = ""


def _factor_label(factor: float) -> str:
    return f"{factor:.3f}".rstrip("0").rstrip(".").replace(".", "p")


def _sample_id(batch_id: str, axis: str, factor: float, seed: int) -> str:
    short_batch = batch_id.replace("mc_pmos_l_", "mc")
    return f"{short_batch}_{axis}_{_factor_label(factor)}_seed{seed:02d}"


def _format_um(value: float) -> str:
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return f"{text}u"


def _load_assignments() -> dict[str, dict[str, Any]]:
    with STATE_PATH.open() as f:
        return json.load(f)["assignments"]


def _mos_line(name: str, d: str, g: str, s: str, b: str, model: str, params: dict[str, Any]) -> str:
    nf = int(params.get("nf", 1))
    multi = int(params.get("multi", 1))
    return (
        f"{name} {d} {g} {s} {b} {model} "
        f"l={_format_um(float(params['l']))} w={_format_um(float(params['w']))} "
        f"multi={multi} nf={nf}"
    )


def build_mos_only_netlist(assignments: dict[str, dict[str, Any]], axis: str, factor: float) -> str:
    """Build the MOS-only SMCNR netlist used by MAGICAL."""
    mutated = json.loads(json.dumps(assignments))
    for inst in AXES[axis]:
        mutated[inst]["l"] = round(float(mutated[inst]["l"]) * factor, 6)

    lines = [f".subckt {TOP_CELL} vdda gnda vin vip ibias vout"]
    lines.append(_mos_line("xm1", "outp", "outp", "gnda", "gnda", "nch_mac", mutated["xm1"]))
    lines.append(_mos_line("xm3", "outn", "outp", "gnda", "gnda", "nch_mac", mutated["xm3"]))
    lines.append(_mos_line("xm7", "ibias", "ibias", "vdda", "vdda", "pch_mac", mutated["xm7"]))
    lines.append(_mos_line("xm6", "net53", "ibias", "vdda", "vdda", "pch_mac", mutated["xm6"]))
    lines.append(_mos_line("xm5", "vout", "ibias", "vdda", "vdda", "pch_mac", mutated["xm5"]))
    lines.append(_mos_line("xm2", "outn", "vip", "net53", "vdda", "pch_mac", mutated["xm2"]))
    lines.append(_mos_line("xm0", "outp", "vin", "net53", "vdda", "pch_mac", mutated["xm0"]))
    lines.append(_mos_line("xm4", "vout", "outn", "gnda", "gnda", "nch_mac", mutated["xm4"]))
    lines.append(f".ends {TOP_CELL}")
    return "\n".join(lines) + "\n"


def write_candidate(case_dir: Path, netlist_text: str) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "gds").mkdir(exist_ok=True)
    (case_dir / "netlist.sp").write_text(netlist_text)
    config = {
        "hspice_netlist": "netlist.sp",
        "resultDir": "./",
        "techfile": "../../../../sky130PDK_trial/sky130.techfile",
        "simple_tech_file": "../../../../sky130PDK_trial/sky130.techfile.simple",
        "lef": "../../../../sky130PDK_trial/sky130.lef",
        "vddNetNames": ["vdda"],
        "vssNetNames": ["gnda"],
        "useDeviceProximity": True,
        "routeTopLevelSignalIoPorts": False,
        "nwellBulkBottomTopLayer": 0,
    }
    (case_dir / "config.json").write_text(json.dumps(config, indent=2) + "\n")


def run_magical(case_dir: Path) -> tuple[bool, str]:
    rel = case_dir.resolve().relative_to(REPO)
    cmd = (
        "docker run --rm "
        f"-v {REPO}:/MAGICAL "
        "jayl940712/magical:latest "
        "bash -lc "
        f"\"cd /MAGICAL/{rel} && "
        f"rm -f {TOP_CELL}.route.gds {TOP_CELL}.place.gds {TOP_CELL}.ioPin && "
        "mkdir -p gds && "
        "python3.7 /MAGICAL/flow/python/Magical.py config.json > run.log 2>&1\""
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
    ok = (case_dir / f"{TOP_CELL}.route.gds").exists()
    return ok, result.stdout + result.stderr


def _copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        shutil.copy(src, dst)


def run_extraction(case_dir: Path, candidate_dir: Path) -> tuple[Path, Path, int | None] | None:
    route_gds = case_dir / f"{TOP_CELL}.route.gds"
    sky130_gds = case_dir / "sky130.gds"
    pinned_gds = case_dir / "pinned.gds"
    netlist = case_dir / "netlist.sp"

    subprocess.run(
        [
            sys.executable,
            str(REPO / "tools/sky130_adapter/remap_gds_to_sky130.py"),
            "--input-gds",
            str(route_gds),
            "--output-gds",
            str(sky130_gds),
            "--allow-experimental",
        ],
        capture_output=True,
        timeout=60,
    )
    if not sky130_gds.exists():
        return None

    iopin = case_dir / f"{TOP_CELL}.ioPin"
    if not iopin.exists():
        return None

    subprocess.run(
        [
            sys.executable,
            str(REPO / "tools/sky130_adapter/add_sky130_pin_shapes_from_iopin.py"),
            "--input-gds",
            str(sky130_gds),
            "--iopin",
            str(iopin),
            "--output-gds",
            str(pinned_gds),
            "--top-cell",
            TOP_CELL,
            "--only-top-ports",
            "--netlist",
            str(netlist),
        ],
        capture_output=True,
        timeout=60,
    )
    subprocess.run(
        [
            sys.executable,
            str(REPO / "tools/sky130_adapter/add_sky130_pin_labels_from_iopin.py"),
            "--input-gds",
            str(pinned_gds),
            "--iopin",
            str(iopin),
            "--output-gds",
            str(pinned_gds),
            "--top-cell",
            TOP_CELL,
            "--only-top-ports",
            "--netlist",
            str(netlist),
        ],
        capture_output=True,
        timeout=60,
    )
    if not pinned_gds.exists():
        return None

    # Name without .gds extension — Magic appends .gds during gds read
    gds_copy = candidate_dir / TOP_CELL
    shutil.copy(pinned_gds, gds_copy)

    env = os.environ.copy()
    env["PDK_ROOT"] = str(PDK_ROOT)
    env["SKY130A"] = str(PDK_ROOT / "sky130A")
    tcl_path = candidate_dir / "extract.tcl"
    tcl_path.write_text(
        "\n".join(
            [
                f"gds read {gds_copy.resolve()}",
                f"load {TOP_CELL}_flat",
                "select top cell",
                "drc check",
                "drc catch",
                "drc count",
                "extract all",
                "ext2spice lvs",
                "ext2spice cthresh 0",
                "ext2spice rthresh 0",
                "ext2spice",
                "quit",
            ]
        )
        + "\n"
    )
    result = subprocess.run(
        [str(MAGIC_BIN), "-dnull", "-noconsole", "-rcfile", str(MAGICRC), str(tcl_path.resolve())],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
        cwd=str(candidate_dir.resolve()),
    )
    (candidate_dir / "extract.log").write_text(result.stdout + result.stderr)
    combined = result.stdout + result.stderr
    # Parse standard Magic "Total DRC errors found: N"
    drc_match = re.search(r"Total DRC errors found:\s*(\d+)", combined)
    if not drc_match:
        # Fallback: custom DRC_COUNT= marker
        drc_match = re.search(r"DRC_COUNT[= ](\d+)", combined)
    drc_count = int(drc_match.group(1)) if drc_match else None

    ext = candidate_dir / f"{TOP_CELL}_flat.ext"
    spice = candidate_dir / f"{TOP_CELL}_flat.spice"
    if ext.exists() and spice.exists():
        return ext, spice, drc_count
    return None


def run_one(batch_dir: Path, batch_id: str, axis: str, factor: float, seed: int) -> CandidateResult:
    sample_id = _sample_id(batch_id, axis, factor, seed)
    candidate_dir = batch_dir / sample_id
    case_dir = candidate_dir / "case"
    candidate_dir.mkdir(parents=True, exist_ok=True)

    netlist = build_mos_only_netlist(_load_assignments(), axis, factor)
    write_candidate(case_dir, netlist)
    (candidate_dir / "state.json").write_text(
        json.dumps({"sample_id": sample_id, "axis": axis, "factor": factor, "seed": seed}, indent=2) + "\n"
    )

    ok, output = run_magical(case_dir)
    if not ok:
        return CandidateResult(sample_id, axis, factor, seed, "rejected", False, "magical", "magical_crash", candidate_dir=str(candidate_dir))

    extracted = run_extraction(case_dir, candidate_dir)
    if extracted is None:
        return CandidateResult(sample_id, axis, factor, seed, "rejected", False, "extraction", "extraction_fail", candidate_dir=str(candidate_dir))

    ext_path, spice_path, drc_count = extracted
    ext_text = ext_path.read_text(errors="ignore")
    equiv_count = sum(1 for line in ext_text.splitlines() if line.startswith("equiv "))
    edges, _per_node, total_ff = parse_extracted_spice(str(spice_path))
    pex_caps = len(edges)

    if drc_count is None:
        return CandidateResult(
            sample_id, axis, factor, seed, "rejected", False, "drc", "drc_unknown",
            drc_count=None, equiv_count=equiv_count, pex_caps=pex_caps,
            pex_total_cap_ff=round(total_ff, 4), candidate_dir=str(candidate_dir), spice_path=str(spice_path)
        )
    if drc_count != 0:
        return CandidateResult(
            sample_id, axis, factor, seed, "rejected", False, "drc", "drc_nonzero",
            drc_count=drc_count, equiv_count=equiv_count, pex_caps=pex_caps,
            pex_total_cap_ff=round(total_ff, 4), candidate_dir=str(candidate_dir), spice_path=str(spice_path)
        )
    if equiv_count:
        return CandidateResult(
            sample_id, axis, factor, seed, "rejected", False, "extraction", "equiv_collapse",
            drc_count=drc_count, equiv_count=equiv_count, pex_caps=pex_caps,
            pex_total_cap_ff=round(total_ff, 4), candidate_dir=str(candidate_dir), spice_path=str(spice_path)
        )

    renames = discover_renames(spice_path)
    lvs_ext = candidate_dir / "lvs_ext_mos.spice"
    prepare_lvs_extracted(spice_path, renames, lvs_ext)
    src_text = netlist.replace("nch_mac", "sky130_fd_pr__nfet_01v8").replace("pch_mac", "sky130_fd_pr__pfet_01v8")
    lvs_src = candidate_dir / "lvs_src.spice"
    lvs_src.write_text(src_text)
    lvs = run_lvs(lvs_src, lvs_ext, SETUP_TCL, candidate_dir)

    accepted = bool(lvs.get("lvs_pass")) and pex_caps > 0
    return CandidateResult(
        sample_id=sample_id,
        axis=axis,
        factor=factor,
        seed=seed,
        status="accepted" if accepted else "rejected",
        accepted=accepted,
        failed_stage=None if accepted else "lvs",
        failure_reason=None if accepted else lvs.get("failure_reason", "lvs_fail"),
        drc_count=drc_count,
        equiv_count=equiv_count,
        pex_caps=pex_caps,
        pex_total_cap_ff=round(total_ff, 4),
        lvs_pass=bool(lvs.get("lvs_pass")),
        source_devices=lvs.get("source_devices"),
        extracted_devices=lvs.get("extracted_devices"),
        source_nets=lvs.get("source_nets"),
        extracted_nets=lvs.get("extracted_nets"),
        renames=renames,
        candidate_dir=str(candidate_dir),
        spice_path=str(spice_path),
    )


def run_batch(batch_id: str, output_root: Path, seed: int = 1) -> list[CandidateResult]:
    batch_dir = output_root / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    results: list[CandidateResult] = []
    for axis in AXES:
        for factor in FACTORS:
            result = run_one(batch_dir, batch_id, axis, factor, seed)
            results.append(result)
            (batch_dir / "batch_results.json").write_text(json.dumps([asdict(r) for r in results], indent=2) + "\n")
            print(
                f"{result.sample_id}: {result.status} "
                f"drc={result.drc_count} equiv={result.equiv_count} "
                f"lvs={'PASS' if result.lvs_pass else 'FAIL'} caps={result.pex_caps}"
            )

    manifest = {
        "batch_id": batch_id,
        "seed": seed,
        "axes": list(AXES),
        "factors": list(FACTORS),
        "total": len(results),
        "accepted": sum(1 for r in results if r.accepted),
        "rejected": sum(1 for r in results if not r.accepted),
    }
    (batch_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic SMCNR PMOS-L MC batch")
    parser.add_argument("--batch-id", default="mc_pmos_l_0002")
    parser.add_argument("--output-root", type=Path, default=REPO / "generated/smcnr_variants")
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()
    run_batch(args.batch_id, args.output_root, args.seed)


if __name__ == "__main__":
    main()
