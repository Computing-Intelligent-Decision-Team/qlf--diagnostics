# IOT Workspace Cleanup Plan

Generated: 2026-08-26

This plan covers the large Codex-managed folders under `references/`.
It is intentionally conservative: no original experiment directory should be
deleted until the target is classified, recoverability is clear, and any active
Git worktree state is handled.

## Current Size Summary

| Path | Size | Current role | Recommendation |
|---|---:|---|---|
| `references/.codex-archives` | 6.7G | Retired worktrees and older archived material | Candidate for compression/offline archival; do not delete blindly. |
| `references/.codex-worktrees` | 901M | Registered Git worktrees, some dirty | Keep for now; clean only after branch state is merged/exported. |
| `references/.codex-trash` | 210M | Recoverable discarded run output | Candidate for delete after checksum manifest or tarball. |
| `references/.codex-envs` | 249M | Local conda/env style runtime for AnalogGym DFCFC2 GRPO | Keep until GRPO inference/training environment is reproduced elsewhere. |
| `references/.codex-backups` | 36K | Small pre-alignment backup | Keep; negligible size. |

Total immediately suspicious space: about 8.0G.

## Detailed Findings

### `references/.codex-worktrees`

Registered worktrees were found:

| Worktree | Git status | Recommendation |
|---|---|---|
| `references/.codex-worktrees/pcs-harness-workflow` | Registered on branch `feat/pcs-harness-workflow`; has modified/untracked files | Keep. This is connected to the active `2026-08-26_pcs_harness_workflow` workstream. |
| `references/.codex-worktrees/analoggym-dfcfc2-grpo-checkpoint` | Registered on branch `codex/dfcfc2-grpo-checkpoint` | Keep until its checkpoint/inference work is committed, merged, or explicitly retired. |
| `references/.codex-worktrees/patent-min-cause-replay` | Registered detached; has modified/untracked files | Do not delete directly. First export patch/diff or intentionally retire with manifest. |

Rule: remove registered worktrees only with `git worktree remove <path>` after
status is clean or the dirty state has been intentionally saved.

### `references/.codex-archives`

Largest archived groups:

| Path | Size | Recommendation |
|---|---:|---|
| `references/.codex-archives/AnalogHarness-retired-20260809` | 5.7G | Best first compression/offline-archive candidate. |
| `references/.codex-archives/retired_worktrees` | 973M | Compression/offline-archive candidate after spot-checking no current links point inside it. |
| `references/.codex-archives/retired_misc_20260821` | 132K | Keep or include in small archive bundle. |

These are not active Git worktrees, but they may contain historical evidence.
Preferred action: create compressed archive plus SHA256, then move the original
directory to a dated local holding area or delete after user confirmation.

### `references/.codex-trash`

Current item:

| Path | Size | Recommendation |
|---|---:|---|
| `references/.codex-trash/grpo_batch_v4_0009_partial_20260822` | 210M | Delete candidate after creating a SHA256 manifest or a compressed backup. |

This is already classified as trash. It is the lowest-risk physical cleanup
target, but still should be recoverable if deleted.

### `references/.codex-envs`

Current item:

| Path | Size | Recommendation |
|---|---:|---|
| `references/.codex-envs/analoggym-dfcfc2-grpo` | 249M | Keep for now. It is small compared with archives and may be useful for GRPO reproducibility. |

## Proposed Cleanup Batches

### Batch A: Safe Metadata-Only Step

Already done:

- create `WORKSPACE.md`;
- create top-level navigation links under `projects/`, `datasets/`, `experiments/`, and `external/`;
- keep `references/` as provenance storage.

### Batch B: Trash Cleanup

Candidate target:

- `references/.codex-trash/grpo_batch_v4_0009_partial_20260822`

Safe procedure:

1. Create a SHA256 file manifest for the directory.
2. Create a deterministic or normal compressed archive under `archives/`.
3. Verify archive extraction listing.
4. Move the original directory to a dated holding folder or delete after explicit approval.

Expected space recovered if deleted: about 210M.

### Batch C: Archive Compression

Candidate targets:

- `references/.codex-archives/AnalogHarness-retired-20260809`
- `references/.codex-archives/retired_worktrees`

Safe procedure:

1. Create tar archives under `archives/codex-archives-20260826/`.
2. Record SHA256 checksums.
3. Verify `gzip -t` and `tar -tzf`.
4. Keep the original directories until the user confirms the archives are enough.
5. Only then remove originals.

Expected space recovered after deleting originals: about 6.7G.
Compression ratio is unknown; EDA outputs may compress well, but GDS/binary
artifacts may not.

### Batch D: Registered Worktree Retirement

Not recommended right now.

Before removing any registered worktree:

1. Run `git -C <worktree> status --short`.
2. If dirty, either commit, stash, export a patch, or explicitly discard.
3. Run `git worktree remove <worktree>`.
4. Run `git worktree prune`.

Current state includes active or dirty worktrees, so this batch is blocked until
those workstreams are resolved.

## Recommended Next Action

Start with Batch B and create a recoverable archive of
`references/.codex-trash/grpo_batch_v4_0009_partial_20260822`.

Do not delete the original in the same step unless the user explicitly approves.
After the archive verifies, deletion is low risk.
