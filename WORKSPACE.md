# IOT Workspace Map

This file is the human entry point for the IOT workspace. The original
repositories and experiment outputs remain in place so existing absolute
provenance paths inside `state.json`, manifests, and reports stay valid.
The top-level folders below are a navigation layer over the current workspace.

## Primary Entry Points

| Path | Purpose |
|---|---|
| `projects/` | Active code repositories and important project mirrors. |
| `datasets/` | Curated, model-ready datasets. |
| `experiments/` | Active or recently important experiment outputs. |
| `external/` | External references such as papers and third-party baselines. |
| `archives/` | Future manually retired workspace material. |
| `agent_workflow/` | Task logs, workstreams, decisions, and execution evidence. |
| `docs/` | Meeting notes, reports, slides, and project documents. |
| `references/` | Original upstream mirrors, raw historical outputs, and provenance roots. |

## Current Active Project Links

| Link | Target | Notes |
|---|---|---|
| `projects/pcs-harness-main` | `references/pcs-harness-align-origin-main-20260815` | Main PCS working tree; most DFCFC2 experiments and tools live here. |
| `projects/pcs-harness-reference` | `references/pcs-harness` | Smaller PCS reference mirror. |
| `projects/analoggym-opt` | `references/AnalogGym-Opt-9f2cbba1463efeb5d6160311630e5d56b297f9bf` | GRPO / AnalogGym-opt upstream workspace. |
| `projects/magical` | `references/MAGICAL-` | MAGICAL-related local reference and generated artifacts. |
| `projects/qlf-diagnostics` | `references/qlf--diagnostics` | Diagnostics and project documentation mirror. |

## Current DFCFC2 Data Products

| Link | Target | Notes |
|---|---|---|
| `datasets/dfcfc2_parasitic/current` | `projects/pcs-harness-main/generated/analog_harness/parasitic_modeling/dfcfc2_trusted_parasitic_95_20260826_v3` | Canonical DFCFC2 trusted parasitic corpus: 95 samples. |
| `datasets/dfcfc2_parasitic/step300_64` | `projects/pcs-harness-main/generated/analog_harness/parasitic_modeling/grpo_step300_dfcfc2_trusted_64_20260826_v2` | Step300-only trusted corpus: 64 samples. |
| `experiments/dfcfc2_grpo/step300_pool100_pcs` | `projects/pcs-harness-main/generated/analog_harness/grpo_batch_v12_trained_step300_pool100_l1_l6_admission_20260825_v1` | Full PCS admission run for 100 step300 GRPO candidates. |
| `experiments/dfcfc2_grpo/step300_pool100_grpo_export` | `projects/pcs-harness-main/generated/analog_harness/grpo_trained_step300_pool100_export_20260825_v1` | Upstream GRPO sizing export used for the step300 PCS run. |

## Rules Of Thumb

1. Use `projects/pcs-harness-main` when changing PCS code or reading current
   experiment tooling.
2. Use `datasets/dfcfc2_parasitic/current` for modeling work unless a task
   explicitly asks for the step300-only subset.
3. Treat `references/` as provenance storage. Do not physically move generated
   experiment directories from it unless the manifests and absolute paths are
   intentionally rewritten and re-audited.
4. Keep new curated datasets under `datasets/`, and link back to the original
   generated/provenance path.
5. Keep temporary experiments under `experiments/`; promote only audited outputs
   into `datasets/`.
6. Record substantial workspace changes in `agent_workflow/`.

## Why This Is A Link Layer

Many PCS and AnalogGym artifacts record absolute source paths for reproducibility.
Moving the raw directories would make old manifests, hashes, and audit reports
harder to trust. The link layer gives the workspace a clean working shape while
preserving the original evidence chain.
