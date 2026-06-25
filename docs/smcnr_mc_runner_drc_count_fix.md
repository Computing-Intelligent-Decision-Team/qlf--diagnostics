# SMCNR MC Runner DRC Count Fix

**Date**: 2026-06-25
**Status**: Fixed — runner is production-ready

## Problem

Before the fix, the runner's `_run_extraction` function used a custom Tcl
command `set drc_total [drc count total]` which produced no stdout output,
leaving `drc_count=None` for all candidates. The gate `if drc_count not in
(0, None)` allowed accepted samples with `drc_count=None` — unacceptable
for trust gate.

## Fix

### 1. Tcl: use standard Magic DRC output

Changed from:
```tcl
drc euclidean on
drc check
set drc_total [drc count total]
puts "DRC_COUNT=$drc_total"
```

To:
```tcl
drc check
drc catch
drc count
```

Magic writes "Total DRC errors found: N" to stdout when `drc count` runs.

### 2. Parsing: parse standard Magic output

```python
drc_match = re.search(r"Total DRC errors found:\s*(\d+)", combined)
if not drc_match:
    drc_match = re.search(r"DRC_COUNT[= ](\d+)", combined)  # fallback
drc_count = int(drc_match.group(1)) if drc_match else None
```

### 3. Gate: reject drc_count=None

```python
if drc_count is None:
    return rejected("drc_unknown")
if drc_count != 0:
    return rejected("drc_nonzero")
```

Only `drc_count == 0` proceeds to equiv/LVS/PEX checks.

## Smoke Test

| Field | Value |
|-------|-------|
| sample_id | smoke_bias_pmos_l_0p95_seed01 |
| status | accepted |
| drc_count | **0** |
| equiv_count | 0 |
| lvs_pass | true |
| pex_caps | 36 |
| pex_total_cap_ff | 80.2488 |

## Tests

```
python3 -m unittest tools.analog_harness.tests.test_parasitic_dataset \
  tools.analog_harness.tests.test_analoggym_importer -v
# 24/24 OK
```
