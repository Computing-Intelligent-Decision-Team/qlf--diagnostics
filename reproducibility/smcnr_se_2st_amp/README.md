# SMCNR_SE_2st_AMP Reproducibility Data

This package contains a curated subset of the local Analog Harness run for
`SMCNR_SE_2st_AMP`. It is meant for inspection, result comparison, warm-start
experiments, and reproducing the closure flow without committing the entire
`generated/` tree.

## What Is Included

- `run_summary/`: top-level `summary.json` and `summary.md`.
- `event_log/events.jsonl`: chronological evidence events from the harness.
- `all_candidates/`: `state.json` and `evidence.jsonl` for all 38 candidates,
  plus `candidate_index.csv` for quick comparison.
- `knowledge_transfer/`: warm-start bank and proxy feedback dataset for later
  GRPO/harness experiments.
- `best_candidate/cand_0031/`: selected case config, SPICE netlists, simulation
  testbenches/results, MOS-only layout evidence, passive-aware evidence, and
  three small reference GDS files.
- `environment/packaging_environment.txt`: tool versions observed when this
  package was created.
- `manifest.json`: machine-readable package summary.

The full local run was about 563 MB. This package is about 2.7 MB because bulk
GDS variants, `.ext` files, and transient logs were intentionally excluded.

## Upstream Diagnostic Archive

For debugging fresh local MAGICAL generation differences, this repository also
includes:

```text
reproducibility/smcnr_se_2st_amp/upstream_artifacts/smcnr_cand0031_upstream_full_run.tar.gz
```

That archive keeps the original `SMCNR_SE_2st_AMP/cand_0031` structure and adds
the raw upstream artifacts that were intentionally omitted from the lightweight
package: MAGICAL logs, `place`/`route`/remapped/pinned GDS stages, Magic Tcl/logs,
`.ext`, extracted SPICE, Netgen LVS files, PEX summaries, environment metadata,
and runner metadata. Use it when comparing the known-clean packaged GDS against
a fresh local MAGICAL GDS that collapses `vdda/gnda`.

## Reference Result

- Design: `SMCNR_SE_2st_AMP`
- Best candidate: `cand_0031`
- Candidate count: 38
- Best closure: `L6_post_layout_pvt`
- Summary scope: `mos_only_projection`
- Passive evidence: best candidate records `pass` with
  `full_passive_inclusive_gds_lvs` evidence in the curated passive packet.

Use `all_candidates/candidate_index.csv` as the quickest table for checking
reward, closure level, DRC count, LVS status, PEX capacitance, PVT status, and
passive-inclusive evidence.

## Reproduction Requirements

Already vendored in this repository:

- AnalogGym GRPO source: `third_party/analoggym_grpo`
- Sky130 PDK convenience copy:
  `third_party/analoggym_grpo/simulation_files/sky130_pdk`
- SMC harness config:
  `tools/analog_harness/configs/smcnr_se_2st_amp.yaml`

The developer still needs to install locally:

- Python 3.10+ and `pip`
- Host Python dependencies from `requirements.txt`
- Optional GRPO dependencies from `requirements-grpo.txt`
- Docker with WSL/Linux integration
- MAGICAL Docker image: `jayl940712/magical:latest`
- Magic, version `8.3.411` or newer
- IC `netgen-lvs` / Netgen 1.x
- `ngspice` for real pre-layout, post-layout, and PVT simulations
- Optional KLayout for viewing GDS

On Windows, the default config expects WSL distro `Ubuntu-24.04`. Edit
`layout.wsl_distro` if the local distro name is different.

## Minimal Checks

```bash
python -m unittest tools.analog_harness.tests.test_config_legalizer_spice tools.analog_harness.tests.test_layout_optimizer_state
python -m tools.analog_harness.cli summarize --config tools/analog_harness/configs/smcnr_se_2st_amp.yaml
```

The second command summarizes `generated/analog_harness/...` when a local run
exists. If only this package is available, inspect `run_summary/summary.json`
and `all_candidates/candidate_index.csv` directly.

## Fresh Run Entry Point

```bash
python -m tools.analog_harness.cli run \
  --config tools/analog_harness/configs/smcnr_se_2st_amp.yaml \
  --max-candidates 1 \
  --layout-budget 1
```

For a full rerun, increase `--max-candidates` and `--layout-budget`. Exact
numeric metrics can vary with Magic, Netgen, ngspice, Docker, and OS versions;
the packaged CSV/JSON files are the reference data from this repository state.
