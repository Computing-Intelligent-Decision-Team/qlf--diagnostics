#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -lt 5 ]]; then
    echo "usage: $0 CASE_NAME CASE_DIR NETLIST_VARIANT POWER_MODE REPORT_PATH" >&2
    echo "  NETLIST_VARIANT: baseline|terminal_swap" >&2
    echo "  POWER_MODE: default|vpwr_vgnd" >&2
    exit 2
fi

CASE_NAME="$1"
CASE_DIR_REL="$2"
NETLIST_VARIANT="$3"
POWER_MODE="$4"
REPORT_REL="$5"
CASE_SLUG="$(printf "%s" "$CASE_NAME" | tr '[:upper:] ' '[:lower:]_' | tr -cd '[:alnum:]_-')"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BASE_DIR="$REPO_ROOT/examples/inverter_sky130_try"
CASE_DIR="$REPO_ROOT/$CASE_DIR_REL"
REPORT="$REPO_ROOT/$REPORT_REL"
OUT_DIR="$REPO_ROOT/generated/sky130_terminal_experiments/$CASE_SLUG"

DEFAULT_SKY130A="/home/to/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A"
SKY130A="${SKY130A:-$DEFAULT_SKY130A}"
MAGICRC="$SKY130A/libs.tech/magic/sky130A.magicrc"
NETGEN_SETUP="$SKY130A/libs.tech/netgen/sky130A_setup.tcl"

MAGICAL_LOG="$OUT_DIR/magical_place_route.log"
REMAP_REPORT="$OUT_DIR/gds_remap_report.md"
LABEL_REPORT="$OUT_DIR/pin_label_report.md"
SHAPE_REPORT="$OUT_DIR/pin_shape_report.md"
MAGIC_TCL="$OUT_DIR/magic_extract.tcl"
MAGIC_LOG="$OUT_DIR/magic_extract.log"
SOURCE_LVS="$OUT_DIR/source_for_lvs.spice"
EXTRACTED_LVS="$OUT_DIR/inverter_core_extracted.spice"
NORMALIZED_LVS="$OUT_DIR/inverter_core_extracted_normalized.spice"
NORMALIZE_REPORT="$OUT_DIR/normalize_lvs_report.md"
NETGEN_LOG="$OUT_DIR/netgen_lvs.log"
NETGEN_REPORT="$OUT_DIR/netgen_lvs_report.out"
NETGEN_TCL="$OUT_DIR/netgen_lvs.tcl"

require_file() {
    if [[ ! -f "$1" ]]; then
        echo "error: required file not found: $1" >&2
        exit 1
    fi
}

if ! command -v docker >/dev/null 2>&1; then
    echo "error: Docker is required for MAGICAL placement/routing stage." >&2
    exit 1
fi
if ! command -v magic >/dev/null 2>&1; then
    echo "error: magic command not found in PATH" >&2
    exit 1
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
if [[ -z "$NETGEN_CMD" ]]; then
    echo "error: IC netgen-lvs command was not found in PATH" >&2
    exit 1
fi

require_file "$BASE_DIR/inverter_core.bound"
require_file "$BASE_DIR/inverter_core.sym"
require_file "$BASE_DIR/inverter_core.symnet"
require_file "$MAGICRC"
require_file "$NETGEN_SETUP"

mkdir -p "$CASE_DIR" "$OUT_DIR" "$(dirname "$REPORT")"
cp "$BASE_DIR/inverter_core.bound" "$CASE_DIR/inverter_core.bound"
cp "$BASE_DIR/inverter_core.sym" "$CASE_DIR/inverter_core.sym"
cp "$BASE_DIR/inverter_core.symnet" "$CASE_DIR/inverter_core.symnet"

case "$NETLIST_VARIANT" in
    baseline)
        nmos_line="M0 (Y A VGND VGND) sky130_fd_pr__nfet_01v8 l=150n w=1u multi=1 nf=1"
        ;;
    terminal_swap)
        nmos_line="M0 (VGND A Y VGND) sky130_fd_pr__nfet_01v8 l=150n w=1u multi=1 nf=1"
        ;;
    *)
        echo "error: unknown NETLIST_VARIANT: $NETLIST_VARIANT" >&2
        exit 2
        ;;
esac

cat > "$CASE_DIR/inverter_sky130_name_test.sp" <<EOF
subckt inverter_core A Y VPWR VGND
$nmos_line
M1 (Y A VPWR VPWR) sky130_fd_pr__pfet_01v8 l=150n w=2u multi=1 nf=1
ends inverter_core
EOF

if [[ "$POWER_MODE" == "vpwr_vgnd" ]]; then
    cat > "$CASE_DIR/inverter_trial.json" <<'EOF'
{
    "spectre_netlist" : "inverter_sky130_name_test.sp",
    "resultDir" : "./",
    "techfile" : "../../generated/sky130PDK_trial/sky130.techfile",
    "simple_tech_file" : "../../generated/sky130PDK_trial/sky130.techfile.simple",
    "lef" : "../../generated/sky130PDK_trial/sky130.lef",
    "vddNetNames" : ["VPWR"],
    "vssNetNames" : ["VGND"]
}
EOF
else
    cat > "$CASE_DIR/inverter_trial.json" <<'EOF'
{
    "spectre_netlist" : "inverter_sky130_name_test.sp",
    "resultDir" : "./",
    "techfile" : "../../generated/sky130PDK_trial/sky130.techfile",
    "simple_tech_file" : "../../generated/sky130PDK_trial/sky130.techfile.simple",
    "lef" : "../../generated/sky130PDK_trial/sky130.lef"
}
EOF
fi

rm -f \
    "$CASE_DIR/inverter_core.route.gds" \
    "$CASE_DIR/inverter_core.place.gds" \
    "$CASE_DIR/inverter_core.ioPin" \
    "$CASE_DIR/inverter_core.sky130.gds" \
    "$CASE_DIR/inverter_core.sky130.pinned.gds" \
    "$CASE_DIR/inverter_core.sky130.pinned_shapes.gds"
mkdir -p "$CASE_DIR/gds"

set +e
docker run --rm -v "$REPO_ROOT:/MAGICAL" jayl940712/magical:latest bash -lc \
    "export PYTHONPATH=/usr/local/lib/python3.7/site-packages:/MAGICAL/flow/python:\${PYTHONPATH:-}; cd /MAGICAL/$CASE_DIR_REL && python3.7 /MAGICAL/flow/python/Magical.py inverter_trial.json" \
    > "$MAGICAL_LOG" 2>&1
magical_status=$?
set -e

if [[ "$magical_status" -ne 0 ]]; then
    echo "error: MAGICAL failed for $CASE_NAME; log: $MAGICAL_LOG" >&2
    exit "$magical_status"
fi
require_file "$CASE_DIR/inverter_core.route.gds"
require_file "$CASE_DIR/inverter_core.ioPin"

python3 "$SCRIPT_DIR/remap_gds_to_sky130.py" \
    --input-gds "$CASE_DIR/inverter_core.route.gds" \
    --output-gds "$CASE_DIR/inverter_core.sky130.gds" \
    --report "$REMAP_REPORT" >/dev/null

python3 "$SCRIPT_DIR/add_sky130_pin_labels_from_iopin.py" \
    --input-gds "$CASE_DIR/inverter_core.sky130.gds" \
    --iopin "$CASE_DIR/inverter_core.ioPin" \
    --output-gds "$CASE_DIR/inverter_core.sky130.pinned.gds" \
    --report "$LABEL_REPORT" >/dev/null

python3 "$SCRIPT_DIR/add_sky130_pin_shapes_from_iopin.py" \
    --input-gds "$CASE_DIR/inverter_core.sky130.pinned.gds" \
    --iopin "$CASE_DIR/inverter_core.ioPin" \
    --output-gds "$CASE_DIR/inverter_core.sky130.pinned_shapes.gds" \
    --report "$SHAPE_REPORT" >/dev/null

cat > "$MAGIC_TCL" <<EOF
puts "TERMINAL_EXPERIMENT: reading GDS $CASE_DIR_REL/inverter_core.sky130.pinned_shapes.gds"
gds read $CASE_DIR_REL/inverter_core.sky130.pinned_shapes.gds
if {[catch {load inverter_core_flat} load_error]} {
    puts stderr "ERROR: failed to load inverter_core_flat"
    puts stderr \$load_error
    quit -noprompt
}
select top cell
extract all
ext2spice lvs
ext2spice cthresh 0
ext2spice rthresh 0
ext2spice
quit -noprompt
EOF

rm -f "$REPO_ROOT/inverter_core_flat.spice" "$REPO_ROOT/inverter_core_flat.sp" "$REPO_ROOT/inverter_core_flat.ext"
set +e
(cd "$REPO_ROOT" && magic -dnull -noconsole -rcfile "$MAGICRC" < "$MAGIC_TCL" > "$MAGIC_LOG" 2>&1)
magic_status=$?
set -e
if [[ "$magic_status" -ne 0 ]]; then
    echo "error: Magic extraction failed for $CASE_NAME; log: $MAGIC_LOG" >&2
    exit "$magic_status"
fi

found_spice=""
for candidate in "$REPO_ROOT/inverter_core_flat.spice" "$REPO_ROOT/inverter_core_flat.sp"; do
    if [[ -f "$candidate" ]]; then
        found_spice="$candidate"
        break
    fi
done
if [[ -z "$found_spice" ]]; then
    echo "error: Magic finished but no extracted SPICE was found for $CASE_NAME" >&2
    exit 1
fi
mv "$found_spice" "$EXTRACTED_LVS"
if [[ -f "$REPO_ROOT/inverter_core_flat.ext" ]]; then
    mv "$REPO_ROOT/inverter_core_flat.ext" "$OUT_DIR/inverter_core_flat.ext"
fi

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
            if (token ~ /^w=/) width = norm_width(token)
            else if (token ~ /^l=/) mos_length = norm_len(token)
        }
        inst = $1
        sub(/^[Mm]/, "X", inst)
        print inst " " $2 " " $3 " " $4 " " $5 " " $6 " w=" width " l=" mos_length
        next
    }
    { print }
    END {
        if (!saw_subckt || !saw_ends) exit 3
    }
' "$CASE_DIR/inverter_sky130_name_test.sp" > "$SOURCE_LVS"

python3 "$SCRIPT_DIR/normalize_lvs_netlists_inverter.py" \
    --input "$EXTRACTED_LVS" \
    --output "$NORMALIZED_LVS" \
    --report "$NORMALIZE_REPORT" >/dev/null

set +e
cat > "$NETGEN_TCL" <<EOF
lvs {$SOURCE_LVS inverter_core} {$NORMALIZED_LVS inverter_core_flat} {$NETGEN_SETUP} {$NETGEN_REPORT}
quit
EOF
"$NETGEN_CMD" -batch source "$NETGEN_TCL" > "$NETGEN_LOG" 2>&1
netgen_status=$?
set -e

nmos_line_raw="$(grep -E '^[[:space:]]*[Xx][^[:space:]]+[[:space:]].*sky130_fd_pr__nfet_01v8' "$EXTRACTED_LVS" | head -n 1 || true)"
pmos_line_raw="$(grep -E '^[[:space:]]*[Xx][^[:space:]]+[[:space:]].*sky130_fd_pr__pfet_01v8' "$EXTRACTED_LVS" | head -n 1 || true)"
subckt_line_raw="$(grep -E '^[[:space:]]*\.subckt[[:space:]]+inverter_core_flat' "$EXTRACTED_LVS" | head -n 1 || true)"
a_n15_exists="no"
if grep -q 'a_n15_90#' "$EXTRACTED_LVS"; then
    a_n15_exists="yes"
fi
anonymous_nodes="$(grep -Eo 'a_[[:alnum:]_]+#|w_[[:alnum:]_]+#' "$EXTRACTED_LVS" | sort -u | paste -sd ', ' - || true)"
if [[ -z "$anonymous_nodes" ]]; then
    anonymous_nodes="none"
fi
anonymous_exists="no"
if [[ "$anonymous_nodes" != "none" ]]; then
    anonymous_exists="yes"
fi
is_power_vpwr="unknown"
is_power_vgnd="unknown"
if grep -q 'addNet netname VPWR .*isPower True' "$MAGICAL_LOG"; then
    is_power_vpwr="True"
elif grep -q 'addNet netname VPWR .*isPower False' "$MAGICAL_LOG"; then
    is_power_vpwr="False"
fi
if grep -q 'addNet netname VGND .*isPower True' "$MAGICAL_LOG"; then
    is_power_vgnd="True"
elif grep -q 'addNet netname VGND .*isPower False' "$MAGICAL_LOG"; then
    is_power_vgnd="False"
fi
recognized_vpwr="no"
recognized_vgnd="no"
if grep -q 'add vdd' "$MAGICAL_LOG"; then
    recognized_vpwr="yes"
fi
if grep -q 'add vss' "$MAGICAL_LOG"; then
    recognized_vgnd="yes"
fi
lvs_match="no"
if [[ -f "$NETGEN_REPORT" ]] && grep -q "Circuits match uniquely" "$NETGEN_REPORT" && grep -q "Netlists match uniquely" "$NETGEN_REPORT"; then
    lvs_match="yes"
fi

{
    echo "# $CASE_NAME Experiment"
    echo
    echo "## Inputs"
    echo
    echo "- Case directory: \`$CASE_DIR_REL\`"
    echo "- Netlist variant: \`$NETLIST_VARIANT\`"
    echo "- Power mode: \`$POWER_MODE\`"
    echo "- NMOS line: \`$nmos_line\`"
    echo
    echo "## Outputs"
    echo
    echo "- MAGICAL log: \`$MAGICAL_LOG\`"
    echo "- Remapped GDS: \`$CASE_DIR_REL/inverter_core.sky130.gds\`"
    echo "- Pinned-shapes GDS: \`$CASE_DIR_REL/inverter_core.sky130.pinned_shapes.gds\`"
    echo "- Magic extraction log: \`$MAGIC_LOG\`"
    echo "- Raw extracted netlist: \`$EXTRACTED_LVS\`"
    echo "- Normalized extracted netlist: \`$NORMALIZED_LVS\`"
    echo "- Netgen report: \`$NETGEN_REPORT\`"
    echo
    echo "## Results"
    echo
    echo "| item | value |"
    echo "| --- | --- |"
    echo "| VPWR isPower | $is_power_vpwr |"
    echo "| VGND isPower | $is_power_vgnd |"
    echo "| VPWR recognized as VDD for power stripe | $recognized_vpwr |"
    echo "| VGND recognized as VSS for power stripe | $recognized_vgnd |"
    echo "| raw .subckt | \`$subckt_line_raw\` |"
    echo "| raw NMOS extraction | \`$nmos_line_raw\` |"
    echo "| raw PMOS extraction | \`$pmos_line_raw\` |"
    echo "| a_n15_90# exists | $a_n15_exists |"
    echo "| anonymous internal nodes exist | $anonymous_exists |"
    echo "| anonymous internal nodes | $anonymous_nodes |"
    echo "| normalized LVS match | $lvs_match |"
    echo "| netgen exit status | $netgen_status |"
    echo
    echo "## Notes"
    echo
    echo "- Raw extraction is the primary signal for this experiment."
    echo "- Normalized LVS still uses the existing inverter-specific normalizer and is reported separately."
} > "$REPORT"

echo "CASE=$CASE_NAME"
echo "REPORT=$REPORT"
echo "VPWR_ISPOWER=$is_power_vpwr"
echo "VGND_ISPOWER=$is_power_vgnd"
echo "VPWR_RECOGNIZED=$recognized_vpwr"
echo "VGND_RECOGNIZED=$recognized_vgnd"
echo "RAW_SUBCKT=$subckt_line_raw"
echo "RAW_NMOS=$nmos_line_raw"
echo "RAW_PMOS=$pmos_line_raw"
echo "A_N15_EXISTS=$a_n15_exists"
echo "ANON_EXISTS=$anonymous_exists"
echo "ANON_NODES=$anonymous_nodes"
echo "LVS_MATCH=$lvs_match"

if [[ "$netgen_status" -ne 0 ]]; then
    echo "warning: Netgen exited with status $netgen_status for $CASE_NAME; continuing because raw extraction is the main experiment output." >&2
fi
