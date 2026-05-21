#!/usr/bin/env python3
"""Collect Sky130 case pipeline summaries into one regression table."""

from __future__ import annotations

import argparse
from pathlib import Path


FIELDS = [
    "CASE_NAME",
    "TOP_CELL",
    "VDD_NET",
    "VSS_NET",
    "DRC_COUNT",
    "RAW_SUBCKT_PORTS",
    "ANONYMOUS_NODES",
    "CONNECTIVITY_LVS_MATCH",
    "NET_RENAMES_USED",
    "PEX_CAPS",
    "PEX_TOTAL_CAP_FF",
]


def load_registry(path: Path) -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_cases = False

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line_without_comment = raw_line.split("#", 1)[0].rstrip()
        if not line_without_comment.strip():
            continue
        if line_without_comment.strip() == "cases:":
            in_cases = True
            continue
        if not in_cases:
            continue
        if line_without_comment.startswith("  ") and not line_without_comment.startswith("    "):
            name = line_without_comment.strip().removesuffix(":")
            current = {"name": name}
            cases.append(current)
            continue
        if current is not None and line_without_comment.startswith("    "):
            item = line_without_comment.strip()
            if ":" not in item:
                continue
            key, value = item.split(":", 1)
            current[key.strip()] = value.strip().strip("'\"")

    return cases


def parse_case_summary(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    if not path.is_file():
        return fields
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line.startswith("|") or line.startswith("| ---"):
            continue
        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) != 2 or parts[0] == "Field":
            continue
        fields[parts[0]] = parts[1]
    return fields


def case_passed(row: dict[str, str]) -> bool:
    return row.get("DRC_COUNT") == "0" and row.get("CONNECTIVITY_LVS_MATCH") == "yes"


def render_regression_summary(rows: list[dict[str, str]]) -> str:
    lines = [
        "# Sky130 Case Regression Summary",
        "",
        "| Case | Status | Top cell | VDD | VSS | DRC | LVS | Anonymous nodes | Net renames | PEX caps | PEX total |",
        "| --- | --- | --- | --- | --- | ---: | --- | --- | --- | ---: | ---: |",
    ]
    for row in rows:
        status = "PASS" if case_passed(row) else "FAIL"
        lines.append(
            "| {case} | {status} | {top} | {vdd} | {vss} | {drc} | {lvs} | {anon} | {renames} | {caps} | {total} |".format(
                case=row.get("CASE_NAME", ""),
                status=status,
                top=row.get("TOP_CELL", ""),
                vdd=row.get("VDD_NET", ""),
                vss=row.get("VSS_NET", ""),
                drc=row.get("DRC_COUNT", ""),
                lvs=row.get("CONNECTIVITY_LVS_MATCH", ""),
                anon=row.get("ANONYMOUS_NODES", ""),
                renames=row.get("NET_RENAMES_USED", ""),
                caps=row.get("PEX_CAPS", ""),
                total=row.get("PEX_TOTAL_CAP_FF", ""),
            )
        )

    lines.extend(
        [
            "",
            "## Raw Subckt Ports",
            "",
            "| Case | Ports |",
            "| --- | --- |",
        ]
    )
    for row in rows:
        lines.append(f"| {row.get('CASE_NAME', '')} | `{row.get('RAW_SUBCKT_PORTS', '')}` |")
    lines.append("")
    return "\n".join(lines)


def collect(registry: Path, output: Path) -> list[dict[str, str]]:
    cases = load_registry(registry)
    rows: list[dict[str, str]] = []
    for case in cases:
        out_dir = Path(case["out_dir"])
        if not out_dir.is_absolute():
            out_dir = registry.resolve().parents[2] / out_dir
        row = {field: "" for field in FIELDS}
        row.update(parse_case_summary(out_dir / "summary.md"))
        row.setdefault("CASE_NAME", case["name"])
        rows.append(row)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_regression_summary(rows), encoding="utf-8")
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Sky130 case regression summaries.")
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = collect(args.registry, args.output)
    failed = [row.get("CASE_NAME", "") for row in rows if not case_passed(row)]
    print(f"cases={len(rows)}")
    print(f"failed={','.join(failed) if failed else 'none'}")
    print(f"summary={args.output}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
