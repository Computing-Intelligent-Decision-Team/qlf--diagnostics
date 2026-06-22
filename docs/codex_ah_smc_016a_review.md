# Codex Review: AH-SMC-016A Differential Audit

## Verdict

**Accepted with required follow-up.**

AH-SMC-016A is accepted for its narrow conclusion:

> NMOS `.pin` fourth entry `-1` is not sufficient as a single-variable root
> cause.

The audit should not yet be treated as proof that Fan_SMC is primarily a MAGICAL
geometry defect. New external provenance from the SMCNR author says the SMCNR
work "largely changed netgen", did not modify NMOS, and mainly built the
Harness. That makes Netgen/LVS normalization and extraction setup a first-class
hypothesis before any MAGICAL source patch.

## Findings

### 1. Missing H4: Netgen / LVS normalization / Harness setup divergence

Severity: high

AH-SMC-016A compares `.pin`, source body nets, and extracted body nets, but it
does not audit whether SMCNR and Fan_SMC use the same Magic extraction options,
LVS preparation script, Netgen setup, normalization rules, source/extracted
renames, passive abstraction, or model-alias policy.

This matters because the SMCNR author stated that the successful SMCNR path
mostly involved Netgen-side changes rather than MAGICAL NMOS changes. Therefore
the next hypothesis must be explicit:

`H4: SMCNR passes because its Harness/Netgen/LVS preparation path normalizes or
abstracts connectivity differently from the Fan_SMC diagnostic path.`

### 2. Magic extraction commands differ between SMCNR and Fan_SMC

Severity: high

The local artifacts show a concrete extraction setup difference:

- SMCNR `magic_extract.tcl`:
  - `ext2spice lvs`
  - `ext2spice cthresh 0`
  - `ext2spice rthresh 0`
  - `ext2spice`

- Fan_SMC psub-tap `magic_extract.tcl`:
  - `ext2spice lvs`
  - `ext2spice cthresh 0`
  - `ext2spice short`
  - `ext2spice`

Before concluding that geometry is the primary differentiator, AH-SMC-016B
should test or at least document the effect of `ext2spice short` and any other
extraction Tcl differences.

### 3. SMCNR GDS is not missing

Severity: medium

AH-SMC-016A states that SMCNR GDS is missing from the reproducibility package.
That is inaccurate for the current local tree. These files exist:

- `reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/gds/SMCNR_SE_2st_AMP.sky130.pinned_shapes.gds`
- `reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/gds/SMCNR_SE_2st_AMP.sky130.pinned_shapes.local_power.gds`
- `reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/gds/native_cap_replaced.gds`

The exact original `layout/lvs_mos_projection_case/...pinned_shapes.gds` path is
not present, but the packaged GDS exists and should be used cautiously for
geometry comparison after recording SHA256 and scope.

### 4. H2/H3 are supported only as candidates, not as final root cause

Severity: medium

Fan_SMC has strong local evidence for psub/diffusion and routing contamination,
but SMCNR lacks local `.ext` and Magic extraction logs. AH-SMC-016A's language
that geometry/substrate/extraction is "the" divergence should be softened to
"candidate divergence". The stronger conclusion is:

`.pin=-1` alone is disproven; the remaining root cause is unresolved among
geometry/substrate/routing and Netgen/LVS setup differences.

## Required Next Task

Run AH-SMC-016B as a read-only provenance/config audit.

Required outputs:

- `docs/ah_smc_016b_netgen_setup_audit.md`
- `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016b/ah_smc_016b_records.json`

Required comparisons:

- Magic extraction Tcl options for SMCNR vs Fan_SMC.
- Netgen setup file path and SHA256 if available.
- Netgen command line / run Tcl for both.
- LVS preparation reports and normalization policies.
- Source model alias rules.
- Extracted net renames.
- Passive abstraction / passive drop policy.
- Whether `ext2spice short` changes Fan_SMC extracted body collapse.

Keep all trust flags failure-case only for Fan_SMC.

## Stop Gate

Do not authorize AH-SMC-016 MAGICAL source modification yet. The current safest
path is:

1. Accept AH-SMC-016A as H1-disproving evidence.
2. Run AH-SMC-016B for Netgen/setup provenance.
3. Only revisit MAGICAL source changes if setup-normalized Fan_SMC still fails
   with the same body-collapse mechanism.
