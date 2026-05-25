# Experimental Native Sky130 Export

默认对外主线是 bridge/remap flow：

```text
MAGICAL internal GDS
-> remap_gds_to_sky130.py
-> pin label / pin shape postprocess
-> Magic DRC / extraction / connectivity LVS / PEX summary
```

native Sky130 export 目前仅作为实验功能保留。它尝试让 MAGICAL/anaroute 在导出 GDS 时直接使用 Sky130 drawing layers，减少后处理 remap 的需求。

## 相关文件

- `flow/python/PnR.py`
- `anaroute/src/writer/wrLayout.cpp`
- `anaroute/src/writer/wrLayout.hpp`
- `tools/sky130_adapter/generate_anaroute_gds_export_map.py`
- `tools/sky130_adapter/run_inverter_sky130_native_export_trial.sh`

实验入口依赖环境变量：

```bash
export MAGICAL_GDS_EXPORT_MAP=/path/to/sky130_anaroute_gds_export.map
```

## 当前定位

- 不作为 README Quick Start。
- 不作为默认 regression pass/fail 标准。
- 可以作为后续 native drawing-layer export 的开发基础。
- 若 `anaroute` 保持 Git submodule 形式，相关 writer 修改需要进入对应子模块仓库，或在本仓库提供 patch 文件。

## 建议处理

在 GitHub 打包时，推荐将 native export 明确标记为 experimental。若暂时不能提交 `anaroute` 子模块内部改动，建议生成 patch 存放在：

```text
tools/sky130_adapter/patches/anaroute_native_sky130_export.patch
```

这样不会丢失实验成果，也不会让主仓库引用一个无法复现的 dirty submodule 状态。
