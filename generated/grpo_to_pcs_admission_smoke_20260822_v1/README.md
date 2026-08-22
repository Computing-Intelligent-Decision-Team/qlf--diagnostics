# GRPO-to-PCS admission smoke v1 summary

- candidates: 4
- L0 prepared/pass: 4
- admitted raw-PEX graph: 2
- rejected before raw-PEX graph: 2
- MAGICAL place-route fail: 2

## Records

| GRPO candidate | PCS cand | M12.M | closure | admission | failed_stage | DRC | LVS | PEX caps | total cap fF |
|---|---|---:|---|---|---|---:|---|---:|---:|
| `grpo_leung_dfcfc2_0000` | `cand_0006` | 363 | `L6_post_layout_pvt` | `admitted_raw_pex_graph` | `None` | 0 | yes | 134 | 3999.37 |
| `grpo_leung_dfcfc2_0001` | `cand_0007` | 178 | `L6_post_layout_pvt` | `admitted_raw_pex_graph` | `None` | 0 | yes | 127 | 3169.88 |
| `grpo_leung_dfcfc2_0002` | `cand_0008` | 127 | `L2_pre_layout_pvt` | `rejected_before_raw_pex_graph` | `magical_place_route` | None | None | None | None |
| `grpo_leung_dfcfc2_0003` | `cand_0009` | 500 | `L2_pre_layout_pvt` | `rejected_before_raw_pex_graph` | `magical_place_route` | None | None | None | None |

## Interpretation

- 0000 and 0001 passed full PCS L1-L6 and are usable raw-PEX capacitor graph samples.
- 0002 and 0003 passed pre-layout nominal/PVT but failed during MAGICAL place-route, so they are negative admission evidence, not graph-training samples.
- PCS reward remains observation-only (`performance: {}`), so `reward=-1.0` is not a statement that the sizing is bad.

## Artifacts

- `admission_summary.json`: machine-readable record.
- `manifest.csv`: compact table.
- `admitted_graphs.jsonl`: only admitted raw-PEX graph samples.
