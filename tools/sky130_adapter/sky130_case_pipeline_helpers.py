#!/usr/bin/env python3
"""Small helpers for the generic Sky130 case pipeline."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


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
    if args.command == "subckt-ports":
        print(subckt_ports(args.line))
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
