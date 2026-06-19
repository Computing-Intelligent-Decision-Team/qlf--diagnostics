#!/usr/bin/env python3
"""Analyze whether extracted passive fragments can be abstracted to source devices."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from prepare_lvs_netlists import parse_extracted_physical_passives, parse_source_passives


PORT_SHORT_RE = re.compile(
    r"Warning:\s*Ports\s+\"([^\"]+)\"\s+and\s+\"([^\"]+)\"\s+are electrically shorted",
    re.IGNORECASE,
)
UNIQUE_NET_RE = re.compile(r"^(?P<base>.+)_uq\d+$", re.IGNORECASE)
QUOTED_NODE_RE = re.compile(r'"([^"]+)"')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze passive abstraction readiness.")
    parser.add_argument("--source-netlist", type=Path, required=True)
    parser.add_argument("--extracted-netlist", type=Path, required=True)
    parser.add_argument("--magic-log", type=Path)
    parser.add_argument("--ext-file", type=Path, help="Optional Magic .ext file for coordinate-based device ownership.")
    parser.add_argument("--identity-json", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument(
        "--candidate-netlist",
        type=Path,
        help="Optional SPICE fragment with diagnostic source-level passive abstraction candidates.",
    )
    parser.add_argument(
        "--packet-json",
        type=Path,
        help="Optional structured passive abstraction packet for downstream harness/LVS rule probes.",
    )
    return parser.parse_args()


def parse_magic_port_shorts(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.is_file():
        return []
    shorts: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for match in PORT_SHORT_RE.finditer(path.read_text(encoding="utf-8", errors="replace")):
        first, second = match.group(1), match.group(2)
        key = tuple(sorted((first, second)))
        if key in seen:
            continue
        seen.add(key)
        shorts.append({"port_a": first, "port_b": second})
    return shorts


def parse_extracted_capacitors(lines: list[str]) -> list[dict[str, Any]]:
    capacitors: list[dict[str, Any]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("*") or stripped.startswith("."):
            continue
        tokens = stripped.replace("(", " ").replace(")", " ").split()
        if len(tokens) < 4 or not tokens[0].lower().startswith("c"):
            continue
        capacitors.append(
            {
                "instance": tokens[0],
                "terminals": [tokens[1], tokens[2]],
                "value": tokens[3],
            }
        )
    return capacitors


def parse_capacitance_ff(value: str) -> float | None:
    text = value.strip().lower()
    match = re.match(r"^([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[-+]?\d+)?)([fpnumk]?)$", text)
    if not match:
        return None
    number = float(match.group(1))
    suffix = match.group(2)
    scale = {
        "": 1.0e15,
        "f": 1.0,
        "p": 1.0e3,
        "n": 1.0e6,
        "u": 1.0e9,
        "m": 1.0e12,
        "k": 1.0e18,
    }.get(suffix)
    return None if scale is None else number * scale


def parse_ext_devres(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.is_file():
        return []
    devices: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped.startswith("device devres "):
            continue
        tokens = stripped.split()
        if len(tokens) < 6:
            continue
        try:
            x = int(tokens[3])
            y = int(tokens[4])
        except ValueError:
            continue
        devices.append(
            {
                "model": tokens[2],
                "ext_x": x,
                "ext_y": y,
                "gds_x": x * 5,
                "gds_y": y * 5,
                "line": stripped,
            }
        )
    return devices


def parse_ext_passive_rsubckts(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.is_file():
        return []
    devices: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped.startswith("device rsubckt "):
            continue
        tokens = stripped.split()
        if len(tokens) < 6:
            continue
        model = tokens[2]
        if "res_" not in model.lower() and "cap" not in model.lower():
            continue
        try:
            x = int(tokens[3])
            y = int(tokens[4])
        except ValueError:
            continue
        devices.append(
            {
                "model": model,
                "ext_x": x,
                "ext_y": y,
                "gds_x": x * 5,
                "gds_y": y * 5,
                "line": stripped,
            }
        )
    return devices


def identity_terminal_boxes(identity: dict[str, Any]) -> list[dict[str, Any]]:
    boxes: list[dict[str, Any]] = []
    for instance in identity.get("instances", []):
        source_instance = str(instance.get("source_instance", ""))
        for terminal in instance.get("terminals", []):
            box = terminal.get("global_box")
            if not box:
                continue
            x1, y1, x2, y2 = [int(value) for value in box]
            xlo, xhi = sorted((x1, x2))
            ylo, yhi = sorted((y1, y2))
            boxes.append(
                {
                    "source_instance": source_instance,
                    "terminal": str(terminal.get("terminal", "")),
                    "box": [xlo, ylo, xhi, yhi],
                    "center": [(xlo + xhi) / 2.0, (ylo + yhi) / 2.0],
                }
            )
    return boxes


def annotate_ext_devres_ownership(
    devres: list[dict[str, Any]],
    identity: dict[str, Any],
) -> list[dict[str, Any]]:
    boxes = identity_terminal_boxes(identity)
    annotated: list[dict[str, Any]] = []
    for device in devres:
        x = int(device["gds_x"])
        y = int(device["gds_y"])
        inside = [
            box
            for box in boxes
            if box["box"][0] <= x <= box["box"][2] and box["box"][1] <= y <= box["box"][3]
        ]
        nearest = None
        if boxes:
            nearest = min(
                boxes,
                key=lambda box: (float(box["center"][0]) - x) ** 2 + (float(box["center"][1]) - y) ** 2,
            )
        item = dict(device)
        if inside:
            item["ownership_status"] = "inside_source_passive_pin_box"
            item["matched_source_instance"] = inside[0]["source_instance"]
            item["matched_source_terminal"] = inside[0]["terminal"]
            item["matched_box"] = inside[0]["box"]
        elif nearest is not None:
            item["ownership_status"] = "nearest_source_passive_pin_box"
            item["matched_source_instance"] = nearest["source_instance"]
            item["matched_source_terminal"] = nearest["terminal"]
            item["matched_box"] = nearest["box"]
            item["nearest_distance_sq"] = (
                (float(nearest["center"][0]) - x) ** 2 + (float(nearest["center"][1]) - y) ** 2
            )
        else:
            item["ownership_status"] = "no_identity_boxes"
            item["matched_source_instance"] = None
            item["matched_source_terminal"] = None
            item["matched_box"] = None
        annotated.append(item)
    return annotated


def is_resistor_model(model: str) -> bool:
    lowered = model.lower()
    return lowered.startswith("r") or "res_" in lowered or "__res_" in lowered


def resistor_conductive_terminals(device: dict[str, Any]) -> list[str]:
    terminals = [str(terminal) for terminal in device.get("terminals", [])]
    model = str(device.get("model", "")).lower()
    if model in {"sky130_fd_pr__res_xhigh_po", "sky130_fd_pr__res_high_po"} and len(terminals) >= 3:
        return terminals[:2]
    if len(terminals) >= 2:
        return terminals[:2]
    return terminals


def source_passive_kind(model: str) -> str:
    lowered = model.lower()
    if lowered.startswith("cfmom"):
        return "capacitor"
    if lowered.startswith("rppoly") or lowered.startswith("res"):
        return "resistor"
    return "unknown"


def electrical_terminals(device: Any) -> tuple[list[str], list[str]]:
    terminals = list(device.terminals)
    if source_passive_kind(device.model) == "resistor" and len(terminals) >= 3:
        return terminals[:2], terminals[2:]
    return terminals, []


def short_aliases(shorts: list[dict[str, str]]) -> dict[str, set[str]]:
    aliases: dict[str, set[str]] = {}
    for item in shorts:
        first = str(item.get("port_a", ""))
        second = str(item.get("port_b", ""))
        aliases.setdefault(first, set()).add(second)
        aliases.setdefault(second, set()).add(first)
    return aliases


def terminal_roles(terminal: str, source_terminals: set[str], aliases: dict[str, set[str]]) -> list[dict[str, str]]:
    roles: list[dict[str, str]] = []
    if terminal in source_terminals:
        roles.append({"role": "exact", "source_terminal": terminal, "extracted_terminal": terminal})
    match = UNIQUE_NET_RE.match(terminal)
    if match:
        base = match.group("base")
        if base in source_terminals:
            roles.append({"role": "split", "source_terminal": base, "extracted_terminal": terminal})
    for source_terminal, equivalents in aliases.items():
        if source_terminal in source_terminals and terminal in equivalents:
            roles.append(
                {
                    "role": "short_equivalent",
                    "source_terminal": source_terminal,
                    "extracted_terminal": terminal,
                }
            )
    return roles


def mapped_source_terminal(terminal: str, source_terminals: set[str], aliases: dict[str, set[str]]) -> str | None:
    roles = terminal_roles(terminal, source_terminals, aliases)
    if not roles:
        return None
    exact = [role for role in roles if role["role"] == "exact"]
    if exact:
        return exact[0]["source_terminal"]
    return roles[0]["source_terminal"]


def node_matches_source_terminal(node: str, source_terminal: str, source_terminals: set[str], aliases: dict[str, set[str]]) -> bool:
    return mapped_source_terminal(node, source_terminals, aliases) == source_terminal


def device_touches_source(
    terminals: list[str],
    source_terminals: set[str],
    aliases: dict[str, set[str]],
) -> tuple[set[str], list[dict[str, str]]]:
    covered: set[str] = set()
    roles: list[dict[str, str]] = []
    for terminal in terminals:
        for role in terminal_roles(terminal, source_terminals, aliases):
            covered.add(role["source_terminal"])
            roles.append(role)
    return covered, roles


def has_expected_two_terminal_device(
    *,
    expected_kind: str,
    expected_pair: list[str],
    source_terminals: set[str],
    aliases: dict[str, set[str]],
    resistors: list[dict[str, Any]],
    capacitors: list[dict[str, Any]],
) -> tuple[bool, list[dict[str, Any]]]:
    if len(expected_pair) < 2:
        return False, []
    expected = set(expected_pair[:2])
    pool = resistors if expected_kind == "resistor" else capacitors if expected_kind == "capacitor" else []
    matches: list[dict[str, Any]] = []
    for device in pool:
        mapped = {
            mapped_source_terminal(str(terminal), source_terminals, aliases)
            for terminal in device.get("terminals", [])
        }
        mapped.discard(None)
        if mapped == expected:
            matches.append(device)
    return bool(matches), matches


def find_segmented_resistor_chain(
    *,
    expected_pair: list[str],
    source_terminals: set[str],
    aliases: dict[str, set[str]],
    resistors: list[dict[str, Any]],
) -> dict[str, Any]:
    if len(expected_pair) < 2:
        return {"present": False, "reason": "missing_expected_pair"}
    start_source, end_source = expected_pair[:2]
    graph: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for resistor in resistors:
        if not is_resistor_model(str(resistor.get("model", ""))):
            continue
        conductive = resistor_conductive_terminals(resistor)
        if len(conductive) < 2 or conductive[0] == conductive[1]:
            continue
        left, right = conductive[:2]
        graph.setdefault(left, []).append((right, resistor))
        graph.setdefault(right, []).append((left, resistor))

    start_nets = sorted(
        net
        for net in graph
        if mapped_source_terminal(net, source_terminals, aliases) == start_source
    )
    end_nets = {
        net
        for net in graph
        if mapped_source_terminal(net, source_terminals, aliases) == end_source
    }
    if not start_nets or not end_nets:
        return {
            "present": False,
            "reason": "missing_source_terminal_on_resistor_graph",
            "start_source_terminal": start_source,
            "end_source_terminal": end_source,
            "start_candidate_nets": start_nets,
            "end_candidate_nets": sorted(end_nets),
        }

    for start_net in start_nets:
        queue: list[tuple[str, list[dict[str, Any]], list[str]]] = [(start_net, [], [start_net])]
        visited = {start_net}
        while queue:
            net, path_devices, path_nets = queue.pop(0)
            if net in end_nets:
                return {
                    "present": True,
                    "start_source_terminal": start_source,
                    "end_source_terminal": end_source,
                    "start_net": start_net,
                    "end_net": net,
                    "device_count": len(path_devices),
                    "device_instances": [str(device.get("instance", "")) for device in path_devices],
                    "device_models": [str(device.get("model", "")) for device in path_devices],
                    "net_sequence": path_nets,
                    "devices": path_devices,
                }
            for neighbor, device in graph.get(net, []):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                queue.append((neighbor, path_devices + [device], path_nets + [neighbor]))
    return {
        "present": False,
        "reason": "no_graph_path_between_expected_terminals",
        "start_source_terminal": start_source,
        "end_source_terminal": end_source,
        "start_candidate_nets": start_nets,
        "end_candidate_nets": sorted(end_nets),
    }


def body_terminal_resolution(
    body_terminals: list[str],
    terminals: set[str],
    aliases: dict[str, set[str]],
) -> dict[str, Any]:
    resolved: list[dict[str, str]] = []
    unresolved: list[str] = []
    for terminal in body_terminals:
        equivalents = sorted(aliases.get(terminal, set()))
        if terminal in terminals:
            resolved.append({"source_terminal": terminal, "resolution": "exact", "extracted_terminal": terminal})
        elif equivalents:
            resolved.append(
                {
                    "source_terminal": terminal,
                    "resolution": "magic_port_short",
                    "extracted_terminal": equivalents[0],
                }
            )
        else:
            unresolved.append(terminal)
    return {
        "resolved": resolved,
        "unresolved": unresolved,
    }


def ext_device_nodes(device: dict[str, Any]) -> list[str]:
    line = str(device.get("line", ""))
    nodes = QUOTED_NODE_RE.findall(line)
    seen: set[str] = set()
    unique_nodes: list[str] = []
    for node in nodes:
        if node in seen:
            continue
        seen.add(node)
        unique_nodes.append(node)
    return unique_nodes


def capacitor_plate_coupling_evidence(
    *,
    electrical: list[str],
    terminals: set[str],
    aliases: dict[str, set[str]],
    coordinate_matched_devres: list[dict[str, Any]],
    capacitors: list[dict[str, Any]],
) -> dict[str, Any]:
    if len(electrical) < 2:
        return {"present": False, "reason": "missing_expected_pair"}
    first, second = electrical[:2]
    plate_nodes: dict[str, set[str]] = {first: {first}, second: {second}}
    for capacitor in capacitors:
        for node in capacitor.get("terminals", []):
            for terminal in (first, second):
                if node_matches_source_terminal(str(node), terminal, terminals, aliases):
                    plate_nodes[terminal].add(str(node))
    for device in coordinate_matched_devres:
        matched = str(device.get("matched_source_terminal", ""))
        if matched not in plate_nodes:
            continue
        for node in ext_device_nodes(device):
            if node.endswith("#") or node_matches_source_terminal(node, matched, terminals, aliases):
                plate_nodes[matched].add(node)

    first_nodes = plate_nodes[first]
    second_nodes = plate_nodes[second]
    coupling_caps: list[dict[str, Any]] = []
    total_ff = 0.0
    for capacitor in capacitors:
        cap_terms = [str(term) for term in capacitor.get("terminals", [])]
        if len(cap_terms) < 2:
            continue
        left, right = cap_terms[:2]
        crosses = (left in first_nodes and right in second_nodes) or (left in second_nodes and right in first_nodes)
        if not crosses:
            continue
        value_ff = parse_capacitance_ff(str(capacitor.get("value", "")))
        item = dict(capacitor)
        item["value_ff"] = value_ff
        coupling_caps.append(item)
        if value_ff is not None:
            total_ff += abs(value_ff)
    return {
        "present": bool(coupling_caps) and total_ff > 0.0,
        "expected_terminals": [first, second],
        "plate_node_counts": {terminal: len(nodes) for terminal, nodes in plate_nodes.items()},
        "plate_nodes": {terminal: sorted(nodes) for terminal, nodes in plate_nodes.items()},
        "coupling_capacitor_count": len(coupling_caps),
        "coupling_capacitance_ff": total_ff,
        "coupling_capacitors": coupling_caps[:24],
        "truncated_coupling_capacitor_count": max(0, len(coupling_caps) - 24),
    }


def build_source_level_abstraction_candidate(
    *,
    source_device: Any,
    expected_kind: str,
    electrical: list[str],
    body: list[str],
    terminals: set[str],
    aliases: dict[str, set[str]],
    segmented_resistor_chain: dict[str, Any],
    capacitor_plate_coupling: dict[str, Any],
    missing_identity: dict[str, list[str]],
) -> dict[str, Any] | None:
    source_equivalent_line = " ".join(
        [source_device.instance] + list(source_device.terminals) + [source_device.model]
    )
    if expected_kind == "resistor" and segmented_resistor_chain.get("present"):
        body_resolution = body_terminal_resolution(body, terminals, aliases)
        unresolved: list[str] = []
        if body_resolution["unresolved"]:
            unresolved.append("unresolved_body_terminals:" + ",".join(body_resolution["unresolved"]))
        missing_body_geometry = sorted(set(body).intersection(missing_identity.get(source_device.instance, [])))
        if missing_body_geometry:
            unresolved.append("body_or_substrate_pin_has_no_magical_geometry:" + ",".join(missing_body_geometry))
        candidate_status = "candidate_requires_review" if unresolved else "candidate"
        return {
            "candidate_type": "segmented_resistor_chain_source_equivalent",
            "candidate_status": candidate_status,
            "source_instance": source_device.instance,
            "source_model": source_device.model,
            "source_terminals": list(source_device.terminals),
            "electrical_terminals": electrical,
            "body_or_reference_terminals": body,
            "body_terminal_resolution": body_resolution,
            "source_equivalent_spice": source_equivalent_line,
            "chain": segmented_resistor_chain,
            "unresolved": unresolved,
        }
    if expected_kind == "capacitor" and capacitor_plate_coupling.get("present"):
        return {
            "candidate_type": "plate_coupling_capacitor_source_equivalent",
            "candidate_status": "candidate_requires_review",
            "source_instance": source_device.instance,
            "source_model": source_device.model,
            "source_terminals": list(source_device.terminals),
            "electrical_terminals": electrical,
            "body_or_reference_terminals": body,
            "source_equivalent_spice": source_equivalent_line,
            "coupling_capacitance_ff": capacitor_plate_coupling.get("coupling_capacitance_ff"),
            "coupling_capacitor_count": capacitor_plate_coupling.get("coupling_capacitor_count"),
            "plate_node_counts": capacitor_plate_coupling.get("plate_node_counts"),
            "unresolved": ["source_capacitor_requires_plate_coupling_abstraction"],
        }
    return None


def terminals_covered_by_devices(
    devices: list[dict[str, Any]],
    source_terminals: set[str],
    aliases: dict[str, set[str]],
) -> set[str]:
    covered: set[str] = set()
    for device in devices:
        touched, _roles = device_touches_source(device.get("terminals", []), source_terminals, aliases)
        covered.update(touched)
    return covered


def identity_missing_terminals(identity: dict[str, Any]) -> dict[str, list[str]]:
    missing: dict[str, list[str]] = {}
    for instance in identity.get("instances", []):
        name = str(instance.get("source_instance", ""))
        terms = [
            str(term.get("terminal"))
            for term in instance.get("terminals", [])
            if term.get("match_status") == "no_pin_geometry"
        ]
        if name and terms:
            missing[name] = terms
    return missing


def analyze(
    *,
    source_lines: list[str],
    extracted_lines: list[str],
    magic_shorts: list[dict[str, str]],
    identity: dict[str, Any] | None = None,
    ext_devres: list[dict[str, Any]] | None = None,
    ext_passive_rsubckts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    source_devices = parse_source_passives(source_lines)
    extracted_resistors = [
        {
            "instance": device.instance,
            "model": device.model,
            "terminals": list(device.terminals),
        }
        for device in parse_extracted_physical_passives(extracted_lines)
    ]
    extracted_capacitors = parse_extracted_capacitors(extracted_lines)
    source_terminals = {terminal for device in source_devices for terminal in device.terminals}
    aliases = short_aliases(magic_shorts)
    identity_data = identity or {}
    missing_identity = identity_missing_terminals(identity_data)
    owned_devres = annotate_ext_devres_ownership(ext_devres or [], identity_data)
    owned_passive_rsubckts = annotate_ext_devres_ownership(ext_passive_rsubckts or [], identity_data)
    analyses: list[dict[str, Any]] = []
    abstraction_candidates: list[dict[str, Any]] = []
    ready_count = 0
    partial_count = 0
    blocker_count = 0
    segmented_chain_count = 0
    capacitor_plate_coupling_count = 0

    for source_device in source_devices:
        expected_kind = source_passive_kind(source_device.model)
        electrical, body = electrical_terminals(source_device)
        terminals = set(source_device.terminals)
        covered: set[str] = set()
        touching_devices: list[dict[str, Any]] = []
        for extracted in extracted_resistors:
            touched, roles = device_touches_source(extracted["terminals"], terminals, aliases)
            if not touched:
                continue
            covered.update(touched)
            touching_devices.append({**extracted, "kind": "resistor", "roles": roles})
        touching_caps: list[dict[str, Any]] = []
        for extracted in extracted_capacitors:
            touched, roles = device_touches_source(extracted["terminals"], terminals, aliases)
            if not touched:
                continue
            covered.update(touched)
            touching_caps.append({**extracted, "kind": "capacitor", "roles": roles})

        has_direct, direct_matches = has_expected_two_terminal_device(
            expected_kind=expected_kind,
            expected_pair=electrical,
            source_terminals=terminals,
            aliases=aliases,
            resistors=extracted_resistors,
            capacitors=extracted_capacitors,
        )
        segmented_resistor_chain = (
            find_segmented_resistor_chain(
                expected_pair=electrical,
                source_terminals=terminals,
                aliases=aliases,
                resistors=extracted_resistors,
            )
            if expected_kind == "resistor"
            else {"present": False, "reason": "not_resistor"}
        )
        if expected_kind == "resistor" and segmented_resistor_chain.get("present"):
            segmented_chain_count += 1
        expected_kind_devices = (
            extracted_resistors
            if expected_kind == "resistor"
            else extracted_capacitors
            if expected_kind == "capacitor"
            else []
        )
        expected_kind_covered = terminals_covered_by_devices(expected_kind_devices, terminals, aliases)
        coordinate_matched_devres = [
            devres_device
            for devres_device in owned_devres
            if devres_device.get("ownership_status") == "inside_source_passive_pin_box"
            and devres_device.get("matched_source_instance") == source_device.instance
        ]
        coordinate_matched_ext_resistors = [
            ext_device
            for ext_device in owned_passive_rsubckts
            if ext_device.get("matched_source_instance") == source_device.instance
            and is_resistor_model(str(ext_device.get("model", "")))
        ]
        capacitor_plate_coupling = (
            capacitor_plate_coupling_evidence(
                electrical=electrical,
                terminals=terminals,
                aliases=aliases,
                coordinate_matched_devres=coordinate_matched_devres,
                capacitors=extracted_capacitors,
            )
            if expected_kind == "capacitor"
            else {"present": False, "reason": "not_capacitor"}
        )
        if expected_kind == "capacitor" and capacitor_plate_coupling.get("present"):
            capacitor_plate_coupling_count += 1
        abstraction_candidate = build_source_level_abstraction_candidate(
            source_device=source_device,
            expected_kind=expected_kind,
            electrical=electrical,
            body=body,
            terminals=terminals,
            aliases=aliases,
            segmented_resistor_chain=segmented_resistor_chain,
            capacitor_plate_coupling=capacitor_plate_coupling,
            missing_identity=missing_identity,
        )
        if abstraction_candidate is not None:
            abstraction_candidates.append(abstraction_candidate)
        missing = sorted(terminals - covered)
        missing_from_expected_kind = sorted(terminals - expected_kind_covered)
        blockers: list[str] = []
        if missing:
            blockers.append("missing_source_terminals:" + ",".join(missing))
        if missing_from_expected_kind:
            blockers.append("missing_expected_kind_terminals:" + ",".join(missing_from_expected_kind))
        if body and set(body).intersection(missing_identity.get(source_device.instance, [])):
            blockers.append("body_or_substrate_pin_has_no_magical_geometry:" + ",".join(body))
        if not has_direct:
            if expected_kind == "resistor" and segmented_resistor_chain.get("present"):
                blockers.append("source_resistor_requires_segmented_chain_abstraction")
            elif expected_kind == "capacitor" and capacitor_plate_coupling.get("present"):
                blockers.append("source_capacitor_requires_plate_coupling_abstraction")
            else:
                blockers.append(f"no_extracted_{expected_kind}_between_expected_electrical_terminals")
        if (
            expected_kind == "resistor"
            and (ext_devres is not None or ext_passive_rsubckts is not None)
            and not coordinate_matched_devres
            and not coordinate_matched_ext_resistors
        ):
            blockers.append("no_coordinate_matched_extracted_resistor_for_source_instance")
        if expected_kind == "capacitor" and coordinate_matched_devres:
            blockers.append("coordinate_matched_devices_are_resistor_markers_not_capacitor")
        if expected_kind == "capacitor" and touching_devices:
            blockers.append("source_capacitor_touches_extracted_resistor_markers_not_a_capacitor_device")
        if expected_kind == "resistor" and touching_caps and not touching_devices:
            blockers.append("source_resistor_only_touches_parasitic_capacitors")

        if has_direct and not missing:
            status = "candidate_for_passive_abstraction"
            ready_count += 1
        elif covered:
            status = "partial_terminal_recovery"
            partial_count += 1
        else:
            status = "no_terminal_recovery"
        blocker_count += len(blockers)
        analyses.append(
            {
                "source_instance": source_device.instance,
                "source_model": source_device.model,
                "expected_kind": expected_kind,
                "terminals": list(source_device.terminals),
                "electrical_terminals": electrical,
                "body_or_reference_terminals": body,
                "covered_terminals": sorted(covered),
                "missing_terminals": missing,
                "expected_kind_covered_terminals": sorted(expected_kind_covered),
                "missing_from_expected_kind_devices": missing_from_expected_kind,
                "status": status,
                "direct_expected_device_present": has_direct,
                "direct_expected_device_matches": direct_matches,
                "segmented_expected_resistor_chain_present": bool(segmented_resistor_chain.get("present")),
                "segmented_expected_resistor_chain": segmented_resistor_chain,
                "capacitor_plate_coupling_present": bool(capacitor_plate_coupling.get("present")),
                "capacitor_plate_coupling": capacitor_plate_coupling,
                "source_level_abstraction_candidate": abstraction_candidate,
                "coordinate_matched_devres_count": len(coordinate_matched_devres),
                "coordinate_matched_devres": coordinate_matched_devres,
                "coordinate_matched_ext_resistor_count": len(coordinate_matched_ext_resistors),
                "coordinate_matched_ext_resistors": coordinate_matched_ext_resistors,
                "touching_extracted_resistors": touching_devices,
                "touching_extracted_capacitors": touching_caps[:16],
                "touching_extracted_capacitor_count": len(touching_caps),
                "blockers": blockers,
            }
        )

    if not source_devices:
        status = "not_applicable"
    elif ready_count == len(source_devices):
        status = "all_source_passives_candidate_for_abstraction"
    elif ready_count or partial_count:
        status = "partial_passive_abstraction_readiness"
    else:
        status = "no_passive_abstraction_readiness"

    return {
        "status": status,
        "source_passive_count": len(source_devices),
        "extracted_physical_resistor_count": len(extracted_resistors),
        "extracted_capacitor_count": len(extracted_capacitors),
        "source_passives_candidate_for_abstraction": ready_count,
        "source_passives_with_partial_terminal_recovery": partial_count,
        "source_resistors_with_segmented_chain": segmented_chain_count,
        "source_capacitors_with_plate_coupling_evidence": capacitor_plate_coupling_count,
        "source_level_abstraction_candidate_count": len(abstraction_candidates),
        "source_level_abstraction_candidates": abstraction_candidates,
        "blocker_count": blocker_count,
        "magic_port_shorts": magic_shorts,
        "ext_devres_count": len(owned_devres),
        "ext_devres_by_source_instance": dict(
            Counter(
                str(device.get("matched_source_instance"))
                for device in owned_devres
                if device.get("ownership_status") == "inside_source_passive_pin_box"
            )
        ),
        "ext_devres": owned_devres,
        "ext_passive_rsubckt_count": len(owned_passive_rsubckts),
        "ext_passive_rsubckt_by_source_instance": dict(
            Counter(
                str(device.get("matched_source_instance"))
                for device in owned_passive_rsubckts
                if device.get("matched_source_instance")
            )
        ),
        "ext_passive_rsubckts": owned_passive_rsubckts,
        "source_passive_terminals": sorted(source_terminals),
        "source_passives": analyses,
    }


def report(summary: dict[str, Any]) -> str:
    lines = [
        "# Passive Abstraction Readiness Report",
        "",
        "## Summary",
        "",
        f"- Status: `{summary.get('status')}`",
        f"- Source passives: {summary.get('source_passive_count', 0)}",
        f"- Extracted physical resistors: {summary.get('extracted_physical_resistor_count', 0)}",
        f"- Extracted capacitors: {summary.get('extracted_capacitor_count', 0)}",
        f"- Coordinate-parsed `.ext` devres devices: {summary.get('ext_devres_count', 0)}",
        f"- Coordinate-parsed `.ext` passive rsubckt devices: {summary.get('ext_passive_rsubckt_count', 0)}",
        f"- Source passives candidate for abstraction: {summary.get('source_passives_candidate_for_abstraction', 0)}",
        f"- Source passives with partial terminal recovery: {summary.get('source_passives_with_partial_terminal_recovery', 0)}",
        f"- Source resistors with segmented chain evidence: {summary.get('source_resistors_with_segmented_chain', 0)}",
        f"- Source capacitors with plate-coupling evidence: {summary.get('source_capacitors_with_plate_coupling_evidence', 0)}",
        f"- Source-level abstraction candidates: {summary.get('source_level_abstraction_candidate_count', 0)}",
        f"- Blockers: {summary.get('blocker_count', 0)}",
        "",
        "## Source Passive Analysis",
        "",
    ]
    for item in summary.get("source_passives", []):
        lines.extend(
            [
                f"### `{item.get('source_instance')}` `{item.get('source_model')}`",
                "",
                f"- Status: `{item.get('status')}`",
                f"- Expected kind: `{item.get('expected_kind')}`",
                f"- Electrical terminals: `{', '.join(item.get('electrical_terminals', []))}`",
                f"- Body/reference terminals: `{', '.join(item.get('body_or_reference_terminals', [])) or 'none'}`",
                f"- Covered terminals: `{', '.join(item.get('covered_terminals', [])) or 'none'}`",
                f"- Missing terminals: `{', '.join(item.get('missing_terminals', [])) or 'none'}`",
                f"- Expected-kind covered terminals: `{', '.join(item.get('expected_kind_covered_terminals', [])) or 'none'}`",
                f"- Missing from expected-kind devices: `{', '.join(item.get('missing_from_expected_kind_devices', [])) or 'none'}`",
                f"- Coordinate-matched `.ext` devres devices: {item.get('coordinate_matched_devres_count', 0)}",
                f"- Coordinate-matched `.ext` resistor rsubckt devices: {item.get('coordinate_matched_ext_resistor_count', 0)}",
                f"- Segmented expected resistor chain present: {item.get('segmented_expected_resistor_chain_present')}",
                f"- Capacitor plate-coupling evidence present: {item.get('capacitor_plate_coupling_present')}",
                f"- Direct expected device present: {item.get('direct_expected_device_present')}",
                "",
                "Blockers:",
                "",
            ]
        )
        blockers = item.get("blockers", [])
        if blockers:
            lines.extend(f"- `{blocker}`" for blocker in blockers)
        else:
            lines.append("- none")
        lines.extend(["", "Touching extracted resistors:", ""])
        resistors = item.get("touching_extracted_resistors", [])
        if resistors:
            lines.extend(["| instance | model | terminals | roles |", "| --- | --- | --- | --- |"])
            for resistor in resistors:
                roles = "; ".join(
                    f"{role.get('role')}:{role.get('source_terminal')}<-{role.get('extracted_terminal')}"
                    for role in resistor.get("roles", [])
                )
                lines.append(
                    f"| `{resistor.get('instance')}` | `{resistor.get('model')}` | "
                    f"`{' '.join(resistor.get('terminals', []))}` | `{roles}` |"
                )
        else:
            lines.append("- none")
        lines.extend(["", "Coordinate-matched `.ext` devres devices:", ""])
        coordinate_devres = item.get("coordinate_matched_devres", [])
        if coordinate_devres:
            lines.extend(["| model | ext coord | GDS coord | matched terminal |", "| --- | --- | --- | --- |"])
            for devres in coordinate_devres:
                lines.append(
                    f"| `{devres.get('model')}` | `({devres.get('ext_x')}, {devres.get('ext_y')})` | "
                    f"`({devres.get('gds_x')}, {devres.get('gds_y')})` | "
                    f"`{devres.get('matched_source_terminal')}` |"
                )
        else:
            lines.append("- none")
        lines.extend(["", "Coordinate-matched `.ext` resistor rsubckt devices:", ""])
        coordinate_rsubckts = item.get("coordinate_matched_ext_resistors", [])
        if coordinate_rsubckts:
            lines.extend(["| model | ext coord | GDS coord | ownership | matched terminal |", "| --- | --- | --- | --- | --- |"])
            for device in coordinate_rsubckts:
                lines.append(
                    f"| `{device.get('model')}` | `({device.get('ext_x')}, {device.get('ext_y')})` | "
                    f"`({device.get('gds_x')}, {device.get('gds_y')})` | "
                    f"`{device.get('ownership_status')}` | `{device.get('matched_source_terminal')}` |"
                )
        else:
            lines.append("- none")
        lines.extend(["", "Segmented expected resistor chain:", ""])
        chain = item.get("segmented_expected_resistor_chain", {})
        if chain.get("present"):
            lines.extend(
                [
                    f"- Terminals: `{chain.get('start_source_terminal')}` -> `{chain.get('end_source_terminal')}`",
                    f"- Extracted nets: `{chain.get('start_net')}` -> `{chain.get('end_net')}`",
                    f"- Segment count: {chain.get('device_count', 0)}",
                    f"- Device path: `{', '.join(chain.get('device_instances', []))}`",
                    f"- Net path: `{', '.join(chain.get('net_sequence', []))}`",
                ]
            )
        else:
            lines.append(f"- none (`{chain.get('reason', 'not_available')}`)")
        lines.extend(["", "Capacitor plate-coupling evidence:", ""])
        coupling = item.get("capacitor_plate_coupling", {})
        if coupling.get("present"):
            lines.extend(
                [
                    f"- Terminals: `{', '.join(coupling.get('expected_terminals', []))}`",
                    f"- Cross-plate capacitors: {coupling.get('coupling_capacitor_count', 0)}",
                    f"- Cross-plate capacitance: {coupling.get('coupling_capacitance_ff', 0.0):.6g} fF",
                    f"- Plate node counts: `{coupling.get('plate_node_counts', {})}`",
                ]
            )
        else:
            lines.append(f"- none (`{coupling.get('reason', 'not_available')}`)")
        lines.extend(["", "Source-level abstraction candidate:", ""])
        candidate = item.get("source_level_abstraction_candidate")
        if candidate:
            body_resolution = candidate.get("body_terminal_resolution", {})
            resolved = body_resolution.get("resolved", [])
            unresolved = candidate.get("unresolved", [])
            lines.extend(
                [
                    f"- Status: `{candidate.get('candidate_status')}`",
                    f"- Type: `{candidate.get('candidate_type')}`",
                    f"- Source-equivalent SPICE: `{candidate.get('source_equivalent_spice')}`",
                    f"- Unresolved checks: `{', '.join(unresolved) or 'none'}`",
                    "- Body/reference resolution:",
                ]
            )
            if resolved:
                for entry in resolved:
                    lines.append(
                        f"  - `{entry.get('source_terminal')}` via `{entry.get('resolution')}` "
                        f"from `{entry.get('extracted_terminal')}`"
                    )
            else:
                lines.append("  - none")
        else:
            lines.append("- none")
        lines.extend(["", "Touching extracted capacitors:", ""])
        cap_count = int(item.get("touching_extracted_capacitor_count", 0) or 0)
        caps = item.get("touching_extracted_capacitors", [])
        if caps:
            lines.extend(["| instance | terminals | value | roles |", "| --- | --- | --- | --- |"])
            for capacitor in caps:
                roles = "; ".join(
                    f"{role.get('role')}:{role.get('source_terminal')}<-{role.get('extracted_terminal')}"
                    for role in capacitor.get("roles", [])
                )
                lines.append(
                    f"| `{capacitor.get('instance')}` | "
                    f"`{' '.join(capacitor.get('terminals', []))}` | `{capacitor.get('value')}` | `{roles}` |"
                )
            if cap_count > len(caps):
                lines.append(f"| ... | ... | ... | `{cap_count - len(caps)} more` |")
        else:
            lines.append("- none")
        lines.append("")
    lines.extend(
        [
            "## Interpretation",
            "",
            "This report is an abstraction-readiness diagnostic. A `candidate_for_passive_abstraction` status means the extracted fragments have enough terminal and device-kind evidence to justify a future LVS rewrite rule; it is not by itself a full passive-aware LVS proof.",
            "",
        ]
    )
    return "\n".join(lines)


def render_candidate_netlist(summary: dict[str, Any]) -> str:
    lines = [
        "* Passive abstraction candidates generated by analyze_passive_abstraction.py",
        "* Diagnostic artifact only; this is not a full passive-aware LVS proof.",
        f"* summary_status={summary.get('status')}",
        f"* candidate_count={summary.get('source_level_abstraction_candidate_count', 0)}",
        "",
    ]
    candidates = summary.get("source_level_abstraction_candidates", [])
    if not candidates:
        lines.append("* no source-level passive abstraction candidates")
    for candidate in candidates:
        lines.extend(
            [
                f"* source_instance={candidate.get('source_instance')}",
                f"* candidate_type={candidate.get('candidate_type')}",
                f"* candidate_status={candidate.get('candidate_status')}",
                f"* unresolved={','.join(candidate.get('unresolved', [])) or 'none'}",
            ]
        )
        chain = candidate.get("chain", {})
        if chain.get("present"):
            lines.append(
                f"* segmented_chain={chain.get('start_net')}->{chain.get('end_net')} "
                f"segments={chain.get('device_count')}"
            )
            lines.append(f"* chain_devices={','.join(chain.get('device_instances', []))}")
        if candidate.get("candidate_type") == "plate_coupling_capacitor_source_equivalent":
            lines.append(f"* coupling_capacitance_ff={candidate.get('coupling_capacitance_ff')}")
            lines.append(f"* coupling_capacitor_count={candidate.get('coupling_capacitor_count')}")
            lines.append(f"* plate_node_counts={candidate.get('plate_node_counts')}")
        lines.append(str(candidate.get("source_equivalent_spice", "")))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_abstraction_packet(summary: dict[str, Any]) -> dict[str, Any]:
    candidates = summary.get("source_level_abstraction_candidates", [])
    source_instances = [
        str(item.get("source_instance"))
        for item in summary.get("source_passives", [])
        if item.get("source_instance")
    ]
    candidate_instances = sorted(
        {
            str(candidate.get("source_instance"))
            for candidate in candidates
            if candidate.get("source_instance")
        }
    )
    missing_candidate_instances = sorted(set(source_instances) - set(candidate_instances))
    unresolved: list[str] = []
    for candidate in candidates:
        unresolved.extend(str(item) for item in candidate.get("unresolved", []))
    unresolved_blockers = sorted(set(unresolved))
    review_count = sum(
        1
        for candidate in candidates
        if str(candidate.get("candidate_status")) != "candidate"
    )
    proof_status = (
        "no_passive_abstraction_candidate"
        if not candidates
        else "candidate_requires_review"
        if review_count or unresolved_blockers
        else "candidate_ready_for_rule_authoring"
    )
    source_passives = [
        {
            "source_instance": item.get("source_instance"),
            "source_model": item.get("source_model"),
            "expected_kind": item.get("expected_kind"),
            "status": item.get("status"),
            "blockers": item.get("blockers", []),
            "direct_expected_device_present": item.get("direct_expected_device_present"),
            "segmented_expected_resistor_chain_present": item.get(
                "segmented_expected_resistor_chain_present"
            ),
            "capacitor_plate_coupling_present": item.get("capacitor_plate_coupling_present"),
        }
        for item in summary.get("source_passives", [])
    ]
    return {
        "schema_version": "passive_abstraction_packet.v1",
        "verification_scope": "passive_abstraction_diagnostic",
        "evidence_class": "source_equivalent_candidate_not_full_lvs_proof",
        "proof_status": proof_status,
        "full_passive_aware_lvs_proven": False,
        "summary_status": summary.get("status"),
        "source_passive_count": summary.get("source_passive_count", 0),
        "source_level_abstraction_candidate_count": len(candidates),
        "source_resistors_with_segmented_chain": summary.get(
            "source_resistors_with_segmented_chain", 0
        ),
        "source_capacitors_with_plate_coupling_evidence": summary.get(
            "source_capacitors_with_plate_coupling_evidence", 0
        ),
        "candidate_summary": {
            "candidate_count": len(candidates),
            "candidate_requires_review_count": review_count,
            "unresolved_blocker_count": len(unresolved_blockers),
            "unresolved_blockers": unresolved_blockers,
            "source_equivalent_netlist": [
                str(candidate.get("source_equivalent_spice", ""))
                for candidate in candidates
                if candidate.get("source_equivalent_spice")
            ],
        },
        "source_instance_coverage": {
            "source_instances": sorted(source_instances),
            "candidate_instances": candidate_instances,
            "covered_source_passive_count": len(candidate_instances),
            "missing_source_passive_instances": missing_candidate_instances,
            "all_source_passives_have_candidate": bool(source_instances)
            and not missing_candidate_instances,
        },
        "candidates": candidates,
        "source_passives": source_passives,
        "limitations": [
            "This packet is generated from extracted passive-fragment evidence.",
            "It is intended for LVS abstraction rule development and review.",
            "It does not prove full passive-aware LVS/PEX by itself.",
        ],
    }


def main() -> int:
    args = parse_args()
    source = args.source_netlist.resolve()
    extracted = args.extracted_netlist.resolve()
    identity = {}
    if args.identity_json and args.identity_json.is_file():
        identity = json.loads(args.identity_json.read_text(encoding="utf-8"))
    source_lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
    extracted_lines = extracted.read_text(encoding="utf-8", errors="replace").splitlines()
    summary = analyze(
        source_lines=source_lines,
        extracted_lines=extracted_lines,
        magic_shorts=parse_magic_port_shorts(args.magic_log),
        identity=identity,
        ext_devres=parse_ext_devres(args.ext_file) if args.ext_file else None,
        ext_passive_rsubckts=parse_ext_passive_rsubckts(args.ext_file) if args.ext_file else None,
    )
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report(summary), encoding="utf-8")
    if args.candidate_netlist is not None:
        args.candidate_netlist.parent.mkdir(parents=True, exist_ok=True)
        args.candidate_netlist.write_text(render_candidate_netlist(summary), encoding="utf-8")
    if args.packet_json is not None:
        args.packet_json.parent.mkdir(parents=True, exist_ok=True)
        args.packet_json.write_text(
            json.dumps(render_abstraction_packet(summary), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(f"status={summary['status']}")
    print(f"source_passives={summary['source_passive_count']}")
    print(f"blockers={summary['blocker_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
