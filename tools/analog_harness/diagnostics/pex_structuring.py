from __future__ import annotations


def _cap_to_ff(value: str) -> float:
    text = value.strip().lower()
    if text.endswith("ff"):
        return float(text[:-2])
    if text.endswith("f"):
        return float(text[:-1])
    if text.endswith("p"):
        return float(text[:-1]) * 1000.0
    return float(text) * 1e15


def summarize_pex_caps(spice_text: str) -> dict:
    per_node = {}
    total = 0.0
    count = 0
    for raw_line in spice_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("*") or not line[0].lower() == "c":
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        node_a, node_b, value = parts[1], parts[2], parts[3]
        cap_ff = _cap_to_ff(value)
        count += 1
        total += cap_ff
        per_node[node_a] = per_node.get(node_a, 0.0) + cap_ff
        per_node[node_b] = per_node.get(node_b, 0.0) + cap_ff
    return {
        "pex_caps": count,
        "pex_total_cap_ff": total,
        "per_node_cap_ff": per_node,
    }
