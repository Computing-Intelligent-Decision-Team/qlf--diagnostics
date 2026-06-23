# SMCNR sky130PDK_trial Provenance Audit

**Date**: 2026-06-23
**Status**: No single root cause identified — residual nondeterminism suspected

## 1. Timeline

| Time | Event |
|------|-------|
| 12:09 | `generated/sky130PDK_trial/` regenerated via `generate_magical_sky130_pdk.py` |
| 15:38 | Multi sweep var_ref_000 MAGICAL GDS generated |
| 15:41 | Multi sweep batch completed: 7/7 PASS |
| 16:00+ | All subsequent harness/shell runs FAIL at magic_extract |

**The multi sweep used the SAME PDK trial that is present now.** The PDK trial
was regenerated at 12:09, and the multi sweep ran at 15:38 — 3.5 hours later.
This eliminates the PDK trial version as the root cause.

## 2. Variables Eliminated

| Variable | Checked | Conclusion |
|----------|---------|------------|
| Netlist content | Diff: identical (formatting only) | Not the cause |
| Config JSON | Diff: identical except filename | Not the cause |
| lvsNetRenames | Present in both | Not the cause |
| MAGICAL PDK trial | Same version (12:09 gen, used at 15:38) | Not the cause |
| CIEL vs bundled PDK | Multi sweep used CIEL; harness run used CIEL too | Not the cause |
| Harness controller vs shell | Both fail in current environment | Not the cause |
| Magic version | 8.3.483 in both | Not the cause |
| MOS-only projection netlist | Byte-identical (except formatting) | Not the cause |
| Techfile diff | Comment-only differences from examples/ | Not functional |
| Git tracking | `generated/` in .gitignore, not tracked | Cannot recover old version |
| Upstream artifact | Does not contain PDK trial | Cannot recover from upstream |

## 3. Remaining Hypotheses

### 3.1 MAGICAL Docker nondeterminism (most likely)

MAGICAL placement/routing is nondeterministic (proven: different md5 for same
netlist). The multi sweep may have coincidentally produced 7 consecutive
"good" placements that extract cleanly. Subsequent runs produce "bad"
placements that trigger well/substrate extraction collapse.

Probability: 7/7 consistent success by chance is low but not impossible,
especially if the multi sweep ran in quick succession (similar Docker state).

### 3.2 Docker state dependency

The first MAGICAL Docker run after container/image pull may behave differently
from subsequent runs. Docker caches layers and container state. The multi sweep
may have run in a "fresh" Docker state, while subsequent runs run in a
different state.

### 3.3 System load / timing

MAGICAL placement uses randomized algorithms that may be sensitive to system
timing. Different system load at 15:38 vs 16:00+ could produce different
placement seeds.

## 4. Recommended Path Forward

### Immediate

1. **Run MAGICAL multiple times with identical inputs** and check the extraction
   pass rate. If ~50% pass, nondeterminism is confirmed.
2. **If pass rate is low (<30%)**, the current MAGICAL+PDK combination is
   unreliable for production. Consider:
   - Pinning MAGICAL random seed (if possible)
   - Using a different PDK that produces consistent device cells
   - Reverting to the upstream pre-generated GDS as the only reliable source

### Longer term

3. **Request the original `generated/sky130PDK_trial/`** from the multi sweep
   run environment (even if identical, worth verifying byte-level).
4. **Consider making PDK trial git-tracked** (add to `.gitignore` exception
   like the reproducibility directory) to prevent silent regeneration.
5. **Add an extraction smoke test** to the pipeline: after MAGICAL, immediately
   extract and verify equiv=0 before proceeding to LVS.

## 5. Current State

| Item | Status |
|------|--------|
| Multi sweep (7/7 PASS) | Only reliable batch |
| All subsequent runs | FAIL at magic_extract |
| Root cause | Unconfirmed — likely MAGICAL nondeterminism |
| PDK trial | Same version used by multi sweep |
| Positive dataset | cand_0031 only (n=1) |
| W/L sweep | Blocked until extraction reliability restored |
