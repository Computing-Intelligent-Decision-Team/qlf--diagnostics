# Vendored AnalogGym GRPO

This directory contains the local AnalogGym GRPO source needed by
`tools/analog_harness`.

Included:

- GRPO source: `grpo.py`
- AMP training entrypoint: `main_AMP_grpo.py`
- AnalogGym AMP environment and helper modules
- `circuit_configs/*.yaml`
- lightweight `simulation_files/<amp>` templates
- small baseline `model/` files

Not included:

- Sky130 PDK copies
- `training_saves/`
- `wandb/`
- `simulation_output/`
- Python caches and editor history

The harness config points to this vendored directory by default:

```yaml
paths:
  analog_gym_root: third_party/analoggym_grpo
```

Sky130 PDK remains an external dependency. Set `SKY130A` before running
simulation/layout flows:

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
