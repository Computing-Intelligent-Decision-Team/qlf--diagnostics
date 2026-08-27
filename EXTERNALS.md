# External References

This file is the root index for external or reference projects in the IOT workspace.
On 2026-08-26, stale third-party and personal-learning checkouts were removed
from the active workspace unless they affected the current DFCFC2 / PCS harness
parasitic-modeling mainline.

## Frontend / Optimization References

| Path | Role | How It Connects |
|---|---|---|
| `AnalogCoderPro/` | LLM natural-language-to-circuit frontend | Converts design intent into PySpice code, initial topology, netlist-like artifacts, and repair loops. It is an upstream source before sizing and layout. |
| `analoggym-opt代码/` | AnalogGym-Opt / GRPO sizing frontend | Provides the GRPO-based analog sizing workflow, parameterized netlist/testbench execution, reward logic, and optimization trajectories. |
| `docs/papers/AnalogGym-Opt.pdf` | Paper reference for AnalogGym-Opt | Explains the GRPO sizing infrastructure, structured electrical records, PVT-aware optimization, and LLM-assisted workflow story. |

## Layout / EDA Tool References

| Path | Role | How It Connects |
|---|---|---|
| `references/MAGICAL-/` | MAGICAL Sky130 bridge/remap baseline | Senior's MAGICAL fork. Keep this as the single local clone for MAGICAL environment and pipeline baseline work. |
| `virtuoso-bridge-lite/` | Related Virtuoso automation project | Independent bridge for AI agent control of Cadence Virtuoso workflows. |

## Learning / Historical Material

| Path | Role |
|---|---|
| `docs/_archive/analog-layout-proto-retired-2026-05-28/` | Retired native/GLayout route notes, previews, and lightweight reports. |

## Removed From Active Workspace

| Path | Removal rationale |
|---|---|
| `PreviousProjects/` | Historical project collection; not part of the current DFCFC2 / PCS parasitic-modeling mainline. |
| `MyLearning/` | Personal learning and old AnalogGym/RGCN/RL materials; not a runtime dependency of the current mainline. |
| `OpenFASOC/` | Third-party GLayout/OpenFASOC checkout; only historical/reference docs depended on it. |
| `references/ALIGN-public/` | Third-party ALIGN checkout; not a current runtime dependency. |
| `BBOPlace-Bench/` | Empty top-level placeholder; older full copy existed under deleted `PreviousProjects/`. |
| `AncstrGNN_benchmark/` | Small constraint-extraction benchmark; useful conceptually, but not required by the current PCS/GRPO parasitic flow. |
| `Others'Projects/` | Third-party project bucket; no active mainline dependency. |
| `LLM/` | Old LLaMA-Factory/tooling checkout and historical software copy; future Agent/LoRA work should use a fresh, scoped checkout instead of this stale folder. |

Deletion manifest: `archives/deleted_third_party_personal_20260826_manifest.txt`.

## Organization Rules

- Keep only external repositories that directly support the current mainline or an explicitly active workstream.
- Use this file, `README.md`, and `plans/` to explain what each remaining external reference is for.
- Promote reusable project knowledge into `.github/skills/`, `docs/`, or `agent_workflow/` instead of editing third-party code directly.
- Treat external repositories as references, baselines, or upstream tools unless a dedicated integration workstream says otherwise.
