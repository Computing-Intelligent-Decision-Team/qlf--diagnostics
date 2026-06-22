# Codex Review: AH-SMC-025 Substrate-Abstracted LVS Probe

## Review Status

**Accepted with wording corrections.**

AH-SMC-025 gives a useful negative result: stripping NMOS body terminals is
insufficient to make Fan_SMC pass LVS. The failure is not limited to fourth-pin
body mismatch.

Fan_SMC remains **failure-case only**.

## Verified Evidence

| Check | Result |
| --- | --- |
| Full LVS | FAIL, 24 vs 24 devices, 18 vs 19 nets |
| 3-term NMOS LVS | FAIL, 24 vs 24 devices, 18 vs 19 nets |
| Full extracted ports | Extracted netlist has only `vinn vinp vout` |
| 3-term extracted ports | Still only `vinn vinp vout` |
| Extracted topology | Many source nets no longer have matching extracted nets |
| `3term+portmatch` | FAIL, but includes 2 artificial voltage sources |
| Trust boundary | Correct final classification: not reward/post-sim/training safe |

## Required Corrections

### 1. Fix metadata trust inconsistency

The AH-SMC-025 metadata currently says:

> `usable_for_mos_only_lvs_diagnostic: true`

but the classification and records correctly say:

> `usable_for_mos_only_lvs_diagnostic: false`

The metadata should be corrected to avoid contradiction.

### 2. Treat `3term+portmatch` as secondary evidence only

The `3term+portmatch` variant adds two 0V voltage sources to alias ports. This
intentionally changes device count from 24 to 26 and also produces odd Netgen
instance text for those artificial elements. That variant is useful as a
stress/diagnostic probe, but it should not be the main proof.

The main proof is the cleaner comparison:

> Full LVS and 3-term NMOS LVS both fail with the same 24 vs 24 device count
> and 18 vs 19 net count.

### 3. Soften "gate terminals are misassigned"

The logs prove that after collapse, net correspondence no longer maps cleanly
between source and extracted netlists. They do not independently prove that
Magic physically assigned gate terminals to the wrong shapes.

Use:

> gate-net correspondence cannot be matched reliably after topology collapse

not:

> gate terminals are misassigned.

### 4. Keep H8 precise

H8 is supported in this narrower form:

> Body abstraction alone does not restore Fan_SMC LVS; extracted connectivity
> has been restructured beyond NMOS body terminals.

Avoid phrasing H8 as proof of the exact physical mechanism. The exact
shape-level collapse path is still a separate localization problem.

## Accepted Interpretation

AH-SMC-025 supports:

- MOS-only / 3-terminal NMOS LVS is insufficient.
- Fan_SMC failure is broader than NMOS body mismatch.
- The extracted netlist has lost enough original net structure that simple
  LVS policy relaxation does not recover a match.
- `usable_for_mos_only_lvs_diagnostic` should be false for this Fan_SMC run.

AH-SMC-025 does **not** prove:

- the exact GDS shape causing collapse,
- that all gate terminals are physically wrong,
- that Magic or MAGICAL must be patched,
- that Fan_SMC can enter reward, training, post-sim, or parasitic modeling.

## Recommended Next Task

Run **AH-SMC-026: final Fan_SMC failure classification and stop-gate report**.

Goal: stop exploratory repair attempts and convert the 25 experiments into a
stable AnalogHarness trust-gate decision.

Minimum requirements:

1. Summarize AH-SMC-009 through AH-SMC-025 as a failure taxonomy, not a repair
   campaign.
2. Mark Fan_SMC as:
   - `full_lvs = fail`
   - `mos_only_3term_lvs = fail`
   - `usable_for_reward = false`
   - `usable_for_post_sim = false`
   - `usable_for_training = false`
   - `usable_for_parasitic_modeling = false`
   - `usable_only_as_failure_case = true`
   - `topology_status = restructured_by_substrate_collapse`
3. Identify which hypotheses are closed:
   - `.pin=-1` sole cause: disproven
   - top-level psub tap fix: insufficient
   - guard-ring config fix: insufficient
   - Netgen rename/setup-only fix: insufficient
   - MOS-only LVS policy: insufficient
4. Identify remaining unknowns:
   - exact GDS shape/primitive path causing collapse,
   - whether a production primitive/layout redesign could avoid collapse,
   - whether a dedicated extraction abstraction could support this circuit.
5. Recommend no further Fan_SMC repair attempts unless the project explicitly
   authorizes MAGICAL primitive/layout strategy changes.
6. Output:
   - `docs/ah_smc_026_fan_smc_stop_gate.md`
   - `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_026/ah_smc_026_records.json`

