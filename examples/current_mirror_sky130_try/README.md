# current_mirror_core Sky130 扩展示例

这是额外 regression/example case，不是 README Quick Start 的主展示对象。

推荐入口：

```bash
python3 tools/sky130_adapter/run_sky130_case_pipeline.py \
  --netlist examples/current_mirror_sky130_try/current_mirror_magical.sp \
  --top-cell current_mirror_core \
  --vdd VDD \
  --vss GND \
  --convert-xschem no \
  --case-name current_mirror_core \
  --out-dir generated/sky130_cases/current_mirror_core
```

建议上传的轻量文件：

- `current_mirror_magical.sp`
- `current_mirror.json`
- `README.md`

GDS、log、ioPin、placement/routing 中间结果均可再生成，不建议提交。
