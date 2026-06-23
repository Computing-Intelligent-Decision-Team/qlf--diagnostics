# Reproducibility Guide

This repository now includes the pieces that were previously local-only:

- Vendored AnalogGym GRPO optimizer under `third_party/analoggym_grpo`.
- Bundled Sky130 PDK convenience copy under
  `third_party/analoggym_grpo/simulation_files/sky130_pdk`.
- Curated SMC run data under `reproducibility/smcnr_se_2st_amp`.

## What Developers Still Need

Install these outside the repository:

- Python 3.10+ and `pip`
- Docker, with access from the Linux/WSL environment used for layout
- MAGICAL Docker image: `jayl940712/magical:latest`
- Magic `8.3.411` or newer
- IC `netgen-lvs` / Netgen 1.x
- `ngspice` for real simulation and PVT reruns
- Optional KLayout for visual GDS inspection

On Windows, use WSL. The default config names `Ubuntu-24.04`; change
`layout.wsl_distro` in `tools/analog_harness/configs/smcnr_se_2st_amp.yaml` if
your distro name is different.

## Setup

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-grpo.txt
docker image inspect jayl940712/magical:latest >/dev/null || docker pull jayl940712/magical:latest
magic --version
netgen-lvs -batch quit
ngspice --version
```

The checked-in SMC config uses the bundled PDK by default. To use another PDK,
set `SKY130A=/path/to/sky130A` and update the config fields
`layout.sky130a` and `simulation.sky130_model_lib`.

## Inspect Packaged Results

```bash
cat reproducibility/smcnr_se_2st_amp/run_summary/summary.json
head reproducibility/smcnr_se_2st_amp/all_candidates/candidate_index.csv
```

The key reference package is:

```text
reproducibility/smcnr_se_2st_amp
```

It contains the 38-candidate evidence set, warm-start data, selected best
candidate netlists/testbenches, passive evidence, and three small GDS reference
files. It intentionally does not include the full 563 MB `generated/` tree.

## Debug Upstream Layout Differences

If a fresh local MAGICAL run does not match the packaged clean `cand_0031`
layout, use the upstream diagnostic archive:

```text
reproducibility/smcnr_se_2st_amp/upstream_artifacts/smcnr_cand0031_upstream_full_run.tar.gz
```

Verify and extract it:

```bash
cd reproducibility/smcnr_se_2st_amp/upstream_artifacts
sha256sum -c smcnr_cand0031_upstream_full_run.sha256
tar -xzf smcnr_cand0031_upstream_full_run.tar.gz
```

The archive root is `SMCNR_SE_2st_AMP/cand_0031/`. It includes MAGICAL
intermediate GDS files, placement/routing logs, Magic DRC/extraction logs,
`.ext`, extracted SPICE, Netgen reports, PEX summaries, passive/native-cap
diagnostics, simulation logs, runner metadata, and environment metadata. This
is the package to use for diagnosing `vdda/gnda` extraction collapse in fresh
local SMCNR generation.

## Rerun

Smoke layout closure:

```bash
python -m tools.analog_harness.cli run \
  --config tools/analog_harness/configs/smcnr_se_2st_amp.yaml \
  --max-candidates 1 \
  --layout-budget 1
```

Summarize an existing local run:

```bash
python -m tools.analog_harness.cli summarize \
  --config tools/analog_harness/configs/smcnr_se_2st_amp.yaml
```

The packaged reference best candidate is `cand_0031`, with
`L6_post_layout_pvt` closure in the recorded run. Numeric simulation values may
vary across tool versions; compare against `candidate_index.csv` and
`run_summary/summary.json`.
