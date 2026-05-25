# LVS / PEX 说明

当前 Sky130 adapter 默认执行的是 connectivity LVS 加 PEX summary，而不是 parasitic-aware LVS。

## Raw Extraction

Magic extraction 从最终 pinned-shapes GDS 生成 raw extracted netlist。该 raw netlist 会保留 Magic 识别到的寄生电容，并作为 PEX summary 的输入保存下来：

```text
generated/sky130_cases/<case>/<top_cell>_extracted.raw.spice
```

## Connectivity LVS

为了验证版图连通性，pipeline 会生成两份比较用 netlist：

- `<top_cell>_source.connectivity.spice`
- `<top_cell>_extracted.connectivity.spice`

connectivity extracted netlist 会删除寄生电容行，并移除 `ad/as/pd/ps` 等 property-only 差异。这样 Netgen 比较的重点是器件连接、端口和网络拓扑。

当前结果摘要在：

```text
generated/sky130_cases/<case>/lvs_result_summary.md
```

`CONNECTIVITY_LVS_MATCH=yes` 表示当前连通性比较通过。

## PEX Summary

PEX summary 不参与当前 LVS 比较。它只读取 raw extracted netlist，统计寄生电容数量和总电容，输出：

```text
generated/sky130_cases/<case>/pex_summary.md
```

因此：

- connectivity LVS 用于回答“源网表和版图连通性是否一致”。
- PEX summary 用于回答“Magic raw extraction 中列出了多少寄生电容、总量大约是多少”。
- 完整 parasitic-aware 后仿需要额外流程，不是当前默认 pipeline 的输出。
