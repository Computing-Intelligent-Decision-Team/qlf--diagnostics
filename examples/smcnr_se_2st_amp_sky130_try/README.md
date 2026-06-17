# SMCNR_SE_2st_AMP Sky130 示例

这是 AnalogGym `SMCNR_SE_2st_AMP` 电路的 Sky130 bridge/remap 示例。该版本来自之前验证通过的 `smcnr_se_2st_amp_physical_final` case，并保留为可重跑的正式 example。

## 输入文件

- `SMCNR_SE_2st_AMP_raw.sp`: 原始参考网表。
- `SMCNR_SE_2st_AMP_layout.sp`: 中间 layout 参考网表。
- `SMCNR_SE_2st_AMP_layout_physical_hspice.sp`: 推荐用于 MAGICAL 的 final physical input netlist。
- `smcnr_se_2st_amp.json`: MAGICAL config。

## 重跑命令

推荐使用仓库内 wrapper：

```bash
tools/sky130_adapter/run_smcnr_se_2st_amp_sky130_pipeline.sh
```

也可以直接调用通用 pipeline：

```bash
tools/sky130_adapter/run_sky130_case_pipeline.sh \
  --case-name SMCNR_SE_2st_AMP \
  --case-dir examples/smcnr_se_2st_amp_sky130_try \
  --top-cell SMCNR_SE_2st_AMP \
  --magical-netlist SMCNR_SE_2st_AMP_layout_physical_hspice.sp \
  --config smcnr_se_2st_amp.json \
  --vdd vdda \
  --vss gnda \
  --out-dir generated/sky130_cases/smcnr_se_2st_amp \
  --convert-xschem no \
  --output-node vout
```

输出目录：

```text
generated/sky130_cases/smcnr_se_2st_amp
```

最终 GDS 会生成在本 example 目录中：

```text
examples/smcnr_se_2st_amp_sky130_try/SMCNR_SE_2st_AMP.sky130.pinned_shapes.gds
```
