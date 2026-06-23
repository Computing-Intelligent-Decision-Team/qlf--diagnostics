# SMCNR Upstream vs Local GDS/Extraction Diff

**Date**: 2026-06-23
**Status**: Root cause identified — missing local power stripe

## 1. Evidence Sources

| Source | Path | Origin |
|--------|------|--------|
| Upstream (clean) | `origin/main:reproducibility/.../upstream_artifacts/` → `/tmp/smcnr_upstream/` | Windows + WSL, `python -m tools.analog_harness.cli run` |
| Local (failed) | `generated/smcnr_variants/seed_test/run1/` | Linux WSL2, manual Docker MAGICAL + remap + pin |

## 2. Extraction Comparison

| Metric | Upstream (clean) | Local fresh (failed) |
|--------|-----------------|---------------------|
| `equiv` records | **0** ✅ | **1** ❌ `equiv "gnda" "vdda"` |
| `substrate` | `"gnda"` | `"gnda"` |
| Port definitions in `.ext` | 6 (vdda=1, gnda=2) | 6 (vdda=2, gnda=3) |
| Ports in `.subckt` | `vdda gnda vin vip ibias vout` | `gnda vin vip ibias vout` (no vdda) |
| Substrate box origin | x=146311 | x=0 |
| Substrate box size | 3393850×34102 | 9079772×120472 (2.7× larger → more area merged) |

## 3. GDS Chain Comparison

| GDS Stage | Upstream | Local fresh | Note |
|-----------|----------|-------------|------|
| `floorplan.gds` | 72K | — | Not produced |
| `place.gds` | 516K | — | Not saved |
| `route.gds` | 522K | 429K | Present in both; upstream 22% larger |
| `sky130.gds` | 522K | 429K | Remapped |
| `sky130.pinned.gds` | 523K | — | Not saved separately |
| `sky130.pinned_shapes.gds` | 523K | — | Not saved separately |
| **`sky130.pinned_shapes.local_power.gds`** | **431K** | **— MISSING** | **Critical gap** |
| `_init.gds` | 5.1M | — | MAGICAL init cell library |

## 4. Root Cause: Missing Pre-Route Local VDD Stripe Env Var

### 4.1 What the pre-route local VDD stripe does

The MAGICAL placer can inject a met5 VDD stripe during device placement
(before routing), controlled by environment variables passed to the MAGICAL
Docker container:

```
MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES=1
MAGICAL_LOCAL_VDD_STRIPE_HEIGHT_DBU=200
MAGICAL_LOCAL_VDD_STRIPE_Y_DBU=13200
MAGICAL_LOCAL_VDD_STRIPE_ACTIVE_KEEP_OUT_DBU=0
MAGICAL_LOCAL_VDD_STRIPE_EXCLUDE_X_DBU=3000:3450,...
```

This stripe:
1. Is added DURING MAGICAL placement (baked into `route.gds`)
2. Physically connects the `vdda` port region to n-well taps
3. Ensures the n-well is properly biased to vdda potential
4. Provides a low-resistance path for well current

### 4.2 Why its absence causes equiv gnda-vdda

Without the pre-route VDD stripe:
- The n-well regions lack a continuous low-resistance met5 connection to vdda
- Magic extraction finds the n-well floating or weakly connected
- The n-well/p-substrate diode junction is interpreted as a DC path
- Result: `equiv "gnda" "vdda"` — extraction collapses the two domains

With the pre-route VDD stripe:
- The n-well is firmly tied to vdda through explicit met5 geometry in the GDS
- Magic extraction correctly resolves n-well potential as vdda
- PMOS bulk terminals stay on vdda
- No equiv between vdda and gnda

### 4.3 Evidence

| Evidence | Upstream | Multi sweep (local, works) | Manual (local, fails) |
|----------|----------|---------------------------|----------------------|
| `MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES` | 1 (via YAML) | 1 (via YAML) | **0 (not set)** |
| GDS size (route.gds) | 522K | 429K | 429K |
| Substrate box origin X (upstream) | 146311 | — | 0 |
| equiv count | 0 | 0 | 1 |
| LVS | PASS | PASS | FAIL |

The post-route `add_local_power_stripe_to_gds.py` step (`MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE`)
was set to **0** (disabled) in the working multi sweep. It is NOT required for clean extraction.
The pre-route stripe injected by MAGICAL during placement IS required.

## 5. ioPin Differences

The upstream ioPin has larger pin boxes, reflecting a physically larger chip:

| Pin | Upstream box (x1,y1)-(x2,y2) | Local box |
|-----|------------------------------|-----------|
| vdda | (-13700, 35550)-(48500, 37350) | (1900, 35550)-(32900, 37350) |
| gnda | (-13700, -3700)-(48500, -1900) | (1900, -3700)-(32900, -1900) |
| vout | layer 2, (13200, 15350)-(54900, 15450) | layer 1, (13350, 13950)-(13450, 15450) |

The upstream chip is ~62K DBU wide; the local chip is ~34K DBU wide. The
upstream vout is on met1 (layer 2), while local vout is on li1 (layer 1).

## 6. Pipeline Step Comparison

| Step | Upstream (harness CLI) | Local (manual) |
|------|----------------------|----------------|
| Netlist compilation | `SpiceCandidateCompiler` | Manual SPICE template |
| MAGICAL config | Auto-generated with `lvsNetRenames` | Manual JSON |
| PDK path | `../../../../sky130PDK_trial/` (relative, resolves in Docker) | `/MAGICAL/examples/sky130PDK/` (Docker-internal) |
| MOS-only projection | Yes (drops passives for initial layout) | No (includes passives) |
| Pre-route VDD stripe env | Yes (`MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES=1`) | **No — MISSING** |
| Post-route VDD stripe | 0 (disabled, not needed) | 0 |
| LVS netlist prep | `prepare_lvs_netlists.py` | No |
| `lvsNetRenames` | Auto-discovered from first-pass extraction | Hardcoded from var_ref_000 |

## 7. Fix Plan

### Immediate (to make local fresh pipeline work)

1. **Pass pre-route VDD stripe env vars to MAGICAL Docker**: Set
   `MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES=1` and associated
   `MAGICAL_LOCAL_VDD_STRIPE_*` vars. The harness YAML config already defines
   these values; the harness CLI passes them automatically.

2. **Use the full pipeline**: `run_sky130_case_pipeline.sh` (or harness CLI)
   which passes all MAGICAL env vars from config and handles LVS netlist prep
   with auto-discovered renames.

### Verification

After enabling pre-route VDD stripe, re-run fresh MAGICAL and verify:
- equiv = 0
- 6 ports in extracted subckt
- PMOS S/B on vdda

The multi sweep (`harness_native_sweep_multi_0001`) already verified this:
7/7 candidates passed with `DRC=0, LVS=yes, PEX=37`.

## 8. Impact on Previous Results

All previous fresh-MAGICAL extraction failures (var_m01, sweep_02-06,
nf=2, v0 candidates, seed runs) are **invalidated as evidence of sizing
sensitivity**. The failures were caused by missing
`MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES=1` env var in manual
MAGICAL Docker runs — not by parameter perturbation. These experiments
must be re-run with the pre-route VDD stripe enabled before any
conclusions about sizing neighborhood stability can be drawn.

## 9. Forbidden Claims

- ❌ Previous "sizing sensitivity" conclusions are NOT valid (missing MAGICAL env var)
- ❌ MAGICAL-Sky130 extraction is NOT fundamentally broken — env var was missing
- ❌ The collapse is NOT caused by PDK quality or device cells
- ❌ The post-route `add_local_power_stripe_to_gds.py` is NOT the critical step
- ❌ Sizing perturbation effects are STILL UNKNOWN until re-tested with fixed pipeline
