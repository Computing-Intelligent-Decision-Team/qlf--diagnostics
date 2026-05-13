# MAGICAL mockPDK 接口分析

本文只分析 `examples/mockPDK/mock.lef`、`mock.techfile`、`techfile.simple` 在当前 MAGICAL flow 中的读取和字段消费方式，用于归纳 sky130 adapter 需要提供的最小 PDK 接口。

## 总体入口

示例 JSON 通过 `Params.fromJson()` 读入三类 PDK 路径：

- `simple_tech_file` -> `examples/mockPDK/techfile.simple`
- `techfile` -> `examples/mockPDK/mock.techfile`
- `lef` -> `examples/mockPDK/mock.lef`

Python 入口和 C++ 解析器关系如下：

| PDK 文件 | Python 入口 | C++/pybind 入口 | 实际解析器 |
| --- | --- | --- | --- |
| `techfile.simple` | `flow/python/MagicalDB.py:20,30-31` | `magicalFlow.parseSimpleTechFile()` | `flow/cpp/magical_flow/src/parser/ParseSimpleTech.cpp:5-29` |
| `techfile.simple` | `flow/python/Placer.py:49-50` | `IdeaPlaceExPy.IdeaPlaceEx.readTechSimpleFile()` | `IdeaPlaceEx/src/parser/ParserTechSimple.h:31-56` |
| `mock.lef` | `flow/python/PnR.py:103` | `anaroutePy.AnaroutePy.parseLef()` | `anaroute/src/parser/parLef.cpp` |
| `mock.techfile` | `flow/python/PnR.py:104` | `anaroutePy.AnaroutePy.parseTechfile()` | `anaroute/src/parser/parTech.cpp` |

`Params.py` 只保存路径字段，不解析文件内容；`lef` 和 `techfile` 只在 routing 阶段进入 `anaroute`。

## `techfile.simple`

### 被哪些文件读取

1. `flow/python/MagicalDB.py`
   - `MagicalDB.parse()` 调用 `parse_simple_techfile(self.params.simple_tech_file)`。
   - `parse_simple_techfile()` 调用 `magicalFlow.parseSimpleTechFile(params, self.techDB)`。

2. `flow/cpp/magical_flow/src/db/TechDB.cpp`
   - `PARSE::parseSimpleTechFile()` 调用 `ParseSimpleTech(techDB).read(file)`。

3. `flow/cpp/magical_flow/src/parser/ParseSimpleTech.cpp`
   - 当前 Python flow 使用的是 `read()`，不是同文件里的 `parse()`。
   - `read()` 对每一行只读取前两个 token：`layerName` 和 `gdsLayer`，然后调用 `_techDB.addNewLayer(gdsLayer, layerName)`。

4. `flow/python/Placer.py`
   - `Placer.dumpInput()` 调用 `self.placer.readTechSimpleFile(self.params.simple_tech_file)`。

5. `IdeaPlaceEx/src/main/IdeaPlaceEx.cpp` 和 `IdeaPlaceEx/src/parser/ParserTechSimple.h`
   - `IdeaPlaceEx::readTechSimpleFile()` 调用 `ParserTechSimple(_db).read(techsimple)`。
   - `ParserTechSimple::read()` 同样逐行读取 `layerName` 和 `gdsLayer`，但只把 `gdsLayer` 加到 placer tech DB：`_db.tech().addGdsLayer(gdsLayer)`；`layerName` 被读出但不使用。

### 实际使用的字段

当前 `techfile.simple` 是两列表：

```text
<layerName> <gdsLayerNumber>
```

实际消费字段：

- `layerName`
  - 在 `magical_flow::TechDB` 中用于 `_layerNameToDbLayer` 映射。
  - 对 placer (`IdeaPlaceEx`) 来说被读出但不进入数据库。

- `gdsLayerNumber`
  - 在 `magical_flow::TechDB` 中用于 DB layer <-> PDK/GDS layer 的双向映射。
  - 在 `IdeaPlaceEx` 中用于初始化 placement 侧 tech rule 数据结构。

当前 flow 没有从 `techfile.simple` 消费 width、spacing、pitch、via 或方向。`ParseSimpleTech.cpp` 里确实还有一个更复杂的 `parse()`，支持 `DBU`、`MANUFACTURINGGRID`、`LAYER ROUTING/CUT/MASTERSLICE`、`WIDTH`、`SPACING`、`DIRECTION`、`TECHLAYER` 和 `VIA` 语法，但 Python 入口调用的是 `read()`，所以 mock 的 `techfile.simple` 最小接口就是“每行 layer name + GDS layer number”。

### mock 中出现的 layer/GDS number

`techfile.simple` 包含比 routing 更多的层。对 MAGICAL 现有 flow 来说，关键是至少覆盖后续 GDS/PDK 层映射会遇到的层名与编号，例如：

- routing/cut 相关：`PO=17`、`CO=30`、`M1=31` ... `M7=37`、`VIA1=51` ... `VIA6=56`
- 器件/版图相关层：`NW=3`、`OD=6`、`PP=25`、`NP=26`、`RPO=29` 等

## `mock.techfile`

### 被哪些文件读取

1. `flow/python/PnR.py`
   - routing 前调用 `router.parseTechfile(self.params.techfile)`。

2. `anaroute/src/api/apiPy.cpp`
   - 暴露 `AnaroutePy::parseTechfile()` 到 Python。

3. `anaroute/src/parser/parser.cpp`
   - `Parser::parseTechfile()` 创建 `TechfileReader` 并调用 `parse()`。

4. `anaroute/src/parser/parTech.cpp`
   - 只查找完全匹配的 `techLayers(\n` 块。
   - 在块内跳过空行和 `;` 注释行。
   - 用 `sscanf(buf, " ( %s %u %*s )\n", layerName, &layerIdx)` 读取 layer name 和 layer number，第三列 abbreviation 被忽略。
   - 调用 `_cir.tech().addStr2LayerMaxIdx(layerName, layerIdx)`。

### 实际使用的字段

`mock.techfile` 的实际接口是：

```text
techLayers(
  ( <layerName> <gdsLayerNumber> <ignoredAbbreviation> )
)
```

实际消费字段：

- `layerName`
  - 必须和 `mock.lef` 中的 LEF layer name 一致。
  - 后续 `CirDB::layerIdx2MaskIdx()` 会通过 LEF layer name 查 `TechfileDB::_mStr2LayerMaskIdx`。

- `gdsLayerNumber`
  - 用于输入 placement GDS 的 layer number 到 router layer index 的映射。
  - 用于 routing 结果写回 GDS 时选择输出 layer number。

- `abbreviation`
  - 当前 parser 使用 `%*s` 丢弃，不消费。

`mock.techfile` 不提供也不消费 width、spacing、pitch、via 几何或 routing rule。它只服务于 `anaroute` 的 LEF layer name -> GDS layer number 映射。

### mock 中需要覆盖的 layer/GDS number

`mock.techfile` 当前列出：

| layer | GDS layer |
| --- | ---: |
| `OD` | 6 |
| `PO` | 17 |
| `CO` | 30 |
| `M1`..`M7` | 31..37 |
| `VIA1`..`VIA6` | 51..56 |

对 `anaroute` 最小需求来说，`mock.techfile` 至少要覆盖 `mock.lef` 中会被加入 LEF DB 的所有 routing、cut、masterslice layer name。否则 `layerIdx2MaskIdx()` 在读/写 GDS 时会查不到 layer name。

## `mock.lef`

### 被哪些文件读取

1. `flow/python/PnR.py`
   - routing 前调用 `router.parseLef(self.params.lef)`。

2. `anaroute/src/api/apiPy.cpp`
   - 暴露 `AnaroutePy::parseLef()` 到 Python。

3. `anaroute/src/parser/parser.cpp`
   - `Parser::parseLef()` 创建 `LefReader` 并调用 `parse()`，随后调用 `_cir.lef().constructViaTableFromViaRule()`。

4. `anaroute/src/parser/parLef.cpp`
   - 通过 Limbo LEF parser 回调读取 `VERSION`、`BUSBITCHARS`、`DIVIDERCHAR`、`UNITS`、`MANUFACTURINGGRID`、`LAYER`、`VIA`、`VIARULE` 等。

### 实际解析字段

#### 全局字段

- `VERSION`
  - 记录版本字符串和 double 值。

- `BUSBITCHARS`、`DIVIDERCHAR`
  - 记录到 LEF DB。

- `UNITS DATABASE MICRONS <N>`
  - 非常关键。`parLef.cpp` 用它把 LEF micron 单位转换成整数 DBU。
  - `mock.lef` 为 `DATABASE MICRONS 2000`，所以 `0.07um -> 140` DBU、`0.13um -> 260` DBU。

- `MANUFACTURINGGRID`
  - 被记录，但 routing 主逻辑中未见强消费。

#### Layer 字段

`LAYER <name>` 的 `TYPE` 决定进入哪类 DB：

- `TYPE MASTERSLICE`
  - 只消费 layer name。
  - mock 中是 `PO`。

- `TYPE CUT`
  - 消费 layer name。
  - 消费 `SPACING`，转换到 DBU，用于 cut/via spacing DRC。
  - 解析 `WIDTH`，但当前代码先转换为 DBU 后又执行 `layer.setMinWidth(v.width())` 覆盖为未缩放值；routing DRC 主要使用 cut spacing 和 via rectangles，未见 cut min width 的关键使用。
  - mock 中是 `CO`、`VIA1`..`VIA6`；其中 `VIA1`..`VIA6` 有 `SPACING 0.07` 和 `WIDTH 0.07`，`CO` 只有 type。

- `TYPE ROUTING`
  - 消费 layer name。
  - 消费 `DIRECTION`，存入 route direction；当前 grid router 里有相关逻辑被注释，主要不是硬约束来源。
  - 消费 `WIDTH`，设置 default/min width。
  - 消费 `AREA`，设置 min area，用于 `DrcMgr::checkWireMinArea()`。
  - 消费 `SPACINGTABLE PARALLELRUNLENGTH ... WIDTH ...`，用于 `LefDB::prlSpacing()`，进而用于 routing layer spacing DRC。
  - 消费普通 `SPACING` 和 `END OF LINE` 三元组，保存 EOL spacing；routing DRC 会调用 EOL spacing 检查。
  - 消费 `PITCH` / `PITCH x y`，保存 pitch/pitchX/pitchY；当前 routing 使用更多来自 flow 的 `gridStep`，pitch 不是主驱动字段，但 adapter 仍应提供以满足 LEF DB 完整性。
  - 消费 `MINSTEP ... MAXEDGES`，用于 DRC 和 post-processing 的 jog/patch 处理。

#### Via 字段

`VIA <name> DEFAULT`：

- 消费 via name。
- 要求 exactly 3 个 `LAYER` section：bottom routing/masterslice、cut、top routing。
- 消费每个 section 的 layer name，并映射到 LEF layer index。
- 消费每个 `RECT xl yl xh yh`，转换为 DBU box。
- 后续 detailed router 通过 via 的 cut layer name 选择候选 via，并把 bottom/cut/top rectangles 加入 routed wire shapes 和 DRC 查询。

`VIARULE <name> GENERATE`：

- `parLef.cpp` 会读取并构造 via rule template。
- `Parser::parseLef()` 后调用 `constructViaTableFromViaRule()`，用于按 row/column 生成 via。
- mock 中存在 `VIAG12`、`VIAG23`、`VIAG34`、`VIAG45`、`VIAG56`、`VIAG67`。注意 `VIAG34` 当前写的是 `LAYER VIA2`，与 M3-M4 的 cut layer 直觉上应为 `VIA3` 不一致；这是 mock 文件现状，adapter 不应照抄这个错误，应该保证 lower/top metal 与 cut layer 对应。

### mock 中的 routing/cut/via 内容

Routing layers：

| LEF layer | Direction | Pitch | Width | Area | Spacing table | EOL spacing | Minstep |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| `M1` | HORIZONTAL | `0.13 0.13` | `0.07` | `0.02` | PRL `0`; width `0/0.1 -> 0.07` | `0.07 WITHIN 0.025` | `0.06 MAXEDGES 1` |
| `M2` | VERTICAL | `0.13 0.13` | `0.07` | `0.02` | same | `0.07 WITHIN 0.025` | same |
| `M3` | HORIZONTAL | `0.13 0.13` | `0.07` | `0.02` | same | `0.07 WITHIN 0.035` | same |
| `M4` | VERTICAL | `0.13` | `0.07` | `0.02` | same | `0.07 WITHIN 0.035` | same |
| `M5` | HORIZONTAL | `0.13` | `0.07` | `0.02` | same | `0.07 WITHIN 0.035` | same |
| `M6` | VERTICAL | `0.13` | `0.07` | `0.02` | same | `0.07 WITHIN 0.035` | same |
| `M7` | HORIZONTAL | `0.13` | `0.07` | `0.02` | same | `0.07 WITHIN 0.035` | same |

Cut layers：

| LEF layer | Spacing | Width |
| --- | ---: | ---: |
| `CO` | absent | absent |
| `VIA1`..`VIA6` | `0.07` | `0.07` |

Default vias in mock：

- M1/VIA1/M2: `VIA12_1C`, `VIA12_1C_H`, `VIA12_1C_V`
- M2/VIA2/M3: `VIA23_1C`, `VIA23_1C_H`, `VIA23_1C_V`, `VIA23_1ST_N`, `VIA23_1ST_S`
- M3/VIA3/M4: `VIA34_1C`, `VIA34_1C_H`, `VIA34_1C_V`, `VIA34_1ST_E`, `VIA34_1ST_W`
- M4/VIA4/M5: `VIA45_1C`, `VIA45_1C_H`, `VIA45_1C_V`, `VIA45_1ST_N`, `VIA45_1ST_S`
- M5/VIA5/M6-like names: `VIA5_0_VH`
- M6/VIA6/M7-like names: `VIA6_0_HV`

每个 default via 的核心接口是三层 layer name 加若干 `RECT`。rect size/extension 会直接成为 routed GDS 几何和 DRC 对象。

## 字段消费关系汇总

| 字段 | 来源文件 | 读取位置 | 后续用途 |
| --- | --- | --- | --- |
| layer name | `techfile.simple` | `ParseSimpleTech::read()` | `TechDB` layer name -> DB layer index |
| GDS layer number | `techfile.simple` | `ParseSimpleTech::read()` / `ParserTechSimple::read()` | flow DB 和 placer tech DB 的 PDK layer 编号 |
| layer name | `mock.techfile` | `TechfileReader::readTechLayers()` | `anaroute` LEF layer name -> GDS layer number |
| GDS layer number | `mock.techfile` | `TechfileReader::readTechLayers()` | placement GDS 读入映射、routing GDS 写出映射 |
| LEF DBU | `mock.lef` | `lef_units_cbk()` | LEF geometry 转整数 DBU、GDS scale |
| routing layer name/type | `mock.lef` | `lef_layer_cbk()` / `parseRoutingLayer()` | layer ordering、routing layer index、GDS 映射 key |
| routing direction | `mock.lef` | `parseRoutingLayer()` | 存入 DB；当前主 router 未强依赖 |
| routing width | `mock.lef` | `parseRoutingLayer()` | layer min/default width；部分 spatial wire/via helper 使用，net routing width 多来自 Python params/net spec |
| routing spacing table | `mock.lef` | `parseRoutingLayer()` | `LefDB::prlSpacing()`，routing spacing DRC |
| routing EOL spacing | `mock.lef` | `parseRoutingLayer()` | EOL spacing DRC |
| routing area | `mock.lef` | `parseRoutingLayer()` | min area DRC |
| routing minstep/maxedges | `mock.lef` | `parseRoutingLayer()` | jog/patch DRC/post-processing |
| routing pitch | `mock.lef` | `parseRoutingLayer()` | 存入 DB；当前不是主要 routing grid 来源 |
| cut layer spacing | `mock.lef` | `parseCutLayer()` | cut/via spacing DRC |
| via layer names | `mock.lef` | `parseDefaultVia()` / viarule parser | via selection、layer index mapping |
| via rects | `mock.lef` | `parseDefaultVia()` / viarule parser | routed geometry、spacing DRC、GDS output |

## sky130 adapter 的最小接口需求

### 1. `techfile.simple`

提供一份两列 layer map：

```text
<MAGICAL_layer_name> <sky130_gds_layer_number>
```

要求：

- 每行至少两个 token。
- GDS layer number 应单调递增，因为 `TechDB::addNewLayer()` 断言新加入的 tech ID 大于上一个。
- 至少覆盖 MAGICAL flow、placer 和 device/layout parser 会看到的层。
- 对当前 flow，不需要在这个文件提供 width、spacing、pitch、via。

### 2. `mock.techfile` 对应的 anaroute techfile

提供 `techLayers(` block：

```text
techLayers(
  ( M1 68 M1 )
  ...
)
```

要求：

- 第一列 layer name 必须匹配 LEF 中的 layer name。
- 第二列是 GDS layer number。
- 第三列可以填同名 abbreviation，但当前会被忽略。
- 至少覆盖 LEF 中所有 routing/cut/masterslice 层，特别是 `PO/CO/M1..Mn/VIA1..VIA(n-1)` 或 adapter 选定的等价命名。

### 3. `mock.lef` 对应的 routing LEF

最小可工作内容：

- `VERSION`、`BUSBITCHARS`、`DIVIDERCHAR`
- `UNITS DATABASE MICRONS <dbu>`，建议与写 GDS/读 GDS scale 一致
- `MANUFACTURINGGRID`
- 一个 masterslice/poly 类层，例如 `PO`
- cut/contact/via 层，例如 `CO`、`VIA1`..`VIA(n-1)`
- routing 层，例如 `M1`..`Mn`
  - `TYPE ROUTING`
  - `DIRECTION`
  - `PITCH`
  - `WIDTH`
  - `AREA`
  - `SPACINGTABLE` 或至少普通 `SPACING`
  - `SPACING ... ENDOFLINE ... WITHIN ...`
  - `MINSTEP ... MAXEDGES ...`
- default vias 或 generated viarules
  - bottom/cut/top layer names 必须能在 LEF layer table 中查到
  - via rects 必须是 sky130 合法 enclosure/cut geometry
  - generated viarules 应确保 cut layer 与 metal pair 对应

### 4. 命名一致性是硬要求

三个文件之间的名字必须对齐：

- `mock.lef` 的 `LAYER M1` 必须能在 `mock.techfile` 里找到 `M1 -> GDS number`。
- flow/device 侧用到的 layer names 必须能在 `techfile.simple` 中找到。
- 如果 sky130 原始 LEF/GDS 命名是 `li1/met1/via/li1` 等，adapter 要么统一改 MAGICAL 内部名，要么保证所有文件和生成代码都使用同一套名字。

## 结论

MAGICAL 对 mockPDK 的最小依赖不是完整 foundry PDK，而是三份相互一致的轻量 tech interface：

1. `techfile.simple`：flow/placer 用的 layer name + GDS number 列表。
2. `mock.techfile`：anaroute 用的 LEF layer name + GDS number 映射。
3. `mock.lef`：anaroute 用的 routing/cut/via 几何和基础 DRC rule。

对 sky130 adapter 来说，优先保证 layer 命名、GDS layer number、LEF routing/cut/via 几何三者一致。width/spacing/pitch/minstep/via rect 的真实 sky130 值主要应落在 LEF；`techfile.simple` 和 `mock.techfile` 主要承担 layer map，而不是 rule database。

## 当前 sky130 adapter 进展

当前 sky130 adapter 仍处于接口验证阶段，尚未完成真实 sky130 PDK 适配。

已完成的工作：

- 已建立 `examples/sky130PDK` 目录。
- `examples/sky130PDK` 当前是 `examples/mockPDK` 的副本，仅用于验证 MAGICAL 的 PDK 路径和最小接口。
- `examples/inverter_sky130_try` 已经能通过 `examples/sky130PDK` 路径跑通 MAGICAL flow。
- `flow/python/DesignDB.py` 已支持 `sky130_fd_pr__nfet_01v8` 和 `sky130_fd_pr__pfet_01v8` 的器件名识别。
- `examples/inverter_sky130_try/convert_sky130_netlist.py` 可将 xschem 导出的 `inverter_raw.spice` 转换为 MAGICAL 当前可读的 `inverter_sky130_name_test.sp` 格式。

当前仍未完成的部分：

- 真实 sky130 layer mapping。
- 真实 sky130 techfile mapping。
- 真实 sky130 DRC rule mapping。

下一步计划：

- 分析 sky130A 的 layer 名称和 GDS layer。
- 建立 MAGICAL layer 到 sky130 layer 的映射表。
- 逐步替换 `examples/sky130PDK` 中的 `lef` / `techfile` / `simple techfile` 内容。
