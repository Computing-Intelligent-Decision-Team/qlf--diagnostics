# Codex Review: AH-SMC-016B Netgen/LVS Setup Provenance Audit

## Verdict

**Accepted with scoped corrections.**

AH-SMC-016B correctly moves the investigation away from immediate MAGICAL
source modification and toward verification provenance. It identifies the hard
Fan_SMC blocker:

- Magic extraction writes `substrate "vout"`.
- Magic extraction writes `equiv "vout" "vdda"` and `equiv "vout" "gnda"`.
- The extracted subcircuit drops `gnda` and `vdda`, leaving only
  `vinn vinp vout`.

That evidence is strong enough to keep Fan_SMC failure-case only and to block
any closure/training/reward claim.

## Accepted Findings

### 1. H1 remains disproven

SMCNR and Fan_SMC both have NMOS `.pin` fourth entries set to `-1`, but SMCNR
passes MOS-only LVS while Fan_SMC collapses substrate/body connectivity. The
`.pin=-1` fact alone is not sufficient as the single-variable root cause.

### 2. The psub-tap Fan_SMC extraction Tcl matches SMCNR

The psub-tap Fan_SMC run and SMCNR both use:

```tcl
extract all
ext2spice lvs
ext2spice cthresh 0
ext2spice rthresh 0
ext2spice
```

The earlier `ext2spice short` difference applies to a different Fan_SMC extract
artifact, not the psub-tap LVS path audited by AH-SMC-016B.

### 3. Port collapse is a primary hard blocker

Fan_SMC source connectivity has five ports:

```spice
.subckt fan_smc_pin_3 gnda vdda vinn vinp vout
```

Fan_SMC extracted connectivity has only three:

```spice
.subckt fan_smc_pin_3_flat vinn vinp vout
```

Together with `.ext` records `substrate "vout"` and `equiv vout<->vdda/gnda`,
this is a layout/extraction-level blocker that Netgen setup cannot honestly
turn into a pass.

## Required Corrections

### 1. Soften the net-rename claim

Severity: medium

AH-SMC-016B says missing net renames "guarantee" internal-node mismatches. That
is too strong. Netgen does not simply compare internal net names as strings; it
matches graph topology and device connectivity. Explicit renames can help align
diagnostic reports and can disambiguate SMCNR-style known internal nodes, but
their effect on Fan_SMC must be demonstrated by a controlled rerun.

Correct wording:

> Fan_SMC lacks the SMCNR-style rename layer. This is a setup divergence worth
> testing, but its contribution to LVS failure is not proven until a
> setup-normalized rerun shows which mismatch classes improve.

### 2. Treat H4 as supported as a setup gap, not as a proven root cause

Severity: medium

H4 is supported in the sense that the setup/provenance differs, especially
around `lvs_renames.txt` and missing SMCNR Netgen stdout/setup provenance. It is
not yet proven that the setup divergence is a primary Fan_SMC root cause.

Suggested status:

- H4 existence: `SUPPORTED`
- H4 root-cause contribution: `UNTESTED`

### 3. Do not expect Netgen setup to repair port collapse

Severity: high

Any next rerun must explicitly preserve the trust boundary:

- If `.ext` still contains `equiv "vout" "gnda"` or `equiv "vout" "vdda"`,
  the run remains failure-case only.
- Forced port edits or artificial renames are diagnostic only and cannot be
  used to claim LVS pass.

## Next Task

Run AH-SMC-016C as a controlled setup-normalized rerun using existing artifacts
or regenerated diagnostic artifacts only.

Required outputs:

- `docs/ah_smc_016c_setup_normalized_rerun.md`
- `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_016c/ah_smc_016c_records.json`

Required checks:

1. Re-run or replay Fan_SMC LVS baseline from the psub-tap artifacts.
2. Add a candidate rename file only for auditable, unambiguous extracted
   internal nets. Mark ambiguous mappings as `unmapped`.
3. Run Netgen with and without the candidate rename file.
4. Compare:
   - source/extracted device counts
   - source/extracted net counts
   - top-port lists
   - unmatched net classes
   - body-terminal collapse
   - `.ext` substrate/equiv records
5. Stop if the candidate rename map is circular, hand-waved, or derived from
   the desired answer rather than from auditable topology/device evidence.

Expected interpretation:

- If renames reduce internal net-class noise but `substrate/equiv` and top-port
  collapse remain, the primary blocker is still layout/extraction semantics.
- If renames unexpectedly resolve most mismatch classes without touching
  `substrate/equiv`, the H4 contribution should be upgraded and audited
  carefully.
- Under no condition should a renamed/edited diagnostic netlist be promoted to
  training-safe or reward-safe.

## Stop Gate

Do not authorize MAGICAL source modification yet. The next valid step is a
diagnostic setup-normalized Fan_SMC rerun, not a source patch.
