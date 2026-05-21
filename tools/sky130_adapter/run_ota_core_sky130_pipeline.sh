#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/run_sky130_case_pipeline.sh" \
    --case-name ota_core \
    --case-dir examples/ota_core_sky130_try \
    --top-cell ota_core \
    --raw-netlist ota_core_raw.spice \
    --magical-netlist ota_core_magical.sp \
    --config ota_core.json \
    --vdd VDD \
    --vss GND \
    --out-dir generated/sky130_cases/ota_core \
    --convert-xschem yes
