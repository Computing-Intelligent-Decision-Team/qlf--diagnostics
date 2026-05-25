# ota_core Sky130 示例

这是 xschem raw netlist 转换后进入 MAGICAL bridge/remap pipeline 的 OTA 示例。

推荐入口：

```bash
python3 tools/sky130_adapter/run_sky130_case_pipeline.py \
  --netlist examples/ota_core_sky130_try/ota_core_raw.spice \
  --top-cell ota_core \
  --vdd VDD \
  --vss GND \
  --convert-xschem yes \
  --case-name ota_core \
  --out-dir generated/sky130_cases/ota_core
```

建议上传的轻量文件：

- `ota_core_raw.spice`
- `ota_core_magical.sp`
- `ota_core.json`
- `README.md`

GDS、log、ioPin、placement/routing 中间结果均可再生成，不建议提交。
