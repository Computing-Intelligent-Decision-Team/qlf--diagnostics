#!/usr/bin/env python3
"""Summarize a Netgen LVS report for Sky130 adapter regression logs."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Netgen LVS result.")
    parser.add_argument("--report", type=Path, required=True, help="Netgen report file.")
    parser.add_argument("--log", type=Path, help="Optional Netgen stdout/stderr log.")
    parser.add_argument("--output", type=Path, required=True, help="Markdown summary output.")
    return parser.parse_args()


def parse_counts(text: str) -> tuple[str, str, str, str]:
    devices = re.search(r"Number of devices:\s*(\d+)\s*\|Number of devices:\s*(\d+)", text)
    nets = re.search(r"Number of nets:\s*(\d+)\s*\|Number of nets:\s*(\d+)", text)
    return (
        devices.group(1) if devices else "unknown",
        devices.group(2) if devices else "unknown",
        nets.group(1) if nets else "unknown",
        nets.group(2) if nets else "unknown",
    )


def main() -> int:
    args = parse_args()
    report_text = args.report.read_text(encoding="utf-8", errors="replace")
    log_text = args.log.read_text(encoding="utf-8", errors="replace") if args.log and args.log.is_file() else ""
    combined = report_text + "\n" + log_text

    circuits_match = "Circuits match uniquely" in combined
    netlists_match = "Netlists match uniquely" in combined
    property_mismatch = bool(re.search(r"property errors|property mismatch", combined, re.IGNORECASE))
    device_mismatch = bool(re.search(r"device mismatch|devices? do not match|unmatched device", combined, re.IGNORECASE))
    net_mismatch = bool(re.search(r"net mismatch|nets? do not match|unmatched net", combined, re.IGNORECASE))
    unmatched = bool(re.search(r"unmatched", combined, re.IGNORECASE))
    status = "PASS" if circuits_match and netlists_match and not property_mismatch else "FAIL"
    c1_dev, c2_dev, c1_net, c2_net = parse_counts(combined)

    likely = []
    if property_mismatch:
        likely.append("property mismatch")
    if device_mismatch or unmatched:
        likely.append("unmatched or mismatched devices")
    if net_mismatch:
        likely.append("net mismatch")
    if not likely and status == "FAIL":
        likely.append("missing unique match markers in Netgen report")
    if not likely:
        likely.append("none detected")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# LVS Result Summary",
        "",
        f"- Netgen report: `{args.report}`",
        f"- Netgen log: `{args.log}`" if args.log else "- Netgen log: not provided",
        f"- LVS status: **{status}**",
        f"- Circuits match uniquely: {'yes' if circuits_match else 'no'}",
        f"- Netlists match uniquely: {'yes' if netlists_match else 'no'}",
        f"- Device mismatch detected: {'yes' if device_mismatch else 'no'}",
        f"- Net mismatch detected: {'yes' if net_mismatch else 'no'}",
        f"- Property mismatch detected: {'yes' if property_mismatch else 'no'}",
        f"- Unmatched devices/nets detected: {'yes' if unmatched else 'no'}",
        "",
        "## Counts",
        "",
        "| Metric | Source | Extracted |",
        "| --- | --- | --- |",
        f"| Devices | {c1_dev} | {c2_dev} |",
        f"| Nets | {c1_net} | {c2_net} |",
        "",
        "## Interpretation",
        "",
        f"- Property mismatch avoided by connectivity normalization: {'yes' if not property_mismatch else 'no'}",
        f"- Most likely failure cause: {', '.join(likely)}",
        "",
    ]
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"status={status}")
    print(f"circuits_match={'yes' if circuits_match else 'no'}")
    print(f"netlists_match={'yes' if netlists_match else 'no'}")
    print(f"property_mismatch={'yes' if property_mismatch else 'no'}")
    print(f"summary={args.output}")
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
