#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/run_sky130_case_pipeline.sh" \
    --case-name SMCNR_SE_2st_AMP \
    --case-dir examples/smcnr_se_2st_amp_sky130_try \
    --top-cell SMCNR_SE_2st_AMP \
    --magical-netlist SMCNR_SE_2st_AMP_layout_physical_hspice.sp \
    --config smcnr_se_2st_amp.json \
    --vdd vdda \
    --vss gnda \
    --out-dir generated/sky130_cases/smcnr_se_2st_amp \
    --convert-xschem no \
    --output-node vout
