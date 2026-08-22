#!/usr/bin/env python3
"""Build a lightweight physical-closure classifier from GRPO→PCS admission runs.

The classifier is intentionally small-data and diagnostic.  It only uses
pre-physical-run features available in the GRPO sizing/source_state contract,
then predicts whether a candidate will become an L6 raw-PEX graph sample.
Outcome-derived PEX fields are kept in the admission table but excluded from
the model feature matrix to avoid leakage.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_SUMMARIES = [
    Path("generated/grpo_to_pcs_admission_batch_v2_20260822/admission_summary_v2.json"),
    Path("generated/grpo_to_pcs_admission_batch_v3_20260822/admission_summary_v3.json"),
    Path("generated/grpo_to_pcs_admission_batch_v4_20260822/admission_summary_v4.json"),
]


@dataclass(frozen=True)
class CandidateRow:
    sample_uid: str
    batch_id: str
    candidate_id: str
    design_id: str
    admission_status: str
    failure_stage: str
    best_closure_level: str
    graph_training_admitted: int
    raw_pex_available: int
    physical_closure_failed_no_raw_pex: int
    simulation_timeout_or_hang: int
    source_state_path: str
    source_state_resolved: str
    m12_m: float | None
    pex_cap_count: int | None
    pex_total_cap_ff: float | None
    raw_spice_sha256: str | None


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_source_state(record: dict[str, Any], repo_root: Path, pcs_root: Path) -> Path:
    raw = record.get("source_state_path")
    if not raw:
        raise ValueError(f"record {record.get('candidate_id')} has no source_state_path")
    p = Path(raw)
    candidates = []
    if p.is_absolute():
        candidates.append(p)
    else:
        candidates.append(repo_root / p)
        candidates.append(pcs_root / p)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"source_state_path not found for {record.get('candidate_id')}: {raw}; "
        f"tried {[str(c) for c in candidates]}"
    )


def safe_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out):
        return None
    return out


def numeric_values(d: dict[str, Any], prefix: str = "") -> dict[str, float]:
    out: dict[str, float] = {}
    for key, value in d.items():
        name = f"{prefix}{key}" if prefix else str(key)
        f = safe_float(value)
        if f is not None:
            out[name] = f
    return out


def mos_group(values: dict[str, float], suffix: str, device_type: str | None = None) -> dict[str, float]:
    selected: dict[str, float] = {}
    for key, value in values.items():
        if not key.startswith("mosfet_") or f"_{suffix}_" not in key:
            continue
        if device_type and not key.endswith(f"_{device_type}"):
            continue
        selected[key] = value
    return selected


def add_stats(features: dict[str, float], prefix: str, values: Iterable[float]) -> None:
    vals = [v for v in values if math.isfinite(v)]
    features[f"{prefix}_count"] = float(len(vals))
    if not vals:
        features[f"{prefix}_sum"] = 0.0
        features[f"{prefix}_mean"] = 0.0
        features[f"{prefix}_min"] = 0.0
        features[f"{prefix}_max"] = 0.0
        return
    features[f"{prefix}_sum"] = float(sum(vals))
    features[f"{prefix}_mean"] = float(statistics.fmean(vals))
    features[f"{prefix}_min"] = float(min(vals))
    features[f"{prefix}_max"] = float(max(vals))


def derived_features(values: dict[str, float], action_normalized: list[Any]) -> dict[str, float]:
    features: dict[str, float] = {}
    for key, value in values.items():
        features[f"sizing__{key}"] = value

    for i, value in enumerate(action_normalized):
        f = safe_float(value)
        if f is not None:
            features[f"action_norm_{i:02d}"] = f

    w_all = mos_group(values, "w")
    l_all = mos_group(values, "l")
    m_all = mos_group(values, "m")
    add_stats(features, "mos_w_all", w_all.values())
    add_stats(features, "mos_l_all", l_all.values())
    add_stats(features, "mos_m_all", m_all.values())

    for device_type in ("pmos", "nmos"):
        w = mos_group(values, "w", device_type)
        l = mos_group(values, "l", device_type)
        m = mos_group(values, "m", device_type)
        add_stats(features, f"{device_type}_w", w.values())
        add_stats(features, f"{device_type}_l", l.values())
        add_stats(features, f"{device_type}_m", m.values())

    area_proxy_sum = 0.0
    gate_area_proxy_sum = 0.0
    aspect_weighted_sum = 0.0
    mos_device_count = 0
    for w_key, w in w_all.items():
        prefix = w_key.replace("_w_", "_")
        # Reconstruct sibling keys by replacing the one '_w_' token.
        l_key = w_key.replace("_w_", "_l_")
        m_key = w_key.replace("_w_", "_m_")
        l = values.get(l_key)
        m = values.get(m_key)
        if l is None or m is None or l == 0:
            continue
        mos_device_count += 1
        area_proxy_sum += w * m
        gate_area_proxy_sum += w * l * m
        aspect_weighted_sum += (w / l) * m
    features["mos_device_count"] = float(mos_device_count)
    features["mos_width_times_m_sum"] = float(area_proxy_sum)
    features["mos_gate_area_proxy_sum"] = float(gate_area_proxy_sum)
    features["mos_aspect_times_m_sum"] = float(aspect_weighted_sum)
    features["pmos_to_nmos_m_ratio"] = (
        features.get("pmos_m_sum", 0.0) / features.get("nmos_m_sum", 1.0)
        if features.get("nmos_m_sum", 0.0) != 0.0
        else 0.0
    )
    features["requested_cap_sum"] = float(
        sum(value for key, value in values.items() if key.startswith("capacitor_"))
    )
    features["bias_current_sum"] = float(
        sum(value for key, value in values.items() if key.startswith("current_"))
    )
    return features


def load_rows_and_features(
    summary_paths: list[Path], repo_root: Path, pcs_root: Path
) -> tuple[list[CandidateRow], list[dict[str, float]]]:
    rows: list[CandidateRow] = []
    features: list[dict[str, float]] = []
    for summary_path in summary_paths:
        summary = load_json(summary_path)
        batch_id = summary["batch_id"]
        for record in summary["records"]:
            source_state = resolve_source_state(record, repo_root, pcs_root)
            state = load_json(source_state)
            values = numeric_values(state.get("values", {}))
            feats = derived_features(values, state.get("action_normalized", []))
            feats["record__m12_m"] = float(record["m12_m"]) if record.get("m12_m") is not None else 0.0
            # Selection bucket is generated before PCS physical run and is safe,
            # but only exists for batch v3.
            bucket = record.get("selection_bucket") or "none"
            for known_bucket in (
                "none",
                "l6_neighborhood_m12_330_390",
                "diagnostic_neighborhood_m12_335_365",
                "boundary_m12_388_397",
                "high_predicted_closure",
                "medium_predicted_closure",
                "low_predicted_closure",
            ):
                feats[f"selection_bucket__{known_bucket}"] = 1.0 if bucket == known_bucket else 0.0

            admitted = 1 if record.get("admission_status") == "admitted_raw_pex_graph" else 0
            raw_available = 1 if record.get("raw_pex_path") else 0
            no_raw_failed = 1 if record.get("admission_status") == "physical_closure_failed" else 0
            timeout = 1 if record.get("admission_status") == "simulation_timeout_or_hang" else 0
            sample_uid = f"{batch_id}/{record['candidate_id']}"
            rows.append(
                CandidateRow(
                    sample_uid=sample_uid,
                    batch_id=batch_id,
                    candidate_id=record["candidate_id"],
                    design_id=record["design_id"],
                    admission_status=record["admission_status"],
                    failure_stage=record.get("failure_stage") or "",
                    best_closure_level=record.get("best_closure_level") or "",
                    graph_training_admitted=admitted,
                    raw_pex_available=raw_available,
                    physical_closure_failed_no_raw_pex=no_raw_failed,
                    simulation_timeout_or_hang=timeout,
                    source_state_path=record.get("source_state_path") or "",
                    source_state_resolved=str(source_state),
                    m12_m=safe_float(record.get("m12_m")),
                    pex_cap_count=record.get("pex_cap_count"),
                    pex_total_cap_ff=safe_float(record.get("pex_total_cap_ff")),
                    raw_spice_sha256=record.get("raw_spice_sha256"),
                )
            )
            features.append(feats)
    return rows, features


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def matrix_rows(rows: list[CandidateRow], features: list[dict[str, float]]) -> tuple[list[dict[str, Any]], list[str]]:
    feature_names = sorted({key for feat in features for key in feat})
    out = []
    for row, feat in zip(rows, features, strict=True):
        item: dict[str, Any] = {
            "sample_uid": row.sample_uid,
            "batch_id": row.batch_id,
            "candidate_id": row.candidate_id,
            "label_graph_training_admitted": row.graph_training_admitted,
            "label_raw_pex_available": row.raw_pex_available,
            "label_physical_closure_failed_no_raw_pex": row.physical_closure_failed_no_raw_pex,
            "label_simulation_timeout_or_hang": row.simulation_timeout_or_hang,
            "admission_status": row.admission_status,
        }
        for name in feature_names:
            item[name] = feat.get(name, 0.0)
        out.append(item)
    return out, feature_names


def labels_as_rows(rows: list[CandidateRow]) -> list[dict[str, Any]]:
    return [
        {
            "sample_uid": row.sample_uid,
            "batch_id": row.batch_id,
            "candidate_id": row.candidate_id,
            "admission_status": row.admission_status,
            "graph_training_admitted": row.graph_training_admitted,
            "raw_pex_available": row.raw_pex_available,
            "physical_closure_failed_no_raw_pex": row.physical_closure_failed_no_raw_pex,
            "simulation_timeout_or_hang": row.simulation_timeout_or_hang,
            "best_closure_level": row.best_closure_level,
            "failure_stage": row.failure_stage,
        }
        for row in rows
    ]


def admission_as_rows(rows: list[CandidateRow]) -> list[dict[str, Any]]:
    return [
        {
            "sample_uid": row.sample_uid,
            "batch_id": row.batch_id,
            "candidate_id": row.candidate_id,
            "design_id": row.design_id,
            "admission_status": row.admission_status,
            "best_closure_level": row.best_closure_level,
            "failure_stage": row.failure_stage,
            "graph_training_admitted": row.graph_training_admitted,
            "raw_pex_available": row.raw_pex_available,
            "physical_closure_failed_no_raw_pex": row.physical_closure_failed_no_raw_pex,
            "simulation_timeout_or_hang": row.simulation_timeout_or_hang,
            "m12_m": row.m12_m,
            "pex_cap_count": row.pex_cap_count,
            "pex_total_cap_ff": row.pex_total_cap_ff,
            "raw_spice_sha256": row.raw_spice_sha256 or "",
            "source_state_path": row.source_state_path,
            "source_state_resolved": row.source_state_resolved,
        }
        for row in rows
    ]


def compute_metrics(y_true: list[int], y_pred: list[int]) -> dict[str, Any]:
    tp = sum(1 for y, p in zip(y_true, y_pred, strict=True) if y == 1 and p == 1)
    tn = sum(1 for y, p in zip(y_true, y_pred, strict=True) if y == 0 and p == 0)
    fp = sum(1 for y, p in zip(y_true, y_pred, strict=True) if y == 0 and p == 1)
    fn = sum(1 for y, p in zip(y_true, y_pred, strict=True) if y == 1 and p == 0)
    n = len(y_true)
    accuracy = (tp + tn) / n if n else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "n": n,
        "accuracy": accuracy,
        "balanced_accuracy": (recall + specificity) / 2,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "f1": f1,
        "confusion_matrix": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
    }


def run_sklearn_models(
    rows: list[CandidateRow], features: list[dict[str, float]], feature_names: list[str]
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    from sklearn.dummy import DummyClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.tree import DecisionTreeClassifier

    x = [[features[i].get(name, 0.0) for name in feature_names] for i in range(len(rows))]
    y = [row.graph_training_admitted for row in rows]
    models = {
        "dummy_most_frequent": DummyClassifier(strategy="most_frequent"),
        "logistic_l2_balanced": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "logistic",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=1000,
                        random_state=0,
                        solver="liblinear",
                    ),
                ),
            ]
        ),
        "decision_tree_depth3_balanced": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "tree",
                    DecisionTreeClassifier(
                        max_depth=3,
                        min_samples_leaf=2,
                        class_weight="balanced",
                        random_state=0,
                    ),
                ),
            ]
        ),
    }

    metrics: dict[str, Any] = {}
    predictions: list[dict[str, Any]] = []
    for model_name, model in models.items():
        y_pred: list[int] = []
        prob_admit: list[float | None] = []
        for heldout in range(len(rows)):
            train_x = [item for i, item in enumerate(x) if i != heldout]
            train_y = [item for i, item in enumerate(y) if i != heldout]
            model.fit(train_x, train_y)
            pred = int(model.predict([x[heldout]])[0])
            y_pred.append(pred)
            if hasattr(model, "predict_proba"):
                proba = model.predict_proba([x[heldout]])[0]
                classes = list(model.classes_)
                prob_admit.append(float(proba[classes.index(1)]) if 1 in classes else 0.0)
            else:
                prob_admit.append(None)
            predictions.append(
                {
                    "model": model_name,
                    "sample_uid": rows[heldout].sample_uid,
                    "candidate_id": rows[heldout].candidate_id,
                    "batch_id": rows[heldout].batch_id,
                    "true_graph_training_admitted": y[heldout],
                    "pred_graph_training_admitted": pred,
                    "prob_graph_training_admitted": prob_admit[-1],
                    "admission_status": rows[heldout].admission_status,
                }
            )
        metrics[model_name] = compute_metrics(y, y_pred)

    fitted_logistic = models["logistic_l2_balanced"].fit(x, y)
    coefs = fitted_logistic.named_steps["logistic"].coef_[0]
    logistic_importance = [
        {
            "model": "logistic_l2_balanced",
            "feature": name,
            "importance": abs(float(coef)),
            "signed_weight": float(coef),
        }
        for name, coef in zip(feature_names, coefs, strict=True)
    ]

    fitted_tree = models["decision_tree_depth3_balanced"].fit(x, y)
    tree_importances = fitted_tree.named_steps["tree"].feature_importances_
    tree_importance = [
        {
            "model": "decision_tree_depth3_balanced",
            "feature": name,
            "importance": float(value),
            "signed_weight": "",
        }
        for name, value in zip(feature_names, tree_importances, strict=True)
        if value > 0
    ]
    return metrics, predictions, logistic_importance + tree_importance


def univariate_feature_summary(
    rows: list[CandidateRow], features: list[dict[str, float]], feature_names: list[str]
) -> list[dict[str, Any]]:
    y = [row.graph_training_admitted for row in rows]
    admitted_idx = [i for i, label in enumerate(y) if label == 1]
    rejected_idx = [i for i, label in enumerate(y) if label == 0]
    out: list[dict[str, Any]] = []
    for name in feature_names:
        admitted_vals = [features[i].get(name, 0.0) for i in admitted_idx]
        rejected_vals = [features[i].get(name, 0.0) for i in rejected_idx]
        mean_a = statistics.fmean(admitted_vals) if admitted_vals else 0.0
        mean_r = statistics.fmean(rejected_vals) if rejected_vals else 0.0
        pooled = statistics.pstdev(admitted_vals + rejected_vals) if len(admitted_vals + rejected_vals) > 1 else 0.0
        effect = abs(mean_a - mean_r) / pooled if pooled else 0.0
        out.append(
            {
                "feature": name,
                "mean_admitted": mean_a,
                "mean_not_admitted": mean_r,
                "delta_admitted_minus_not": mean_a - mean_r,
                "abs_standardized_effect": effect,
            }
        )
    return sorted(out, key=lambda row: row["abs_standardized_effect"], reverse=True)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def make_recommendation(
    rows: list[CandidateRow],
    metrics: dict[str, Any],
    feature_summary: list[dict[str, Any]],
    output_dir: Path,
) -> None:
    counts = Counter(row.admission_status for row in rows)
    top = feature_summary[:12]
    lines = [
        "# Batch v4 sampling recommendation from physical_closure_classifier_v1",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Evidence scope",
        "",
        f"- Input samples: {len(rows)} GRPO→PCS admission records from configured summaries.",
        f"- Admitted L6 raw-PEX graph samples: {sum(row.graph_training_admitted for row in rows)}.",
        f"- Status counts: {dict(counts)}.",
        "- This is a diagnostic small-data classifier, not a production feasibility oracle.",
        "- Action-space must not be hard-coded from this result; every candidate still needs L0→L6 admission.",
        "",
        "## Model sanity check",
        "",
    ]
    for model, data in metrics.items():
        lines.append(
            f"- `{model}` LOO balanced_accuracy={data['balanced_accuracy']:.3f}, "
            f"accuracy={data['accuracy']:.3f}, f1={data['f1']:.3f}, "
            f"cm={data['confusion_matrix']}"
        )
    lines += [
        "",
        "## Strongest current feature signals",
        "",
    ]
    for item in top:
        lines.append(
            f"- `{item['feature']}`: mean admitted={item['mean_admitted']:.4g}, "
            f"mean not-admitted={item['mean_not_admitted']:.4g}, "
            f"standardized effect={item['abs_standardized_effect']:.3f}"
        )
    lines += [
        "",
        "## Recommended batch v4 policy",
        "",
        "1. Keep using the same AnalogGym action-space contract; do not shrink it by a single M12 threshold.",
        "2. Export a larger candidate pool first, then stratify candidates by the classifier risk score into low/medium/high predicted closure likelihood.",
        "3. Sample all three strata deliberately: high-likelihood candidates grow the training graph set, while medium/high-risk candidates keep the failure boundary visible.",
        "4. Prefer combinations that diversify the top feature signals above, especially full W/L/M/cap/bias combinations rather than only sweeping M12.",
        "5. For the next practical run, target 24–36 candidates and report admitted/raw-not-L6/no-raw separately.",
        "6. Treat this classifier as a sampling guide only; final dataset admission remains actual L0→L6 + raw PEX graph evidence.",
        "",
    ]
    (output_dir / "batch_v4_sampling_recommendation.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    write_json(
        output_dir / "batch_v4_sampling_recommendation.json",
        {
            "schema_version": "physical_closure_classifier.batch_v4_sampling_recommendation.v1",
            "input_records": len(rows),
            "status_counts": dict(counts),
            "model_metrics": metrics,
            "top_feature_signals": top,
            "policy": [
                "same_action_space_contract_no_single_feature_hard_prune",
                "classifier_guided_stratified_sampling",
                "actual_l0_to_l6_raw_pex_admission_remains_source_of_truth",
            ],
        },
    )


def build_classifier_outputs(
    repo_root: Path, pcs_root: Path, summary_paths: list[Path], output_dir: Path
) -> dict[str, Any]:
    rows, features = load_rows_and_features(summary_paths, repo_root, pcs_root)
    if not rows:
        raise ValueError("no candidate rows loaded")
    matrix, feature_names = matrix_rows(rows, features)
    labels = labels_as_rows(rows)
    admission = admission_as_rows(rows)

    write_csv(output_dir / "admission_table.csv", admission, list(admission[0].keys()))
    write_csv(output_dir / "label_matrix.csv", labels, list(labels[0].keys()))
    write_csv(output_dir / "feature_matrix.csv", matrix, list(matrix[0].keys()))
    write_jsonl(output_dir / "admission_table.jsonl", admission)
    write_jsonl(output_dir / "label_matrix.jsonl", labels)

    metrics, predictions, model_importance = run_sklearn_models(rows, features, feature_names)
    write_csv(output_dir / "leave_one_out_predictions.csv", predictions, list(predictions[0].keys()))
    write_json(output_dir / "model_metrics.json", metrics)

    feature_summary = univariate_feature_summary(rows, features, feature_names)
    feature_importance = sorted(
        model_importance,
        key=lambda row: (row["model"], -float(row["importance"])),
    )
    write_csv(
        output_dir / "feature_importance.csv",
        feature_importance,
        ["model", "feature", "importance", "signed_weight"],
    )
    write_csv(
        output_dir / "univariate_feature_summary.csv",
        feature_summary,
        [
            "feature",
            "mean_admitted",
            "mean_not_admitted",
            "delta_admitted_minus_not",
            "abs_standardized_effect",
        ],
    )
    write_json(
        output_dir / "feature_summary.json",
        {
            "schema_version": "physical_closure_classifier.feature_summary.v1",
            "feature_count": len(feature_names),
            "top_univariate_signals": feature_summary[:30],
        },
    )
    make_recommendation(rows, metrics, feature_summary, output_dir)

    manifest = {
        "schema_version": "physical_closure_classifier.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_summaries": [str(path) for path in summary_paths],
        "pcs_root": str(pcs_root),
        "output_dir": str(output_dir),
        "record_count": len(rows),
        "feature_count": len(feature_names),
        "label_counts": Counter(row.admission_status for row in rows),
        "admitted_count": sum(row.graph_training_admitted for row in rows),
        "raw_pex_available_count": sum(row.raw_pex_available for row in rows),
        "simulation_timeout_or_hang_count": sum(row.simulation_timeout_or_hang for row in rows),
        "model_metrics": metrics,
    }
    manifest["label_counts"] = dict(manifest["label_counts"])
    write_json(output_dir / "manifest.json", manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="qlf--diagnostics repository root",
    )
    parser.add_argument(
        "--pcs-root",
        type=Path,
        default=Path("/home/qlf/IOT/references/pcs-harness-align-origin-main-20260815"),
        help="PCS worktree root containing source_state artifacts",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        action="append",
        default=None,
        help="Admission summary JSON. May be passed multiple times.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("generated/physical_closure_classifier_20260822_v1"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    pcs_root = args.pcs_root.resolve()
    summary_paths = args.summary or DEFAULT_SUMMARIES
    summary_paths = [path if path.is_absolute() else repo_root / path for path in summary_paths]
    output_dir = args.output_dir if args.output_dir.is_absolute() else repo_root / args.output_dir
    manifest = build_classifier_outputs(repo_root, pcs_root, summary_paths, output_dir)
    print(
        json.dumps(
            {
                "output_dir": manifest["output_dir"],
                "record_count": manifest["record_count"],
                "feature_count": manifest["feature_count"],
                "admitted_count": manifest["admitted_count"],
                "label_counts": manifest["label_counts"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
