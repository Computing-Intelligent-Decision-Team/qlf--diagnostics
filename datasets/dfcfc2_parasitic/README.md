# DFCFC2 Parasitic Datasets

| Link | Use |
|---|---|
| `current` | Use this by default. It points to the 95-sample trusted DFCFC2 parasitic corpus v3. |
| `step300_64` | Step300-only subset with 64 trusted samples. Use when comparing only the latest GRPO checkpoint batch. |

The current trust contract is:

- sizing lineage must be present;
- DRC must pass;
- connectivity LVS must pass;
- raw PEX must exist and be parseable;
- PM, reward, pre-layout simulation, PVT, and post-layout performance are observation-only.

Scope: `mos_only_projection`. The current labels support capacitance summary
and capacitor-graph modeling, not RC joint modeling.
