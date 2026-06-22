# Codex Review: AH-DIAG-001

## Decision

`AH-DIAG-001` is accepted.

## TDD Evidence

- Pre-task focused baseline: 21 tests passed.
- RED: the selected test failed because
  `decide_sample_trust_from_lvs_text` did not exist.
- GREEN: the selected test passed after the minimum composition helper was
  added.
- Focused regression: 22 tests passed.
- Full AnalogHarness suite: 73 tests run, 71 passed, 2 failed.
- The two full-suite failures are the same pre-existing local Python command
  lookup and Windows-to-WSL path translation assumptions recorded before this
  task. No new full-suite failure was observed.

## Reviewed Behavior

`decide_sample_trust_from_lvs_text(evidence, lvs_text)`:

1. Parses the supplied Netgen text with `classify_lvs_summary`.
2. Copies the caller evidence rather than mutating it.
3. Overrides any caller-supplied `lvs_match` with the parser result.
4. Keeps LVS categories and stable trust reason codes in separate outputs.
5. Does not touch controller, reward, GRPO, or closure state.

The inline Fan_SMC fixture contains equal device counts but unequal net counts
and a direct `Netlists do not match` conclusion. The test therefore guards the
specific failure mode that device-count equality is not LVS equivalence.

## Full Local Artifact Verification

Codex also applied the helper directly to the reviewed local Netgen report:

```text
/home/qlf/IOT/references/MAGICAL-/generated/analoggym_adapter_audits/
fan_smc_pin_3/magical_case/smc09_no_c0/sky130_pipeline/extract_b1/
lvs/netgen_lvs.out
```

Result:

- LVS diagnosis: `fail`, `lvs_match=false`, `net_mismatch`
- `usable_for_reward=false`
- `usable_for_post_sim=false`
- `usable_for_training=false`
- `usable_for_parasitic_modeling=true`
- `usable_only_as_failure_case=true`
- Stable reasons: `lvs_not_matched`, `post_sim_invalid`, `pvt_invalid`, and
  `scope_not_full_passive_inclusive_gds_lvs`

## Limitations

This evidence is a local artifact from a C0-removed diagnostic control. It is
not proof of closure for the original Fan_SMC circuit and is not training-safe.

## Next Gate

Proceed to `AH-SMC-001`: establish a read-only, reproducible baseline for the
original Fan_SMC circuit with C0 present before selecting a repair variable.
