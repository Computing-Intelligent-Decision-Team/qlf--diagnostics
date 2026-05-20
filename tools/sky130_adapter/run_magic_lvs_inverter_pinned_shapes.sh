#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

DEFAULT_SKY130A="/home/to/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A"
SKY130A="${SKY130A:-$DEFAULT_SKY130A}"

INPUT_GDS_REL="examples/inverter_sky130_try/inverter_core.sky130.pinned_shapes.gds"
SOURCE_SPICE_REL="examples/inverter_sky130_try/inverter_sky130_name_test.sp"
INPUT_GDS="$REPO_ROOT/$INPUT_GDS_REL"
SOURCE_SPICE="$REPO_ROOT/$SOURCE_SPICE_REL"
MAGICRC="$SKY130A/libs.tech/magic/sky130A.magicrc"
NETGEN_SETUP="$SKY130A/libs.tech/netgen/sky130A_setup.tcl"

OUT_DIR="$REPO_ROOT/generated/sky130_lvs_pinned_shapes"
MAGIC_TCL="$OUT_DIR/inverter_magic_extract_pinned_shapes.tcl"
MAGIC_LOG="$OUT_DIR/inverter_magic_extract_pinned_shapes.log"
SOURCE_LVS="$OUT_DIR/inverter_source_for_lvs.spice"
EXTRACTED_LVS="$OUT_DIR/inverter_core_extracted_pinned_shapes.spice"
NORMALIZED_EXTRACTED_LVS="$OUT_DIR/inverter_core_extracted_pinned_shapes_normalized.spice"
NORMALIZE_REPORT="$OUT_DIR/normalize_lvs_pinned_shapes_report.md"
EXTRACTED_EXT="$OUT_DIR/inverter_core_flat_pinned_shapes.ext"
NETGEN_LOG="$OUT_DIR/netgen_lvs_pinned_shapes.log"
NETGEN_REPORT="$OUT_DIR/netgen_lvs_pinned_shapes_report.out"
PINNED_SHAPES_REPORT="$OUT_DIR/pinned_shapes_lvs_report.md"
NORMALIZE_SCRIPT="$REPO_ROOT/tools/sky130_adapter/normalize_lvs_netlists_inverter.py"

KNOWN_INTERNAL_NODES=("a_55_90#" "a_25_70#" "w_245_n115#" "a_n15_90#" "a_n135_n215#")

mkdir -p "$OUT_DIR"

fail=0
if ! command -v magic >/dev/null 2>&1; then
    echo "error: magic command not found in PATH" >&2
    fail=1
fi

NETGEN_CMD=""
if command -v netgen >/dev/null 2>&1; then
    NETGEN_CMD="$(command -v netgen)"
elif command -v netgen-lvs >/dev/null 2>&1; then
    NETGEN_CMD="$(command -v netgen-lvs)"
fi

for path in "$INPUT_GDS" "$SOURCE_SPICE" "$NORMALIZE_SCRIPT" "$MAGICRC" "$NETGEN_SETUP"; do
    if [[ ! -f "$path" ]]; then
        echo "error: required file not found: $path" >&2
        fail=1
    fi
done

if [[ "$fail" -ne 0 ]]; then
    exit 1
fi

cat > "$MAGIC_TCL" <<'EOF'
puts "MAGIC_LVS_PINNED_SHAPES: reading GDS examples/inverter_sky130_try/inverter_core.sky130.pinned_shapes.gds"
gds read examples/inverter_sky130_try/inverter_core.sky130.pinned_shapes.gds

puts "MAGIC_LVS_PINNED_SHAPES: loading top cell inverter_core_flat"
if {[catch {load inverter_core_flat} load_error]} {
    puts stderr "ERROR: failed to load inverter_core_flat"
    puts stderr "HINT: check the GDS top-level cell name."
    puts stderr $load_error
    quit -noprompt
}

puts "MAGIC_LVS_PINNED_SHAPES: selecting top cell"
select top cell
puts "MAGIC_LVS_PINNED_SHAPES: extracting all"
extract all
puts "MAGIC_LVS_PINNED_SHAPES: configuring ext2spice for LVS"
ext2spice lvs
ext2spice cthresh 0
ext2spice rthresh 0
puts "MAGIC_LVS_PINNED_SHAPES: writing extracted SPICE"
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
echo "Pinned-shapes input GDS: $INPUT_GDS"
echo "Source SPICE: $SOURCE_SPICE"
echo "Magic extraction log: $MAGIC_LOG"
echo "Raw extracted netlist: $EXTRACTED_LVS"
echo "Normalized extracted netlist: $NORMALIZED_EXTRACTED_LVS"
echo "Pinned-shapes LVS report: $PINNED_SHAPES_REPORT"
echo "Netgen command: ${NETGEN_CMD:-not found}"

rm -f \
    "$EXTRACTED_LVS" \
    "$NORMALIZED_EXTRACTED_LVS" \
    "$NORMALIZE_REPORT" \
    "$EXTRACTED_EXT" \
    "$NETGEN_LOG" \
    "$NETGEN_REPORT" \
    "$PINNED_SHAPES_REPORT" \
    "$REPO_ROOT/inverter_core_flat.spice" \
    "$REPO_ROOT/inverter_core_flat.sp" \
    "$REPO_ROOT/inverter_core_flat.ext"

cd "$REPO_ROOT"
set +e
magic -dnull -noconsole -rcfile "$MAGICRC" < "$MAGIC_TCL" > "$MAGIC_LOG" 2>&1
magic_status=$?
set -e

if [[ "$magic_status" -ne 0 ]]; then
    echo "error: Magic extraction failed with status $magic_status" >&2
    echo "Magic extraction log: $MAGIC_LOG" >&2
    exit "$magic_status"
fi

found_spice=""
for candidate in \
    "$REPO_ROOT/inverter_core_flat.spice" \
    "$REPO_ROOT/inverter_core_flat.sp" \
    "$OUT_DIR/inverter_core_flat.spice" \
    "$OUT_DIR/inverter_core_flat.sp"; do
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
fi
mv "$found_spice" "$EXTRACTED_LVS"

raw_all_pins="yes"
raw_pin_rows=""
for net in A Y VPWR VGND; do
    if grep -Eq "(^|[[:space:]])${net}([[:space:]]|$)" "$EXTRACTED_LVS"; then
        raw_pin_rows="${raw_pin_rows}| ${net} | yes |\n"
    else
        raw_pin_rows="${raw_pin_rows}| ${net} | no |\n"
        raw_all_pins="no"
    fi
done

known_rows=""
known_remaining=()
for node in "${KNOWN_INTERNAL_NODES[@]}"; do
    if grep -q "$node" "$EXTRACTED_LVS"; then
        known_rows="${known_rows}| ${node} | yes |\n"
        known_remaining+=("$node")
    else
        known_rows="${known_rows}| ${node} | no |\n"
    fi
done

known_remaining_text="none"
if [[ "${#known_remaining[@]}" -gt 0 ]]; then
    known_remaining_text="$(IFS=', '; echo "${known_remaining[*]}")"
fi

subckt_line="$(grep -E '^[[:space:]]*\.subckt[[:space:]]+inverter_core_flat' "$EXTRACTED_LVS" | head -n 1 || true)"
subckt_has_ports="no"
subckt_field_count=0
if [[ -n "$subckt_line" ]]; then
    subckt_field_count="$(awk '{print NF}' <<< "$subckt_line")"
fi
if [[ "$subckt_field_count" -gt 2 ]]; then
    subckt_has_ports="yes"
fi

nmos_line="$(grep -E '^[[:space:]]*[Xx]0[[:space:]]+' "$EXTRACTED_LVS" | head -n 1 || true)"
nmos_source="$(awk '{print $4}' <<< "$nmos_line")"
if [[ -z "$nmos_source" ]]; then
    nmos_source="unknown"
fi
nmos_source_is_internal="no"
if [[ "$nmos_source" == "a_n15_90#" ]]; then
    nmos_source_is_internal="yes"
fi

raw_cleaner="no"
raw_cleaner_note="Known internal nodes still remain after adding pin-purpose shapes."
if [[ "$known_remaining_text" == "none" && "$subckt_has_ports" == "yes" && "$nmos_source_is_internal" == "no" ]]; then
    raw_cleaner="yes"
    raw_cleaner_note="Raw extraction has target pins, no known internal nodes, a ported subckt line, and no a_n15_90# NMOS source."
elif [[ "$known_remaining_text" == "none" ]]; then
    raw_cleaner="partial"
    raw_cleaner_note="Known internal nodes are gone, but subckt port formatting or MOS terminal checks are not fully clean."
elif [[ "$subckt_has_ports" == "yes" && "$raw_all_pins" == "yes" ]]; then
    raw_cleaner="partial"
    raw_cleaner_note="Raw extraction is cleaner than the label-only trial for top-level port declaration, but known internal nodes still remain: $known_remaining_text."
fi

python3 "$NORMALIZE_SCRIPT" \
    --input "$EXTRACTED_LVS" \
    --output "$NORMALIZED_EXTRACTED_LVS" \
    --report "$NORMALIZE_REPORT"

if [[ -z "$NETGEN_CMD" ]]; then
    echo "error: neither netgen nor netgen-lvs command was found in PATH" >&2
    echo "Netgen LVS log: $NETGEN_LOG" >&2
    exit 127
fi

set +e
"$NETGEN_CMD" -batch lvs \
    "$SOURCE_LVS inverter_core" \
    "$NORMALIZED_EXTRACTED_LVS inverter_core_flat" \
    "$NETGEN_SETUP" \
    "$NETGEN_REPORT" \
    > "$NETGEN_LOG" 2>&1
netgen_status=$?
set -e

lvs_match="no"
if [[ -f "$NETGEN_REPORT" ]] \
    && grep -q "Circuits match uniquely" "$NETGEN_REPORT" \
    && grep -q "Netlists match uniquely" "$NETGEN_REPORT"; then
    lvs_match="yes"
fi

normalization_required="yes"
normalization_note="Normalization is still required for this trial."
if [[ "$known_remaining_text" == "none" && "$subckt_has_ports" == "yes" && "$lvs_match" == "yes" ]]; then
    normalization_note="Normalization is still used for parasitic capacitor removal and ad/as/pd/ps property cleanup, but pin naming is much closer to native."
elif [[ "$known_remaining_text" != "none" ]]; then
    normalization_note="Normalization is still required because raw extraction retains internal node names: $known_remaining_text."
fi

{
    echo "# Pinned Shapes GDS LVS Trial Report"
    echo
    echo "## Summary"
    echo
    echo "- Input pinned-shapes GDS: \`$INPUT_GDS\`"
    echo "- Magic extraction log: \`$MAGIC_LOG\`"
    echo "- Raw extracted netlist: \`$EXTRACTED_LVS\`"
    echo "- Normalized extracted netlist: \`$NORMALIZED_EXTRACTED_LVS\`"
    echo "- Normalization report: \`$NORMALIZE_REPORT\`"
    echo "- Netgen log: \`$NETGEN_LOG\`"
    echo "- Netgen report: \`$NETGEN_REPORT\`"
    echo "- Raw Magic extraction contains all A/Y/VPWR/VGND names: $raw_all_pins"
    echo "- Known internal nodes still present: $known_remaining_text"
    echo "- .subckt has explicit port list: $subckt_has_ports"
    echo "- NMOS source terminal: $nmos_source"
    echo "- NMOS source is still a_n15_90#: $nmos_source_is_internal"
    echo "- Raw extraction cleaner than label-only pinned trial: $raw_cleaner"
    echo "- Netgen LVS match after current normalization: $lvs_match"
    echo "- Normalization still used: yes"
    echo
    echo "## Raw Target Net Name Check"
    echo
    echo "| net | appears in raw extracted netlist |"
    echo "| --- | --- |"
    printf "%b" "$raw_pin_rows"
    echo
    echo "## Known Internal Node Check"
    echo
    echo "| internal node | appears in raw extracted netlist |"
    echo "| --- | --- |"
    printf "%b" "$known_rows"
    echo
    echo "## Interpretation"
    echo
    echo "$raw_cleaner_note"
    echo
    echo "$normalization_note"
    echo
    echo "This pinned-shapes trial is experimental and does not replace the existing inverter pipeline."
} > "$PINNED_SHAPES_REPORT"

echo "Magic extraction completed successfully."
echo "Raw extraction contains all A/Y/VPWR/VGND: $raw_all_pins"
echo "Known internal nodes still present: $known_remaining_text"
echo ".subckt has explicit port list: $subckt_has_ports"
echo "NMOS source terminal: $nmos_source"
echo "Netgen exited with status: $netgen_status"
echo "LVS match after current normalization: $lvs_match"
echo "Pinned-shapes LVS report: $PINNED_SHAPES_REPORT"

if [[ "$netgen_status" -ne 0 || "$lvs_match" != "yes" ]]; then
    exit 1
fi
