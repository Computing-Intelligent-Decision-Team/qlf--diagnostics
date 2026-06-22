from __future__ import annotations


def classify_lvs_summary(text: str) -> dict:
    lowered = text.lower()
    categories = []
    if (
        "device mismatch detected: yes" in lowered
        or "device classes" in lowered
        or "not equivalent" in lowered
    ):
        categories.append("device_mismatch")
    if "net mismatch detected: yes" in lowered or "netlists do not match" in lowered:
        categories.append("net_mismatch")
    if (
        "property mismatch detected: yes" in lowered
        or "property errors" in lowered
    ):
        categories.append("property_mismatch")
    if "power" in lowered and "short" in lowered:
        categories.append("power_domain_short")
    if "pin label overlap" in lowered or "label overlap" in lowered:
        categories.append("pin_label_overlap")
    if "missing top port label" in lowered or (
        "missing" in lowered and "port label" in lowered
    ):
        categories.append("missing_top_port_label")
    status = (
        "pass"
        if (
            "lvs status: **pass**" in lowered
            or "circuits match uniquely" in lowered
            or "netlists match uniquely" in lowered
        )
        and not categories
        else "fail"
    )
    return {
        "status": status,
        "lvs_match": status == "pass" and not categories,
        "failure_categories": categories,
    }
