#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CASE_DIR="$REPO_ROOT/examples/inverter_sky130_try"

if [[ ! -f "$CASE_DIR/inverter_trial.json" || -w "$CASE_DIR/inverter_trial.json" ]]; then
    cat > "$CASE_DIR/inverter_trial.json" <<'JSON'
{
    "spectre_netlist" : "inverter_sky130_name_test.sp",
    "resultDir" : "./",
    "techfile" : "../../generated/sky130PDK_trial/sky130.techfile",
    "simple_tech_file" : "../../generated/sky130PDK_trial/sky130.techfile.simple",
    "lef" : "../../generated/sky130PDK_trial/sky130.lef",
    "vddNetNames" : ["VPWR"],
    "vssNetNames" : ["VGND"]
}
JSON
else
    echo "NOTE: using existing read-only inverter_trial.json"
fi

"$SCRIPT_DIR/run_sky130_case_pipeline.sh" \
    --case-name inverter_core \
    --case-dir examples/inverter_sky130_try \
    --top-cell inverter_core \
    --raw-netlist inverter_sky130_name_test.sp \
    --magical-netlist inverter_sky130_name_test.sp \
    --config inverter_trial.json \
    --vdd VPWR \
    --vss VGND \
    --out-dir generated/sky130_cases/inverter_core \
    --convert-xschem no
