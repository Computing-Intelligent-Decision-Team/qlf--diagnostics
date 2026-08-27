# Handoff Note

## Metadata

- `handoff_id`:
- `created_at`:
- `repo_path`: `/home/qlf/IOT`
- `branch_or_workspace`:
- `workstream`:
- `current_task`:
- `status`: active | paused | blocked | finished

## Selected Context Packs

List the Repomix packs the next Agent should read first.

| pack | generated_path | why needed |
|---|---|---|
| `iot-core-pack` | `docs/context/generated/iot-core-pack.xml` | Project map, AGENTS rules, plans, workstreams |
| `layout-closure-pack` | `docs/context/generated/layout-closure-pack.xml` | Native layout, DRC/LVS/PEX, postlayout, reward |
| `constraint-frontend-pack` | `docs/context/generated/constraint-frontend-pack.xml` | AnalogCoderPro, AnalogGym-Opt, AncstrGNN, SPICE topology, vars, constraint IR |

## Goal At Handoff

Write the current goal in one sentence.

## Completed Since Last Handoff

- Completed task:
- Main result:
- Artifact:
- Verification:

## Files Changed

| path | reason | status |
|---|---|---|
| `path/to/file` | why it changed | created / modified / deleted |

## Files Investigated

| path | what was learned |
|---|---|
| `path/to/file` | short finding |

## Verification Evidence

Paste exact commands and key outputs. Do not say something passed without command evidence.

```bash
echo "replace with verification command"
```

Key result:

```text
replace with important output line or exit status
```

## Open Risks / Gaps

- Risk or gap:
- Why it matters:
- Suggested next check:

## Do Not Touch

List files, generated outputs, or external repos that should not be modified by the next Agent unless explicitly requested.

- `docs/context/generated/` generated packs are ignored and should not be committed.
- External large repositories should not be moved or deeply reorganized during unrelated tasks.

## Next 3-7 Steps

1. First concrete next step.
2. Second concrete next step.
3. Third concrete next step.

## Reactivation Prompt

Paste this into a fresh Codex session:

```text
You are continuing work in /home/qlf/IOT.

First read this handoff note:
<path-to-this-handoff-note>

Then use the selected context packs:
<pack-list>

Continue from workstream:
<workstream-path>

Current task:
<task-id-and-title>

Respect AGENTS.md:
- use agent_workflow tasks;
- record context_pack;
- update execution-log.md immediately;
- verify before claiming completion;
- do not modify generated Repomix pack files under docs/context/generated/.
```
