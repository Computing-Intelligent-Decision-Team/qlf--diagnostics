# SMCNR Upstream Artifact Request

**Date**: 2026-06-23
**Requester context**: AnalogHarness local replay and diagnostics
**Purpose**: identify why the upstream packaged SMCNR GDS extracts cleanly while
fresh local MAGICAL-generated SMCNR GDS collapses `vdda`/`gnda`.

## 1. Short Message To 师兄

师兄好，我们现在已经确认：

```text
packaged SMCNR/cand_0031 GDS -> Magic extraction/LVS/PEX pass
local fresh MAGICAL GDS with exact cand_0031 sizing -> extraction collapse
local fresh MAGICAL GDS with sizing/nf/multi/seed variants -> extraction collapse or no useful PEX diversity
```

所以现在最需要的不是新的优化结果，而是你当时生成成功
`SMCNR_SE_2st_AMP/cand_0031` 的完整原始 run artifacts。我们想 diff
你的 clean GDS 生成链和本地失败生成链，定位差异是在 MAGICAL 版本、Anaroute、
Python/gdspy/gdstk、PDK trial 生成、GDS postprocess、pin/label/well/tap 处理，
还是某个 runner/env 细节。

请尽量上传完整目录，不要只上传最终 GDS。

## 2. Local Evidence Summary

### Passing artifact

Only the curated packaged replay GDS currently passes:

```text
reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031
```

Local replay result:

```text
DRC: 0
Extraction: substrate=gnda, equiv=0
LVS: PASS, "Circuits match uniquely"
PEX: parsed, 37 caps
```

### Failing local fresh generation

Fresh local MAGICAL generation fails even with exact `cand_0031` sizing:

```text
exact cand_0031 sizing x multiple fresh MAGICAL runs -> equiv gnda-vdda
vdda dropped from extracted subckt
PMOS source/body extracted on gnda
MOS-only LVS fails
```

Observed local failure classes:

```text
nf=2              -> extracted raw MOS 8 -> 10, vdda dropped, LVS fail
multi+1           -> gate pass but PEX signature normalized/no confirmed diversity
W/L perturbation  -> equiv gnda-vdda / extraction collapse
same-sizing seed  -> 0/3 clean extraction
```

Current conclusion:

```text
Harness trust gate is usable.
Local fresh layout producer is not yet usable for new SMCNR positives.
Upstream clean-generation artifacts are required to locate the gap.
```

## 3. Please Upload: Minimum Required Package

Please upload the original successful `SMCNR_SE_2st_AMP/cand_0031` run tree,
including intermediate layout files. Minimum useful package:

```text
SMCNR_SE_2st_AMP/cand_0031/
  state.json
  evidence.jsonl
  candidate.json or equivalent candidate metadata
  source/input SPICE netlist used by MAGICAL
  MAGICAL JSON/config used for this candidate
  MAGICAL logs
  placement logs
  routing logs
  *.place.gds
  *.route.gds
  final MAGICAL GDS before Sky130 remap
  Sky130-remapped GDS
  pinned/pin-label/pin-shape postprocessed GDS, if any
  lvsNetRenames or equivalent net rename file/config
  Magic DRC Tcl/log
  Magic extraction Tcl/log
  *.ext
  extracted raw SPICE
  extracted connectivity SPICE
  Netgen LVS Tcl/log/report
  PEX summary
  PEX raw extracted SPICE with capacitors
```

If the exact directory is large, please keep the structure and compress it:

```bash
tar -czf smcnr_cand0031_upstream_full_run.tar.gz SMCNR_SE_2st_AMP/cand_0031/
```

## 4. Please Upload: Full Batch If Available

If available, the full SMCNR run is more valuable than only `cand_0031`:

```text
SMCNR_SE_2st_AMP/
  run_summary/
  all_candidates/
  best_candidate/
  generated layout directories for pass and fail candidates
  candidate_index.csv
  optimizer logs
  batch logs
```

Especially useful:

```text
all candidates that reached DRC/LVS/PEX
all candidates that failed extraction/LVS
candidate index with sizing values and closure level
```

This lets us compare successful and failed upstream GDS patterns.

## 5. Please Include Environment Metadata

Please include exact environment information from the machine/run that generated
the clean GDS:

```text
MAGICAL commit hash
MAGICAL repo status / patch diff, if modified
Docker image tag and image hash, if Docker was used
Anaroute version or commit
Python version
gdspy version
gdstk version, if used
numpy version
sky130 PDK source/version/hash
PDK_ROOT
SKY130A
Magic version
Netgen version
ngspice version
OS / WSL / Docker base image
```

Helpful commands:

```bash
git -C <MAGICAL_REPO> rev-parse HEAD
git -C <MAGICAL_REPO> status --short
python3 --version
python3 - <<'PY'
import sys
print("python", sys.version)
for name in ["gdspy", "gdstk", "numpy"]:
    try:
        mod = __import__(name)
        print(name, getattr(mod, "__version__", "unknown"))
    except Exception as exc:
        print(name, "not importable", repr(exc))
PY
magic --version
netgen-lvs -batch quit
ngspice --version
docker image inspect <IMAGE_NAME_OR_ID> --format '{{.Id}} {{.RepoTags}}'
```

## 6. Please Include Runner Command And Env

Please include the exact command or script used to generate `cand_0031`:

```text
entrypoint script
command-line arguments
random seed
working directory
environment variables
mounted paths, if Docker/WSL was used
PDK generation command, if any
postprocess scripts and their order
```

Useful shell capture:

```bash
env | sort > upstream_env.txt
history | tail -200 > upstream_recent_commands.txt
```

If a runner script exists, please upload the script rather than a screenshot.

## 7. What We Will Diff Locally

After receiving the artifacts, we will compare:

```text
upstream clean route/final/pinned GDS
vs
local failed fresh MAGICAL GDS
```

Main checks:

```text
GDS hierarchy and cell names
per-device GDS cells
well/tap/substrate-related layers
pin labels and pin shapes
vdda/gnda metal and labels
lvsNetRenames
Magic .ext equiv records
extracted PMOS source/body nets
PEX cap graph
tool versions and postprocess steps
```

Target answer:

```text
What does upstream clean GDS contain, or avoid, that local fresh GDS does not?
```

## 8. Boundary

We are not asking to declare new samples positive. We are asking for upstream
artifacts to explain the toolchain gap. Until this gap is resolved:

```text
cand_0031 remains the only reviewed positive SMCNR baseline
local fresh MAGICAL SMCNR generation is not trusted for positive data production
failed local variants are failure-case diagnostics only
```
