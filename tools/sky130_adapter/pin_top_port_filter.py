#!/usr/bin/env python3
"""Helpers for filtering MAGICAL ioPin entries to real top subckt ports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class PinFilterResult:
    processed: list[str]
    skipped: list[str]
    skipped_reasons: dict[str, str]


def _logical_netlist_lines(path: Path) -> list[str]:
    lines: list[str] = []
    current = ""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("*"):
            continue
        if line.startswith("+"):
            current = f"{current} {line[1:].strip()}"
            continue
        if current:
            lines.append(current)
        current = line
    if current:
        lines.append(current)
    return lines


def parse_top_ports(netlist: Path, top_cell: str) -> list[str]:
    """Return the port list from `.subckt <top_cell>` or `subckt <top_cell>`."""

    for line in _logical_netlist_lines(netlist):
        parts = line.split()
        if len(parts) < 2:
            continue
        keyword = parts[0].lower()
        if keyword not in {".subckt", "subckt"}:
            continue
        if parts[1] == top_cell:
            return parts[2:]
    raise ValueError(f"Could not find subckt {top_cell!r} in {netlist}")


def filter_named_pins(pin_names: Iterable[str], top_ports: Iterable[str]) -> PinFilterResult:
    top_port_set = set(top_ports)
    processed: list[str] = []
    skipped: list[str] = []
    skipped_reasons: dict[str, str] = {}

    for name in pin_names:
        if name in top_port_set:
            processed.append(name)
            continue
        skipped.append(name)
        skipped_reasons[name] = "not in top subckt port list"

    return PinFilterResult(processed=processed, skipped=skipped, skipped_reasons=skipped_reasons)


def filter_pin_objects(pins: list[T], top_ports: Iterable[str], name_attr: str = "name") -> tuple[list[T], PinFilterResult]:
    result = filter_named_pins((getattr(pin, name_attr) for pin in pins), top_ports)
    skipped_names = set(result.skipped)
    return [pin for pin in pins if getattr(pin, name_attr) not in skipped_names], result
