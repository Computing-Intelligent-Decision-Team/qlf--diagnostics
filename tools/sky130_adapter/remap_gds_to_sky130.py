#!/usr/bin/env python3
"""Remap MAGICAL internal-layer GDS output to proposed Sky130 GDS layers.

This is a binary GDSII record rewriter. It only edits LAYER records and their
following DATATYPE/TEXTTYPE/NODETYPE/BOXTYPE records when a confirmed mapping
exists in sky130_gds_export_map.yaml. Unmapped and TBD layers are preserved.
"""

from __future__ import annotations

import argparse
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - depends on local environment.
    yaml = None


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_GDS = REPO_ROOT / "examples/inverter_sky130_try/inverter_core.route.gds"
DEFAULT_OUTPUT_GDS = REPO_ROOT / "examples/inverter_sky130_try/inverter_core.sky130.gds"
DEFAULT_EXPORT_MAP = REPO_ROOT / "generated/sky130PDK_trial/sky130_gds_export_map.yaml"
DEFAULT_REPORT = REPO_ROOT / "docs/sky130_adapter/gds_remap_report.md"

ELEMENT_RECORDS = {
    0x08: "BOUNDARY",
    0x09: "PATH",
    0x0C: "TEXT",
    0x15: "NODE",
    0x2D: "BOX",
}
LAYER_RECORD = 0x0D
DATATYPE_RECORDS = {
    0x0E: "DATATYPE",
    0x16: "TEXTTYPE",
    0x2A: "NODETYPE",
    0x2E: "BOXTYPE",
}
ENDEL_RECORD = 0x11


@dataclass(frozen=True)
class TargetSpec:
    sky130_layer_name: str
    sky130_gds_layer: int | None
    sky130_datatype: int | None
    status: str
    risk: str


@dataclass(frozen=True)
class RemapTarget:
    magical_layer: str
    internal_layer: int
    sky130_layer_name: str
    sky130_gds_layer: int | None
    sky130_datatype: int | None
    status: str
    risk: str
    datatype_overrides: dict[int, TargetSpec]


@dataclass(frozen=True)
class LayerAction:
    input_layer: int
    input_datatype: int
    output_layer: int
    output_datatype: int
    element_type: str
    datatype_record: str
    action: str
    mapping: str


def read_int2(payload: bytes) -> int:
    if len(payload) < 2:
        raise ValueError("GDS int2 record payload is too short")
    return struct.unpack(">h", payload[:2])[0]


def write_int2(value: int) -> bytes:
    if value < -32768 or value > 32767:
        raise ValueError(f"GDS int2 value out of range: {value}")
    return struct.pack(">h", value)


def int_or_none(value: Any) -> int | None:
    try:
        text = str(value).strip()
        if text.upper() in {"", "TBD", "UNKNOWN", "NONE"}:
            return None
        return int(text)
    except Exception:
        return None


def load_export_map(path: Path) -> dict[int, RemapTarget]:
    if yaml is None:
        raise RuntimeError("PyYAML is required to read sky130_gds_export_map.yaml.")
    with path.open("r", encoding="utf-8") as fp:
        data = yaml.safe_load(fp) or {}

    mapping: dict[int, RemapTarget] = {}
    for entry in data.get("layers", []):
        internal = entry.get("magical_internal_number")
        if not isinstance(internal, int):
            continue
        mapping[internal] = RemapTarget(
            magical_layer=str(entry.get("magical_layer", "TBD")),
            internal_layer=internal,
            sky130_layer_name=str(entry.get("sky130_layer_name", "TBD")),
            sky130_gds_layer=int_or_none(entry.get("sky130_gds_layer")),
            sky130_datatype=int_or_none(entry.get("sky130_datatype")),
            status=str(entry.get("status", "tbd")),
            risk=str(entry.get("risk", "TBD")),
            datatype_overrides=parse_datatype_overrides(entry),
        )
    return mapping


def parse_datatype_overrides(entry: dict[str, Any]) -> dict[int, TargetSpec]:
    raw = entry.get("datatype_overrides", {})
    overrides: dict[int, TargetSpec] = {}
    if isinstance(raw, dict):
        iterable = raw.items()
    elif isinstance(raw, list):
        iterable = ((item.get("input_datatype"), item) for item in raw if isinstance(item, dict))
    else:
        iterable = ()
    for raw_datatype, spec_data in iterable:
        datatype = int_or_none(raw_datatype)
        if datatype is None or not isinstance(spec_data, dict):
            continue
        overrides[datatype] = TargetSpec(
            sky130_layer_name=str(spec_data.get("sky130_layer_name", spec_data.get("name", "TBD"))),
            sky130_gds_layer=int_or_none(spec_data.get("sky130_gds_layer")),
            sky130_datatype=int_or_none(spec_data.get("sky130_datatype")),
            status=str(spec_data.get("status", entry.get("status", "tbd"))),
            risk=str(spec_data.get("risk", entry.get("risk", "TBD"))),
        )
    return overrides


def base_spec(target: RemapTarget) -> TargetSpec:
    return TargetSpec(
        sky130_layer_name=target.sky130_layer_name,
        sky130_gds_layer=target.sky130_gds_layer,
        sky130_datatype=target.sky130_datatype,
        status=target.status,
        risk=target.risk,
    )


def usable_target(spec: TargetSpec, allow_experimental: bool) -> bool:
    if spec.status == "confirmed":
        return spec.sky130_gds_layer is not None and spec.sky130_datatype is not None
    if allow_experimental and spec.status == "experimental":
        return spec.sky130_gds_layer is not None and spec.sky130_datatype is not None
    return False


def spec_for_datatype(target: RemapTarget, input_datatype: int) -> TargetSpec:
    return target.datatype_overrides.get(input_datatype, base_spec(target))


def target_for(
    layer: int,
    input_datatype: int,
    mapping: dict[int, RemapTarget],
    *,
    allow_experimental: bool = False,
    exclude_input_pairs: set[tuple[int, int]] | None = None,
) -> tuple[RemapTarget, TargetSpec] | None:
    if exclude_input_pairs and (layer, input_datatype) in exclude_input_pairs:
        return None
    target = mapping.get(layer)
    if target is None:
        return None
    spec = spec_for_datatype(target, input_datatype)
    if usable_target(spec, allow_experimental):
        return target, spec
    return None


def describe_mapping(
    layer: int,
    input_datatype: int,
    mapping: dict[int, RemapTarget],
    *,
    allow_experimental: bool = False,
    exclude_input_pairs: set[tuple[int, int]] | None = None,
) -> tuple[str, str]:
    if exclude_input_pairs and (layer, input_datatype) in exclude_input_pairs:
        target = mapping.get(layer)
        if target is None:
            return "preserved_excluded", "excluded by input-pair override"
        suffix = f"[{input_datatype}]" if input_datatype in target.datatype_overrides else ""
        return "preserved_excluded", f"{target.magical_layer}{suffix} excluded by input-pair override"
    target = mapping.get(layer)
    if target is None:
        return "preserved_unmapped", "not listed in export map"
    spec = spec_for_datatype(target, input_datatype)
    datatype_suffix = f"[{input_datatype}]" if input_datatype in target.datatype_overrides else ""
    if not usable_target(spec, allow_experimental):
        if spec.sky130_gds_layer is not None and spec.sky130_datatype is not None:
            return (
                "preserved_tbd",
                f"{target.magical_layer}{datatype_suffix} -> {spec.sky130_layer_name} "
                f"{spec.sky130_gds_layer}/{spec.sky130_datatype} ({spec.status})",
            )
        return "preserved_tbd", f"{target.magical_layer}{datatype_suffix} -> TBD"
    return (
        "remapped",
        f"{target.magical_layer}{datatype_suffix} -> {spec.sky130_layer_name} "
        f"{spec.sky130_gds_layer}/{spec.sky130_datatype}",
    )


def remap_gds(
    data: bytes,
    mapping: dict[int, RemapTarget],
    *,
    allow_experimental: bool = False,
    exclude_input_pairs: set[tuple[int, int]] | None = None,
) -> tuple[bytes, list[LayerAction]]:
    output = bytearray(data)
    actions: list[LayerAction] = []
    offset = 0
    current_element = ""
    current_layer: int | None = None
    current_layer_payload_start: int | None = None

    while offset < len(data):
        if offset + 4 > len(data):
            raise ValueError(f"Truncated GDS record header at byte {offset}")
        record_len, record_type, _data_type = struct.unpack(">HBB", data[offset : offset + 4])
        if record_len < 4:
            raise ValueError(f"Invalid GDS record length {record_len} at byte {offset}")
        payload_start = offset + 4
        payload_end = offset + record_len
        payload = data[payload_start:payload_end]

        if record_type in ELEMENT_RECORDS:
            current_element = ELEMENT_RECORDS[record_type]
            current_layer = None
            current_layer_payload_start = None
        elif record_type == LAYER_RECORD:
            current_layer = read_int2(payload)
            current_layer_payload_start = payload_start
        elif record_type in DATATYPE_RECORDS and current_layer is not None and current_layer_payload_start is not None:
            input_datatype = read_int2(payload)
            resolved = target_for(
                current_layer,
                input_datatype,
                mapping,
                allow_experimental=allow_experimental,
                exclude_input_pairs=exclude_input_pairs,
            )
            if resolved is None:
                output_layer = current_layer
                output_datatype = input_datatype
            else:
                _target, spec = resolved
                assert spec.sky130_gds_layer is not None
                assert spec.sky130_datatype is not None
                output_layer = spec.sky130_gds_layer
                output_datatype = spec.sky130_datatype
            output[current_layer_payload_start : current_layer_payload_start + 2] = write_int2(output_layer)
            output[payload_start : payload_start + 2] = write_int2(output_datatype)
            action, mapping_text = describe_mapping(
                current_layer,
                input_datatype,
                mapping,
                allow_experimental=allow_experimental,
                exclude_input_pairs=exclude_input_pairs,
            )
            actions.append(
                LayerAction(
                    input_layer=current_layer,
                    input_datatype=input_datatype,
                    output_layer=output_layer,
                    output_datatype=output_datatype,
                    element_type=current_element or "UNKNOWN",
                    datatype_record=DATATYPE_RECORDS[record_type],
                    action=action,
                    mapping=mapping_text,
                )
            )
        elif record_type == ENDEL_RECORD:
            current_element = ""
            current_layer = None
            current_layer_payload_start = None

        offset += record_len

    return bytes(output), actions


def unique_actions(actions: list[LayerAction]) -> list[LayerAction]:
    seen: set[tuple[int, int, int, int, str, str, str]] = set()
    unique: list[LayerAction] = []
    for action in actions:
        key = (
            action.input_layer,
            action.input_datatype,
            action.output_layer,
            action.output_datatype,
            action.element_type,
            action.datatype_record,
            action.action,
        )
        if key not in seen:
            seen.add(key)
            unique.append(action)
    return sorted(unique, key=lambda item: (item.input_layer, item.input_datatype, item.element_type))


def generate_report(
    input_gds: Path,
    output_gds: Path,
    export_map: Path,
    actions: list[LayerAction],
    *,
    allow_experimental: bool = False,
    exclude_input_pairs: set[tuple[int, int]] | None = None,
) -> str:
    unique = unique_actions(actions)
    remapped = [item for item in unique if item.action == "remapped"]
    preserved_tbd = [item for item in unique if item.action == "preserved_tbd"]
    preserved_unmapped = [item for item in unique if item.action == "preserved_unmapped"]
    preserved_excluded = [item for item in unique if item.action == "preserved_excluded"]

    lines = [
        "# GDS Remap Report",
        "",
        "## Summary",
        "",
        f"- Input GDS: `{input_gds}`",
        f"- Output GDS: `{output_gds}`",
        f"- Export map: `{export_map}`",
        f"- Unique input layer/datatype pairs: {len(unique)}",
        f"- Successfully remapped pairs: {len(remapped)}",
        f"- Preserved TBD pairs: {len(preserved_tbd)}",
        f"- Preserved unmapped pairs: {len(preserved_unmapped)}",
        f"- Preserved excluded pairs: {len(preserved_excluded)}",
        "",
        "The original MAGICAL GDS is not modified. This post-processing step rewrites confirmed MAGICAL internal layers to their proposed Sky130 GDS layer/datatype targets. TBD and unmapped layers are left unchanged.",
        f"Experimental datatype-specific mappings enabled: {'yes' if allow_experimental else 'no'}.",
        f"Excluded input layer/datatype pairs: {sorted(exclude_input_pairs or [])}",
        "",
        "## Layer Actions",
        "",
        "| input layer | input datatype | element type | output layer | output datatype | action | mapping |",
        "| ---: | ---: | --- | ---: | ---: | --- | --- |",
    ]

    for item in unique:
        lines.append(
            f"| {item.input_layer} | {item.input_datatype} | {item.element_type} | "
            f"{item.output_layer} | {item.output_datatype} | {item.action} | {item.mapping} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `remapped` means both GDS layer and datatype were replaced from `sky130_gds_export_map.yaml`.",
            "- Datatype-specific overrides allow one MAGICAL layer number to map different input datatypes to different Sky130 targets.",
            "- `preserved_tbd` means the MAGICAL layer exists in the export map but its Sky130 target is not confirmed.",
            "- `preserved_unmapped` means the input GDS layer is not listed in the export map.",
            "- `preserved_excluded` means the input layer/datatype matched an explicit exclusion override.",
            "- This remap is a layer/datatype translation only; it does not make the layout Sky130 DRC-clean.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Remap MAGICAL internal-layer GDS to Sky130 layer/datatype.")
    parser.add_argument("--input-gds", type=Path, default=DEFAULT_INPUT_GDS, help="MAGICAL input GDS.")
    parser.add_argument("--output-gds", type=Path, default=DEFAULT_OUTPUT_GDS, help="Remapped output GDS.")
    parser.add_argument("--export-map", type=Path, default=DEFAULT_EXPORT_MAP, help="Sky130 export map YAML.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="Markdown report output.")
    parser.add_argument(
        "--allow-experimental",
        action="store_true",
        help="Enable datatype-specific export-map entries marked status=experimental.",
    )
    parser.add_argument(
        "--exclude-input-pair",
        action="append",
        default=[],
        metavar="LAYER:DATATYPE",
        help="Preserve this input layer/datatype pair even if the export map would remap it.",
    )
    return parser.parse_args(argv)


def parse_input_pair(text: str) -> tuple[int, int]:
    if ":" in text:
        left, right = text.split(":", 1)
    elif "/" in text:
        left, right = text.split("/", 1)
    else:
        raise ValueError(f"input pair must be LAYER:DATATYPE, got {text!r}")
    return int(left.strip()), int(right.strip())


def parse_input_pairs(values: list[str]) -> set[tuple[int, int]]:
    return {parse_input_pair(value) for value in values}


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    input_gds = args.input_gds.resolve()
    output_gds = args.output_gds.resolve()
    export_map = args.export_map.resolve()
    report_path = args.report.resolve()

    try:
        if not input_gds.is_file():
            raise FileNotFoundError(input_gds)
        if not export_map.is_file():
            raise FileNotFoundError(export_map)

        mapping = load_export_map(export_map)
        exclude_input_pairs = parse_input_pairs(list(args.exclude_input_pair or []))
        remapped_data, actions = remap_gds(
            input_gds.read_bytes(),
            mapping,
            allow_experimental=bool(args.allow_experimental),
            exclude_input_pairs=exclude_input_pairs,
        )

        output_gds.parent.mkdir(parents=True, exist_ok=True)
        output_gds.write_bytes(remapped_data)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            generate_report(
                input_gds,
                output_gds,
                export_map,
                actions,
                allow_experimental=bool(args.allow_experimental),
                exclude_input_pairs=exclude_input_pairs,
            ),
            encoding="utf-8",
        )

        unique = unique_actions(actions)
        print(f"Input GDS: {input_gds}")
        print(f"Output GDS: {output_gds}")
        print(f"Report: {report_path}")
        print("Layer actions:")
        for item in unique:
            print(
                f"  {item.input_layer}/{item.input_datatype} -> "
                f"{item.output_layer}/{item.output_datatype} "
                f"({item.action}; {item.mapping})"
            )
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
