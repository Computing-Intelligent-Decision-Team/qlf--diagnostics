# SMCNR cand_0031 Upstream Artifact Package

This directory contains the diagnostic package requested for reproducing and
debugging the `SMCNR_SE_2st_AMP/cand_0031` upstream clean-generation path.

## Files

- `smcnr_cand0031_upstream_full_run.tar.gz`: compressed upstream artifact tree.
- `smcnr_cand0031_upstream_full_run.sha256`: SHA256 checksum for the archive.

Archive checksum:

```text
4431cfdc6035890cc8a81cab80b43c745ae5b726e9a505b1fdb17d620ade4439  smcnr_cand0031_upstream_full_run.tar.gz
```

## Why This Exists

The lightweight reproducibility package intentionally omitted raw Magic `.ext`
files and bulk logs. That was sufficient for result replay, but not sufficient
for debugging why a fresh local MAGICAL SMCNR run can collapse `vdda/gnda`
during Magic extraction while the packaged `cand_0031` GDS extracts cleanly.

This archive is meant for upstream-vs-local diffing of:

- MAGICAL input netlist/config and placement/routing logs.
- `floorplan`, `place`, `route`, Sky130-remapped, pinned, pin-shape, and
  local-power GDS stages.
- Magic DRC/extraction Tcl and logs.
- Magic `.ext`, raw extracted SPICE, connectivity SPICE, and PEX summaries.
- Netgen LVS Tcl/log/report.
- Passive/native-cap diagnostic artifacts under `layout_passive_existing_gds`.
- Simulation logs and PVT replay files.
- Environment and runner metadata captured at packaging time.

## Archive Layout

After extraction, the root is:

```text
SMCNR_SE_2st_AMP/
  summary.json
  summary.md
  cand_0031/
    state.json
    evidence.jsonl
    upstream_artifact_manifest.json
    upstream_artifact_filelist_sha256.txt
    upstream_environment.txt
    runner_command.txt
    case/
    layout/
    layout_passive_aware/
    layout_passive_existing_gds/
    netgen_env_check/
    runner/
    sim/
```

`layout_passive_aware/` includes the top-level files only. Its large
subdirectory search space was excluded because it is mostly exploratory probe
combinatorics. The full `layout_passive_existing_gds/` tree is included because
it contains the native passive/cap replacement evidence chain.

## Extract

```bash
cd reproducibility/smcnr_se_2st_amp/upstream_artifacts
sha256sum -c smcnr_cand0031_upstream_full_run.sha256
tar -xzf smcnr_cand0031_upstream_full_run.tar.gz
```

On PowerShell:

```powershell
Get-FileHash -Algorithm SHA256 .\smcnr_cand0031_upstream_full_run.tar.gz
tar -xzf .\smcnr_cand0031_upstream_full_run.tar.gz
```

## Suggested Local Diff Targets

Compare the clean upstream chain against a fresh failing local chain in this
order:

1. `case/SMCNR_SE_2st_AMP.place.gds`
2. `case/SMCNR_SE_2st_AMP.route.gds`
3. `case/SMCNR_SE_2st_AMP.sky130.gds`
4. `case/SMCNR_SE_2st_AMP.sky130.pinned_shapes.gds`
5. `case/SMCNR_SE_2st_AMP.sky130.pinned_shapes.local_power.gds`
6. `layout/magic_drc.log`
7. `layout/lvs_mos_projection/SMCNR_SE_2st_AMP_flat.ext`
8. `layout/lvs_mos_projection/SMCNR_SE_2st_AMP_extracted.raw.spice`
9. `layout/lvs_mos_projection/lvs_result_summary.md`
10. `layout/lvs_mos_projection/pex_summary.md`

The most relevant question is whether the failing fresh GDS differs in
well/tap/substrate geometry, power routing, pin labels, `lvs_renames.txt`, or
Magic `.ext equiv` records.

