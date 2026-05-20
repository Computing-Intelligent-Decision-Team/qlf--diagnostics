#!/usr/bin/env python3
"""Ensure the Sky130 inverter MAGICAL config declares VPWR/VGND power nets."""

import argparse
import json
from pathlib import Path


DEFAULT_CONFIG = Path("examples/inverter_sky130_try/inverter.json")
DEFAULT_REPORT = Path("generated/sky130_powernet_pipeline/inverter/powernet_config_check.md")
VDD_NETS = ["VPWR"]
VSS_NETS = ["VGND"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Ensure inverter.json contains Sky130 VPWR/VGND power-net names."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help=f"MAGICAL inverter config to update (default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"report path (default: {DEFAULT_REPORT})",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="only check the config; fail if VPWR/VGND are missing or different",
    )
    return parser.parse_args()


def load_config(path):
    if not path.is_file():
        raise FileNotFoundError(f"config not found: {path}")
    with path.open() as f:
        return json.load(f)


def write_config(path, data):
    with path.open("w") as f:
        json.dump(data, f, indent=4)
        f.write("\n")


def write_report(path, config_path, before_vdd, before_vss, changed, check_only):
    path.parent.mkdir(parents=True, exist_ok=True)
    status = "changed" if changed else "already correct"
    mode = "check-only" if check_only else "ensure"
    with path.open("w") as f:
        f.write("# Sky130 Inverter Power-Net Config Check\n\n")
        f.write(f"- Mode: `{mode}`\n")
        f.write(f"- Config: `{config_path}`\n")
        f.write(f"- Status: `{status}`\n")
        f.write(f"- Previous `vddNetNames`: `{before_vdd}`\n")
        f.write(f"- Previous `vssNetNames`: `{before_vss}`\n")
        f.write(f"- Required `vddNetNames`: `{VDD_NETS}`\n")
        f.write(f"- Required `vssNetNames`: `{VSS_NETS}`\n")


def main():
    args = parse_args()
    data = load_config(args.config)

    before_vdd = data.get("vddNetNames")
    before_vss = data.get("vssNetNames")
    changed = before_vdd != VDD_NETS or before_vss != VSS_NETS

    if changed and args.check_only:
        write_report(args.report, args.config, before_vdd, before_vss, changed, True)
        raise SystemExit(
            "Sky130 inverter config is missing required VPWR/VGND power-net names"
        )

    if changed:
        data["vddNetNames"] = VDD_NETS
        data["vssNetNames"] = VSS_NETS
        write_config(args.config, data)

    write_report(args.report, args.config, before_vdd, before_vss, changed, args.check_only)

    if changed:
        print(f"updated {args.config}: vddNetNames={VDD_NETS}, vssNetNames={VSS_NETS}")
    else:
        print(f"{args.config} already has Sky130 VPWR/VGND power-net names")
    print(f"report: {args.report}")


if __name__ == "__main__":
    main()
