#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="/home/qlf/IOT"
PCS_ROOT="$WORKSPACE/references/.codex-worktrees/pcs-harness-workflow"
APP_ROOT="$WORKSPACE/apps/pcs-harness-workflow"
HARNESS_PYTHON="/home/qlf/anaconda3/envs/Harness/bin/python"
DEFAULT_SKY130A="/home/qlf/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A"
RUNS_ROOT="$WORKSPACE/generated/analog_harness/ota_core_grpo_demo_20260826/recording_run"
SELECTION="$WORKSPACE/generated/analog_harness/ota_core_grpo_demo_20260826/boundary_scan/selection.json"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --run-root)
            RUNS_ROOT="$2"
            shift 2
            ;;
        --selection)
            SELECTION="$2"
            shift 2
            ;;
        *)
            echo "unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

for required in "$PCS_ROOT" "$APP_ROOT" "$HARNESS_PYTHON" "$DEFAULT_SKY130A"; do
    if [[ ! -e "$required" ]]; then
        echo "required path is missing: $required" >&2
        exit 2
    fi
done
if [[ ! -f "$SELECTION" ]]; then
    echo "frozen boundary selection is missing: $SELECTION" >&2
    echo "run workflow-boundary-scan before recording rehearsal" >&2
    exit 2
fi

mkdir -p "$RUNS_ROOT"
source "$WORKSPACE/scripts/env/magical_sky130_env.sh"
export IOT_WORKSPACE="$WORKSPACE"
export PCS_HARNESS_ROOT="$PCS_ROOT"
export PCS_HARNESS_PYTHON="$HARNESS_PYTHON"
export PCS_WORKFLOW_RUNS_ROOT="$RUNS_ROOT"
export PCS_WORKFLOW_BOUNDARY_SELECTION="$SELECTION"
export PCS_WORKFLOW_HOST="127.0.0.1"
export PCS_WORKFLOW_PORT="8103"
export SKY130A="${SKY130A:-$DEFAULT_SKY130A}"
export MAGICAL_ANAROUTE_PYTHONPATH="${MAGICAL_ANAROUTE_PYTHONPATH:-/MAGICAL/generated/analog_harness/stage2_pin_shape_repair_v1/preflight/anaroute_release_module}"

cleanup() {
    local status=$?
    trap - EXIT INT TERM
    if [[ -n "${API_PID:-}" ]]; then kill "$API_PID" 2>/dev/null || true; fi
    if [[ -n "${WEB_PID:-}" ]]; then kill "$WEB_PID" 2>/dev/null || true; fi
    wait "${API_PID:-}" "${WEB_PID:-}" 2>/dev/null || true
    exit "$status"
}
trap cleanup EXIT INT TERM

cd "$APP_ROOT"
"$HARNESS_PYTHON" backend/app.py &
API_PID=$!
pnpm dev --host 127.0.0.1 --port 3103 &
WEB_PID=$!

echo "PCS-Harness Workflow: http://127.0.0.1:3103/"
echo "Live API: http://127.0.0.1:8103/"
echo "No circuit run starts until the verified OTA netlist is submitted in the browser."
wait -n "$API_PID" "$WEB_PID"
