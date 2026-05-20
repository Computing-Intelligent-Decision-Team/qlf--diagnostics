#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

DEFAULT_SKY130A="/home/to/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A"
SKY130A="${SKY130A:-$DEFAULT_SKY130A}"

INPUT_GDS_REL="examples/inverter_sky130_try/inverter_core.sky130.pinned_shapes.gds"
INPUT_GDS="$REPO_ROOT/$INPUT_GDS_REL"
MAGICRC="$SKY130A/libs.tech/magic/sky130A.magicrc"

OUT_DIR="$REPO_ROOT/generated/sky130_lvs_pinned_shapes"
TCL_FILE="$OUT_DIR/magic_nmos_terminal_probe.tcl"
LOG_FILE="$OUT_DIR/magic_nmos_terminal_probe.log"

if ! command -v magic >/dev/null 2>&1; then
    echo "error: magic command not found in PATH" >&2
    exit 1
fi

if [[ ! -f "$INPUT_GDS" ]]; then
    echo "error: input GDS not found: $INPUT_GDS" >&2
    exit 1
fi

if [[ ! -f "$MAGICRC" ]]; then
    echo "error: sky130A.magicrc not found: $MAGICRC" >&2
    echo "hint: set SKY130A to the Sky130A PDK root if the default path is not valid" >&2
    exit 1
fi

mkdir -p "$OUT_DIR"

cat > "$TCL_FILE" <<'EOF'
puts "MAGIC_NMOS_PROBE: reading GDS examples/inverter_sky130_try/inverter_core.sky130.pinned_shapes.gds"
gds read examples/inverter_sky130_try/inverter_core.sky130.pinned_shapes.gds

puts "MAGIC_NMOS_PROBE: loading top cell inverter_core_flat"
if {[catch {load inverter_core_flat} load_error]} {
    puts stderr "ERROR: failed to load inverter_core_flat"
    puts stderr "HINT: check the GDS top-level cell name."
    puts stderr $load_error
    quit -noprompt
}

select top cell

proc probe_area {name xlo ylo xhi yhi} {
    puts "MAGIC_NMOS_PROBE: probing $name box=($xlo,$ylo)-($xhi,$yhi)"
    select clear
    box $xlo $ylo $xhi $yhi
    select area
    if {[catch {what} what_error]} {
        puts stderr "WARNING: what failed for $name"
        puts stderr $what_error
    }
}

probe_area "NMOS_LEFT_TERMINAL_expected_a_n15_90" -75 450 125 1450
probe_area "NMOS_RIGHT_TERMINAL_expected_Y" 275 450 475 1450
probe_area "VGND_PIN_RAIL" -650 -1050 3250 -950
probe_area "Y_PIN" 350 550 2250 650

puts "MAGIC_NMOS_PROBE: running extraction for cross-check"
extract all
quit -noprompt
EOF

cd "$REPO_ROOT"

echo "SKY130A=$SKY130A"
echo "Input GDS: $INPUT_GDS"
echo "Magic rcfile: $MAGICRC"
echo "TCL file: $TCL_FILE"
echo "Probe log: $LOG_FILE"

rm -f "$REPO_ROOT/inverter_core_flat.ext" "$REPO_ROOT/inverter_core_flat.spice"

set +e
magic -dnull -noconsole -rcfile "$MAGICRC" < "$TCL_FILE" > "$LOG_FILE" 2>&1
status=$?
set -e

rm -f "$REPO_ROOT/inverter_core_flat.ext" "$REPO_ROOT/inverter_core_flat.spice"

echo "Magic probe exited with status: $status"
echo "Probe log written to: $LOG_FILE"
exit "$status"
