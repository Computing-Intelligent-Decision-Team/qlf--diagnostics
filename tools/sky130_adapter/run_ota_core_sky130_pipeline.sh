#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
EXAMPLE_DIR="$REPO_ROOT/examples/ota_core_sky130_try"
OUT_DIR="$REPO_ROOT/generated/sky130_ota_core_pipeline"
SUMMARY="$OUT_DIR/summary.md"
DOCKER_IMAGE="jayl940712/magical:latest"

DEFAULT_SKY130A="/home/to/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A"
SKY130A="${SKY130A:-$DEFAULT_SKY130A}"
MAGICRC="$SKY130A/libs.tech/magic/sky130A.magicrc"
NETGEN_SETUP="$SKY130A/libs.tech/netgen/sky130A_setup.tcl"

RAW_NETLIST="$EXAMPLE_DIR/ota_core_raw.spice"
MAGICAL_NETLIST="$EXAMPLE_DIR/ota_core_magical.sp"
CONFIG="$EXAMPLE_DIR/ota_core.json"
CELL="ota_core"
MAGIC_CELL="${CELL}_flat"

CONVERT_LOG="$OUT_DIR/convert.log"
MAGICAL_LOG="$OUT_DIR/magical_place_route.log"
MAGICAL_RUN_LOG="$EXAMPLE_DIR/run_ota_core_trial.log"
REMAP_REPORT="$OUT_DIR/gds_remap_report.md"
LABEL_REPORT="$OUT_DIR/pin_label_report.md"
SHAPE_REPORT="$OUT_DIR/pin_shape_report.md"
DRC_TCL="$OUT_DIR/magic_drc.tcl"
DRC_LOG="$OUT_DIR/magic_drc.log"
MAGIC_TCL="$OUT_DIR/magic_extract.tcl"
MAGIC_LOG="$OUT_DIR/magic_extract.log"
EXTRACTED_LVS="$OUT_DIR/ota_core_extracted.spice"
LVS_PREP_REPORT="$OUT_DIR/lvs_preparation_report.md"
NETGEN_LOG="$OUT_DIR/netgen_lvs.log"
NETGEN_REPORT="$OUT_DIR/netgen_lvs_report.out"
LVS_RESULT_SUMMARY="$OUT_DIR/lvs_result_summary.md"
PEX_SUMMARY="$OUT_DIR/pex_summary.md"

mkdir -p "$OUT_DIR"

fail() {
    local stage="$1"
    local message="$2"
    {
        echo "# Sky130 OTA Core Pipeline Summary"
        echo
        echo "| Item | Result |"
        echo "| --- | --- |"
        echo "| Status | FAIL |"
        echo "| Failed stage | $stage |"
        echo "| Message | $message |"
    } > "$SUMMARY"
    echo "FAIL[$stage]: $message" >&2
    exit 1
}

require_file() {
    [[ -f "$1" ]] || fail "$2" "required file not found: $1"
}

command -v docker >/dev/null 2>&1 || fail "setup" "Docker is required for MAGICAL placement/routing stage."
command -v magic >/dev/null 2>&1 || fail "setup" "magic command not found in PATH"

NETGEN_CMD=""
if command -v netgen >/dev/null 2>&1; then
    NETGEN_CMD="$(command -v netgen)"
elif command -v netgen-lvs >/dev/null 2>&1; then
    NETGEN_CMD="$(command -v netgen-lvs)"
else
    fail "setup" "neither netgen nor netgen-lvs command was found in PATH"
fi

require_file "$RAW_NETLIST" "setup"
require_file "$CONFIG" "setup"
require_file "$MAGICRC" "setup"
require_file "$NETGEN_SETUP" "setup"

echo "RUN: convert xschem Sky130 netlist"
python3 "$SCRIPT_DIR/convert_xschem_sky130_netlist.py" \
    --input "$RAW_NETLIST" \
    --output "$MAGICAL_NETLIST" \
    --global-port GND \
    > "$CONVERT_LOG" 2>&1 || fail "convert" "xschem-to-MAGICAL conversion failed; see $CONVERT_LOG"

echo "RUN: MAGICAL placement/routing in Docker"
docker run --rm \
    -v "$REPO_ROOT:/MAGICAL" \
    "$DOCKER_IMAGE" \
    bash -lc "export PYTHONPATH=/usr/local/lib/python3.7/site-packages:/MAGICAL/flow/python:\${PYTHONPATH:-}; cd /MAGICAL/examples/ota_core_sky130_try && rm -rf ${CELL}.route.gds ${CELL}.place.gds ${CELL}.ioPin gds && mkdir -p gds && python3.7 /MAGICAL/flow/python/Magical.py ota_core.json > run_ota_core_trial.log 2>&1" \
    > "$MAGICAL_LOG" 2>&1 || fail "magical_place_route" "MAGICAL failed; see $MAGICAL_LOG and $MAGICAL_RUN_LOG"

require_file "$EXAMPLE_DIR/${CELL}.route.gds" "magical_output"
require_file "$EXAMPLE_DIR/${CELL}.ioPin" "magical_output"

echo "RUN: remap GDS"
python3 "$SCRIPT_DIR/remap_gds_to_sky130.py" \
    --input-gds "$EXAMPLE_DIR/${CELL}.route.gds" \
    --output-gds "$EXAMPLE_DIR/${CELL}.sky130.gds" \
    --report "$REMAP_REPORT" >/dev/null || fail "gds_remap" "GDS remap failed"

echo "RUN: add Sky130 pin labels"
python3 "$SCRIPT_DIR/add_sky130_pin_labels_from_iopin.py" \
    --input-gds "$EXAMPLE_DIR/${CELL}.sky130.gds" \
    --iopin "$EXAMPLE_DIR/${CELL}.ioPin" \
    --output-gds "$EXAMPLE_DIR/${CELL}.sky130.pinned.gds" \
    --report "$LABEL_REPORT" \
    --cell "$MAGIC_CELL" \
    --netlist "$MAGICAL_NETLIST" \
    --top-cell "$CELL" \
    --only-top-ports >/dev/null || fail "pin_labels" "pin label postprocess failed"

echo "RUN: add Sky130 pin shapes"
python3 "$SCRIPT_DIR/add_sky130_pin_shapes_from_iopin.py" \
    --input-gds "$EXAMPLE_DIR/${CELL}.sky130.pinned.gds" \
    --iopin "$EXAMPLE_DIR/${CELL}.ioPin" \
    --output-gds "$EXAMPLE_DIR/${CELL}.sky130.pinned_shapes.gds" \
    --report "$SHAPE_REPORT" \
    --cell "$MAGIC_CELL" \
    --netlist "$MAGICAL_NETLIST" \
    --top-cell "$CELL" \
    --only-top-ports >/dev/null || fail "pin_shapes" "pin shape postprocess failed"

cat > "$DRC_TCL" <<EOF
puts "OTA_DRC: reading pinned-shapes GDS"
gds read examples/ota_core_sky130_try/${CELL}.sky130.pinned_shapes.gds
if {[catch {load ${MAGIC_CELL}} load_error]} {
    puts stderr "ERROR: failed to load ${MAGIC_CELL}"
    puts stderr \$load_error
    quit -noprompt
}
drc check
drc count
quit -noprompt
EOF

echo "RUN: Magic DRC"
(cd "$REPO_ROOT" && magic -dnull -noconsole -rcfile "$MAGICRC" < "$DRC_TCL" > "$DRC_LOG" 2>&1) || fail "magic_drc" "Magic DRC command failed; see $DRC_LOG"

cat > "$MAGIC_TCL" <<EOF
puts "OTA_LVS: reading pinned-shapes GDS"
gds read examples/ota_core_sky130_try/${CELL}.sky130.pinned_shapes.gds
if {[catch {load ${MAGIC_CELL}} load_error]} {
    puts stderr "ERROR: failed to load ${MAGIC_CELL}"
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

rm -f "$REPO_ROOT/${MAGIC_CELL}.spice" "$REPO_ROOT/${MAGIC_CELL}.sp" "$REPO_ROOT/${MAGIC_CELL}.ext"
echo "RUN: Magic extraction"
(cd "$REPO_ROOT" && magic -dnull -noconsole -rcfile "$MAGICRC" < "$MAGIC_TCL" > "$MAGIC_LOG" 2>&1) || fail "magic_extract" "Magic extraction command failed; see $MAGIC_LOG"

found_spice=""
for candidate in "$REPO_ROOT/${MAGIC_CELL}.spice" "$REPO_ROOT/${MAGIC_CELL}.sp"; do
    if [[ -f "$candidate" ]]; then
        found_spice="$candidate"
        break
    fi
done
[[ -n "$found_spice" ]] || fail "magic_extract" "Magic did not produce ${MAGIC_CELL}.spice"
mv "$found_spice" "$EXTRACTED_LVS"
if [[ -f "$REPO_ROOT/${MAGIC_CELL}.ext" ]]; then
    mv "$REPO_ROOT/${MAGIC_CELL}.ext" "$OUT_DIR/${MAGIC_CELL}.ext"
fi

echo "RUN: prepare raw/connectivity LVS netlists"
python3 "$SCRIPT_DIR/prepare_lvs_netlists.py" \
    --source "$MAGICAL_NETLIST" \
    --extracted "$EXTRACTED_LVS" \
    --out-dir "$OUT_DIR" \
    --prefix "$CELL" \
    --report "$LVS_PREP_REPORT" >/dev/null || fail "lvs_prepare" "LVS preparation failed"

echo "RUN: Netgen connectivity LVS"
set +e
"$NETGEN_CMD" -batch lvs \
    "$OUT_DIR/${CELL}_source.connectivity.spice $CELL" \
    "$OUT_DIR/${CELL}_extracted.connectivity.spice $MAGIC_CELL" \
    "$NETGEN_SETUP" \
    "$NETGEN_REPORT" \
    > "$NETGEN_LOG" 2>&1
netgen_status=$?
set -e

echo "RUN: analyze LVS result"
set +e
python3 "$SCRIPT_DIR/analyze_lvs_result.py" \
    --report "$NETGEN_REPORT" \
    --log "$NETGEN_LOG" \
    --output "$LVS_RESULT_SUMMARY" >/dev/null
analyze_status=$?
set -e

echo "RUN: summarize Magic PEX"
python3 "$SCRIPT_DIR/summarize_magic_pex.py" \
    --input "$OUT_DIR/${CELL}_extracted.raw.spice" \
    --output "$PEX_SUMMARY" >/dev/null || fail "pex_summary" "PEX summary failed"

subckt_line="$(grep -E "^[[:space:]]*\\.subckt[[:space:]]+${MAGIC_CELL}" "$EXTRACTED_LVS" | head -n 1 || true)"
mos_count="$(grep -Ec '^[[:space:]]*[Xx][^[:space:]]+[[:space:]].*sky130_fd_pr__(n|p)fet_01v8' "$EXTRACTED_LVS" || true)"
anon_nodes="$(grep -Eo 'a_[[:alnum:]_]+#|w_[[:alnum:]_]+#' "$EXTRACTED_LVS" | sort -u | paste -sd ', ' - || true)"
[[ -n "$anon_nodes" ]] || anon_nodes="none"
drc_count="$(awk '/Total DRC errors found:/ {print $NF}' "$DRC_LOG" | tail -n 1)"
[[ -n "$drc_count" ]] || drc_count="unknown"
pex_caps="$(awk -F': ' '/Parasitic capacitor count:/ {print $2}' "$PEX_SUMMARY" | tail -n 1)"
[[ -n "$pex_caps" ]] || pex_caps="unknown"
pex_total="$(awk -F': ' '/Total listed capacitance:/ {print $2}' "$PEX_SUMMARY" | tail -n 1)"
[[ -n "$pex_total" ]] || pex_total="unknown"
lvs_match="no"
if [[ "$netgen_status" -eq 0 && "$analyze_status" -eq 0 ]] && grep -q "LVS status: \\*\\*PASS\\*\\*" "$LVS_RESULT_SUMMARY"; then
    lvs_match="yes"
fi

cat > "$SUMMARY" <<EOF
# Sky130 OTA Core Pipeline Summary

| Item | Result |
| --- | --- |
| Status | complete |
| MAGICAL placement/routing | pass |
| Raw subckt | \`$subckt_line\` |
| Raw extracted MOS count | $mos_count |
| Anonymous extracted nodes | $anon_nodes |
| Magic DRC error count | $drc_count |
| Connectivity LVS status | $lvs_match |
| Netgen exit status | $netgen_status |
| Net renaming used | no |
| PEX summary status | generated |
| Parasitic capacitor count | $pex_caps |
| Total listed capacitance | $pex_total |

## Key Outputs

- Converted MAGICAL netlist: \`$MAGICAL_NETLIST\`
- MAGICAL log: \`$MAGICAL_LOG\`
- MAGICAL run log: \`$MAGICAL_RUN_LOG\`
- ioPin: \`$EXAMPLE_DIR/${CELL}.ioPin\`
- Pinned-shapes GDS: \`$EXAMPLE_DIR/${CELL}.sky130.pinned_shapes.gds\`
- DRC log: \`$DRC_LOG\`
- Raw extracted netlist: \`$EXTRACTED_LVS\`
- Raw extracted netlist copy: \`$OUT_DIR/${CELL}_extracted.raw.spice\`
- Connectivity source netlist: \`$OUT_DIR/${CELL}_source.connectivity.spice\`
- Connectivity extracted netlist: \`$OUT_DIR/${CELL}_extracted.connectivity.spice\`
- LVS preparation report: \`$LVS_PREP_REPORT\`
- Netgen connectivity LVS report: \`$NETGEN_REPORT\`
- LVS result summary: \`$LVS_RESULT_SUMMARY\`
- PEX summary: \`$PEX_SUMMARY\`
EOF

echo "Summary written: $SUMMARY"
echo "RAW_SUBCKT=$subckt_line"
echo "RAW_MOS_COUNT=$mos_count"
echo "ANON_NODES=$anon_nodes"
echo "DRC_COUNT=$drc_count"
echo "CONNECTIVITY_LVS_MATCH=$lvs_match"
echo "PEX_CAPS=$pex_caps"

[[ "$lvs_match" == "yes" ]] || fail "connectivity_lvs" "Connectivity LVS did not pass; see $LVS_RESULT_SUMMARY"
