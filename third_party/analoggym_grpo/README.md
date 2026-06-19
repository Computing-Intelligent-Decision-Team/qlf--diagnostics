# Vendored AnalogGym GRPO

This directory contains the local AnalogGym GRPO source needed by
`tools/analog_harness`.

Included:

- GRPO source: `grpo.py`
- AMP training entrypoint: `main_AMP_grpo.py`
- AnalogGym AMP environment and helper modules
- `circuit_configs/*.yaml`
- lightweight `simulation_files/<amp>` templates
- bundled Sky130 PDK convenience copy at `simulation_files/sky130_pdk`
- small baseline `model/` files

Not included:

- duplicate `mosfet_model/sky130_pdk` copy
- `training_saves/`
- `wandb/`
- `simulation_output/`
- Python caches and editor history

The harness config points to this vendored directory by default:

```yaml
paths:
  analog_gym_root: third_party/analoggym_grpo
```

The repository includes a Sky130 PDK convenience copy for reproducible local
development:

```text
third_party/analoggym_grpo/simulation_files/sky130_pdk
```

You can still override it with an external PDK by setting `SKY130A` and editing
the harness config:

```bash
export SKY130A=/path/to/sky130A
```

Install optional GRPO dependencies with:

```bash
python3 -m pip install -r requirements-grpo.txt
```

The quick harness smoke test does not require a long GRPO training run:

```bash
python -m tools.analog_harness.cli run \
  --config tools/analog_harness/configs/smcnr_se_2st_amp.yaml \
  --max-candidates 1 \
  --layout-budget 0 \
  --skip-layout \
  --skip-sim
```
