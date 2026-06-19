#!/usr/bin/env python3
"""Probe Magic extraction of a native Sky130 capacitor gencell.

This does not modify the MAGICAL layout.  It proves whether the local Sky130
PDK plus Magic can generate and extract a native capacitor device such as
``sky130_fd_pr__cap_mim_m3_1``.  The harness uses this as a hard gate before
attempting to replace MAGICAL MOM geometry with a PDK-recognized capacitor.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any


CAP_DEVICE_RE = re.compile(
    r"^\s*(?P<instance>X\S+)\s+(?P<node1>\S+)\s+(?P<node2>\S+)\s+"
    r"(?P<model>sky130_fd_pr__cap_[A-Za-z0-9_]+)\b(?P<params>.*)$",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe native Sky130 capacitor gencell extraction.")
    parser.add_argument("--sky130a", required=True, help="sky130A PDK root. May be a WSL POSIX path.")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--wsl-distro", help="WSL distro used on Windows.")
    parser.add_argument("--model", default="sky130_fd_pr__cap_mim_m3_1")
    parser.add_argument("--cell-name", default="sky130_native_cap_gencell_probe")
    parser.add_argument("--width-um", type=float, default=10.0)
    parser.add_argument("--length-um", type=float, default=10.0)
    return parser.parse_args()


def _wsl_path(path: Path | str) -> str:
    text = str(path)
    match = re.match(r"^(?P<drive>[A-Za-z]):[\\/](?P<rest>.*)$", text)
    if match:
        rest = match.group("rest").replace("\\", "/")
        return f"/mnt/{match.group('drive').lower()}/{rest}"
    return text.replace("\\", "/")


def _path_for_shell(path: Path | str, *, wsl: bool) -> str:
    return _wsl_path(path) if wsl else str(path)


def _write_magic_tcl(path: Path, *, model: str, cell_name: str, width_um: float, length_um: float) -> None:
    if not re.fullmatch(r"sky130_fd_pr__cap_[A-Za-z0-9_]+", model):
        raise ValueError(f"unsupported capacitor model name: {model}")
    proc_name = f"sky130::{model}_draw"
    defaults_name = f"sky130::{model}_defaults"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "crashbackups stop",
                f"set gname {cell_name}",
                "cellname create $gname",
                "pushstack $gname",
                f"set params [{defaults_name}]",
                f"dict set params w {width_um:.6g}",
                f"dict set params l {length_um:.6g}",
                "dict set params doports 1",
                f"{proc_name} $params",
                "property library sky130",
                f"property gencell {model}",
                "property parameters $params",
                "save $gname",
                "gds write ${gname}.gds",
                "extract all",
                "ext2spice lvs",
                "ext2spice cthresh 0",
                "ext2spice rthresh 0",
                "ext2spice ${gname}.ext",
                "quit -noprompt",
                "",
            ]
        ),
        encoding="ascii",
    )


def parse_extracted_native_caps(spice_path: Path) -> list[dict[str, Any]]:
    if not spice_path.is_file():
        return []
    devices: list[dict[str, Any]] = []
    for line in spice_path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = CAP_DEVICE_RE.match(line)
        if match:
            devices.append(
                {
                    "instance": match.group("instance"),
                    "terminals": [match.group("node1"), match.group("node2")],
                    "model": match.group("model"),
                    "params": match.group("params").strip(),
                    "line": line.strip(),
                }
            )
    return devices


def run_magic_probe(
    *,
    sky130a: str,
    out_dir: Path,
    model: str,
    cell_name: str,
    width_um: float,
    length_um: float,
    wsl_distro: str | None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    tcl = out_dir / "native_cap_gencell_probe.tcl"
    log = out_dir / "native_cap_gencell_probe.magic.log"
    _write_magic_tcl(tcl, model=model, cell_name=cell_name, width_um=width_um, length_um=length_um)
    magicrc = str(Path(sky130a) / "libs.tech" / "magic" / "sky130A.magicrc")
    use_wsl = os.name == "nt" and bool(wsl_distro) and shutil.which("wsl") is not None
    if use_wsl:
        command = " ".join(
            [
                "cd",
                shlex.quote(_path_for_shell(out_dir.resolve(), wsl=True)),
                "&&",
                "magic -dnull -noconsole -rcfile",
                shlex.quote(_path_for_shell(magicrc, wsl=True)),
                shlex.quote(tcl.name),
                ">",
                shlex.quote(log.name),
                "2>&1",
            ]
        )
        cmd = ["wsl", "-d", str(wsl_distro), "--", "bash", "-lc", command]
    else:
        cmd = [
            "magic",
            "-dnull",
            "-noconsole",
            "-rcfile",
            magicrc,
            str(tcl),
        ]
    result = subprocess.run(
        cmd,
        cwd=out_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if not use_wsl:
        log.write_text(result.stdout or "", encoding="utf-8")
    spice = out_dir / f"{cell_name}.spice"
    mag = out_dir / f"{cell_name}.mag"
    gds = out_dir / f"{cell_name}.gds"
    ext = out_dir / f"{cell_name}.ext"
    devices = parse_extracted_native_caps(spice)
    expected_devices = [device for device in devices if str(device.get("model")) == model]
    status = "pass" if result.returncode == 0 and expected_devices else "fail"
    return {
        "status": status,
        "returncode": result.returncode,
        "model": model,
        "cell_name": cell_name,
        "width_um": width_um,
        "length_um": length_um,
        "magicrc": magicrc,
        "tcl": str(tcl),
        "log": str(log),
        "spice": str(spice),
        "mag": str(mag),
        "gds": str(gds),
        "ext": str(ext),
        "native_capacitor_devices": devices,
        "recognized_native_capacitor_device_count": len(expected_devices),
    }


def write_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Sky130 Native Capacitor Gencell Probe",
        "",
        f"- Status: `{summary.get('native_cap_gencell_extraction_status')}`",
        f"- Model: `{summary.get('model')}`",
        f"- Cell: `{summary.get('cell_name')}`",
        f"- Size: `{summary.get('width_um')}um x {summary.get('length_um')}um`",
        f"- Recognized devices: `{summary.get('recognized_native_capacitor_device_count')}`",
        f"- Spice: `{summary.get('spice')}`",
        f"- GDS: `{summary.get('gds')}`",
        f"- Magic log: `{summary.get('log')}`",
        "",
        "## Extracted Devices",
        "",
    ]
    devices = summary.get("native_capacitor_devices") or []
    if devices:
        lines.extend(["| Instance | Terminals | Model | Params |", "| --- | --- | --- | --- |"])
        for device in devices:
            lines.append(
                "| {instance} | {terminals} | {model} | {params} |".format(
                    instance=device.get("instance"),
                    terminals=", ".join(device.get("terminals") or []),
                    model=device.get("model"),
                    params=device.get("params") or "-",
                )
            )
    else:
        lines.append("No native capacitor device was extracted.")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    probe = run_magic_probe(
        sky130a=args.sky130a,
        out_dir=args.out_dir,
        model=args.model,
        cell_name=args.cell_name,
        width_um=args.width_um,
        length_um=args.length_um,
        wsl_distro=args.wsl_distro,
    )
    summary = {
        "schema_version": "sky130_native_cap_gencell_probe.v1",
        **probe,
        "native_cap_gencell_extraction_status": probe["status"],
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(args.report, summary)
    print(f"native_cap_gencell_extraction_status={summary['native_cap_gencell_extraction_status']}")
    print(f"recognized_native_capacitor_device_count={summary['recognized_native_capacitor_device_count']}")
    return 0 if summary["native_cap_gencell_extraction_status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
