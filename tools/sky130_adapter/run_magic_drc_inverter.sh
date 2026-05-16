#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

DEFAULT_SKY130A="/home/to/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A"
SKY130A="${SKY130A:-$DEFAULT_SKY130A}"

INPUT_GDS_REL="examples/inverter_sky130_try/inverter_core.sky130.gds"
INPUT_GDS="$REPO_ROOT/$INPUT_GDS_REL"
MAGICRC="$SKY130A/libs.tech/magic/sky130A.magicrc"
OUT_DIR="$REPO_ROOT/generated/sky130_drc"
TCL_FILE="$OUT_DIR/inverter_magic_drc.tcl"
LOG_FILE="$OUT_DIR/inverter_magic_drc.log"

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
puts "MAGIC_DRC: reading GDS examples/inverter_sky130_try/inverter_core.sky130.gds"
gds read examples/inverter_sky130_try/inverter_core.sky130.gds

puts "MAGIC_DRC: loading top cell inverter_core_flat"
if {[catch {load inverter_core_flat} load_error]} {
    puts stderr "ERROR: failed to load inverter_core_flat"
    puts stderr "HINT: check the GDS top-level cell name, then update generated/sky130_drc/inverter_magic_drc.tcl or this wrapper script."
    puts stderr $load_error
    quit -noprompt
}

puts "MAGIC_DRC: running drc check"
drc check
puts "MAGIC_DRC: running drc count"
drc count
quit -noprompt
EOF

cd "$REPO_ROOT"

echo "SKY130A=$SKY130A"
echo "Input GDS: $INPUT_GDS"
echo "Magic rcfile: $MAGICRC"
echo "TCL file: $TCL_FILE"
echo "Log file: $LOG_FILE"

set +e
magic -dnull -noconsole -rcfile "$MAGICRC" < "$TCL_FILE" > "$LOG_FILE" 2>&1
status=$?
set -e

if grep -q "failed to load inverter_core_flat" "$LOG_FILE"; then
    echo "warning: Magic could not load inverter_core_flat; check the GDS top-level cell name." >&2
fi

echo "Magic exited with status: $status"
echo "DRC log written to: $LOG_FILE"
exit "$status"
