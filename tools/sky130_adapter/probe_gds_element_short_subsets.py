#!/usr/bin/env python3
"""Probe which selected flat-GDS elements are sufficient to remove Magic port shorts."""

from __future__ import annotations

import argparse
import itertools
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from compare_mos_connectivity import compare as compare_mos_connectivity
from compare_mos_connectivity import render_report as render_mos_report
from strip_passive_geometry_from_gds import element_selector_key, strip_gds


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe selected GDS element subsets for Magic port shorts.")
    parser.add_argument("--input-gds", type=Path, required=True)
    parser.add_argument("--crossing-summary-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--sky130a", required=True)
    parser.add_argument("--wsl-distro")
    parser.add_argument("--top-cell", required=True)
    parser.add_argument("--magic-cell")
    parser.add_argument("--vdd", default="vdda")
    parser.add_argument("--vss", default="gnda")
    parser.add_argument("--max-combination-size", type=int, default=1)
    parser.add_argument("--max-probes", type=int)
    parser.add_argument("--run-baseline", action="store_true")
    parser.add_argument("--run-all-elements", action="store_true")
    parser.add_argument("--stop-at-first-short-free-size", action="store_true")
    parser.add_argument("--reference-netlist", type=Path)
    parser.add_argument("--compare-all", action="store_true")
    parser.add_argument(
        "--strip-mode",
        choices=("crossing", "clip-crossing", "crop-crossing"),
        default="crossing",
        help="How to remove selected crossing elements before Magic extraction.",
    )
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def wsl_path(path: Path | str) -> str:
    text = str(path)
    if re.match(r"^[A-Za-z]:[\\/]", text):
        drive = text[0].lower()
        rest = text[2:].replace("\\", "/")
        return f"/mnt/{drive}{rest}"
    return text.replace("\\", "/")


def shell_quote_path(path: Path | str, *, use_wsl: bool) -> str:
    return shlex.quote(wsl_path(path) if use_wsl else str(path))


def join_foreign_path(root: str, *parts: str) -> str:
    text = root.replace("\\", "/").rstrip("/")
    if text.startswith("/") and not re.match(r"^/[A-Za-z]:", text):
        return "/".join([text, *parts])
    return str(Path(root).joinpath(*parts))


def parse_wsl_distro_lines(text: str) -> list[str]:
    clean = text.replace("\x00", "")
    distros: list[str] = []
    for raw in clean.splitlines():
        line = raw.strip()
        if not line or line.startswith("wsl:"):
            continue
        if line.lower().startswith("name ") or " version" in line.lower():
            continue
        distros.append(line.lstrip("* ").strip())
    return [item for item in distros if item]


def resolve_wsl_distro(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    env_distro = os.environ.get("MAGICAL_WSL_DISTRO") or os.environ.get("SKY130_WSL_DISTRO")
    if env_distro:
        return env_distro
    if not (sys.platform.startswith("win") and shutil.which("wsl")):
        return None
    result = subprocess.run(
        ["wsl", "-l", "-q"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return None
    distros = parse_wsl_distro_lines(result.stdout or "")
    for distro in distros:
        if not distro.lower().startswith("docker-desktop"):
            return distro
    return distros[0] if distros else None


def parse_magic_port_shorts(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    shorts: list[dict[str, str]] = []
    pattern = re.compile(r'Ports\s+"([^"]+)"\s+and\s+"([^"]+)"\s+are electrically shorted', re.IGNORECASE)
    for match in pattern.finditer(text):
        shorts.append({"port_a": match.group(1), "port_b": match.group(2)})
    return shorts


def has_short(shorts: list[dict[str, str]], first: str, second: str) -> bool:
    pair = {first.lower(), second.lower()}
    return any({item["port_a"].lower(), item["port_b"].lower()} == pair for item in shorts)


def load_crossing_summary(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    elements = data.get("stripped_samples") or data.get("elements") or []
    if not isinstance(elements, list):
        elements = []
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(elements):
        if not isinstance(item, dict):
            continue
        key = element_selector_key(item)
        if key is None:
            continue
        copied = dict(item)
        copied["probe_id"] = copied.get("probe_id") or f"e{index:02d}"
        normalized.append(copied)
    strip_boxes = data.get("strip_boxes") or []
    if not isinstance(strip_boxes, list):
        strip_boxes = []
    return normalized, strip_boxes


def build_probe_sets(
    elements: list[dict[str, Any]],
    *,
    max_combination_size: int,
    run_baseline: bool,
    run_all_elements: bool,
) -> list[dict[str, Any]]:
    probes: list[dict[str, Any]] = []
    if run_baseline:
        probes.append({"name": "baseline_no_strip", "kind": "baseline", "elements": []})
    bounded_size = min(max(0, max_combination_size), len(elements))
    for size in range(1, bounded_size + 1):
        for combo in itertools.combinations(range(len(elements)), size):
            name = f"combo_{size}_" + "_".join(f"{index:02d}" for index in combo)
            probes.append(
                {
                    "name": name,
                    "kind": f"size_{size}",
                    "element_indices": list(combo),
                    "elements": [elements[index] for index in combo],
                }
            )
    if run_all_elements and len(elements) > bounded_size:
        probes.append(
            {
                "name": f"all_{len(elements)}",
                "kind": "all_elements",
                "element_indices": list(range(len(elements))),
                "elements": elements,
            }
        )
    return probes


def write_magic_tcl(*, tcl_path: Path, gds_path_for_magic: str, magic_cell: str) -> None:
    tcl_path.write_text(
        "\n".join(
            [
                'puts "SKY130_GDS_ELEMENT_SHORT_SUBSET_PROBE: reading selected-strip GDS"',
                f"gds read {{{gds_path_for_magic}}}",
                f"if {{[catch {{load {magic_cell}}} load_error]}} {{",
                f'    puts stderr "ERROR: failed to load {magic_cell}"',
                "    puts stderr $load_error",
                "    quit -noprompt",
                "}",
                "select top cell",
                "extract all",
                "ext2spice lvs",
                "ext2spice cthresh 0",
                "ext2spice rthresh 0",
                "ext2spice",
                "quit -noprompt",
                "",
            ]
        ),
        encoding="ascii",
    )


def run_magic_extract(
    *,
    repo_root: Path,
    sky130a: str,
    tcl_path: Path,
    log_path: Path,
    raw_extracted: Path,
    ext_copy: Path,
    magic_cell: str,
    wsl_distro: str | None = None,
) -> int:
    use_wsl = sys.platform.startswith("win") and shutil.which("wsl") is not None
    resolved_wsl_distro = resolve_wsl_distro(wsl_distro) if use_wsl else None
    magicrc = join_foreign_path(sky130a, "libs.tech", "magic", "sky130A.magicrc")
    if use_wsl:
        command = (
            f"cd {shell_quote_path(repo_root, use_wsl=True)} && "
            f"rm -f {shlex.quote(magic_cell + '.spice')} {shlex.quote(magic_cell + '.sp')} "
            f"{shlex.quote(magic_cell + '.ext')} && "
            f"magic -dnull -noconsole -rcfile {shell_quote_path(magicrc, use_wsl=True)} "
            f"< {shell_quote_path(tcl_path, use_wsl=True)} > {shell_quote_path(log_path, use_wsl=True)} 2>&1; "
            "status=$?; "
            f"if [ -f {shlex.quote(magic_cell + '.spice')} ]; then mv {shlex.quote(magic_cell + '.spice')} {shell_quote_path(raw_extracted, use_wsl=True)}; fi; "
            f"if [ -f {shlex.quote(magic_cell + '.sp')} ]; then mv {shlex.quote(magic_cell + '.sp')} {shell_quote_path(raw_extracted, use_wsl=True)}; fi; "
            f"if [ -f {shlex.quote(magic_cell + '.ext')} ]; then mv {shlex.quote(magic_cell + '.ext')} {shell_quote_path(ext_copy, use_wsl=True)}; fi; "
            "exit $status"
        )
        wsl_cmd = ["wsl"]
        if resolved_wsl_distro:
            wsl_cmd.extend(["-d", resolved_wsl_distro])
        wsl_cmd.extend(["bash", "-lc", command])
        result = subprocess.run(
            wsl_cmd,
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    else:
        command = (
            f"cd {shell_quote_path(repo_root, use_wsl=False)} && "
            f"rm -f {shlex.quote(magic_cell + '.spice')} {shlex.quote(magic_cell + '.sp')} "
            f"{shlex.quote(magic_cell + '.ext')} && "
            f"magic -dnull -noconsole -rcfile {shell_quote_path(magicrc, use_wsl=False)} "
            f"< {shell_quote_path(tcl_path, use_wsl=False)} > {shell_quote_path(log_path, use_wsl=False)} 2>&1; "
            "status=$?; "
            f"if [ -f {shlex.quote(magic_cell + '.spice')} ]; then mv {shlex.quote(magic_cell + '.spice')} {shell_quote_path(raw_extracted, use_wsl=False)}; fi; "
            f"if [ -f {shlex.quote(magic_cell + '.sp')} ]; then mv {shlex.quote(magic_cell + '.sp')} {shell_quote_path(raw_extracted, use_wsl=False)}; fi; "
            f"if [ -f {shlex.quote(magic_cell + '.ext')} ]; then mv {shlex.quote(magic_cell + '.ext')} {shell_quote_path(ext_copy, use_wsl=False)}; fi; "
            "exit $status"
        )
        result = subprocess.run(
            ["bash", "-lc", command],
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    wrapper_log = log_path.with_suffix(".wrapper.log")
    wrapper_log.write_text(result.stdout or "", encoding="utf-8")
    return result.returncode


def run_probe(
    *,
    probe: dict[str, Any],
    input_gds: Path,
    output_dir: Path,
    strip_boxes: list[dict[str, Any]],
    repo_root: Path,
    sky130a: str,
    top_cell: str,
    magic_cell: str,
    vdd: str,
    vss: str,
    reference_netlist: Path | None,
    compare_all: bool,
    strip_mode: str,
    wsl_distro: str | None,
) -> dict[str, Any]:
    probe_dir = output_dir / probe["name"]
    probe_dir.mkdir(parents=True, exist_ok=True)
    output_gds = probe_dir / f"{top_cell}.{probe['name']}.gds"
    selector_keys = {
        key
        for item in probe.get("elements", [])
        if (key := element_selector_key(item)) is not None
    }
    strip_summary = strip_gds(
        input_gds=input_gds,
        output_gds=output_gds,
        strip_box_items=strip_boxes,
        mode=strip_mode,
        selected_elements=selector_keys,
        max_samples=120,
    )
    strip_summary_path = probe_dir / f"{probe['name']}_strip_summary.json"
    strip_summary_path.write_text(json.dumps(strip_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    use_wsl = sys.platform.startswith("win") and shutil.which("wsl") is not None
    tcl_path = probe_dir / f"{probe['name']}_magic_extract.tcl"
    log_path = probe_dir / f"{probe['name']}_magic_extract.log"
    raw_extracted = probe_dir / f"{probe['name']}_extracted.spice"
    ext_copy = probe_dir / f"{probe['name']}.ext"
    write_magic_tcl(
        tcl_path=tcl_path,
        gds_path_for_magic=wsl_path(output_gds.resolve()) if use_wsl else str(output_gds.resolve()),
        magic_cell=magic_cell,
    )
    returncode = run_magic_extract(
        repo_root=repo_root,
        sky130a=sky130a,
        tcl_path=tcl_path,
        log_path=log_path,
        raw_extracted=raw_extracted,
        ext_copy=ext_copy,
        magic_cell=magic_cell,
        wsl_distro=wsl_distro,
    )
    shorts = parse_magic_port_shorts(log_path)
    extraction_ok = returncode == 0 and raw_extracted.is_file()
    supply_short = has_short(shorts, vdd, vss) if extraction_ok else None
    mos_summary: dict[str, Any] | None = None
    if reference_netlist is not None and raw_extracted.is_file() and (compare_all or supply_short is False):
        mos_summary = compare_mos_connectivity(
            reference_path=reference_netlist,
            candidate_path=raw_extracted,
            netgen_report=None,
            vdd=vdd,
            vss=vss,
        )
        (probe_dir / f"{probe['name']}_mos_connectivity_summary.json").write_text(
            json.dumps(mos_summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (probe_dir / f"{probe['name']}_mos_connectivity_report.md").write_text(
            render_mos_report(mos_summary),
            encoding="utf-8",
        )
    return {
        "name": probe["name"],
        "kind": probe.get("kind"),
        "element_indices": probe.get("element_indices", []),
        "elements": [
            {
                "probe_id": item.get("probe_id"),
                "layer_key": item.get("layer_key"),
                "bbox": item.get("bbox"),
                "matching_instances": item.get("matching_instances"),
            }
            for item in probe.get("elements", [])
        ],
        "strip_mode": strip_mode,
        "stripped_element_count": strip_summary["stripped_element_count"],
        "clipped_element_count": strip_summary.get("clipped_element_count", 0),
        "clipped_fragment_count": strip_summary.get("clipped_fragment_count", 0),
        "cropped_element_count": strip_summary.get("cropped_element_count", 0),
        "cropped_fragment_count": strip_summary.get("cropped_fragment_count", 0),
        "selected_element_missing_count": strip_summary["selected_element_missing_count"],
        "magic_returncode": returncode,
        "magic_extraction_ok": extraction_ok,
        "magic_port_shorts": shorts,
        "magic_supply_short_present": supply_short,
        "raw_extracted_netlist_present": raw_extracted.is_file(),
        "mos_connectivity_status": mos_summary.get("status") if mos_summary else None,
        "artifacts": {
            "probe_dir": str(probe_dir),
            "output_gds": str(output_gds),
            "strip_summary": str(strip_summary_path),
            "magic_log": str(log_path),
            "raw_extracted_netlist": str(raw_extracted),
        },
    }


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# GDS Element Short Subset Probe",
        "",
        "## Summary",
        "",
        f"- Input GDS: `{summary.get('input_gds')}`",
        f"- VDD/VSS: `{summary.get('vdd')}` / `{summary.get('vss')}`",
        f"- Strip mode: `{summary.get('strip_mode')}`",
        f"- Candidate elements: {summary.get('candidate_element_count')}",
        f"- Probes run: {summary.get('probe_count')}",
        f"- Minimal short-free element set size: `{summary.get('minimal_short_free_size')}`",
        f"- Full passive-aware LVS proven: `False`",
        "",
        "## Minimal Short-Free Sets",
        "",
    ]
    minimal = summary.get("minimal_short_free_sets", [])
    if minimal:
        lines.extend(["| probe | elements | MOS status |", "| --- | --- | --- |"])
        for item in minimal:
            elements = ", ".join(
                f"{element.get('probe_id')}:{element.get('layer_key')}:{element.get('bbox')}"
                for element in item.get("elements", [])
            )
            lines.append(f"| `{item.get('name')}` | `{elements}` | `{item.get('mos_connectivity_status')}` |")
    else:
        lines.append("- none")
    lines.extend(["", "## Probe Results", ""])
    results = summary.get("results", [])
    if results:
        lines.extend(
            [
                "| probe | stripped | clipped | cropped | supply short | MOS status |",
                "| --- | ---: | ---: | ---: | --- | --- |",
            ]
        )
        for item in results:
            lines.append(
                f"| `{item.get('name')}` | {item.get('stripped_element_count')} | "
                f"{item.get('clipped_element_count')} | "
                f"{item.get('cropped_element_count', 0)} | "
                f"`{item.get('magic_supply_short_present')}` | `{item.get('mos_connectivity_status')}` |"
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This is a localization probe only. A short-free selected-strip result means the selected GDS elements are sufficient to remove the Magic port short, but deleting geometry is not a layout repair and does not prove passive-aware LVS/PEX signoff.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    resolved_wsl_distro = resolve_wsl_distro(args.wsl_distro)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    elements, strip_boxes = load_crossing_summary(args.crossing_summary_json.resolve())
    if not elements:
        raise SystemExit("no selectable elements found in crossing summary")
    probes = build_probe_sets(
        elements,
        max_combination_size=args.max_combination_size,
        run_baseline=args.run_baseline,
        run_all_elements=args.run_all_elements,
    )
    if args.max_probes is not None:
        probes = probes[: args.max_probes]

    results: list[dict[str, Any]] = []
    stop_size: int | None = None
    for probe in probes:
        element_count = len(probe.get("elements", []))
        if stop_size is not None and element_count > stop_size:
            break
        result = run_probe(
            probe=probe,
            input_gds=args.input_gds.resolve(),
            output_dir=output_dir,
            strip_boxes=strip_boxes,
            repo_root=args.repo_root.resolve(),
            sky130a=args.sky130a,
            top_cell=args.top_cell,
            magic_cell=args.magic_cell or f"{args.top_cell}_flat",
            vdd=args.vdd,
            vss=args.vss,
            reference_netlist=args.reference_netlist.resolve() if args.reference_netlist else None,
            compare_all=args.compare_all,
            strip_mode=args.strip_mode,
            wsl_distro=resolved_wsl_distro,
        )
        results.append(result)
        if (
            args.stop_at_first_short_free_size
            and element_count > 0
            and result["magic_returncode"] == 0
            and not result["magic_supply_short_present"]
        ):
            stop_size = element_count

    short_free = [
        item
        for item in results
        if item.get("magic_extraction_ok") and item.get("magic_supply_short_present") is False
    ]
    minimal_size = min((len(item.get("elements", [])) for item in short_free), default=None)
    minimal = [
        item for item in short_free if len(item.get("elements", [])) == minimal_size
    ] if minimal_size is not None else []
    summary = {
        "schema_version": "gds_element_short_subset_probe.v1",
        "input_gds": str(args.input_gds.resolve()),
        "crossing_summary_json": str(args.crossing_summary_json.resolve()),
        "output_dir": str(output_dir),
        "top_cell": args.top_cell,
        "magic_cell": args.magic_cell or f"{args.top_cell}_flat",
        "wsl_distro": resolved_wsl_distro,
        "vdd": args.vdd,
        "vss": args.vss,
        "strip_mode": args.strip_mode,
        "candidate_element_count": len(elements),
        "probe_count": len(results),
        "minimal_short_free_size": minimal_size,
        "minimal_short_free_sets": minimal,
        "results": results,
        "full_passive_aware_lvs_proven": False,
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(summary), encoding="utf-8")
    print(f"probe_count={len(results)}")
    print(f"minimal_short_free_size={minimal_size}")
    print(f"summary_json={args.summary_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
