#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

DEFAULT_SKY130A="/home/to/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A"
SKY130A="${SKY130A:-$DEFAULT_SKY130A}"

INPUT_GDS_REL="examples/inverter_sky130_try/inverter_core.sky130.gds"
SOURCE_SPICE_REL="examples/inverter_sky130_try/inverter_sky130_name_test.sp"
INPUT_GDS="$REPO_ROOT/$INPUT_GDS_REL"
SOURCE_SPICE="$REPO_ROOT/$SOURCE_SPICE_REL"
MAGICRC="$SKY130A/libs.tech/magic/sky130A.magicrc"
NETGEN_SETUP="$SKY130A/libs.tech/netgen/sky130A_setup.tcl"

OUT_DIR="$REPO_ROOT/generated/sky130_lvs"
MAGIC_TCL="$OUT_DIR/inverter_magic_extract.tcl"
MAGIC_LOG="$OUT_DIR/inverter_magic_extract.log"
SOURCE_LVS="$OUT_DIR/inverter_source_for_lvs.spice"
EXTRACTED_LVS="$OUT_DIR/inverter_core_extracted.spice"
NORMALIZED_EXTRACTED_LVS="$OUT_DIR/inverter_core_extracted_normalized.spice"
NORMALIZE_REPORT="$OUT_DIR/normalize_lvs_report.md"
EXTRACTED_EXT="$OUT_DIR/inverter_core_flat.ext"
NETGEN_LOG="$OUT_DIR/netgen_lvs.log"
NETGEN_REPORT="$OUT_DIR/netgen_lvs_report.out"
NETGEN_TCL="$OUT_DIR/netgen_lvs.tcl"
NORMALIZE_SCRIPT="$REPO_ROOT/tools/sky130_adapter/normalize_lvs_netlists_inverter.py"

mkdir -p "$OUT_DIR"

fail=0

if ! command -v magic >/dev/null 2>&1; then
    echo "error: magic command not found in PATH" >&2
    fail=1
fi

NETGEN_CMD=""
if command -v netgen-lvs >/dev/null 2>&1; then
    NETGEN_CMD="$(command -v netgen-lvs)"
elif command -v netgen >/dev/null 2>&1; then
    netgen_candidate="$(command -v netgen)"
    netgen_version_out="$("$netgen_candidate" -batch quit 2>&1 || true)"
    if printf '%s\n' "$netgen_version_out" | grep -q 'Netgen 1\.'; then
        NETGEN_CMD="$netgen_candidate"
    fi
fi

if [[ ! -f "$INPUT_GDS" ]]; then
    echo "error: input GDS not found: $INPUT_GDS" >&2
    fail=1
fi

if [[ ! -f "$SOURCE_SPICE" ]]; then
    echo "error: source SPICE not found: $SOURCE_SPICE" >&2
    fail=1
fi

if [[ ! -f "$NORMALIZE_SCRIPT" ]]; then
    echo "error: normalize script not found: $NORMALIZE_SCRIPT" >&2
    fail=1
fi

if [[ ! -f "$MAGICRC" ]]; then
    echo "error: sky130A.magicrc not found: $MAGICRC" >&2
    echo "hint: set SKY130A to the Sky130A PDK root if the default path is not valid" >&2
    fail=1
fi

if [[ ! -f "$NETGEN_SETUP" ]]; then
    echo "error: sky130A netgen setup not found: $NETGEN_SETUP" >&2
    fail=1
fi

if [[ "$fail" -ne 0 ]]; then
    exit 1
fi

cat > "$MAGIC_TCL" <<'EOF'
puts "MAGIC_LVS: reading GDS examples/inverter_sky130_try/inverter_core.sky130.gds"
gds read examples/inverter_sky130_try/inverter_core.sky130.gds

puts "MAGIC_LVS: loading top cell inverter_core_flat"
if {[catch {load inverter_core_flat} load_error]} {
    puts stderr "ERROR: failed to load inverter_core_flat"
    puts stderr "HINT: check the GDS top-level cell name, then update generated/sky130_lvs/inverter_magic_extract.tcl or this wrapper script."
    puts stderr $load_error
    quit -noprompt
}

puts "MAGIC_LVS: selecting top cell"
select top cell
puts "MAGIC_LVS: extracting all"
extract all
puts "MAGIC_LVS: configuring ext2spice for LVS"
ext2spice lvs
ext2spice cthresh 0
ext2spice rthresh 0
puts "MAGIC_LVS: writing extracted SPICE"
ext2spice
quit -noprompt
EOF

awk '
    BEGIN { saw_subckt = 0; saw_ends = 0 }
    function norm_len(value) {
        sub(/^l=/, "", value)
        if (value ~ /n$/) {
            sub(/n$/, "", value)
            return value / 1000.0
        }
        return value
    }
    function norm_width(value) {
        sub(/^w=/, "", value)
        sub(/u$/, "", value)
        return value
    }
    /^[[:space:]]*subckt[[:space:]]+/ {
        sub(/^[[:space:]]*subckt/, ".subckt")
        saw_subckt = 1
        print
        next
    }
    /^[[:space:]]*ends([[:space:]]+|$)/ {
        sub(/^[[:space:]]*ends/, ".ends")
        saw_ends = 1
        print
        next
    }
    /^[[:space:]]*[Mm][^[:space:]]+[[:space:]]/ {
        gsub(/[()]/, "")
        width = ""
        mos_length = ""
        for (i = 7; i <= NF; ++i) {
            token = tolower($i)
            if (token ~ /^w=/) {
                width = norm_width(token)
            } else if (token ~ /^l=/) {
                mos_length = norm_len(token)
            }
        }
        if (width == "" || mos_length == "") {
            print "* ERROR: missing w/l on source MOS line: " $0 > "/dev/stderr"
            exit 4
        }
        inst = $1
        sub(/^[Mm]/, "X", inst)
        print inst " " $2 " " $3 " " $4 " " $5 " " $6 " w=" width " l=" mos_length
        next
    }
    { print }
    END {
        if (!saw_subckt) {
            print "* ERROR: no subckt line found in source netlist" > "/dev/stderr"
            exit 2
        }
        if (!saw_ends) {
            print "* ERROR: no ends line found in source netlist" > "/dev/stderr"
            exit 3
        }
    }
' "$SOURCE_SPICE" > "$SOURCE_LVS"

echo "SKY130A=$SKY130A"
echo "Input GDS: $INPUT_GDS"
echo "Source SPICE: $SOURCE_SPICE"
echo "Magic rcfile: $MAGICRC"
echo "Netgen setup: $NETGEN_SETUP"
echo "Magic TCL: $MAGIC_TCL"
echo "Magic extraction log: $MAGIC_LOG"
echo "LVS source netlist: $SOURCE_LVS"
echo "LVS extracted netlist: $EXTRACTED_LVS"
echo "LVS normalized extracted netlist: $NORMALIZED_EXTRACTED_LVS"
echo "LVS normalization report: $NORMALIZE_REPORT"
echo "Magic extracted EXT: $EXTRACTED_EXT"
echo "LVS command: ${NETGEN_CMD:-not found}"
echo "Netgen log: $NETGEN_LOG"
echo "Netgen report: $NETGEN_REPORT"

rm -f "$EXTRACTED_LVS" "$NORMALIZED_EXTRACTED_LVS" "$NORMALIZE_REPORT" "$EXTRACTED_EXT" "$NETGEN_LOG" "$NETGEN_REPORT"

cd "$REPO_ROOT"
set +e
magic -dnull -noconsole -rcfile "$MAGICRC" < "$MAGIC_TCL" > "$MAGIC_LOG" 2>&1
magic_status=$?
set -e

if grep -q "failed to load inverter_core_flat" "$MAGIC_LOG"; then
    echo "warning: Magic could not load inverter_core_flat; check the GDS top-level cell name." >&2
fi

if [[ "$magic_status" -ne 0 ]]; then
    echo "error: Magic extraction failed with status $magic_status" >&2
    echo "Magic extraction log: $MAGIC_LOG" >&2
    exit "$magic_status"
fi

found_spice=""
for candidate in \
    "$REPO_ROOT/inverter_core_flat.spice" \
    "$REPO_ROOT/inverter_core_flat.sp" \
    "$REPO_ROOT/inverter_core.spice" \
    "$REPO_ROOT/inverter_core.sp" \
    "$OUT_DIR/inverter_core_flat.spice" \
    "$OUT_DIR/inverter_core_flat.sp" \
    "$OUT_DIR/inverter_core.spice" \
    "$OUT_DIR/inverter_core.sp"; do
    if [[ -f "$candidate" ]]; then
        found_spice="$candidate"
        break
    fi
done

if [[ -z "$found_spice" ]]; then
    found_spice="$(find "$REPO_ROOT" "$OUT_DIR" -maxdepth 1 -type f \( -name '*.spice' -o -name '*.sp' \) -printf '%T@ %p\n' 2>/dev/null | sort -nr | awk 'NR == 1 {print $2}')"
fi

if [[ -z "$found_spice" || ! -f "$found_spice" ]]; then
    echo "error: Magic extraction completed, but no extracted SPICE file was found." >&2
    echo "Magic extraction log: $MAGIC_LOG" >&2
    exit 1
fi

if [[ -f "$REPO_ROOT/inverter_core_flat.ext" ]]; then
    mv "$REPO_ROOT/inverter_core_flat.ext" "$EXTRACTED_EXT"
    echo "Moved Magic EXT from $REPO_ROOT/inverter_core_flat.ext to $EXTRACTED_EXT"
fi

if [[ "$found_spice" != "$EXTRACTED_LVS" ]]; then
    mv "$found_spice" "$EXTRACTED_LVS"
    echo "Moved Magic extracted SPICE from $found_spice to $EXTRACTED_LVS"
fi

python3 "$NORMALIZE_SCRIPT" \
    --input "$EXTRACTED_LVS" \
    --output "$NORMALIZED_EXTRACTED_LVS" \
    --report "$NORMALIZE_REPORT"

if [[ -z "$NETGEN_CMD" ]]; then
    {
        echo "error: IC netgen-lvs command was not found in PATH"
        echo "Magic extraction succeeded and produced: $EXTRACTED_LVS"
        echo "Install netgen-lvs, or add an IC Netgen 1.x command to PATH, then rerun this script."
        echo "Expected LVS command:"
        echo "netgen-lvs -batch source \"$NETGEN_TCL\""
    } > "$NETGEN_LOG"
    echo "error: IC netgen-lvs command was not found in PATH" >&2
    echo "Netgen LVS log: $NETGEN_LOG" >&2
    exit 127
fi

set +e
cat > "$NETGEN_TCL" <<EOF
lvs {$SOURCE_LVS inverter_core} {$NORMALIZED_EXTRACTED_LVS inverter_core_flat} {$NETGEN_SETUP} {$NETGEN_REPORT}
quit
EOF
"$NETGEN_CMD" -batch source "$NETGEN_TCL" > "$NETGEN_LOG" 2>&1
netgen_status=$?
set -e

echo "Magic extraction completed successfully."
echo "Netgen exited with status: $netgen_status"
echo "Magic extraction log: $MAGIC_LOG"
echo "Netgen LVS log: $NETGEN_LOG"
echo "Netgen LVS report: $NETGEN_REPORT"
exit "$netgen_status"
