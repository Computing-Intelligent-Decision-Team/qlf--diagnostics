---
name: analog-harness-parasitic-export
description: Use when exporting recent PCS or AnalogHarness L6 experiment artifacts into a portable archive for trustworthy parasitic modeling, especially when DRC/LVS/PEX evidence must be revalidated instead of trusting stage labels.
---

# AnalogHarness Parasitic Export

Generate a read-only, evidence-backed parasitic dataset and a portable archive. Do not treat an `L6` label or a generated PEX file alone as proof that a sample is trustworthy.

## Trust contract

A positive sample MUST independently establish all four conditions:

1. sizing lineage reaches the source candidate netlist and layout artifacts;
2. DRC has exactly zero violations;
3. connectivity LVS explicitly matches;
4. raw PEX exists, is non-empty, and contains parseable parasitic R/C elements.

PM, reward, pre-layout simulation, PVT, and post-layout performance are observation-only. They never reject an otherwise trustworthy parasitic label. A missing or ambiguous physical condition is rejected, never inferred as PASS. Label MOS-only evidence as connectivity-only; do not claim property-level or native-passive signoff.

Read [references/trust-contract.md](references/trust-contract.md) when adapting evidence fields or reviewing rejected candidates.

## Run

Resolve this skill's directory, then execute its deterministic exporter:

```bash
python3 <skill-directory>/scripts/export_parasitics.py \
  --root <generated/analog_harness> \
  --output <new-export-directory> \
  --days 7
```

Repeat `--root` for multiple data roots. Use `--since` and `--until` for an exact UTC ISO-8601 window. If `--root` is omitted, the script searches common local AnalogHarness locations. Never overwrite a non-empty output directory.

The exporter copies complete trusted candidate directories, skips symlinks and likely credentials/licenses, records rejected candidates without copying them, retains duplicate runs, emits manifests and SHA-256 checksums, and creates `<output>.tar.gz`. It never moves, deletes, or edits source experiments.

## Handoff

Inspect the printed JSON summary. Report:

- exact UTC window and scanned roots;
- discovered, in-window, trusted, and rejected counts;
- absolute archive path and archive SHA-256;
- rejection reasons and any MOS-only scope limitation.

Attach or upload the archive only when the current interface supports it and the destination is authorized. Otherwise provide the absolute path; generating an archive is not permission to send it externally.
