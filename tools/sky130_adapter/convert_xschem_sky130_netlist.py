#!/usr/bin/env python3
"""Convert a small xschem Sky130 ngspice MOS netlist to MAGICAL syntax."""

from __future__ import annotations

import argparse
import re
import shlex
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = REPO_ROOT / "examples/ota_core_sky130_try/ota_core_raw.spice"
DEFAULT_OUTPUT = REPO_ROOT / "examples/ota_core_sky130_try/ota_core_magical.sp"
DROP_PARAMS = {"ad", "as", "pd", "ps", "nrd", "nrs", "sa", "sb", "sd"}


@dataclass(frozen=True)
class MosInstance:
    name: str
    drain: str
    gate: str
    source: str
    bulk: str
    model: str
    length: str
    width: str
    nf: str
    multi: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert xschem Sky130 MOS netlist to MAGICAL format.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--global-port",
        action="append",
        default=[],
        help="Global net to append to the top subckt ports if present, e.g. --global-port GND.",
    )
    return parser.parse_args()


def strip_comment_prefix(line: str) -> str:
    stripped = line.strip()
    if stripped.startswith("**"):
        return stripped[2:].strip()
    if stripped.startswith("*"):
        return stripped[1:].strip()
    return stripped


def logical_lines(lines: list[str]) -> list[str]:
    merged: list[str] = []
    current = ""
    for raw in lines:
        line = raw.rstrip("\n")
        if line.lstrip().startswith("+"):
            current += " " + line.lstrip()[1:].strip()
            continue
        if current:
            merged.append(current)
        current = line
    if current:
        merged.append(current)
    return merged


def find_subckt(lines: list[str]) -> tuple[str, list[str]]:
    for line in lines:
        text = strip_comment_prefix(line)
        if text.lower().startswith(".subckt"):
            tokens = text.split()
            if len(tokens) < 2:
                raise ValueError(f"malformed subckt line: {line}")
            return tokens[1], tokens[2:]
    raise ValueError("could not find commented .subckt line")


def global_nets(lines: list[str]) -> set[str]:
    nets: set[str] = set()
    for line in lines:
        text = line.strip()
        if text.lower().startswith(".global"):
            nets.update(text.split()[1:])
    return nets


def parse_params(tokens: list[str]) -> dict[str, str]:
    params: dict[str, str] = {}
    for token in tokens:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        params[key.lower()] = value.strip("'\"")
    return params


def normalize_length(value: str) -> str:
    value = value.strip().lower()
    if value.endswith(("n", "u")):
        return value
    number = float(value)
    if number < 10:
        return f"{number * 1000:g}n"
    return f"{number:g}u"


def normalize_width(value: str) -> str:
    value = value.strip().lower()
    if value.endswith(("n", "u")):
        return value
    return f"{float(value):g}u"


def parse_mos(line: str) -> MosInstance | None:
    stripped = line.strip()
    if not stripped or not stripped.lower().startswith("xm"):
        return None
    tokens = shlex.split(stripped, posix=False)
    if len(tokens) < 6:
        raise ValueError(f"malformed MOS line: {line}")
    params = parse_params(tokens[6:])
    length = normalize_length(params.get("l", params.get("length", "")))
    width = normalize_width(params.get("w", params.get("width", "")))
    nf = params.get("nf", "1")
    multi = params.get("multi", params.get("mult", params.get("m", "1")))
    return MosInstance(
        name="M" + tokens[0][2:],
        drain=tokens[1],
        gate=tokens[2],
        source=tokens[3],
        bulk=tokens[4],
        model=tokens[5],
        length=length,
        width=width,
        nf=nf,
        multi=multi,
    )


def convert(input_path: Path, output_path: Path, global_ports: list[str]) -> tuple[str, list[str], list[MosInstance], set[str]]:
    physical_lines = input_path.read_text(encoding="utf-8").splitlines()
    lines = logical_lines(physical_lines)
    name, ports = find_subckt(lines)
    globals_found = global_nets(lines)
    for port in global_ports:
        if port in globals_found and port not in ports:
            ports.append(port)

    mos: list[MosInstance] = []
    for line in lines:
        inst = parse_mos(line)
        if inst is not None:
            mos.append(inst)
    if not mos:
        raise ValueError("no Sky130 XM MOS lines found")

    output_lines = [f"subckt {name} {' '.join(ports)}"]
    for inst in mos:
        output_lines.append(
            f"{inst.name} ({inst.drain} {inst.gate} {inst.source} {inst.bulk}) "
            f"{inst.model} l={inst.length} w={inst.width} multi={inst.multi} nf={inst.nf}"
        )
    output_lines.append(f"ends {name}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
    return name, ports, mos, globals_found


def main() -> int:
    args = parse_args()
    name, ports, mos, globals_found = convert(args.input.resolve(), args.output.resolve(), args.global_port)
    nmos = sum(1 for inst in mos if "nfet" in inst.model)
    pmos = sum(1 for inst in mos if "pfet" in inst.model)
    print(f"input={args.input}")
    print(f"output={args.output}")
    print(f"subckt={name}")
    print(f"ports={' '.join(ports)}")
    print(f"globals={','.join(sorted(globals_found)) if globals_found else 'none'}")
    print(f"converted_nmos={nmos}")
    print(f"converted_pmos={pmos}")
    print(f"dropped_params={','.join(sorted(DROP_PARAMS))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
