"""Build capacitor graph edge tables directly from raw PEX SPICE files."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "parasitic_raw_spice_graph_edges.v1"
POWER_NODES = {"gnd", "gnda", "vss", "vssa", "vdd", "vdda", "vcc", "vee"}
_CAP_LINE_RE = re.compile(
    r"^(?P<cap_id>C\S*)\s+(?P<node_1>\S+)\s+(?P<node_2>\S+)\s+"
    r"(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)(?P<unit>[a-zA-Z]*)"
    r"(?:\s|$)"
)
_UNIT_TO_FF = {
    "": 1e15,
    "f": 1.0,
    "ff": 1.0,
    "p": 1e3,
    "pf": 1e3,
    "n": 1e6,
    "nf": 1e6,
    "u": 1e9,
    "uf": 1e9,
    "m": 1e12,
    "mf": 1e12,
    "a": 1e-3,
    "af": 1e-3,
}


def read_raw_spice_manifest(manifest_path: Path) -> list[dict[str, Any]]:
    """Read a CSV manifest with design_id, candidate_id, and raw_spice_path."""

    entries: list[dict[str, Any]] = []
    with manifest_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"design_id", "candidate_id", "raw_spice_path"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"raw SPICE manifest missing fields: {sorted(missing)}")
        for row in reader:
            entries.append(
                {
                    "design_id": row["design_id"],
                    "candidate_id": row["candidate_id"],
                    "raw_spice_path": row["raw_spice_path"],
                }
            )
    return entries


def parse_raw_spice_capacitor_edges(
    raw_spice_path: Path,
    *,
    design_id: str,
    candidate_id: str,
) -> dict[str, Any]:
    """Parse capacitor records from one raw ``*_extracted.raw.spice`` file."""

    raw_spice_path = raw_spice_path.resolve()
    edges: list[dict[str, Any]] = []
    with raw_spice_path.open(encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith(("*", ".", "+")):
                continue
            match = _CAP_LINE_RE.match(stripped)
            if not match:
                continue
            node_1 = match.group("node_1")
            node_2 = match.group("node_2")
            cap_ff = _to_ff(float(match.group("value")), match.group("unit").lower())
            edges.append(
                {
                    "design_id": design_id,
                    "candidate_id": candidate_id,
                    "cap_id": match.group("cap_id"),
                    "node_1": node_1,
                    "node_2": node_2,
                    "capacitance_ff": round(cap_ff, 9),
                    "is_zero": cap_ff == 0.0,
                    "is_power_edge": _is_power_node(node_1) or _is_power_node(node_2),
                    "raw_spice_available": True,
                    "raw_spice_path_reported": str(raw_spice_path),
                    "raw_spice_sha256_reported": _sha256_file(raw_spice_path),
                    "needs_raw_spice_verification": False,
                    "source_type": "raw_spice_direct_capacitor_table",
                    "raw_line_number": line_number,
                }
            )
    return {
        "design_id": design_id,
        "candidate_id": candidate_id,
        "raw_spice_path": str(raw_spice_path),
        "edges": edges,
        "summary": _summarize_edges(edges, raw_spice_path),
    }


def build_raw_spice_edge_dataset(manifest_entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Build an edge-table dataset from raw SPICE manifest entries."""

    design_results = []
    all_edges = []
    for entry in manifest_entries:
        result = parse_raw_spice_capacitor_edges(
            Path(entry["raw_spice_path"]),
            design_id=entry["design_id"],
            candidate_id=entry["candidate_id"],
        )
        design_results.append(result)
        all_edges.extend(result["edges"])
    return {
        "schema_version": SCHEMA_VERSION,
        "source_type": "raw_spice_direct_capacitor_table",
        "counts": {
            "designs": len(design_results),
            "edges_all": len(all_edges),
            "edges_positive": sum(1 for edge in all_edges if not edge["is_zero"]),
            "zero_edges": sum(1 for edge in all_edges if edge["is_zero"]),
        },
        "graph_summaries": [result["summary"] for result in design_results],
        "edges": all_edges,
    }


def augment_dataset_with_raw_spice_edges(
    unified_dataset: dict[str, Any],
    manifest_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return a copy of a unified dataset with raw-SPICE graphs attached."""

    dataset = deepcopy(unified_dataset)
    graph_edges_by_design = dataset.setdefault("graph_edges_by_design", {})
    records_by_design = {record["design_id"]: record for record in dataset.get("records", [])}
    raw_graph_records = 0
    for entry in manifest_entries:
        design_id = entry["design_id"]
        if design_id not in records_by_design:
            raise ValueError(f"manifest design_id not present in unified dataset: {design_id}")
        result = parse_raw_spice_capacitor_edges(
            Path(entry["raw_spice_path"]),
            design_id=design_id,
            candidate_id=entry["candidate_id"],
        )
        graph_edges_by_design[design_id] = result["edges"]
        record = records_by_design[design_id]
        record["graph"] = _record_graph_summary(result["summary"])
        record.setdefault("modeling_availability", {})["capacitor_graph"] = "usable_with_raw_spice_provenance"
        raw_graph_records += 1
    dataset["counts"] = _updated_counts(dataset, raw_graph_records)
    dataset["graph_schema"] = SCHEMA_VERSION
    dataset.setdefault("source_boundaries", []).append(
        "Some capacitor graphs are parsed directly from regenerated raw PEX SPICE files."
    )
    return dataset


def write_raw_spice_edge_outputs(
    raw_edge_dataset: dict[str, Any],
    augmented_dataset: dict[str, Any],
    output_dir: Path,
) -> dict[str, Path]:
    """Write raw edge table, augmented dataset, CSV manifest, and README."""

    output_dir.mkdir(parents=True, exist_ok=True)
    edge_json = output_dir / "raw_spice_capacitor_edges.json"
    edge_csv = output_dir / "raw_spice_capacitor_edges.csv"
    dataset_json = output_dir / "parasitic_modeling_dataset_with_raw_graphs.json"
    readme = output_dir / "README.md"
    edge_json.write_text(json.dumps(raw_edge_dataset, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    dataset_json.write_text(json.dumps(augmented_dataset, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    _write_edge_csv(raw_edge_dataset["edges"], edge_csv)
    readme.write_text(_render_readme(raw_edge_dataset, augmented_dataset), encoding="utf-8")
    return {
        "raw_edge_json": edge_json,
        "raw_edge_csv": edge_csv,
        "augmented_dataset_json": dataset_json,
        "markdown": readme,
    }


def _record_graph_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "available": True,
        "edge_count_all": summary["edge_count_all"],
        "edge_count_positive": summary["edge_count_positive"],
        "edge_count_zero": summary["edge_count_zero"],
        "edge_records_attached": summary["edge_count_all"],
        "max_cap_ff": summary["max_cap_ff"],
        "mean_positive_cap_ff": summary["mean_positive_cap_ff"],
        "needs_raw_spice_verification": False,
        "node_count": summary["node_count"],
        "power_edge_count": summary["power_edge_count"],
        "raw_spice_available": True,
        "raw_spice_path_reported": summary["raw_spice_path_reported"],
        "raw_spice_sha256_reported": summary["raw_spice_sha256"],
        "signal_edge_count": summary["signal_edge_count"],
        "source_type": "raw_spice_direct_capacitor_table",
        "total_cap_ff": summary["total_cap_ff"],
    }


def _summarize_edges(edges: list[dict[str, Any]], raw_spice_path: Path) -> dict[str, Any]:
    positive = [edge for edge in edges if not edge["is_zero"]]
    nodes = {edge["node_1"] for edge in edges} | {edge["node_2"] for edge in edges}
    total_cap = sum(float(edge["capacitance_ff"]) for edge in edges)
    return {
        "design_id": edges[0]["design_id"] if edges else None,
        "candidate_id": edges[0]["candidate_id"] if edges else None,
        "raw_spice_path_reported": str(raw_spice_path),
        "raw_spice_sha256": _sha256_file(raw_spice_path),
        "edge_count_all": len(edges),
        "edge_count_positive": len(positive),
        "edge_count_zero": len(edges) - len(positive),
        "node_count": len(nodes),
        "power_edge_count": sum(1 for edge in edges if edge["is_power_edge"]),
        "signal_edge_count": sum(1 for edge in edges if not edge["is_power_edge"]),
        "total_cap_ff": round(total_cap, 9),
        "max_cap_ff": round(max((float(edge["capacitance_ff"]) for edge in edges), default=0.0), 9),
        "mean_positive_cap_ff": round(
            sum(float(edge["capacitance_ff"]) for edge in positive) / len(positive), 9
            if positive
            else 0.0,
        ),
    }


def _updated_counts(dataset: dict[str, Any], raw_graph_records: int) -> dict[str, Any]:
    counts = dict(dataset.get("counts", {}))
    graph_edges_by_design = dataset.get("graph_edges_by_design", {})
    records = dataset.get("records", [])
    counts["records"] = len(records)
    counts["records_with_graph"] = sum(1 for record in records if record.get("graph", {}).get("available"))
    counts["summary_only_records"] = counts["records"] - counts["records_with_graph"]
    counts["graph_training_records"] = len(graph_edges_by_design)
    counts["raw_spice_graph_records"] = raw_graph_records
    counts["records_with_raw_spice_graph"] = sum(
        1
        for record in records
        if record.get("graph", {}).get("source_type") == "raw_spice_direct_capacitor_table"
    )
    return counts


def _write_edge_csv(edges: list[dict[str, Any]], path: Path) -> None:
    fields = [
        "design_id",
        "candidate_id",
        "cap_id",
        "node_1",
        "node_2",
        "capacitance_ff",
        "is_zero",
        "is_power_edge",
        "raw_spice_path_reported",
        "raw_spice_sha256_reported",
        "raw_line_number",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for edge in edges:
            writer.writerow({field: edge.get(field) for field in fields})


def _render_readme(raw_edge_dataset: dict[str, Any], augmented_dataset: dict[str, Any]) -> str:
    lines = [
        "# Raw SPICE capacitor graph edges",
        "",
        f"- schema_version: `{raw_edge_dataset['schema_version']}`",
        f"- designs: {raw_edge_dataset['counts']['designs']}",
        f"- edges_all: {raw_edge_dataset['counts']['edges_all']}",
        f"- augmented_records_with_graph: {augmented_dataset['counts']['records_with_graph']}",
        f"- augmented_summary_only_records: {augmented_dataset['counts']['summary_only_records']}",
        "",
        "| design_id | edges | positive | zero | nodes | total cap fF |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for summary in raw_edge_dataset["graph_summaries"]:
        lines.append(
            f"| {summary['design_id']} | {summary['edge_count_all']} | "
            f"{summary['edge_count_positive']} | {summary['edge_count_zero']} | "
            f"{summary['node_count']} | {summary['total_cap_ff']:.6f} |"
        )
    lines.extend(
        [
            "",
            "These edges are parsed directly from raw PEX SPICE capacitor records.",
            "",
        ]
    )
    return "\n".join(lines)


def _is_power_node(node: str) -> bool:
    return node.rstrip("!").lower() in POWER_NODES


def _to_ff(value: float, unit: str) -> float:
    if unit not in _UNIT_TO_FF:
        raise ValueError(f"unsupported capacitance unit in raw SPICE: {unit}")
    return value * _UNIT_TO_FF[unit]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--raw-manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    entries = read_raw_spice_manifest(args.raw_manifest)
    raw_edge_dataset = build_raw_spice_edge_dataset(entries)
    augmented_dataset = augment_dataset_with_raw_spice_edges(dataset, entries)
    outputs = write_raw_spice_edge_outputs(raw_edge_dataset, augmented_dataset, args.output_dir)
    print(json.dumps({key: str(value) for key, value in outputs.items()}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
