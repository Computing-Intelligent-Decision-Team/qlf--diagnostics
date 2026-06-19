#!/usr/bin/env python3
"""Small helpers for the generic Sky130 case pipeline."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path


PASSIVE_MODEL_NAMES = {"rppoly", "rppoly_m", "rppolywo_m", "rppolywo", "cfmom", "cfmom_2t"}
CONFIG_PATH_KEYS = ("techfile", "simple_tech_file", "lef")


@dataclass(frozen=True)
class PowerNetCheck:
    vdd_present: bool
    vss_present: bool
    missing: list[str]


def check_power_nets(config: Path, vdd: str, vss: str) -> PowerNetCheck:
    data = json.loads(config.read_text(encoding="utf-8"))
    vdd_names = data.get("vddNetNames", [])
    vss_names = data.get("vssNetNames", [])
    if not isinstance(vdd_names, list) or not isinstance(vss_names, list):
        raise ValueError("vddNetNames and vssNetNames must be JSON arrays")

    vdd_present = vdd in vdd_names
    vss_present = vss in vss_names
    missing = []
    if not vdd_present:
        missing.append(vdd)
    if not vss_present:
        missing.append(vss)
    return PowerNetCheck(vdd_present=vdd_present, vss_present=vss_present, missing=missing)


def connectivity_lvs_projection(config: Path) -> str:
    data = json.loads(config.read_text(encoding="utf-8"))
    mode = data.get("connectivityLvsProjection", "none")
    if mode in (None, "", "none"):
        return "none"
    if mode != "mos_only":
        raise ValueError(f"unsupported connectivityLvsProjection: {mode}")
    return mode


def lvs_renames(config: Path) -> list[str]:
    data = json.loads(config.read_text(encoding="utf-8"))
    raw_items = data.get("lvsNetRenames", [])
    if raw_items in (None, ""):
        return []
    if not isinstance(raw_items, list):
        raise ValueError("lvsNetRenames must be a JSON array")

    renames: list[str] = []
    for item in raw_items:
        if isinstance(item, str):
            if "=" not in item:
                raise ValueError(f"invalid lvsNetRenames item: {item!r}")
            old, new = item.split("=", 1)
        elif isinstance(item, dict):
            old = item.get("old", item.get("from"))
            new = item.get("new", item.get("to"))
        else:
            raise ValueError(f"invalid lvsNetRenames item: {item!r}")
        if not old or not new:
            raise ValueError(f"invalid lvsNetRenames item: {item!r}")
        renames.append(f"{old}={new}")
    return renames


def experimental_passive_remap(config: Path) -> bool:
    data = json.loads(config.read_text(encoding="utf-8"))
    return bool(data.get("experimentalPassiveRemap", False))


def line_has_unsupported_passive(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith("*"):
        return False
    tokens = stripped.replace("(", " ").replace(")", " ").split()
    if not tokens:
        return False
    device_prefix = tokens[0][0].lower()
    if device_prefix in {"r", "c"}:
        return True
    if device_prefix != "x":
        return False
    return any(token.split("=", 1)[0].lower() in PASSIVE_MODEL_NAMES for token in tokens[1:])


def write_mos_only_netlist(source: Path, output: Path) -> int:
    dropped = 0
    output_lines: list[str] = []
    for line in source.read_text(encoding="utf-8").splitlines(keepends=True):
        if line_has_unsupported_passive(line):
            dropped += 1
            continue
        output_lines.append(line)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(output_lines), encoding="utf-8")
    return dropped


def _resolve_config_path(config: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (config.parent / path).resolve()


def pdk_line_ending_issues(config: Path) -> list[str]:
    data = json.loads(config.read_text(encoding="utf-8"))
    issues: list[str] = []
    for key in CONFIG_PATH_KEYS:
        value = data.get(key)
        if not value:
            continue
        path = _resolve_config_path(config, str(value))
        if not path.exists():
            issues.append(f"missing\t{key}\t{path}")
            continue
        raw = path.read_bytes()
        if b"\r\n" in raw:
            issues.append(f"crlf\t{key}\t{path}")
    return issues


def _rel_from(base: Path, target: Path) -> str:
    return os.path.relpath(target.resolve(), base.resolve()).replace(os.sep, "/")


def write_mos_projection_case(
    source: Path,
    config: Path,
    case_dir: Path,
    netlist_name: str,
    config_name: str,
) -> tuple[Path, Path, int]:
    case_dir.mkdir(parents=True, exist_ok=True)
    projection_netlist = case_dir / netlist_name
    projection_config = case_dir / config_name
    dropped = write_mos_only_netlist(source, projection_netlist)

    data = json.loads(config.read_text(encoding="utf-8"))
    for key in CONFIG_PATH_KEYS:
        if key in data and data[key]:
            data[key] = _rel_from(case_dir, _resolve_config_path(config, str(data[key])))

    data.pop("connectivityLvsProjection", None)
    if "hspice_netlist" in data:
        data["hspice_netlist"] = netlist_name
    if "spectre_netlist" in data:
        data["spectre_netlist"] = netlist_name
    if "hspice_netlist" not in data and "spectre_netlist" not in data:
        data["hspice_netlist"] = netlist_name
    data["resultDir"] = "./"

    projection_config.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")
    return projection_netlist, projection_config, dropped


def subckt_ports(subckt_line: str) -> str:
    parts = subckt_line.strip().split()
    if len(parts) <= 2:
        return ""
    return " ".join(parts[2:])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Helpers for generic Sky130 case pipeline shell scripts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check-power-nets")
    check.add_argument("--config", type=Path, required=True)
    check.add_argument("--vdd", required=True)
    check.add_argument("--vss", required=True)

    projection = subparsers.add_parser("connectivity-projection")
    projection.add_argument("--config", type=Path, required=True)

    renames = subparsers.add_parser("lvs-renames")
    renames.add_argument("--config", type=Path, required=True)

    passive_remap = subparsers.add_parser("experimental-passive-remap")
    passive_remap.add_argument("--config", type=Path, required=True)

    pdk_line_endings = subparsers.add_parser("pdk-line-endings")
    pdk_line_endings.add_argument("--config", type=Path, required=True)

    mos_projection = subparsers.add_parser("write-mos-projection")
    mos_projection.add_argument("--source", type=Path, required=True)
    mos_projection.add_argument("--config", type=Path, required=True)
    mos_projection.add_argument("--case-dir", type=Path, required=True)
    mos_projection.add_argument("--netlist-name", required=True)
    mos_projection.add_argument("--config-name", required=True)

    ports = subparsers.add_parser("subckt-ports")
    ports.add_argument("--line", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "check-power-nets":
        result = check_power_nets(args.config, args.vdd, args.vss)
        print(f"vdd_present={'yes' if result.vdd_present else 'no'}")
        print(f"vss_present={'yes' if result.vss_present else 'no'}")
        print(f"missing={','.join(result.missing) if result.missing else 'none'}")
        return 0 if not result.missing else 2
    if args.command == "connectivity-projection":
        print(connectivity_lvs_projection(args.config))
        return 0
    if args.command == "lvs-renames":
        for rename in lvs_renames(args.config):
            print(rename)
        return 0
    if args.command == "experimental-passive-remap":
        print("yes" if experimental_passive_remap(args.config) else "no")
        return 0
    if args.command == "pdk-line-endings":
        issues = pdk_line_ending_issues(args.config)
        for issue in issues:
            print(issue)
        return 2 if issues else 0
    if args.command == "write-mos-projection":
        projection_netlist, projection_config, dropped = write_mos_projection_case(
            args.source,
            args.config,
            args.case_dir,
            args.netlist_name,
            args.config_name,
        )
        print(f"netlist={projection_netlist}")
        print(f"config={projection_config}")
        print(f"dropped_passives={dropped}")
        return 0
    if args.command == "subckt-ports":
        print(subckt_ports(args.line))
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
