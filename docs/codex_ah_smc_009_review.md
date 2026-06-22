# Codex Review: AH-SMC-009 Fan_SMC Diagnostic P+ Substrate Tap

## Review Summary

AH-SMC-009 executed the approved single-variable diagnostic experiment: add one
top-level p+ substrate tap stack tied to the existing `gnda` met5 rail in the
bounded-C0 Fan_SMC candidate.

Codex review accepts the run as a useful diagnostic artifact, not as a closure
success. The added tap is present and DRC reports zero errors, but Magic
extraction still equates `vout`, `vdda`, and `gnda`, Netgen LVS still fails, and
the trust gate correctly rejects the sample for reward, training, post-sim, and
parasitic modeling.

## Checked Artifacts

| Artifact | Path | Review result |
| --- | --- | --- |
| Injection report | `generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/psub_tap_injection.json` | Present; one stack; 14 boundaries; original records preserved |
| Candidate GDS | `generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3.psub_tap.gds` | Present |
| GDS structure | `generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/gds_structure.md` | Present; one top cell; 10 text labels |
| Magic DRC log | `generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/magic_drc.log` | Present; `Total DRC errors found: 0` |
| Magic extraction | `generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3_flat.ext` | Present; still records substrate/equiv collapse |
| Key extraction records | `generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/ext_key_records.txt` | Present; `substrate "vout"`, `equiv "vout" "vdda"`, `equiv "vout" "gnda"` |
| LVS report | `generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/lvs_prepared/netgen_lvs_report.log` | Present; netlists do not match |
| Trust decision | `generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/trust_decision.json` | Present; all usability flags false except failure-case use |

## Findings

No critical process violation found.

The run stayed within the approved observation-only scope:

- No controller, reward, GRPO, or closure-level changes.
- No SMCNR positive baseline status copied to Fan_SMC.
- No NMOS primitive change, C0 change, second anchor, PEX, post-layout sim, PVT,
  DFCFC2 execution, commit, or push.
- Output artifacts were written under
  `generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/`.

## Technical Result

The tested hypothesis was not supported. A single top-level p+ substrate tap tied
to `gnda` did not change Magic's extracted substrate identity or equivalence
records.

Key evidence:

```text
substrate "vout"
equiv "vout" "vdda"
equiv "vout" "gnda"
```

Netgen still reports mismatch:

```text
Circuit 1 contains 18 nets, Circuit 2 contains 19 nets. *** MISMATCH ***
Result: Netlists do not match.
```

Trust gate decision is conservative and correct:

```json
{
  "drc_clean": true,
  "lvs_match": false,
  "usable_for_training": false,
  "usable_only_as_failure_case": true
}
```

## Display Use

AH-SMC-009 is useful for Core Technology 4 as a feedback-loop diagnostic visual:

```text
Generated layout -> verification finds substrate/supply collapse -> diagnostic
tap repair attempt -> trust gate blocks unsafe sample
```

Do not present AH-SMC-009 as a successful optimized Fan_SMC closure.

