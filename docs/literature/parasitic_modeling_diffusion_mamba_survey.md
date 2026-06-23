# Parasitic Modeling Literature Survey: GNN, Diffusion, and Mamba

Last updated: 2026-06-22

## Current Judgment

ML-based parasitic prediction is not a blank area. There are established GNN,
MLP, DNN, and extraction-acceleration baselines. The more defensible gap is:

> Trust-aware analog extracted-PEX capacitance graph datasets and direct
> diffusion or Mamba/SSM modeling of parasitic capacitance networks remain
> underexplored compared with GNN/ML surrogate prediction.

## Evidence Basis

### GNN and ML parasitic prediction

- ParaGraph, DAC 2020, predicts net parasitics and device parameters by
  converting schematics into graphs and using GNN techniques. Sources:
  IEEE `https://ieeexplore.ieee.org/document/9218515/`, NVIDIA PDF
  `https://research.nvidia.com/sites/default/files/pubs/2020-07_ParaGraph%3A-Layout-Parasitics/057_4_Paragraph.pdf`.
- Parasitic-aware analog circuit sizing with GNN and Bayesian optimization,
  DATE 2021, uses ParaGraph-style parasitic prediction in analog sizing
  context. Source:
  `https://past.date-conference.com/proceedings-archive/2021/pdf/1142.pdf`.
- Deep-learning-based pre-layout parasitic capacitance prediction on SRAM
  designs uses a GNN classifier and MLP regressors for net parasitics. Sources:
  `https://arxiv.org/abs/2507.06549`,
  `https://www.cse.cuhk.edu.hk/~byu/papers/C210-GLSVLSI2024-CapPred.pdf`.
- MLParest, DAC 2020, is a machine-learning parasitic estimation direction for
  custom circuit design. It is cited by the DATE 2021 paper above.

### Capacitance extraction and ML acceleration

- ASP-DAC 2025 invited survey "Deep Learning Inspired Capacitance Extraction
  Techniques" explicitly surveys deep-learning usage in IC capacitance
  extraction. Sources:
  `https://dl.acm.org/doi/10.1145/3658617.3703148`,
  `https://numbda.cs.tsinghua.edu.cn/papers/aspdac253.pdf`.
- Work such as DNN-based capacitance matrix prediction and ML-assisted
  interconnect capacitance extraction shows that capacitance extraction itself
  is an active ML target. Example source:
  `https://www.mdpi.com/2079-9292/12/6/1440`.

### Mamba/SSM in analog EDA

- M3, "Mamba-assisted Multi-Circuit Optimization via MBRL with Effective
  Scheduling", applies Mamba to analog multi-circuit optimization. It is
  relevant as a Mamba-in-analog-EDA anchor, but it is not direct extracted PEX
  graph modeling. Sources:
  `https://arxiv.org/abs/2411.16019`,
  `https://ieeexplore.ieee.org/document/11240790/`.

### Diffusion in EDA

Diffusion models appear in EDA and layout-generation adjacent work, but current
survey evidence does not yet establish a direct baseline for analog extracted
PEX capacitance graph generation. This should be treated as a search target,
not a proven novelty claim.

## Research Positioning

### What is not novel enough

- "Use ML to predict parasitic capacitance."
- "Use a GNN for parasitic prediction."
- "Use pre-layout graphs to estimate layout parasitics."

These have clear prior art.

### What may be novel

- A trust-aware dataset that stores extracted PEX capacitance networks together
  with DRC/LVS/post-sim/PVT evidence flags.
- Modeling extracted parasitic edge distributions rather than only regressing
  net-level lumped capacitance.
- Using diffusion to generate or denoise candidate parasitic edge sets under
  circuit/topology constraints.
- Using Mamba/SSM over canonicalized PEX edge streams for long-range
  capacitance-network modeling.
- Explicitly separating positive supervised data from failure-case-only PEX
  graphs.

## Proposed Model Ladder

1. Non-neural statistics: total cap, per-node cap, largest edge, output-node
   cap, power-rail coupling.
2. GNN baseline: graph-level and node-level cap prediction over schematic and
   extracted net nodes.
3. Diffusion candidate: conditional edge-set distribution over parasitic caps.
4. Mamba/SSM candidate: canonical PEX edge stream modeling and reduction.

## Claude Next Task

Do not train a model yet. Build dataset v0 and expose enough graph fields that
all four model ladders can be evaluated later.

## Acceptance Criteria

- Dataset report cites this survey's conservative novelty boundary.
- Dataset records preserve both graph edges and trust flags.
- Any future model experiment includes at least one non-neural or GNN baseline
  before claiming diffusion/Mamba value.

## Forbidden Claims

- Do not say "no one has done parasitic ML."
- Do not say "Mamba is novel for all analog EDA."
- Do not say "diffusion/Mamba will outperform GNN" before experiments.
- Do not cite failure-case-only PEX as clean supervised labels.
