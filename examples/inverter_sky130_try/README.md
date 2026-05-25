# inverter_core Sky130 示例

这是默认推荐的最小 MAGICAL clean netlist 示例。

推荐入口：

```bash
python3 tools/sky130_adapter/run_sky130_case_pipeline.py \
  --netlist examples/inverter_sky130_try/inverter_clean.sp \
  --top-cell inverter_core \
  --vdd VPWR \
  --vss VGND \
  --convert-xschem no \
  --case-name inverter_core \
  --out-dir generated/sky130_cases/inverter_core
```

建议上传的轻量文件：

- `inverter_clean.sp`
- `inverter_sky130_name_test.sp`
- `inverter_raw.spice`
- `inverter.json`
- `README.md`

GDS、log、ioPin、placement/routing 中间结果均可再生成，不建议提交。
