# Trusted parasitic-label contract

## Positive-label gate

| Condition | Accept | Reject / unknown |
|---|---|---|
| Sizing lineage | Non-empty action/sizing/assignment payload plus resolvable source netlist | Stage name alone, missing source netlist, empty sizing payload |
| DRC | Numeric `drc_count == 0` in layout-verification evidence | Missing count, nonzero count, inferred success |
| Connectivity LVS | Explicit `yes`, `pass`, `matched`, or boolean-equivalent result | Missing, `no`, mismatch, tool exit without match evidence |
| Raw PEX | Resolvable non-empty raw extraction containing at least one R/C statement | Hybrid simulation overlay only, empty file, log summary without raw netlist |

An L6 closure label is necessary for an L6 export, but it is not sufficient for a trusted parasitic label.

## Observation-only fields

Preserve PM, reward, front-end metrics, pre-layout PVT, post-layout PVT, convergence, and post-layout performance when present. Never use them to remove a sample after the physical trust gate passes.

## Verification scope

`mos_only_projection` proves only the recorded connectivity contract. Preserve the scope verbatim in manifests and state that property-level or native-passive signoff was not established.

## Failure handling

- Keep each rejected candidate in `rejected_candidates.csv` with every applicable reason.
- Do not copy rejected experiment trees by default; this prevents an invalid PEX from being mistaken for a positive training label.
- Keep duplicate trustworthy runs and list hash-identical groups in `duplicate_groups.json`.
- Prefer evidence timestamps over directory names and filesystem modification time.
