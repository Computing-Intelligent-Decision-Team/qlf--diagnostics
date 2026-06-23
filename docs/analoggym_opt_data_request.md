# AnalogGym-Opt Data Request For Parasitic Modeling

Last updated: 2026-06-22

## Current Judgment

AnalogGym-Opt should be used as a candidate generator, not as the final source
of parasitic modeling labels. The evidence endpoint remains AnalogHarness:

```text
AnalogGym-Opt candidate
-> AnalogHarness ingest
-> MAGICAL layout
-> Sky130 remap
-> Magic DRC/extract/PEX
-> Netgen LVS
-> trust-gated parasitic graph JSONL
```

This division is important. AnalogGym-Opt can provide many sizing candidates
and optimizer metadata; AnalogHarness must decide which samples are positive,
failure-case-only, or unusable.

## Requested First Batch

Start small and auditable:

| Field | Request |
| --- | --- |
| Topology count | 1 AMP topology first, preferably close to SMCNR/DFCFC2 |
| Candidate count | Top 50 candidates |
| Ranking source | AnalogGym-Opt reward/pre-layout metrics |
| Required output | One directory per candidate |
| Primary goal | Produce enough candidates for AnalogHarness PEX/LVS/trust-gate expansion |

If the first batch is stable, expand to 100 candidates or a second topology.

## Candidate Directory Contract

Each candidate should be exported as:

```text
analoggym_opt_batch_<date>/
  batch_manifest.json
  circuit_<name>/
    cand_0001/
      candidate.json
      sizing.json
      source.spice
      pre_sim_metrics.json
      optimizer_metadata.json
      logs/
        optimizer.log
```

## Required `candidate.json`

```json
{
  "candidate_id": "cand_0001",
  "source": "AnalogGym-Opt",
  "circuit": "AMP_DFCFC2",
  "topology_id": "amp_dfcfc2",
  "optimizer": "grpo",
  "rank": 1,
  "reward": 0.0,
  "source_spice": "source.spice",
  "sizing_json": "sizing.json",
  "pre_sim_metrics_json": "pre_sim_metrics.json",
  "optimizer_metadata_json": "optimizer_metadata.json",
  "notes": ""
}
```

## Required `sizing.json`

Keep raw design variables and resolved device parameters:

```json
{
  "design_variables": {},
  "devices": {
    "xm0": {"model": "sky130_fd_pr__nfet_01v8", "w": 1.0, "l": 1.0, "nf": 1, "multi": 1}
  },
  "passives": {},
  "constraints": {}
}
```

## Required `pre_sim_metrics.json`

```json
{
  "simulator": "ngspice",
  "pdk_or_model_source": "",
  "corner": "tt",
  "temperature_c": 27,
  "vdd": 1.8,
  "metrics": {
    "dcgain": null,
    "GBW": null,
    "phase_margin": null,
    "Power": null
  },
  "passed_pre_sim": null
}
```

## Required `optimizer_metadata.json`

```json
{
  "repo": "Computing-Intelligent-Decision-Team/AnalogGym-Opt",
  "commit": "",
  "run_id": "",
  "seed": null,
  "config": {},
  "objective": "",
  "timestamp": ""
}
```

## AnalogHarness Ingest Expectations

AnalogHarness will add:

- layout artifact paths;
- Magic DRC count;
- raw extracted SPICE with PEX capacitors;
- PEX graph fields;
- Netgen LVS result;
- passive evidence scope if applicable;
- post-layout simulation and PVT evidence if run;
- trust labels:
  `usable_for_supervised_positive_training`,
  `usable_for_parasitic_modeling`,
  `usable_only_as_failure_case`.

## Claude Next Task

Prepare an importer design that maps this batch format into
`tools/analog_harness/ml/parasitic_dataset.py` or a future sibling module.
Do not implement a parallel harness.

## Acceptance Criteria

- Every imported candidate keeps optimizer provenance.
- Every sample can be traced back to the source SPICE and sizing JSON.
- No candidate becomes training-positive without AnalogHarness LVS/trust
  evidence.
- Failure candidates remain useful as failure-case-only records.

## Forbidden Claims

- Do not claim AnalogGym-Opt output is parasitic ground truth.
- Do not treat high pre-layout reward as post-layout validity.
- Do not treat PEX availability as LVS pass.
- Do not mix failure-case-only records into supervised positive training.
