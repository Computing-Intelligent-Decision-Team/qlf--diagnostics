# Shared Agent Board

> 最后更新：2026-06-19
> 当前 agent：Claude Code (重大发现：Li Jintao AnalogHarness 已集成，正在验证)

## BREAKING: AnalogHarness 已集成（代码在 Windows/GitHub，WSL 仅有报告文档）

- `AnalogHarness.md` ✅ 在 MAGICAL repo 根目录
- `tools/analog_harness/` ❌ 不在 WSL repo 中
- 代码位置：Windows `E:\codex-magical-sky130-harness\` 或 GitHub `Computing-Intelligent-Decision-Team/AnalogHarness`
- **阻塞**：无法在 WSL 运行 harness CLI 命令，需先同步代码

## Active Workstreams

| # | Circuit | DRC | PEX | equiv | LVS | Harness |
|---|---------|-----|-----|-------|-----|---------|
| 1 | DFCFC2 | ✅ 0 | ✅ 176 caps | ✅ 0 | ❌ 26≠30 | reject |
| 2 | SMC (no-C0+B1) | ✅ 0 | ✅ 351 caps | ✅ 0 | ❌ 18≠39 | reject |
| 3 | **AnalogHarness SMCNR_SE_2st_AMP** | ✅ 0 | ✅ | ✅ | ✅ L6 | **accept** 🎉 |

## Next Action

SMC-15 executed: targeted M11 nwell deletion confirms vdda-vout collapse is structural (nwell=essential to device, removing it kills device rather than breaking short). AnalogHarness code still unavailable in WSL. Both circuits at LVS ceiling. Next requires external input.

## SMC Tasks Status

| Task | Title | Status |
|------|-------|--------|
| SMC-01 | MAGICAL config fix + P&R | done |
| SMC-02 | Sky130 remap + extraction | done |
| SMC-03/04/05 | Metal layer deletion A/B | done |
| SMC-06 | Document findings | done |
| SMC-07 | Body/well A/B + placement mapping | done |
| SMC-08 | SMC vs DFCFC2 comparison | done |
| SMC-09 | C0 removal diagnostic | done |
| SMC-10 | no-C0 M5/all-metals A/B | done |
| SMC-11 | B1 containment DRC/PEX/LVS | done |
| SMC-12 | Formal evidence + device mapping + RC2 quantification | done |
| SMC-13 | Targeted M11 nwell/tap+diff deletion | done — collapse systemic, not localized |
| SMC-14 | ext2spice tuning ceiling | done — short=merge=hier+merge, 33 nets irreducible |
| SMC-15 | Targeted M11/M23 nwell deletion | done — M11 nwell critical; 24→23 devs, confirms structural collapse |

## Cross-Circuit RC2 Pattern

| | DFCFC2 | SMC |
|---|--------|-----|
| Terminal mismatches per device | ~3.6 | ~3.7 |
| Extracted/Source net ratio | 1.4x | 2.2x |

Consistent ~3.6-3.7 mismatches/device — RC2 is systemic, not circuit-specific.
SMC-14 confirmed: `ext2spice short` = `merge` = `hier off+merge` — 33 anonymous nets is the irreducible floor under current Magic extraction.

## Next Action

Both circuits at LVS ceiling. RC2 = toolchain floor (ext2spice exhausted). RC1 = MAGICAL architectural. No further Claude Code executable experiments without external direction. Options require:
1. Custom Netgen setup with per-net equivalence rules (needs Codex design input)
2. MAGICAL device_generation/wellgen source modification (needs Docker image rebuild)
3. Accept current state as documented ceiling, move to post-sim on extracted netlist only

## Stop Conditions

- [ ] 所有 equiv 清零且 LVS 通过 → 进入 PEX 后仿
- [x] SMC equiv 清零 (no-C0+B1) ✅
- [x] SMC formal evidence delivered ✅
- [x] DFCFC2 containment done ✅
- [x] RC2 cross-circuit quantified ✅
