# PCS-Harness Workflow

## Objective

Build an independent `apps/pcs-harness-workflow` application and a reproducible OTA experiment that visualizes an Agent-directed, GRPO-sized PCS-Harness L0-to-L6 closure with trustworthy DRC/LVS/PEX evidence and measured stage timing.

## Success boundary

The application is independent of `apps/analog-circuit-platform`. Raw experiments remain under `generated/analog_harness`; the app contains only lightweight, traceable display snapshots. No implementation or experiment execution starts until the design spec is reviewed and approved.

## Design

See `docs/superpowers/specs/2026-08-26-pcs-harness-workflow-design.md`.
