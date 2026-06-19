# Sky130 Adapter 用户快速指南

本文档给出 MAGICAL Sky130 bridge/remap flow 的最短使用路径。默认推荐 Python CLI，底层 shell pipeline 仍可直接调用。

## 环境准备

安装并确保以下命令在 `PATH` 中：

- `docker`
- `magic`
- IC LVS `netgen-lvs`
- 可选：`klayout`

安装 host Python 依赖：

```bash
python3 -m pip install -r requirements.txt
```

设置 Sky130 PDK：

```bash
export SKY130A=/path/to/sky130A
```

`$SKY130A` 下需要存在：

- `libs.tech/magic/sky130A.magicrc`
- `libs.tech/netgen/sky130A_setup.tcl`

## 运行 MAGICAL Clean Netlist

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

如果只提供 `--netlist` 和 `--top-cell` 之外的必要 power net 参数，CLI 会自动创建 `generated/user_cases/<case_name>/`，复制输入网表并生成最小 JSON config。

## 运行 xschem Raw Netlist

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

xschem raw netlist 中常见的 `XM` MOS 实例会转换成 MAGICAL clean syntax。若 GND 以 `.GLOBAL GND` 出现，请显式传入 `--vss GND`，转换脚本会将其补入 top subckt port。

## 结果查看

运行结束后终端会打印：

- `FINAL_GDS`
- `DRC_COUNT`
- `CONNECTIVITY_LVS_MATCH`
- `PEX_CAPS`
- `PEX_TOTAL_CAP_FF`
- `SUMMARY_MD`

最终 GDS 可用 KLayout 打开：

```bash
klayout <FINAL_GDS>
```

## 常见失败

- `Docker not found`：安装 Docker 或修正 `PATH`。
- `Magic not found`：安装 Magic 或修正 `PATH`。
- `IC netgen-lvs command was not found in PATH`：安装 Netgen。
- `SKY130A path invalid`：设置正确的 Sky130 PDK 路径。
- `sky130A.magicrc not found`：检查 PDK 的 Magic tech 文件。
- `sky130A_setup.tcl not found`：检查 PDK 的 Netgen setup 文件。
## Netgen LVS Note

Use IC LVS `netgen-lvs` for Sky130 LVS. Do not rely on an unrelated meshing
binary named `netgen`; current scripts only accept plain `netgen` when its
version output identifies IC Netgen 1.x.
