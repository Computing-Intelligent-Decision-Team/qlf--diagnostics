# Codex Review: Parasitic Modeling Dataset v0

Review date: 2026-06-22

## Current Judgment

Dataset v0 is acceptable as a research-foundation artifact. It is not a
training-complete corpus and should not be used to claim model performance.

The core delivery is real:

- `tools/analog_harness/ml/parasitic_dataset.py` builds five parasitic graph
  records.
- `tools/analog_harness/tests/test_parasitic_dataset.py` verifies parser and
  trust-label behavior.
- `generated/parasitic_modeling/dataset_v0.jsonl` and
  `generated/parasitic_modeling/parasitic_dataset_v0.jsonl` currently contain
  identical records.
- `docs/parasitic_modeling_dataset_v0.md` records the dataset schema and trust
  boundaries.

## Evidence Basis

Fresh verification command:

```bash
python3 -m unittest tools.analog_harness.tests.test_parasitic_dataset -v
```

Result observed by Codex:

```text
Ran 17 tests in 0.030s
OK
```

Dataset record audit:

| Record | LVS | Caps | Total cap | Positive training | Failure-only |
| --- | --- | ---: | ---: | --- | --- |
| `smcnr_se_2st_amp_cand_0031` | PASS | 37 | 71.4964 fF | true | false |
| `fan_smc_c0_proxy_psub_tap` | FAIL | 95 | 23.8473 fF | false | true |
| `fan_smc_c0_proxy_guardring_true` | FAIL | 92 | 30.0572 fF | false | true |
| `dfcfc2_mim_proxy` | FAIL | 103 | 865.0103 fF | false | true |
| `dfcfc2_mos_only_rerun` | FAIL | 51 | 34.8776 fF | false | true |

The DFCFC2 `mim_proxy` record now matches the audited PEX summary count and
total after parser support for `p` suffixes and `$ **FLOATING` comments.

## Review Findings

No blocking correctness issue was found in the verified dataset v0 path.

Non-blocking issues:

1. There are two generated JSONL filenames with identical content:
   `dataset_v0.jsonl` and `parasitic_dataset_v0.jsonl`. Pick one canonical
   filename before commit or publication.
2. The terminal-rendered Claude delivery table was visually corrupted and
   should not be used as formal evidence. Use the Markdown report and JSONL
   audit instead.
3. Dataset v0 lacks layout-geometry features such as device boxes, wire
   length, layer tags, coupling context, and metal spacing. It is graph-ready
   for PEX topology, not yet layout-feature-complete.
4. Fan_SMC and DFCFC2 extracted connectivity is LVS-failing; their parasitic
   edges may be useful for diagnostics and robustness tests, not clean labels.

## Claude Next Task

Move from dataset v0 delivery to data expansion planning:

1. Keep `dataset_v0.jsonl` as the canonical generated filename unless the team
   deliberately chooses `parasitic_dataset_v0.jsonl`.
2. Add a schema validator test that reads the generated JSONL and checks every
   required field.
3. Add parser tests for `ff`, `pf`, and uppercase suffix variants if future
   artifacts contain them.
4. Prepare ingestion requirements for AnalogGym-Opt candidate batches.

## Acceptance Criteria

- SMCNR/cand_0031 remains the only positive supervised record.
- Fan_SMC and DFCFC2 remain failure-case-only until independent LVS/passive
  evidence proves otherwise.
- DFCFC2 `mim_proxy` remains aligned with 103 caps and about 865.01 fF.
- Any future dataset expansion records optimizer provenance, source netlist,
  extracted PEX, LVS status, and trust decision.

## Forbidden Claims

- Do not claim dataset v0 is enough to train diffusion/Mamba/GNN models.
- Do not claim Fan_SMC or DFCFC2 passed LVS.
- Do not claim PEX availability means positive training data.
- Do not use terminal table rendering as evidence when Markdown/JSON artifacts
  are available.
