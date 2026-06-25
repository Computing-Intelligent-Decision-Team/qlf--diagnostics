# SMCNR PMOS-L Monte Carlo Pipeline Report

**Date**: 2026-06-24
**Status**: Production-ready; 15/16 LVS PASS (94%), 2 verified PMOS L axes

## 1. Pipeline Overview

The SMCNR PMOS-L Monte Carlo pipeline generates parasitic modeling candidates
by perturbing PMOS channel lengths around the verified cand_0031 baseline. All
candidates go through MOS-only projection → MAGICAL → extraction → auto-rename
→ Netgen LVS → PEX before trust classification.

```text
cand_0031 baseline sizing
  → PMOS-L perturbation (±1% to ±5%, whitelist: bias_pmos_l, second_stage_pmos_l)
  → MOS-only projection (R+C passives stripped)
  → MAGICAL Docker (placement + routing, jayl940712/magical:latest)
  → Sky130 GDS remap
  → Magic DRC (require 0 errors)
  → Magic extraction (require equiv=0, 6 ports, PMOS S/B on vdda)
  → auto_lvs_rename_smcnr.py (auto-discover net renames)
  → Netgen LVS (require Circuits match uniquely)
  → PEX parsing
  → trust gate (classify: review-pool / rejected / failure-only)
```

## 2. Tool Locations

| Tool | Path | Role |
|------|------|------|
| MC runner | `tools/analog_harness/ml/smcnr_pmos_l_mc_runner.py` | Generate candidates, run batch |
| Auto LVS rename | `tools/analog_harness/ml/auto_lvs_rename_smcnr.py` | Auto-discover net renames for LVS |
| Dataset registry | `tools/analog_harness/ml/parasitic_dataset.py` | Register samples with trust labels |
| Multi-seed runner | `generated/smcnr_variants/mc_pmos_l_0001/multi_seed_runner.py` | Seed-level retry logic |

## 3. Verified Parameter Axes

| Axis | Sensitivity | Safe range | LVS pass rate |
|------|------------|------------|---------------|
| `bias_pmos_l` | High (triggers structural change at ±1%) | ±1% to ±5% | 8/8 (100%) |
| `second_stage_pmos_l` | Medium (triggers structural change at ±3-5%) | -5% to +3% | 7/8 (88%) |

### Forbidden axes (do not perturb)

| Parameter | Reason |
|-----------|--------|
| `diff_pair_w`, `diff_pair_l` | MAGICAL grid assertion crash |
| `nf` (any device) | Device count split (8→10), extraction collapse |
| `multi` (any device) | No confirmed PEX diversity after normalization |
| Full passive-inclusive netlist | R+C geometry triggers well/substrate collapse locally |

## 4. Batch 0001 Results (16 candidates, 2 axes)

| Candidate | Axis | ΔL | Caps | ΔTotal (fF) | LVS | Class |
|-----------|------|-----|------|-------------|-----|-------|
| mc_bias_pmos_0p95 | bias_pmos | -5% | 35 | -0.70 | PASS | structural |
| mc_bias_pmos_0p97 | bias_pmos | -3% | 35 | -0.37 | PASS | structural |
| mc_bias_pmos_0p98 | bias_pmos | -2% | 35 | -0.31 | PASS | structural |
| mc_bias_pmos_0p99 | bias_pmos | -1% | 36 | -0.05 | PASS | structural |
| mc_bias_pmos_1p01 | bias_pmos | +1% | 35 | +0.33 | PASS | structural |
| mc_bias_pmos_1p02 | bias_pmos | +2% | 35 | +0.38 | PASS | structural |
| mc_bias_pmos_1p03 | bias_pmos | +3% | 35 | +0.66 | PASS | structural |
| mc_bias_pmos_1p05 | bias_pmos | +5% | 35 | +1.10 | PASS | structural |
| mc_2nd_stage_0p95 | 2nd_stage | -5% | 35 | -0.28 | PASS | structural |
| mc_2nd_stage_0p97 | 2nd_stage | -3% | 36 | -0.24 | PASS | structural |
| mc_2nd_stage_0p98 | 2nd_stage | -2% | 36 | -0.21 | PASS | structural |
| mc_2nd_stage_0p99 | 2nd_stage | -1% | 36 | -0.03 | PASS | structural |
| mc_2nd_stage_1p01 | 2nd_stage | +1% | 36 | +0.10 | PASS | structural |
| mc_2nd_stage_1p02 | 2nd_stage | +2% | 36 | +0.12 | PASS | structural |
| mc_2nd_stage_1p03 | 2nd_stage | +3% | 35 | +0.32 | PASS | structural |
| mc_2nd_stage_1p05 | 2nd_stage | +5% | 35 | -2.02 | FAIL | **rejected** |

## 5. Integration Points

### Extending the dataset

After a batch completes, add passing candidates to `parasitic_dataset.py`:

```python
{
    "sample_id": "mc_bias_pmos_1p03",
    "circuit": "SMCNR_SE_2st_AMP",
    "lvs_status": "PASS",
    "trust_scope": "mos_only_projection",
    "candidate_for_parasitic_modeling_review": True,
    "evidence_scope": "mos_only_projection",
    "diversity_class": "structural_diverse",
    ...
}
```

### Running auto-rename + LVS

```bash
python3 tools/analog_harness/ml/auto_lvs_rename_smcnr.py \
  --batch generated/smcnr_variants/mc_pmos_l_0001
```

### Regenerating the dataset

```bash
python3 -m tools.analog_harness.ml.parasitic_dataset \
  --output generated/parasitic_modeling/dataset_v0.jsonl \
  --summary
```

## 6. Known Issues

1. **magic_extract writes to CWD**: The extraction outputs (.ext, .spice) are
   written to the current working directory. The runner copies them to the
   seed directory afterward. If two extractions run concurrently, file
   collisions occur.
2. **Docker-owned files**: MAGICAL creates files owned by root. Cleanup
   requires `sudo rm -rf` or `docker run --user`.
3. **PDK path depth sensitivity**: MAGICAL config uses relative paths to
   `sky130PDK_trial/`. The number of `../` levels depends on the case
   directory depth. All runners must use the same depth as the baseline.
4. **Anonymous node naming**: Magic extraction produces different anonymous
   node names for each MAGICAL run. The auto-rename tool handles this via
   suffix pattern matching, but new suffixes may require pattern updates.

## 7. Trust Boundary

- `cand_0031` is the only reviewed positive baseline (training-positive).
- All MC/L-only samples are MOS-only projection review-pool candidates.
- `usable_for_supervised_positive_training=false` for all new samples.
- Passive-inclusive evidence is not claimed from MOS-only extraction.
- No candidate is promoted to training-positive without Codex review.
