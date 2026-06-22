# Codex Review: AH-SMC-010 Fan_SMC Primitive/Body/Substrate Minimization

## Review Summary

Codex accepts AH-SMC-010 as `accepted_localization`: the evidence is strong
enough to name the next likely blocker and design the next single-variable
experiment.

The accepted finding is narrower than "Fan_SMC root cause fully proven":
AH-SMC-010 proves that the first auditable semantic divergence is the NMOS
primitive/pin contract, where the source netlist requires explicit `B=gnda` but
all generated NMOS fourth pins are `-1`. It does not prove that changing this
contract alone will close LVS. That must be tested in the next bounded run.

Fan_SMC remains a failure-case diagnostic sample only. It is not reward-safe,
post-simulation-safe, training-safe, or parasitic-modeling-safe.

## Checked Artifacts

| Artifact | Path | Review result |
| --- | --- | --- |
| AH-SMC-010 summary | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_010/ah_smc_010_summary.md` | Present; includes the three required evidence tables |
| AH-SMC-010 records | `generated/diagnostics/fan_smc_c0_proxy_94x10/ah_smc_010/ah_smc_010_records.json` | Present; valid JSON |
| Claude run report | `docs/claude_code_run_report.md` | Contains AH-SMC-010 section |
| Baseline `.ext` | `generated/diagnostics/fan_smc_c0_proxy_94x10/extract/fan_smc_pin_3_flat.ext` | Confirms `substrate "vout"` and `equiv "vout"` with `vdda`/`gnda` |
| AH-SMC-009 `.ext` | `generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3_flat.ext` | Confirms substrate/equiv records remain unchanged after p+ tap |
| Source netlist | `generated/diagnostics/fan_smc_c0_proxy_94x10/case/fan_smc_pin_3.sp` | Confirms M11/M23/M9 source terminals |
| MAGICAL `.pin` | `generated/diagnostics/fan_smc_c0_proxy_94x10/case/fan_smc_pin_3.pin` | Confirms M23 fourth pin is `-1`; M11/M9 have body boxes |
| Extracted SPICE | `generated/diagnostics/fan_smc_c0_proxy_94x10/extract/fan_smc_pin_3_flat.spice` | Confirms extracted terminal collapse for M11/M23/M9 |
| AH-SMC-009 LVS report | `generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/lvs_prepared/netgen_lvs_report.log` | Confirms LVS mismatch remains |
| AH-SMC-009 trust decision | `generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/trust_decision.json` | Correctly keeps all usability flags false except failure-case use |

## Scope Gate

| Gate | Result | Notes |
| --- | --- | --- |
| No controller/reward/GRPO/closure changes | Pass | AH-SMC-010 artifacts are observation-only |
| No SMCNR status copied to Fan_SMC | Pass | Fan_SMC remains failure-case only |
| No MAGICAL- artifact rewrite | Pass | Review found no required evidence of MAGICAL- edits for AH-SMC-010 |
| No DFCFC2 run | Pass | AH-SMC-010 scope is Fan_SMC only |
| No closure/training/reward/post-sim claim | Pass | Claude report explicitly preserves failure-case trust |
| No commit or push | Pass | No commit/push evidence observed |

There are pre-existing unrelated working-tree changes in the repository. They
are outside the AH-SMC-010 review scope and were not reverted.

## Structure Gate

| Gate | Result | Notes |
| --- | --- | --- |
| `ah_smc_010_summary.md` exists | Pass | Present |
| `ah_smc_010_records.json` exists and parses | Pass | `python3 -m json.tool` succeeds |
| Run report contains AH-SMC-010 section | Pass | Present in `docs/claude_code_run_report.md` |
| Evidence paths are absolute | Pass | Claude tables use absolute paths for cited artifacts |
| Required tables are present | Pass | Substrate identity, device terminal divergence, baseline-vs-tap delta |
| Claims cite raw lines or structured fields | Pass with caveat | Raw substrate/equiv/device lines are cited; root-cause wording is stronger than current evidence proves |

## Technical Findings

### 1. AH-SMC-009 Did Not Repair Substrate Collapse

Codex independently confirmed that both baseline and AH-SMC-009 extraction
contain:

```text
substrate "vout"
equiv "vout" "vdda"
equiv "vout" "gnda"
```

The p+ tap changed parasitic details but did not change Magic's substrate
identity or the vout/vdda/gnda equivalence records. This supports the AH-SMC-010
delta classification: semantic extraction state is `unchanged`.

### 2. The First Auditable Divergence Is The NMOS Body Contract

The source netlist requires M23 body to be `gnda`:

```text
M23 (vout net049 gnda gnda) sky130_fd_pr__nfet_01v8 ...
```

The MAGICAL `.pin` contract for M23 declares four pins but uses `-1` for the
fourth pin. The extracted `.ext` and extracted SPICE then show M23 body/source
collapsed to `vout`, not `gnda`.

This is accepted as the first evidenced semantic divergence for the next
experiment.

### 3. This Is Not Yet A Complete Root-Cause Proof

Claude's report sometimes says "root cause" in a stronger sense than current
evidence can prove. The evidence proves:

- all NMOS body pins are absent in the `.pin` contract;
- no NMOS extracted body is `gnda`;
- M23 body/source collapses to `vout`;
- adding a top-level p+ tap did not change substrate/equiv extraction.

The evidence does not yet prove that adding NMOS body pin geometry alone will
resolve LVS. PMOS devices also collapse to `vout` despite having body pin boxes,
so supply-domain routing/nwell/psub interactions may still be a second blocker.

## Trust Boundary Decision

AH-SMC-010 remains failure-case only:

```json
{
  "usable_for_reward": false,
  "usable_for_post_sim": false,
  "usable_for_training": false,
  "usable_for_parasitic_modeling": false,
  "usable_only_as_failure_case": true
}
```

No Fan_SMC artifact is promoted to reward, post-layout simulation, training, or
parasitic-modeling use.

## Next Single-Variable Experiment

Proceed to AH-SMC-011:

```text
Fan_SMC bounded NMOS body-pin contract probe
```

Recommended hypothesis:

```text
If the generated NMOS `.pin` contract provides a real fourth body pin geometry
that is tied to the intended `gnda` body/substrate domain, Magic extraction
should no longer assign those NMOS bodies to `vout`.
```

Constraints:

- one small bounded fixture first, preferably M23 or a minimal M23/M11 local
  extraction probe;
- do not change C0;
- do not add a second p+ tap as the primary variable;
- do not modify controller, reward, GRPO, optimizer, or closure logic;
- do not run DFCFC2;
- do not claim closure unless DRC/LVS/PEX/post-sim/PVT/trust evidence is later
  reviewed separately.

Acceptance evidence for AH-SMC-011 should include:

- before/after `.pin` fourth-pin record for the selected NMOS instance;
- before/after `.ext` device record;
- before/after extracted SPICE instance;
- before/after substrate/equiv records;
- Netgen LVS status if a full bounded candidate is rerun;
- trust decision remains failure-case unless LVS and downstream evidence pass.

## Phase Decision

Fan_SMC may proceed to the next **diagnostic phase**: AH-SMC-011 single-variable
NMOS body-pin contract probe.

Fan_SMC may not proceed to closure, post-layout simulation, PVT, reward, or
training use.

DFCFC2 remains pending until the Fan_SMC diagnostics path produces a verified
repair pattern or a clearer adapter-level boundary.
