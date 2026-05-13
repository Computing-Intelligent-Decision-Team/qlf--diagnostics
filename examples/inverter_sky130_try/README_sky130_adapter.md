# sky130 Adapter Inverter Smoke Test

This directory contains a minimal smoke test for the early sky130 adapter work.
The test checks that an xschem/ngspice-style sky130 inverter netlist can be
converted into MAGICAL's current netlist format, and then passed through
placement and routing.

## Test Steps

From `examples/inverter_sky130_try/`:

```bash
python3 convert_sky130_netlist.py
cat inverter_sky130_name_test.sp
```

Then run MAGICAL in Docker from the MAGICAL repository root. Replace the image
name if your local MAGICAL image uses a different tag:

```bash
docker run --rm -it \
  -v "$PWD":/MAGICAL \
  -w /MAGICAL/examples/inverter_sky130_try \
  magical-eda/magical:latest \
  bash -lc './run.sh 2>&1 | tee run_sky130_name_test.log'
```

Inspect the end of the run log:

```bash
tail -n 100 run_sky130_name_test.log
```

## Success Criteria

The converted netlist should contain both sky130 1.8 V MOS device names:

```bash
grep -E 'sky130_fd_pr__(nfet|pfet)_01v8' inverter_sky130_name_test.sp
```

The MAGICAL log should show placement and routing completion, including:

```text
placement finished
routing finished
```

The run should produce these output files:

```bash
test -f inverter_core.route.gds
test -f inverter_core.ioPin
```

## Current Limitations

- `examples/sky130PDK` is still a renamed copy of `examples/mockPDK`.
- The generated result is not a real sky130 DRC-clean layout.
- This stage only verifies sky130 device-name recognition and netlist-format
  conversion for the MAGICAL flow.
