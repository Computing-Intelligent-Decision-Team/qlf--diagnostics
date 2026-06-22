# Tech3/Tech4 Showcase Asset Index

This index maps presentation visuals to locally auditable layout artifacts. It is
for external-facing demonstration material, not for claiming new closure results.

## Core Technology 3: Constraint-Driven Layout Generation

Recommended story:

```text
Circuit netlist -> floorplan -> placement -> routing -> Sky130 remap -> pin-ready GDS
```

Use Fan_SMC as the main visual sequence because it has clear intermediate GDS
stages in the AnalogHarness workspace.

| Slide role | Screenshot | Source GDS | Suggested caption |
| --- | --- | --- | --- |
| Layout planning | `docs/assets/tech3_tech4/fan_smc/01_floorplan.png` | `generated/diagnostics/fan_smc_c0_proxy_94x10/case/fan_smc_pin_3.floorplan.gds` | Automatically generated floorplan frame |
| Device placement | `docs/assets/tech3_tech4/fan_smc/02_place.png` | `generated/diagnostics/fan_smc_c0_proxy_94x10/case/fan_smc_pin_3.place.gds` | Devices placed under structural constraints |
| Routing | `docs/assets/tech3_tech4/fan_smc/03_route.png` | `generated/diagnostics/fan_smc_c0_proxy_94x10/case/fan_smc_pin_3.route.gds` | Key nets routed into an initial layout |
| Sky130 mapping | `docs/assets/tech3_tech4/fan_smc/04_sky130.png` | `generated/diagnostics/fan_smc_c0_proxy_94x10/fan_smc_pin_3.sky130.gds` | MAGICAL layers remapped to Sky130 layers |
| Verification-ready pins | `docs/assets/tech3_tech4/fan_smc/05_pinned_shapes.png` | `generated/diagnostics/fan_smc_c0_proxy_94x10/fan_smc_pin_3.pinned_shapes.gds` | Pin labels and pin shapes added for downstream checks |

Suggested slide wording:

```text
从电路网表自动解析器件与约束，完成版图规划、器件布局、关键网络布线和
Sky130 工艺层映射，生成可进入物理验证流程的初始版图。
```

Internal caveat:

```text
Fan_SMC is a layout-generation and diagnostic case, not a final positive closure
sample. Do not claim LVS/post-layout/PVT success for Fan_SMC.
```

## Core Technology 4: Verification Feedback And Iterative Repair

Recommended story:

```text
Generated layout -> physical verification -> diagnosis -> feedback repair ->
trust decision -> successful baseline comparison
```

Use Fan_SMC for the diagnostic/repair attempt and SMCNR for the successful
closed-loop positive baseline.

| Slide role | Screenshot | Source artifact | Suggested caption |
| --- | --- | --- | --- |
| Initial generated layout | `docs/assets/tech3_tech4/fan_smc/05_pinned_shapes.png` | `generated/diagnostics/fan_smc_c0_proxy_94x10/fan_smc_pin_3.pinned_shapes.gds` | Initial generated layout enters verification |
| Diagnostic repair attempt | `docs/assets/tech3_tech4/fan_smc/06_psub_tap_diagnostic.png` | `generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/fan_smc_pin_3.psub_tap.gds` | Feedback-driven substrate tap diagnostic |
| Trust gate evidence | `generated/diagnostics/fan_smc_c0_proxy_94x10_psub_tap/trust_decision.json` | AH-SMC-009 trust decision | Unsafe sample blocked from training and reward |
| Positive baseline layout | `docs/assets/tech3_tech4/smcnr/01_pinned_shapes.png` | `reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/gds/SMCNR_SE_2st_AMP.sky130.pinned_shapes.gds` | Reviewed positive baseline layout |
| Local-power derivative | `docs/assets/tech3_tech4/smcnr/02_local_power.png` | `reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/gds/SMCNR_SE_2st_AMP.sky130.pinned_shapes.local_power.gds` | Power-aware derived layout |
| Native-passive derivative | `docs/assets/tech3_tech4/smcnr/03_native_cap_replaced.png` | `reproducibility/smcnr_se_2st_amp/best_candidate/cand_0031/gds/native_cap_replaced.gds` | Native passive replacement for stronger evidence |

Suggested slide wording:

```text
系统对生成版图进行物理验证、寄生提取和失效诊断，将问题反馈到版图修正
流程；对不可信样本自动拦截，避免错误后仿或训练反馈进入优化闭环。
```

Do not say:

```text
Fan_SMC has been fully closed.
```

Safe wording:

```text
Fan_SMC demonstrates verification-driven diagnosis and repair attempts; SMCNR
serves as the reviewed positive closed-loop baseline.
```

## Asset Checklist

| Asset group | Status |
| --- | --- |
| Fan_SMC stage screenshots | ready |
| SMCNR final/derived screenshots | ready |
| AH-SMC-009 diagnostic result | reviewed as failure-case evidence |
| DFCFC2 visuals | optional backup only |

