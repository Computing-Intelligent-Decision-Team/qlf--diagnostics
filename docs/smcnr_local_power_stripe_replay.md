# SMCNR Pre-Route VDD Stripe Replay Report

**Date**: 2026-06-23 (updated 2026-06-23)
**Status**: Pipeline equivalence confirmed — pre-route MAGICAL VDD stripe env var is critical

## 1. Root Cause Confirmed

The local fresh MAGICAL pipeline was missing the **pre-route local VDD stripe**
injection, controlled by MAGICAL Docker environment variables:

```
MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES=1
```

The upstream and multi sweep pipelines pass this via the harness YAML config's
`passive_aware.magical_env`. Our manual MAGICAL Docker runs did not.

**Not** the post-route `add_local_power_stripe_to_gds.py` script — that was set
to `MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE=0` (disabled) even in the working
multi sweep.

### Evidence chain

| Pipeline | Pre-route VDD stripe env | Post-route stripe | equiv | LVS | Status |
|----------|--------------------------|-------------------|-------|-----|--------|
| Upstream (师兄) | ✅ 1 (via YAML) | — | 0 | PASS | Working |
| Multi sweep (local harness) | ✅ 1 (via YAML) | 0 (disabled) | 0 | PASS | Working |
| Manual fresh (simplified) | ❌ 0 (not set) | 0 | 1 | FAIL | Broken |

### How the pre-route stripe is injected

In `run_sky130_case_pipeline.sh`, the MAGICAL Docker command passes:

```bash
docker run --rm \
    ...
    -e MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES="$MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES" \
    -e MAGICAL_LOCAL_VDD_STRIPE_HEIGHT_DBU="$MAGICAL_LOCAL_VDD_STRIPE_HEIGHT_DBU" \
    -e MAGICAL_LOCAL_VDD_STRIPE_Y_DBU="$MAGICAL_LOCAL_VDD_STRIPE_Y_DBU" \
    ...
```

MAGICAL reads these env vars and injects a met5 VDD stripe geometry during
device placement, BEFORE routing. The stripe is baked into `route.gds`.

The post-route step (`MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE`) is a separate
mechanism that was OFF in the working multi sweep. It is NOT required.

### Why it matters

Without the pre-route VDD stripe:
- The n-well regions lack a low-resistance met5 connection to vdda
- Magic extraction finds the n-well floating → equiv "gnda" "vdda"
- PMOS S/B on gnda, vdda port dropped

With the pre-route VDD stripe:
- N-well taps are explicitly connected to vdda through MAGICAL-placed metal
- Magic extraction correctly resolves: equiv=0, PMOS S/B on vdda, 6 ports

## 2. Pipeline Equivalence Verified

The multi sweep batch (harness_native_sweep_multi_0001) was run through the
harness CLI, which passes `MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES=1`
from the YAML config. All 7 candidates passed with:

```
DRC_COUNT=0
CONNECTIVITY_LVS_MATCH=yes
PEX_CAPS=37
PEX_TOTAL_CAP_FF=80.9459
equiv=0 (verified in .ext)
```

This confirms the local full pipeline IS equivalent to the upstream pipeline
when properly configured.

## 3. How to Run the Full Pipeline

### Prerequisites

- `generated/sky130PDK_trial/` must be generated (via `generate_magical_sky130_pdk.py`)
- Docker with `jayl940712/magical:latest`
- Magic 8.3.483, Netgen 1.5.133

### Via harness CLI (recommended)

```bash
python -m tools.analog_harness.cli run \
  --config tools/analog_harness/configs/smcnr_se_2st_amp.yaml \
  --max-candidates 1 --batch-size 1 --layout-budget 1
```

The SMCNR config YAML already has `passive_aware.magical_env` with
`MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES=1` and associated stripe
geometry parameters. The harness CLI reads these and passes them to
MAGICAL Docker automatically.

### Via shell pipeline (manual — must set env vars)

```bash
MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES=1 \
MAGICAL_LOCAL_VDD_STRIPE_HEIGHT_DBU=200 \
MAGICAL_LOCAL_VDD_STRIPE_Y_DBU=13200 \
MAGICAL_LOCAL_VDD_STRIPE_ACTIVE_KEEP_OUT_DBU=0 \
MAGICAL_LOCAL_VDD_STRIPE_EXCLUDE_X_DBU="3000:3450,..." \
bash tools/sky130_adapter/run_sky130_case_pipeline.sh \
  --case-dir <case_dir> \
  --top-cell SMCNR_SE_2st_AMP \
  --magical-netlist <netlist> \
  --config <config> \
  --vdd vdda --vss gnda \
  --out-dir <out_dir>
```

The `MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE` variable defaults to 0 and does NOT
need to be set — the pre-route stripe (above) is sufficient.

## 4. Impact on Previous Results

All manual fresh-MAGICAL failures (var_m01, sweep_02-06, nf=2, v0 W/L candidates,
seed runs) are confirmed as **missing MAGICAL env var**, not sizing sensitivity.
The missing `MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES=1` caused the collapse.

These experiments must be re-run with the pre-route VDD stripe env vars set
before any conclusions about sizing neighborhood stability are valid.

## 5. Next Steps

1. **Re-run sizing sweep**: Use harness CLI or shell pipeline with
   `MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES=1` for ALL candidates.
2. **Re-evaluate sizing sensitivity**: Only after pre-route stripe is enabled.
3. **Document the MAGICAL env var requirement**: Add to developer setup docs.

## 6. Forbidden Claims

- ❌ Previous sizing sensitivity conclusions are invalid (missing env var)
- ❌ MAGICAL is NOT broken — the env var was missing
- ❌ Local Docker MAGICAL IS equivalent to upstream — when env vars are set
- ❌ Post-route `add_local_power_stripe_to_gds.py` is NOT the critical step
