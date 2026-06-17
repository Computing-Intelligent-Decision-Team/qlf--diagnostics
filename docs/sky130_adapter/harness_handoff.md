# Harness Handoff

## 目标

本仓库的定位不是单一电路 demo，而是 `MAGICAL-Sky130 bridge/remap flow` 的可重跑工程基础。

当前需要基于这套仓库搭建的 harness，目标是：

- 面向大部分电路的通用反馈修正流程
- 能围绕已有代表性电路样本做自动化运行、结果收集、失败判定与后续修正
- 后续可以持续加入新的电路、新的失败模式和新的修正策略

当前仓库提供的是第一批可用于搭建 harness 的基线样本与主线 flow，不追求一次性覆盖所有复杂情况。

## 主线 Flow

```text
Sky130 netlist
-> MAGICAL placement/routing
-> Sky130 GDS remap
-> top-port pin label / pin shape postprocess
-> Magic DRC
-> Magic extraction
-> netgen-lvs connectivity LVS
-> PEX summary
```

推荐入口：

- `tools/sky130_adapter/run_sky130_case_pipeline.py`
- `tools/sky130_adapter/run_sky130_case_pipeline.sh`
- `tools/sky130_adapter/run_sky130_case_regression.sh`
- `tools/sky130_adapter/run_smcnr_se_2st_amp_sky130_pipeline.sh`

## 当前 baseline case

| Case | Path | Entry | Expected DRC | Expected LVS | Notes |
| --- | --- | --- | --- | --- | --- |
| `inverter_core` | `examples/inverter_sky130_try` | `run_sky130_case_pipeline.py` | `0` | `yes` | 最小闭环样本 |
| `ota_core` | `examples/ota_core_sky130_try` | `run_sky130_case_pipeline.py` | `see summary` | `yes` | 中等复杂度样本 |
| `current_mirror_core` | `examples/current_mirror_sky130_try` | `run_sky130_case_pipeline.py` | `see summary` | `yes` | 简单模拟结构 |
| `SMCNR_SE_2st_AMP` | `examples/smcnr_se_2st_amp_sky130_try` | `run_smcnr_se_2st_amp_sky130_pipeline.sh` | `0` | `yes` | 复杂模拟样本 |

这些样本的作用不是展示某一个电路本身，而是帮助抽象一套以后可以不断扩展的通用 harness。

## SMC baseline

本阶段已将历史 SMC 尝试收敛为正式 example：

```text
examples/smcnr_se_2st_amp_sky130_try/
```

当前已验证结果来自：

```text
generated/sky130_cases/smcnr_se_2st_amp/summary.md
```

关键结果：

- `DRC_COUNT = 0`
- `CONNECTIVITY_LVS_MATCH = yes`
- `PEX_CAPS = 33`
- `PEX_TOTAL_CAP_FF = 630.779 fF`
- `RAW_SUBCKT_PORTS = vdda gnda vin vip ibias vout`
- `ANONYMOUS_NODES = a_1225_510#,a_1260_490# a_3184_4586#`

这组结果可以作为当前 SMC baseline 的验收参考。

## GitHub 边界

建议上传：

- 主线源码
- 正式 examples
- 运行脚本
- 用户说明文档
- 本交接文档

建议不上传：

- `generated/`
- `*.gds`
- `*.log`
- `*.ext`
- `*.raw`
- 旧的历史试验目录
- 外层 `/home/to/eda` 工作区内容

说明：

`generated/` 默认视为运行结果区，不作为 GitHub 主交付物。若需要保留 baseline 信息，优先保留摘要和文档，而不是整批生成产物。

## 环境要求

从零搭建运行环境时，请先完成 `docs/sky130_adapter/environment_setup.md` 中的步骤。

必须具备：

- `docker`
- `python3`
- `magic`
- `netgen-lvs`
- `SKY130A`

如果这些依赖未就绪，不要直接开始调试 harness。

## 下一步建议

建议先抽象：

1. 统一 case 入口
2. 统一收集 `summary.md` / DRC / `netgen-lvs` / PEX 结果
3. 建立成功 / 失败判定逻辑
4. 用 `inverter`、`ota`、`current_mirror`、`smc` 四类样本验证通用 harness 框架
5. 后续逐步加入更多复杂电路和失败修正策略

当前仓库目标不是“最后形态的 harness”，而是“可持续扩展的 harness 起点”。
