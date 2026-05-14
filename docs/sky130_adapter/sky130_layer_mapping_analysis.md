# Sky130 Layer Mapping Analysis

## 1. 当前目标

本阶段目标是把 MAGICAL 默认的 `examples/mockPDK` 逐步替换为真实开源 Sky130 PDK，而不是长期保留一个 mockPDK 副本。

当前 `examples/sky130PDK` 仍然只是从 `examples/mockPDK` 复制并重命名得到的临时骨架。它的作用是验证 MAGICAL 的 PDK 路径、文件名和最小接口是否能跑通，不代表已经完成 Sky130 PDK 适配。真实适配还需要替换 layer number、LEF routing/via 规则、器件生成层名、techfile/simple techfile 映射，并最终接入 Magic/KLayout DRC 检查。

本次分析只做 layer / GDS mapping 调研，不修改源码，不修改 `examples/sky130PDK`。

## 2. MAGICAL 当前使用的 PDK layer

当前 `examples/sky130PDK` 是 mockPDK 副本，因此下面的 layer number 是 MAGICAL/mockPDK 当前编号，不是 Sky130 真实编号。

| MAGICAL layer | 当前 layer number | 当前用途 | 出现在哪个文件 | 是否第一阶段必须支持 |
| --- | ---: | --- | --- | --- |
| `NW` | 3 | PMOS nwell / guard ring / well 标记 | `sky130.techfile.simple`, `device_generation/glovar.py`, MOS generator | 是，器件生成会画 PMOS well |
| `OD` | 6 | diffusion/active，MOS S/D、tap、router 读 GDS 时专门提取 OD | `sky130.techfile`, `sky130.techfile.simple`, `glovar.py`, `Mosfet.py`, `parGds.cpp` | 是 |
| `VTL_N` | 12 | mock 低阈值 NMOS implant/mark | `sky130.techfile.simple`, `glovar.py`, `Mosfet.py` | 阶段一可保留占位；真实 Sky130 无同名直接层 |
| `VTL_P` | 13 | mock 低阈值 PMOS implant/mark | `sky130.techfile.simple`, `glovar.py`, `Mosfet.py` | 阶段一可保留占位；真实 Sky130 无同名直接层 |
| `PO` | 17 | poly/gate/poly resistor body | `sky130.lef`, `sky130.techfile`, `sky130.techfile.simple`, `glovar.py`, `Mosfet.py`, `Resistor.py` | 是 |
| `OD_25` | 18 | mock 2.5V/OD option marker | `sky130.techfile.simple`, `glovar.py`, `Mosfet.py` | 否，除非启用 2.5/3.3V 器件 |
| `PP` | 25 | P implant / PMOS or p+ region marker | `sky130.techfile.simple`, `glovar.py`, `Mosfet.py`, `Resistor.py` | 是，PMOS/guard ring/部分 resistor 使用 |
| `NP` | 26 | N implant / NMOS or n+ region marker | `sky130.techfile.simple`, `glovar.py`, `Mosfet.py` | 是 |
| `RPO` | 29 | resistor poly block / poly resistor marker | `sky130.techfile.simple`, `glovar.py`, `Resistor.py` | 若只跑 inverter 可非必须；支持 resistor 时必须 |
| `CO` | 30 | contact/cut，mock 里作为 OD/PO 到 M1 的 contact | `sky130.lef`, `sky130.techfile`, `sky130.techfile.simple`, `glovar.py`, `Mosfet.py`, `Resistor.py` | 是 |
| `M1` | 31 | 第一层 routing metal，device pin/contact metal，router 第一 routing 层 | `sky130.lef`, `sky130.techfile`, `sky130.techfile.simple`, `glovar.py`, device generator, router | 是 |
| `M2` | 32 | 第二层 routing metal | `sky130.lef`, `sky130.techfile`, `sky130.techfile.simple` | 是，router 使用 |
| `M3` | 33 | 第三层 routing metal | `sky130.lef`, `sky130.techfile`, `sky130.techfile.simple` | 是，router 使用 |
| `M4` | 34 | 第四层 routing metal | `sky130.lef`, `sky130.techfile`, `sky130.techfile.simple` | 是，router 使用 |
| `M5` | 35 | 第五层 routing metal | `sky130.lef`, `sky130.techfile`, `sky130.techfile.simple` | 是，router 使用 |
| `M6` | 36 | 第六层 routing metal / power layer 默认值 | `sky130.lef`, `sky130.techfile`, `sky130.techfile.simple`, `Params.py` | 是，现有 flow 默认 powerLayer=6 |
| `M7` | 37 | 第七层 routing metal | `sky130.lef`, `sky130.techfile`, `sky130.techfile.simple` | 阶段一不建议直接映射到 Sky130，因为 Sky130 只有 li1 + met1..met5 |
| `M8` | 38 | mock extra routing layer | `sky130.techfile.simple`, `glovar.py` | 否 |
| `M9` | 39 | mock extra routing layer | `sky130.techfile.simple` | 否 |
| `M10` | 40 | mock extra routing layer | `sky130.techfile.simple` | 否 |
| `VIA1` | 51 | M1-M2 cut in mock LEF | `sky130.lef`, `sky130.techfile`, `sky130.techfile.simple`, `glovar.py` | 是，如果保留 mock routing stack 命名 |
| `VIA2` | 52 | M2-M3 cut | `sky130.lef`, `sky130.techfile`, `sky130.techfile.simple`, `glovar.py` | 是 |
| `VIA3` | 53 | M3-M4 cut | `sky130.lef`, `sky130.techfile`, `sky130.techfile.simple`, `glovar.py` | 是 |
| `VIA4` | 54 | M4-M5 cut | `sky130.lef`, `sky130.techfile`, `sky130.techfile.simple`, `glovar.py` | 是 |
| `VIA5` | 55 | M5-M6 cut | `sky130.lef`, `sky130.techfile`, `sky130.techfile.simple`, `glovar.py` | 是 |
| `VIA6` | 56 | M6-M7 cut | `sky130.lef`, `sky130.techfile`, `sky130.techfile.simple`, `glovar.py` | 不建议阶段一采用；Sky130 无 met6/met7 |
| `VIA7` | 57 | mock extra via | `sky130.techfile.simple`, `glovar.py` | 否 |
| `VIA8` | 58 | mock extra via | `sky130.techfile.simple`, `glovar.py` | 否 |
| `VIA9` | 59 | mock extra via | `sky130.techfile.simple` | 否 |
| `TECHDB` | 63 | mock marker layer | `sky130.techfile.simple` | 否 |
| `VTH_N` | 67 | mock high/threshold marker | `sky130.techfile.simple`, `glovar.py`, `Mosfet.py` | 仅 hvt/lvt 器件需要；基础 1.8V inverter 可不支持 |
| `VTH_P` | 68 | mock high/threshold marker | `sky130.techfile.simple`, `glovar.py`, `Mosfet.py` | 仅 hvt/lvt 器件需要 |
| `RPDMY` | 115 | resistor dummy marker | `sky130.techfile.simple`, `glovar.py` | 否，除非支持 resistor |
| `RH` | 117 | high-resistor marker | `sky130.techfile.simple`, `glovar.py`, `Resistor.py` | 否，除非支持 resistor |
| `MRDMY` | 150 | metal resistor dummy marker | `sky130.techfile.simple`, `glovar.py` as `DMEXCL` | 否 |
| `TSV_PPI` | 155 | mock MOM dummy / PPI marker | `sky130.techfile.simple`, `glovar.py` as `MOMDMY` | 否 |
| `STDPIN` | 171 | mock standard-cell pin marker | `sky130.techfile.simple` | 否 |
| `STOPIN` | 未出现 | 用户需求中提到，但当前 `sky130.techfile/simple/lef` 未出现该层 | 未在扫描文件中找到 | 否；需确认是否为 `STDPIN` 或外部流程命名 |
| `LVS_DUMMY` | 208 | LVS dummy marker；`glovar.py` 中类似 `LVSDMY` | `sky130.techfile.simple`, `glovar.py` | 否 |

当前 LEF 中实际被 router 解析的层只有 `PO`、`CO`、`M1`..`M7`、`VIA1`..`VIA6`。`sky130.techfile` 只包含 `OD`、`PO`、`CO`、`M1`..`M7`、`VIA1`..`VIA6`，用于 anaroute 的 LEF layer name 到 GDS layer number 映射。

## 3. Sky130 真实 PDK 中可用的 layer

本机查找结果：

- `$PDK_ROOT=/home/to/.ciel`
- `$PDK_ROOT/sky130A` 存在，实际是 symlink：`/home/to/.ciel/sky130A -> ciel/sky130/versions/.../sky130A`
- `~/.ciel/sky130A` 同一位置存在
- `/usr/local/share/pdk/sky130A` 未找到

主要参考文件：

- `/home/to/.ciel/sky130A/libs.tech/klayout/tech/sky130A.map`
- `/home/to/.ciel/sky130A/libs.tech/klayout/tech/sky130A.lyp`
- `/home/to/.ciel/sky130A/libs.tech/magic/sky130A-GDS.tech`
- `/home/to/.ciel/sky130A/libs.tech/magic/sky130A.tech`
- `/home/to/.ciel/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef`

| Sky130 layer name | GDS layer | datatype | 来源文件 | 备注 |
| --- | ---: | ---: | --- | --- |
| `nwell.drawing` / Magic `NWELL` | 64 | 20 | `sky130A.lyp`, `sky130A-GDS.tech` | nwell drawing |
| `nwell.pin` | 64 | 16 | `sky130A.lyp`, `sky130A.map` | LEF pin / pin purpose |
| `pwell.pin` | 122 | 16 | `sky130A.map` | pwell pin purpose |
| `diff.drawing` / Magic `DIFF` | 65 | 20 | `sky130A.lyp`, `sky130A-GDS.tech` | active/diffusion drawing |
| `tap.drawing` / Magic `TAP` | 65 | 44 | `sky130A.lyp`, `sky130A-GDS.tech` | tap diffusion |
| `psdm.drawing` / Magic `PSDM` | 94 | 20 | `sky130A.lyp`, `sky130A-GDS.tech` | p+ source/drain implant |
| `nsdm.drawing` / Magic `NSDM` | 93 | 44 | `sky130A.lyp`, `sky130A-GDS.tech` | n+ source/drain implant |
| `poly.drawing` / Magic `POLY` | 66 | 20 | `sky130A.lyp`, `sky130A-GDS.tech` | polysilicon / gate |
| `npc.drawing` / Magic `NPC` | 95 | 20 | `sky130A.lyp`, `sky130A-GDS.tech` | nitride poly cut, often used around poly contacts |
| `li1.drawing` / LEF `li1` | 67 | 20 | `sky130A.map`, `sky130A.lyp`, techlef | local interconnect routing layer |
| `licon` / Magic `LICON` | 66/67 | 44 | `sky130A-GDS.tech`, techlef | contact from diffusion/poly to li1; KLayout map emphasizes LEF `mcon` for li1-met1 |
| `mcon.drawing` / LEF `mcon` | 67 | 44 | `sky130A.map`, `sky130A.lyp`, techlef | contact/via between li1 and met1 |
| `met1.drawing` / LEF `met1` | 68 | 20 | `sky130A.map`, `sky130A.lyp`, techlef | first true metal |
| `via.drawing` / LEF `via` | 68 | 44 | `sky130A.map`, `sky130A.lyp`, techlef | met1-met2 via |
| `met2.drawing` / LEF `met2` | 69 | 20 | `sky130A.map`, `sky130A.lyp`, techlef | second true metal |
| `via2.drawing` / LEF `via2` | 69 | 44 | `sky130A.map`, `sky130A.lyp`, techlef | met2-met3 via |
| `met3.drawing` / LEF `met3` | 70 | 20 | `sky130A.map`, `sky130A.lyp`, techlef | third true metal |
| `via3.drawing` / LEF `via3` | 70 | 44 | `sky130A.map`, `sky130A.lyp`, techlef | met3-met4 via |
| `met4.drawing` / LEF `met4` | 71 | 20 | `sky130A.map`, `sky130A.lyp`, techlef | fourth true metal |
| `via4.drawing` / LEF `via4` | 71 | 44 | `sky130A.map`, `sky130A.lyp`, techlef | met4-met5 via |
| `met5.drawing` / LEF `met5` | 72 | 20 | `sky130A.map`, `sky130A.lyp`, techlef | top true metal |
| `LVTN` | 125 | 44 | `sky130A-GDS.tech` | low-Vt NMOS marker; not named `VTL_N` |
| `HVTP` | 78 | 44 | `sky130A-GDS.tech` | high-Vt PMOS marker; not named `VTL_P` |
| `RPM` | 86 | 20 | `sky130A-GDS.tech` | poly resistor marker |

Sky130 LEF routing stack from `sky130_fd_sc_hd__nom.tlef`:

| LEF layer | Type | Direction | GDS drawing layer/datatype | Notes |
| --- | --- | --- | --- | --- |
| `li1` | ROUTING | VERTICAL | 67/20 | local interconnect, pitch `0.46 0.34`, width `0.17` |
| `mcon` | CUT | n/a | 67/44 | li1-met1 cut, width `0.17`, spacing `0.19` |
| `met1` | ROUTING | HORIZONTAL | 68/20 | width `0.14`, pitch `0.34` |
| `via` | CUT | n/a | 68/44 | met1-met2 via |
| `met2` | ROUTING | VERTICAL | 69/20 | width `0.14`, pitch `0.46` |
| `via2` | CUT | n/a | 69/44 | met2-met3 via |
| `met3` | ROUTING | HORIZONTAL | 70/20 | width `0.3`, pitch `0.68` |
| `via3` | CUT | n/a | 70/44 | met3-met4 via |
| `met4` | ROUTING | VERTICAL | 71/20 | width `0.3`, pitch `0.92` |
| `via4` | CUT | n/a | 71/44 | met4-met5 via |
| `met5` | ROUTING | HORIZONTAL | 72/20 | width `1.6`, pitch `3.4` |

## 4. 初步 layer mapping 建议

下面是第一轮建议，不是最终规则。核心问题是 Sky130 有 `li1/mcon/met1` 结构，而 MAGICAL mockPDK 的 `M1` 当前是第一层 routing metal，同时 device generator 也把 `M1` 当作 contact 后的第一层金属来画。

| MAGICAL layer | 可能对应的 Sky130 layer | 映射依据 | 风险 | 是否建议第一阶段采用 |
| --- | --- | --- | --- | --- |
| `NW` | `nwell.drawing` 64/20 | PMOS well 语义一致 | nwell enclosure/tap DRC 仍需真实规则 | 是 |
| `OD` | `diff.drawing` 65/20 | MAGICAL OD 是 active/diffusion；Sky130 `diff` 是 active diffusion | Sky130 还区分 `tap` 65/44；MAGICAL 当前 OD 同时可能承载 device diffusion/tap | 是，但 tap 需另行处理 |
| `PO` | `poly.drawing` 66/20 | gate/poly 语义一致 | Sky130 poly contact 需要 `licon`/`npc` 规则，不是单纯 PO+CO | 是 |
| `CO` | `licon` 或 `mcon`，需拆分；临时可映射到 `licon`/contact 语义 | MAGICAL CO 表示 OD/PO 到第一导体的 contact；Sky130 到 li1 的 contact 是 licon，li1 到 met1 是 mcon | 一个 `CO` 无法同时表示 licon 和 mcon；若 MAGICAL M1 映射到 met1，则 CO 更像 mcon；若 M1 映射到 li1，则 CO 更像 licon | 谨慎；第一阶段需要明确 routing stack 方案 |
| `M1` | 方案 A: `li1` 67/20；方案 B: `met1` 68/20 | MAGICAL M1 是第一 routing layer。Sky130 LEF 中第一 routing layer是 `li1`，第一 true metal 是 `met1` | 方案 A 更贴 LEF routing stack，但 device generator 的 M1 会输出 local interconnect；方案 B 更贴“metal1”直觉，但会跳过 li1/licon/mcon 结构 | 建议阶段一优先评估方案 A；若只做粗略 GDS 输出可试方案 B |
| `VIA1` | 方案 A: `mcon` 67/44；方案 B: `via` 68/44 | 如果 M1=li1 且 M2=met1，VIA1 应为 mcon；如果 M1=met1 且 M2=met2，VIA1 应为 via | 取决于 M1/M2 stack 选择，不能独立决定 | 随 M1/M2 方案确定 |
| `M2` | 方案 A: `met1`; 方案 B: `met2` | 若纳入 li1，M2=met1；若跳过 li1，M2=met2 | 方案 B 跳过 Sky130 local interconnect | 随方案确定 |
| `VIA2` | 方案 A: `via`; 方案 B: `via2` | 与 M2/M3 对应 | 同上 | 随方案确定 |
| `M3` | 方案 A: `met2`; 方案 B: `met3` | 与 stack 对应 | 同上 | 随方案确定 |
| `VIA3` | 方案 A: `via2`; 方案 B: `via3` | 与 stack 对应 | 同上 | 随方案确定 |
| `M4` | 方案 A: `met3`; 方案 B: `met4` | 与 stack 对应 | 同上 | 随方案确定 |
| `VIA4` | 方案 A: `via3`; 方案 B: `via4` | 与 stack 对应 | 同上 | 随方案确定 |
| `M5` | 方案 A: `met4`; 方案 B: `met5` | 与 stack 对应 | 同上 | 随方案确定 |
| `VIA5` | 方案 A: `via4`; 方案 B: 无真实对应 | Sky130 最高 via 是 via4，即 met4-met5 | 若使用方案 B，M6 无对应真实 metal；如果方案 A，VIA5=via4 且 M6=met5 | 仅方案 A 建议 |
| `M6` | 方案 A: `met5`; 方案 B: 无真实对应 | Sky130 top metal 是 met5；MAGICAL 默认 powerLayer=6 | 如果 router 需要 M6，方案 A 刚好能映射到 met5；但 LEF 层数和 via 表需一致 | 是，建议方案 A 下采用 |
| `M7` | 无直接对应 | Sky130 无 met6/met7 | 当前 mock LEF 有 M7，但 Sky130 stack 不支持 | 否 |
| `VIA6` | 无直接对应 | Sky130 无 met6/met7 | 当前 mock LEF 有 VIA6，但真实 Sky130 无对应 | 否 |
| `NP` | `nsdm.drawing` 93/44 | MAGICAL NP 是 n+ implant；Sky130 NSDM 是 n+ source/drain implant | 需确认 n-tap/diff/tap 组合规则 | 是 |
| `PP` | `psdm.drawing` 94/20 | MAGICAL PP 是 p+ implant；Sky130 PSDM 是 p+ source/drain implant | 需确认 p-tap/diff/tap 组合规则 | 是 |
| `RPO` | `RPM` 86/20 或 resistor-specific marker | MAGICAL RPO 用于 poly resistor block；Sky130 有 RPM/poly resistor marker | resistor flow 需要更多规则 | 非 inverter 阶段可暂缓 |
| `VTL_N` | 可能是 `LVTN` 125/44 | 名称语义接近 low-Vt NMOS | Sky130 基础 `nfet_01v8` 不一定需要 LVTN；MAGICAL 名称 `VTL_N` 和 Sky130 `LVTN` 不同 | 基础 inverter 不建议启用；lvt 器件另议 |
| `VTL_P` | 无明确直接对应；可能与 Sky130 PMOS threshold option 层不同 | Magic GDS tech 中看到 `HVTP`，未看到与 `VTL_P` 同义的基础层 | 直接映射风险高 | 否，先占位或禁用 |
| `VTH_N` | 未确认直接对应 | mock hvt marker | Sky130 hvt/lvt device marker 与 MAGICAL mock 不同 | 否 |
| `VTH_P` | `HVTP` 78/44 可能相关 | Magic GDS tech 有 HVTP | 只适用于 hvt PMOS，不适用于基础 1.8V pfet | 否 |
| `LVS_DUMMY` / `LVSDMY` | 无直接阶段一映射 | mock LVS dummy | 不影响基础 inverter routing | 否 |
| `STDPIN` / `STOPIN` | Sky130 LEF pin purpose通常是 datatype 16/48/58 等 | mock standard pin marker | `STOPIN` 未在当前文件出现；需确认外部需求 | 否 |

关于重点问题：

- `OD` 最接近 Sky130 `diff.drawing`，而不是 `ndiff`/`pdiff`。在 Magic 中 `ndiff`/`pdiff` 是由 diffusion 加 implant/well 组合出来的抽象/derived layer，GDS drawing 层是 `DIFF` 65/20，加上 `NSDM`/`PSDM` 和 well/tap 区分。
- `PO` 应对应 `poly.drawing` 66/20。
- `CO` 不能无脑映射。MAGICAL 的 `CO` 是单一 contact；Sky130 从 diffusion/poly 到 local interconnect 是 `licon1`，从 `li1` 到 `met1` 是 `mcon`。本机 PDK 中 `sky130A.lyp` 标出 `licon1.drawing - 66/44`，Magic GDS tech 也有 `calma LICON1 66 44`，因此当前 layer map 将 `CO` 映射为 `licon1.drawing` 66/44。`VIA1` 继续对应 `mcon` 67/44。
- `M1` 建议优先考虑映射到 `li1`，因为 Sky130 tech LEF 把 `li1` 定义为第一 ROUTING layer。但这会让 MAGICAL device generator 中的 `M1` 变成 local interconnect，需要重新审视 MOS/contact 输出。
- `VIA1` 若采用 `M1=li1, M2=met1`，应对应 `mcon`；若采用 `M1=met1, M2=met2`，则对应 `via`。
- `M2/M3/M4/M5/M6` 若采用包含 li1 的方案，建议对应 `met1/met2/met3/met4/met5`。
- `NW` 应对应 `nwell.drawing` 64/20。
- `NP/PP` 应分别对应 `nsdm.drawing` 93/44 和 `psdm.drawing` 94/20。
- `VTL_N/VTL_P` 没有与 mock 名称完全一致的 Sky130 直接层。基础 `sky130_fd_pr__nfet_01v8/pfet_01v8` 阶段应尽量不依赖这些层；LVT/HVT 器件需要单独建立 device variant 到 Sky130 marker layer 的映射。

## 5. 不能直接替换的风险

- Sky130 有 `li1/mcon/met1` 结构，而 MAGICAL mockPDK 当前可能假设 `M1` 是第一层 routing metal。直接把 `M1` 改成 `met1` 会跳过 local interconnect；直接把 `M1` 改成 `li1` 又会改变 device generator 中 `M1` 的物理语义。
- MAGICAL 的 MOS generator 默认使用 `OD/PO/CO/M1/NP/PP/NW` 等固定层名，并通过 `device_generation/device_generation/glovar.py` 写死 layer number、datatype、间距和 enclosure。真实 Sky130 需要拆分 diffusion、tap、licon、li1、mcon、met1 等规则，不能只改 three PDK files。
- Anaroute 侧还会在 `parGds.cpp` 中通过 techfile 查找 `"OD"` 来提取 diffusion blockage/OD overlap 信息，所以 `OD` 映射必须同时满足 router 的读 GDS 逻辑。
- 真实 Sky130 DRC 需要 Magic/KLayout tech 规则，不是简单改 GDS layer number 就能满足。比如 nwell tap、implant enclosure、poly contact 的 `npc`、li/mcon/met1 enclosure 都需要真实规则。
- 第一阶段可能只能做到“输出到真实 Sky130 layer number / datatype 的近似 GDS”，不能保证 DRC clean，也不能保证 LVS/extraction 完全正确。
- 当前 mock LEF 有 `M1`..`M7` 和 `VIA1`..`VIA6`，但 Sky130 routing stack 只有 `li1 + met1..met5` 和 `mcon/via/via2/via3/via4`。如果 MAGICAL 仍强依赖第 6 层 powerLayer 或 M7，需要调整 routing layer count 或 layer mapping。
- `techfile.simple` 当前只有 layer number，没有 datatype；Sky130 许多关键层用相同 GDS layer 不同 datatype 区分，例如 `li1` 67/20 与 `mcon` 67/44，`diff` 65/20 与 `tap` 65/44。只保留 layer number 会丢失真实 Sky130 purpose 信息。

## 6. 推荐下一步工程路线

1. 先建立 `sky130_layer_map.yaml`，明确每个 MAGICAL layer 对应的 Sky130 layer name、GDS layer、datatype、用途、是否参与 routing、是否参与 device generation。
2. 在 `sky130_layer_map.yaml` 中显式选择 routing stack 方案。建议优先评估：
   - `M1 -> li1`
   - `VIA1 -> mcon`
   - `M2 -> met1`
   - `VIA2 -> via`
   - `M3 -> met2`
   - `VIA3 -> via2`
   - `M4 -> met3`
   - `VIA4 -> via3`
   - `M5 -> met4`
   - `VIA5 -> via4`
   - `M6 -> met5`
3. 再写生成脚本，从 `sky130_layer_map.yaml` 生成：
   - `examples/sky130PDK/sky130.techfile`
   - `examples/sky130PDK/sky130.techfile.simple`
   - `examples/sky130PDK/sky130.lef`
4. 生成 `sky130.lef` 时，不要从 mock LEF 只替换名字；应以 Sky130 tech LEF 的 `li1/mcon/met1/via/.../met5` width、spacing、pitch、area、via rule 为基础，再裁剪成 MAGICAL anaroute 能解析的最小 LEF。
5. 用 `examples/inverter_sky130_try` 做 smoke regression：
   - 转换 xschem netlist。
   - 跑 MAGICAL placement/routing。
   - 检查输出 GDS 是否落在预期 Sky130 layer/datatype。
6. 最后接 Magic/KLayout DRC：
   - 先检查 layer/datatype 是否被工具正确识别。
   - 再看基础 DRC 错误。
   - 根据错误逐步修正 device generator 和 router LEF/rule，而不是一次性宣称 DRC clean。

## 7. internal layer id 与 Sky130 GDS mapping 分离

`generated/sky130PDK_trial` 的第一次回归暴露了一个关键限制：不能直接用 Sky130 真实 GDS layer number 替换 MAGICAL `techfile` / `techfile.simple` 中的 layer id。

原因是 MAGICAL 的 `TechDB::addNewLayer` 要求 layer id 按递增顺序加入。mockPDK 的 internal layer id 是按 MAGICAL 当前数据库顺序组织的，例如 `M1=31`、`M2=32`、`VIA1=51`。如果直接替换成 Sky130 GDS layer，例如 `M1=67`、`M2=68`、`VIA1=67`，同一个文件中的 layer id 顺序会倒退或重复，触发 `TechDB::addNewLayer: the order of adding layers is wrong`。

当前采用的策略是分离两类编号：

- MAGICAL internal layer id：继续保留 mockPDK 原始数值和原始顺序，用于 `sky130.techfile`、`sky130.techfile.simple` 和 LEF 解析，保证当前 MAGICAL flow 能跑通。
- Sky130 GDS export mapping：单独记录到 `generated/sky130PDK_trial/sky130_gds_export_map.yaml`，包含 MAGICAL layer、internal number、Sky130 layer name、GDS layer、datatype、status 和 risk。

这个策略意味着 trial PDK 的第一目标是保持 MAGICAL 内部流程兼容。要让最终 GDS 真正落到 Sky130 layer/datatype，还需要后续实现 GDS export remap 或独立后处理脚本。

## 本次查看的文件

MAGICAL 当前接口文件：

- `examples/sky130PDK/sky130.techfile`
- `examples/sky130PDK/sky130.techfile.simple`
- `examples/sky130PDK/sky130.lef`

MAGICAL 源码/生成器相关文件：

- `device_generation/device_generation/glovar.py`
- `device_generation/device_generation/Mosfet.py`
- `device_generation/device_generation/Resistor.py`
- `anaroute/src/parser/parGds.cpp`
- `flow/python/Params.py`

真实 Sky130 PDK 文件：

- `/home/to/.ciel/sky130A/libs.tech/klayout/tech/sky130A.map`
- `/home/to/.ciel/sky130A/libs.tech/klayout/tech/sky130A.lyp`
- `/home/to/.ciel/sky130A/libs.tech/magic/sky130A-GDS.tech`
- `/home/to/.ciel/sky130A/libs.tech/magic/sky130A.tech`
- `/home/to/.ciel/sky130A/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef`
