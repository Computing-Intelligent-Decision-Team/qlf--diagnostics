# Diagnostics Module Status

This note summarizes the current observation-only diagnostics package for
Codex/Claude coordination. It does not authorize controller, reward, GRPO, or
closure-level integration.

## Current Package

```text
tools/analog_harness/diagnostics/
  __init__.py
  artifact_verifier.py
  lvs_failure_taxonomy.py
  pex_structuring.py
  sample_trust_gate.py
```

Focused test command:

```bash
python3 -m unittest tools.analog_harness.tests.test_diagnostics_trust_gate -v
```

Current expected focused result:

```text
Ran 22 tests
OK
```

The governing positive fixture contract is documented in
`docs/smcnr_positive_baseline_contract.md`. It records both the accepted trust
decision and the curated/backfilled evidence caveats.

## Artifact Verifier Helpers

`artifact_verifier.py` currently supports these pure helpers:

| Helper | Input | Output purpose |
| --- | --- | --- |
| `verify_artifact_path(...)` | one path string | classify one artifact as `present`, `generated_only_reference`, `not_portable`, or `missing` |
| `verify_artifact_map(...)` | one EvidencePacket `artifacts` dict | produce artifact-level reports and `status_counts` |
| `verify_evidence_packets(...)` | a `state["evidence"]` list | produce stage-level artifact validity reports |
| `verify_state_artifacts(...)` | one candidate `state.json` dict | preserve `candidate_id` and produce candidate-level artifact validity |

Known reason codes include:

- `windows_absolute_path`
- `invalid_path_text`

The verifier intentionally treats original Windows absolute paths and absent
`generated/` references as different evidence classes.

## Trust Gate Helpers

`sample_trust_gate.py` currently supports:

| Helper | Input | Output purpose |
| --- | --- | --- |
| `decide_sample_trust(...)` | normalized trust input dict | produce separate `usable_*` flags and `reasons` |
| `decide_sample_trust_from_state(...)` | one candidate `state.json` dict | derive trust input from EvidencePacket stages |

The current positive baseline is the packaged SMCNR state:

```text
reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/state.json
```

The focused tests lock the current SMCNR artifact-validity baseline:

| Field | Value |
| --- | ---: |
| `packet_count` | 5 |
| `artifact_count` | 86 |
| `not_portable` | 30 |
| `generated_only_reference` | 28 |
| `missing` | 28 |

## Parser Helpers

`lvs_failure_taxonomy.py` currently classifies small LVS summaries into:

- `pass`
- `fail`
- `device_mismatch`
- `net_mismatch`
- `property_mismatch`
- `power_domain_short`
- `pin_label_overlap`
- `missing_top_port_label`

It recognizes the local markdown-style `LVS status: **PASS**` summary format
and common Netgen phrases such as `Circuits match uniquely`,
`Netlists match uniquely`, `Netlists do not match`, `not equivalent`, and
`Property errors`.
It also recognizes early blocker phrases for power-domain shorts, pin-label
overlap, and missing top-port labels.

`pex_structuring.py` currently summarizes simple extracted-SPICE capacitor
lines into:

- `pex_caps`
- `pex_total_cap_ff`
- `per_node_cap_ff`

These parsers are intentionally small. Do not assume they fully parse every
Netgen or Magic output format until old MAGICAL- artifacts are reviewed.

## Next Review Gate

Before old DFCFC2/Fan_SMC artifacts become diagnostics fixtures:

1. Claude Code should fill `docs/dfcfc2_smc_artifact_inventory.md`.
2. Codex should review it with
   `docs/codex_artifact_inventory_review_checklist.md`.
3. Codex should choose one small negative fixture.
4. New parser/trust-gate tests should be added for that fixture.
5. Controller/reward integration remains out of scope.

## Do Not Claim

- Do not claim DFCFC2 or Fan_SMC is impossible to close.
- Do not claim PEX availability means LVS passed.
- Do not claim a sample is training-safe without trust-gate review.
- Do not promote diagnostics output into reward or closure-level logic without
  a separate reviewed task.
