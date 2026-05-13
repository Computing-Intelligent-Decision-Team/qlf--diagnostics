#!/usr/bin/env python3
"""Convert the xschem sky130 inverter netlist into MAGICAL spectre-like input."""

from pathlib import Path
import re
import sys


INPUT_FILE = Path("inverter_raw.spice")
OUTPUT_FILE = Path("inverter_sky130_name_test.sp")

NFET = "sky130_fd_pr__nfet_01v8"
PFET = "sky130_fd_pr__pfet_01v8"
SUPPORTED_MOS = {NFET, PFET}
OUTPUT_PORTS = ["A", "Y", "VPWR", "VGND"]

DROP_PARAMS = {
    "ad", "as", "pd", "ps", "nrd", "nrs", "sa", "sb", "sc", "sd",
    "area", "pj", "perim",
}


def fail(message):
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def parse_value_with_unit(value):
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))(?:([a-zA-Z]+))?", value)
    if not match:
        raise ValueError(f"unsupported numeric value: {value}")
    number = float(match.group(1))
    unit = (match.group(2) or "u").lower()
    return number, unit


def to_nm(value):
    number, unit = parse_value_with_unit(value)
    scale = {
        "m": 1_000_000.0,
        "u": 1_000.0,
        "n": 1.0,
        "p": 0.001,
    }
    if unit not in scale:
        raise ValueError(f"unsupported length unit: {unit}")
    nm = number * scale[unit]
    if abs(nm - round(nm)) < 1e-9:
        return f"{int(round(nm))}n"
    return f"{nm:g}n"


def to_um(value, width_scale=1.0):
    number, unit = parse_value_with_unit(value)
    scale = {
        "m": 1_000_000.0,
        "u": 1.0,
        "n": 0.001,
        "p": 0.000001,
    }
    if unit not in scale:
        raise ValueError(f"unsupported width unit: {unit}")
    um = number * scale[unit] * width_scale
    if abs(um - round(um)) < 1e-9:
        return f"{int(round(um))}u"
    return f"{um:g}u"


def parse_params(tokens):
    params = {}
    for token in tokens:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        key = key.lower()
        if key in DROP_PARAMS:
            continue
        params[key] = value
    return params


def find_subckt_name(lines):
    for line in lines:
        stripped = line.strip()
        if not stripped.lower().startswith("**.subckt"):
            continue
        tokens = stripped[2:].split()
        if len(tokens) >= 2 and tokens[0].lower() == ".subckt":
            return tokens[1]
    raise ValueError("could not find commented xschem .subckt line like '**.subckt inverter_core ...'")


def convert_mos_line(line, index):
    tokens = line.split()
    if len(tokens) < 6:
        raise ValueError(f"malformed MOS line: {line}")

    name = tokens[0]
    if not name.upper().startswith("XM"):
        raise ValueError(f"not an xschem MOS instance: {line}")

    drain, gate, source, bulk = tokens[1:5]
    model = tokens[5]
    if model not in SUPPORTED_MOS:
        raise ValueError(f"unsupported MOS model {model}")

    params = parse_params(tokens[6:])
    if "l" not in params:
        raise ValueError(f"missing L parameter on {name}")
    if "w" not in params:
        raise ValueError(f"missing W parameter on {name}")

    width_scale = 2.0 if model == PFET else 1.0
    length = to_nm(params["l"])
    width = to_um(params["w"], width_scale=width_scale)
    nf = params.get("nf", "1")
    multi = params.get("multi", params.get("mult", "1"))

    return f"M{index} ({drain} {gate} {source} {bulk}) {model} l={length} w={width} multi={multi} nf={nf}"


def main():
    if not INPUT_FILE.exists():
        return fail(f"input file not found: {INPUT_FILE}")

    lines = INPUT_FILE.read_text().splitlines()
    try:
        subckt_name = find_subckt_name(lines)
    except ValueError as exc:
        return fail(str(exc))

    mos_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("*"):
            continue
        tokens = stripped.split()
        if len(tokens) >= 6 and tokens[0].upper().startswith("XM") and tokens[5] in SUPPORTED_MOS:
            mos_lines.append(stripped)

    if not mos_lines:
        return fail(f"no supported sky130 MOS lines found in {INPUT_FILE}")

    converted = []
    nmos_count = 0
    pmos_count = 0
    try:
        for index, line in enumerate(mos_lines):
            model = line.split()[5]
            if model == NFET:
                nmos_count += 1
            elif model == PFET:
                pmos_count += 1
            converted.append(convert_mos_line(line, index))
    except ValueError as exc:
        return fail(str(exc))

    output = [
        f"subckt {subckt_name} {' '.join(OUTPUT_PORTS)}",
        *converted,
        f"ends {subckt_name}",
        "",
    ]
    OUTPUT_FILE.write_text("\n".join(output))

    print(f"Input:  {INPUT_FILE}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Converted NMOS: {nmos_count}")
    print(f"Converted PMOS: {pmos_count}")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
