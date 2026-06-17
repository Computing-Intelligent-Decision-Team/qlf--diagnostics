# Environment Setup

本文档面向一台尚未安装项目依赖的新机器，目标是在最短路径内复现当前仓库可运行的 Sky130 bridge/remap flow，并为后续搭建 harness 做准备。

## 推荐环境

- WSL2 Ubuntu 24.04.4 LTS
- Kernel: `6.6.87.2-microsoft-standard-WSL2`
- Host Python: 3.12.3
- Docker: 29.4.1
- Magic: 8.3.637
- `netgen-lvs`: 1.5.133

Linux 原生环境也可以，但本文档优先按照上面的验证环境描述。

## 必装工具

必须具备：

- `git`
- `docker`
- `python3`
- `pip`
- `magic`
- `netgen-lvs`
- Sky130 PDK

可选：

- `klayout`

## 安装后检查

完成安装后，先确认这些命令都可用：

```bash
git --version
docker --version
python3 --version
python3 -m pip --version
which magic
magic --version
which netgen-lvs
netgen-lvs -batch quit
echo "$SKY130A"
```

若上述任一项缺失，优先解决环境问题，再开始运行 flow 或搭建 harness。

## 获取仓库

```bash
git clone https://github.com/pcs152/magical-sky130-harness.git
cd magical-sky130-harness
```

安装 host Python 依赖：

```bash
python3 -m pip install -r requirements.txt
```

## Docker 要求

默认 MAGICAL placement/routing 在 Docker 容器中运行：

- image: `jayl940712/magical:latest`

建议先验证 Docker 能正常访问 daemon：

```bash
docker ps
docker image inspect jayl940712/magical:latest >/dev/null
```

若镜像尚未拉取：

```bash
docker pull jayl940712/magical:latest
```

常见问题：

- 在受限环境或 WSL 集成未启用时，脚本内部 `docker run` 可能报：

```text
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
```

这说明 Docker daemon 权限或 WSL 集成仍未就绪，应先修复 Docker 环境，而不是继续调试 pipeline 本身。

## Magic 与 netgen-lvs

当前验证机器上的路径：

- `magic`: `/home/to/eda/tools/install/magic-src/bin/magic`
- `netgen-lvs`: `/usr/bin/netgen-lvs`

本仓库运行时默认依赖 `netgen-lvs` 做 connectivity LVS。文档和 harness 判定逻辑都应以 `netgen-lvs` 为准。

## Sky130 PDK

仓库不包含 Sky130 PDK。必须自行准备 `sky130A`，并确保 `SKY130A` 指向其根目录。

关键文件：

- `libs.tech/magic/sky130A.magicrc`
- `libs.tech/netgen/sky130A_setup.tcl`

示例：

```bash
export SKY130A=/path/to/sky130A
```

检查：

```bash
test -f "$SKY130A/libs.tech/magic/sky130A.magicrc"
test -f "$SKY130A/libs.tech/netgen/sky130A_setup.tcl"
```

## 推荐首次跑通顺序

建议按复杂度从低到高验证：

1. `inverter_core`
2. `ota_core`
3. `current_mirror_core`
4. `SMCNR_SE_2st_AMP`

### 1. inverter

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

### 2. ota_core

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

### 3. current_mirror_core

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

### 4. SMCNR_SE_2st_AMP

```bash
tools/sky130_adapter/run_smcnr_se_2st_amp_sky130_pipeline.sh
```

## 输出与验收

每个 case 的主要输出目录默认位于：

```text
generated/sky130_cases/<case_name>/
```

建议优先检查：

- `summary.md`
- `magic_drc.log`
- `netgen_lvs_report.out`
- `lvs_result_summary.md`
- `pex_summary.md`

## 对 harness 的意义

环境搭通后，不要先把流程绑定到单个电路。建议先抽象这些通用能力：

- case 输入组织
- flow 调用
- summary 收集
- `netgen-lvs` 结果判定
- DRC / LVS / PEX 验收
- 失败样本归档

更多样本和交接背景见 `docs/sky130_adapter/harness_handoff.md`。
