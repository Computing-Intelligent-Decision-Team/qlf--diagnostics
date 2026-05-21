#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REGISTRY="$SCRIPT_DIR/sky130_case_registry.yaml"
SUMMARY="$REPO_ROOT/generated/sky130_cases/regression_summary.md"
RUN_LOG_DIR="$REPO_ROOT/generated/sky130_cases/regression_logs"

mkdir -p "$RUN_LOG_DIR"

registry_rows="$(
    python3 - "$REGISTRY" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]).resolve().parent))
from collect_sky130_case_summaries import load_registry

for case in load_registry(Path(sys.argv[1])):
    fields = [
        "name",
        "case_dir",
        "top_cell",
        "vdd",
        "vss",
        "convert_xschem",
        "raw_netlist",
        "magical_netlist",
        "config",
        "out_dir",
        "output_node",
    ]
    print("\t".join(case.get(field, "") for field in fields))
PY
)"

failed=0
while IFS=$'\t' read -r name case_dir top_cell vdd vss convert_xschem raw_netlist magical_netlist config out_dir output_node; do
    [[ -n "$name" ]] || continue
    echo "RUN CASE: $name"
    log="$RUN_LOG_DIR/${name}.log"
    args=(
        --case-name "$name"
        --case-dir "$case_dir"
        --top-cell "$top_cell"
        --magical-netlist "$magical_netlist"
        --config "$config"
        --vdd "$vdd"
        --vss "$vss"
        --out-dir "$out_dir"
        --convert-xschem "$convert_xschem"
    )
    if [[ -n "$raw_netlist" ]]; then
        args+=(--raw-netlist "$raw_netlist")
    fi
    if [[ -n "$output_node" ]]; then
        args+=(--output-node "$output_node")
    fi

    set +e
    "$SCRIPT_DIR/run_sky130_case_pipeline.sh" "${args[@]}" > "$log" 2>&1
    status=$?
    set -e
    if [[ "$status" -ne 0 ]]; then
        echo "FAIL CASE: $name (see $log)" >&2
        failed=1
    else
        echo "PASS CASE: $name"
    fi
done <<< "$registry_rows"

echo "RUN: collect regression summaries"
set +e
python3 "$SCRIPT_DIR/collect_sky130_case_summaries.py" \
    --registry "$REGISTRY" \
    --output "$SUMMARY"
collect_status=$?
set -e

echo "Regression summary written: $SUMMARY"
if [[ "$failed" -ne 0 || "$collect_status" -ne 0 ]]; then
    exit 1
fi
