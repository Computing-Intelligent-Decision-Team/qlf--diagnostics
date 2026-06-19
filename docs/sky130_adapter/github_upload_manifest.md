# GitHub 上传 Manifest

本文档用于上传前分类，避免把额外 PDK 副本、GDS、log、generated 结果和早期实验目录误提交。

## must_upload

| 路径 | 原因 |
| --- | --- |
| `README.md` | 对外入口说明，中文主文档。 |
| `requirements.txt` | Host Python 依赖。 |
| `requirements-grpo.txt` | Vendored AnalogGym GRPO 的可选训练依赖。 |
| `.gitignore` | 防止 generated/GDS/log/build 产物进入仓库。 |
| `third_party/analoggym_grpo/` | GRPO optimizer、AMP 模板和受控 bundled Sky130 PDK。 |
| `tools/sky130_adapter/run_sky130_case_pipeline.py` | 推荐用户入口。 |
| `tools/sky130_adapter/run_sky130_case_pipeline.sh` | 底层稳定 pipeline。 |
| `tools/sky130_adapter/run_sky130_case_regression.sh` | regression 入口。 |
| `tools/sky130_adapter/convert_xschem_sky130_netlist.py` | xschem raw netlist 转换。 |
| `tools/sky130_adapter/remap_gds_to_sky130.py` | bridge/remap 主线核心。 |
| `tools/sky130_adapter/add_sky130_pin_labels_from_iopin.py` | top-port pin label postprocess。 |
| `tools/sky130_adapter/add_sky130_pin_shapes_from_iopin.py` | top-port pin shape postprocess。 |
| `tools/sky130_adapter/prepare_lvs_netlists.py` | connectivity LVS netlist 准备。 |
| `tools/sky130_adapter/analyze_lvs_result.py` | Netgen LVS 摘要。 |
| `tools/sky130_adapter/summarize_magic_pex.py` | PEX summary。 |
| `tools/sky130_adapter/sky130_case_pipeline_helpers.py` | pipeline helper。 |
| `tools/sky130_adapter/collect_sky130_case_summaries.py` | regression summary。 |
| `tools/sky130_adapter/sky130_case_registry.yaml` | regression case registry。 |
| `docs/sky130_adapter/user_quick_start.md` | 用户快速开始。 |
| `docs/sky130_adapter/lvs_pex_explanation.md` | LVS/PEX 方法说明。 |
| `docs/sky130_adapter/native_export_experimental.md` | native export experimental 说明。 |
| `docs/sky130_adapter/github_upload_manifest.md` | 上传清单。 |

## optional_upload

| 路径 | 原因 |
| --- | --- |
| `examples/inverter_sky130_try/` | 主线 inverter 示例，仅应保留输入网表、转换后网表、JSON config、README。 |
| `examples/ota_core_sky130_try/` | 主线 OTA 示例，仅应保留输入网表、转换后网表、JSON config、README。 |
| `examples/current_mirror_sky130_try/` | extra regression 示例，建议清理掉 GDS/log/run 产物后再上传。 |
| `docs/sky130_adapter/sky130_case_pipeline.md` | 既有 pipeline 开发记录，可保留为补充文档。 |
| `docs/sky130_adapter/*analysis*.md` | 调试/分析记录，可合并或放入 archive。 |
| `tools/sky130_adapter/test_*.py` | 轻量单元测试。 |
| `tools/sky130_adapter/generate_anaroute_gds_export_map.py` | experimental native export 工具。 |
| `tools/sky130_adapter/patches/anaroute_native_sky130_export.patch` | 保存 `anaroute` 子模块 native export dirty diff，避免修改丢失。 |
| `flow/python/PnR.py` | experimental native export 支持。 |

## do_not_upload

| 路径/模式 | 原因 |
| --- | --- |
| `generated/` | 大量运行结果和临时输出。 |
| `*.gds` | 版图产物，体积大且可再生成。 |
| `*.log` | 运行日志。 |
| `*.raw` | 临时 raw 文件。 |
| `*.ext` | Magic extraction 临时文件。 |
| `*.spice.tmp` | 临时 netlist。 |
| `anaroute_build/`, `build/`, `*.o`, `*.so` | build 产物。 |
| 其他 Sky130 PDK 副本 | 只保留 `third_party/analoggym_grpo/simulation_files/sky130_pdk` 这一份受控副本。 |
| `examples/inverter_sky130_try_powernets/` | 早期 powernet 实验目录，不作为主线示例。 |
| `examples/inverter_sky130_try_terminal_swap/` | 早期 terminal swap 实验目录，不作为主线示例。 |
| `examples/inverter_sky130_try_terminal_swap_powernets/` | 早期组合实验目录，不作为主线示例。 |
| `tools/sky130_adapter/run_inverter_sky130_pipeline.sh` | 旧 inverter 专用 trial 入口，已被通用 pipeline 取代。 |
| `tools/sky130_adapter/run_magic_lvs_inverter_pinned.sh` | 旧 inverter 专用 LVS trial。 |

## need_review

| 路径 | 需要确认的问题 |
| --- | --- |
| `anaroute/` | 当前是 Git submodule，内部有 `src/writer/wrLayout.cpp/.hpp` 修改。已生成 patch；仍需决定是否提交到子模块仓库并更新父仓库指针。 |
| `docs/sky130_adapter/gds_text_label_analysis*.md` | 分析记录是否合并到 pin label 文档，还是放入 archive。 |
| `docs/sky130_adapter/inverter_pipeline.md` | 是否仍有对外价值，或只保留 quick start。 |
| `docs/sky130_adapter/sky130_pin_label_postprocess.md` | 可作为详细实现文档，但与 README/quick start 有重叠。 |
| `examples/inverter_sky130_try/convert_sky130_netlist.py` | 旧示例本地转换脚本，通用转换脚本已在 `tools/sky130_adapter/`。 |

## 当前建议

不要使用 `git add .`。建议按 commit 主题精确添加文件，并在每次 commit 前运行：

```bash
git diff --cached --name-only
```
