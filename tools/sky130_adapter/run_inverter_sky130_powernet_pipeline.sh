#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
EXAMPLE_DIR="$REPO_ROOT/examples/inverter_sky130_try"
OUT_DIR="$REPO_ROOT/generated/sky130_powernet_pipeline/inverter"
SUMMARY="$OUT_DIR/summary.md"
DOCKER_IMAGE="jayl940712/magical:latest"

DEFAULT_SKY130A="/home/to/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A"
SKY130A="${SKY130A:-$DEFAULT_SKY130A}"
MAGICRC="$SKY130A/libs.tech/magic/sky130A.magicrc"
NETGEN_SETUP="$SKY130A/libs.tech/netgen/sky130A_setup.tcl"

MAGICAL_LOG="$OUT_DIR/magical_place_route.log"
TRIAL_LOG="$EXAMPLE_DIR/run_trial_sky130PDK.log"
REMAP_REPORT="$OUT_DIR/gds_remap_report.md"
LABEL_REPORT="$OUT_DIR/pin_label_report.md"
SHAPE_REPORT="$OUT_DIR/pin_shape_report.md"
DRC_TCL="$OUT_DIR/magic_drc_pinned_shapes.tcl"
DRC_LOG="$OUT_DIR/magic_drc_pinned_shapes.log"
MAGIC_TCL="$OUT_DIR/magic_extract_pinned_shapes.tcl"
MAGIC_LOG="$OUT_DIR/magic_extract_pinned_shapes.log"
EXTRACTED_LVS="$OUT_DIR/inverter_core_extracted.spice"
RAW_EXTRACTED_COPY="$OUT_DIR/inverter_core_extracted.raw.spice"
CONNECTIVITY_SOURCE="$OUT_DIR/inverter_source.connectivity.spice"
CONNECTIVITY_EXTRACTED="$OUT_DIR/inverter_core_extracted.connectivity.spice"
LVS_PREP_REPORT="$OUT_DIR/lvs_preparation_report.md"
NETGEN_LOG="$OUT_DIR/netgen_lvs.log"
NETGEN_REPORT="$OUT_DIR/netgen_lvs_report.out"
LVS_RESULT_SUMMARY="$OUT_DIR/lvs_result_summary.md"
PEX_SUMMARY="$OUT_DIR/pex_summary.md"
POWERNET_CONFIG_REPORT="$OUT_DIR/powernet_config_check.md"

mkdir -p "$OUT_DIR"

fail() {
    echo "error: $*" >&2
    exit 1
}

require_file() {
    [[ -f "$1" ]] || fail "required file not found: $1"
}

command -v docker >/dev/null 2>&1 || fail "Docker is required for MAGICAL placement/routing stage."
command -v magic >/dev/null 2>&1 || fail "magic command not found in PATH"

NETGEN_CMD=""
if command -v netgen >/dev/null 2>&1; then
    NETGEN_CMD="$(command -v netgen)"
elif command -v netgen-lvs >/dev/null 2>&1; then
    NETGEN_CMD="$(command -v netgen-lvs)"
else
    fail "neither netgen nor netgen-lvs command was found in PATH"
fi

require_file "$EXAMPLE_DIR/inverter_sky130_name_test.sp"
require_file "$EXAMPLE_DIR/inverter.json"
require_file "$EXAMPLE_DIR/run_with_trial_sky130PDK.sh"
require_file "$MAGICRC"
require_file "$NETGEN_SETUP"

echo "RUN: ensure Sky130 VPWR/VGND power-net config"
python3 "$SCRIPT_DIR/ensure_sky130_inverter_powernets.py" \
    --config "$EXAMPLE_DIR/inverter.json" \
    --report "$POWERNET_CONFIG_REPORT" >/dev/null

echo "RUN: MAGICAL placement/routing in Docker"
docker run --rm \
    -v "$REPO_ROOT:/MAGICAL" \
    "$DOCKER_IMAGE" \
    bash -lc "cd /MAGICAL/examples/inverter_sky130_try && ./run_with_trial_sky130PDK.sh" \
    > "$MAGICAL_LOG" 2>&1

require_file "$EXAMPLE_DIR/inverter_core.route.gds"
require_file "$EXAMPLE_DIR/inverter_core.ioPin"

echo "RUN: remap GDS"
python3 "$SCRIPT_DIR/remap_gds_to_sky130.py" \
    --input-gds "$EXAMPLE_DIR/inverter_core.route.gds" \
    --output-gds "$EXAMPLE_DIR/inverter_core.sky130.gds" \
    --report "$REMAP_REPORT" >/dev/null

echo "RUN: add Sky130 pin labels"
python3 "$SCRIPT_DIR/add_sky130_pin_labels_from_iopin.py" \
    --input-gds "$EXAMPLE_DIR/inverter_core.sky130.gds" \
    --iopin "$EXAMPLE_DIR/inverter_core.ioPin" \
    --output-gds "$EXAMPLE_DIR/inverter_core.sky130.pinned.gds" \
    --report "$LABEL_REPORT" \
    --netlist "$EXAMPLE_DIR/inverter_sky130_name_test.sp" \
    --top-cell "inverter_core" \
    --only-top-ports >/dev/null

echo "RUN: add Sky130 pin shapes"
python3 "$SCRIPT_DIR/add_sky130_pin_shapes_from_iopin.py" \
    --input-gds "$EXAMPLE_DIR/inverter_core.sky130.pinned.gds" \
    --iopin "$EXAMPLE_DIR/inverter_core.ioPin" \
    --output-gds "$EXAMPLE_DIR/inverter_core.sky130.pinned_shapes.gds" \
    --report "$SHAPE_REPORT" \
    --netlist "$EXAMPLE_DIR/inverter_sky130_name_test.sp" \
    --top-cell "inverter_core" \
    --only-top-ports >/dev/null

cat > "$DRC_TCL" <<'EOF'
puts "POWER_FIX_DRC: reading pinned-shapes GDS"
gds read examples/inverter_sky130_try/inverter_core.sky130.pinned_shapes.gds
if {[catch {load inverter_core_flat} load_error]} {
    puts stderr "ERROR: failed to load inverter_core_flat"
    puts stderr $load_error
    quit -noprompt
}
drc check
drc count
quit -noprompt
EOF

echo "RUN: Magic DRC on pinned-shapes GDS"
(cd "$REPO_ROOT" && magic -dnull -noconsole -rcfile "$MAGICRC" < "$DRC_TCL" > "$DRC_LOG" 2>&1)

cat > "$MAGIC_TCL" <<'EOF'
puts "POWER_FIX_LVS: reading pinned-shapes GDS"
gds read examples/inverter_sky130_try/inverter_core.sky130.pinned_shapes.gds
if {[catch {load inverter_core_flat} load_error]} {
    puts stderr "ERROR: failed to load inverter_core_flat"
    puts stderr $load_error
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
echo "RUN: Magic extraction on pinned-shapes GDS"
(cd "$REPO_ROOT" && magic -dnull -noconsole -rcfile "$MAGICRC" < "$MAGIC_TCL" > "$MAGIC_LOG" 2>&1)

found_spice=""
for candidate in "$REPO_ROOT/inverter_core_flat.spice" "$REPO_ROOT/inverter_core_flat.sp"; do
    if [[ -f "$candidate" ]]; then
        found_spice="$candidate"
        break
    fi
done
[[ -n "$found_spice" ]] || fail "Magic extraction did not produce inverter_core_flat.spice"
mv "$found_spice" "$EXTRACTED_LVS"
if [[ -f "$REPO_ROOT/inverter_core_flat.ext" ]]; then
    mv "$REPO_ROOT/inverter_core_flat.ext" "$OUT_DIR/inverter_core_flat.ext"
fi

echo "RUN: prepare raw/connectivity LVS netlists"
python3 "$SCRIPT_DIR/prepare_lvs_netlists.py" \
    --source "$EXAMPLE_DIR/inverter_sky130_name_test.sp" \
    --extracted "$EXTRACTED_LVS" \
    --out-dir "$OUT_DIR" \
    --report "$LVS_PREP_REPORT" >/dev/null

echo "RUN: Netgen connectivity LVS"
"$NETGEN_CMD" -batch lvs \
    "$CONNECTIVITY_SOURCE inverter_core" \
    "$CONNECTIVITY_EXTRACTED inverter_core_flat" \
    "$NETGEN_SETUP" \
    "$NETGEN_REPORT" \
    > "$NETGEN_LOG" 2>&1

echo "RUN: analyze LVS result"
python3 "$SCRIPT_DIR/analyze_lvs_result.py" \
    --report "$NETGEN_REPORT" \
    --log "$NETGEN_LOG" \
    --output "$LVS_RESULT_SUMMARY" >/dev/null

echo "RUN: summarize Magic PEX"
python3 "$SCRIPT_DIR/summarize_magic_pex.py" \
    --input "$RAW_EXTRACTED_COPY" \
    --output "$PEX_SUMMARY" >/dev/null

subckt_line="$(grep -E '^[[:space:]]*\.subckt[[:space:]]+inverter_core_flat' "$EXTRACTED_LVS" | head -n 1 || true)"
nmos_line="$(grep -E '^[[:space:]]*[Xx][^[:space:]]+[[:space:]].*sky130_fd_pr__nfet_01v8' "$EXTRACTED_LVS" | head -n 1 || true)"
pmos_line="$(grep -E '^[[:space:]]*[Xx][^[:space:]]+[[:space:]].*sky130_fd_pr__pfet_01v8' "$EXTRACTED_LVS" | head -n 1 || true)"
anon_nodes="$(grep -Eo 'a_[[:alnum:]_]+#|w_[[:alnum:]_]+#' "$EXTRACTED_LVS" | sort -u | paste -sd ', ' - || true)"
[[ -n "$anon_nodes" ]] || anon_nodes="none"
drc_count="$(awk '/Total DRC errors found:/ {print $NF}' "$DRC_LOG" | tail -n 1)"
[[ -n "$drc_count" ]] || drc_count="unknown"
lvs_match="no"
if grep -q "Circuits match uniquely" "$NETGEN_REPORT" && grep -q "Netlists match uniquely" "$NETGEN_REPORT"; then
    lvs_match="yes"
fi
net_renames_used="no"
grep -q 'Net rename enabled: no' "$LVS_PREP_REPORT" || net_renames_used="yes"
pex_caps="$(awk -F': ' '/Parasitic capacitor count:/ {print $2}' "$PEX_SUMMARY" | tail -n 1)"
[[ -n "$pex_caps" ]] || pex_caps="unknown"
vpwr_recognized="no"
vgnd_recognized="no"
grep -q 'add vdd' "$TRIAL_LOG" && vpwr_recognized="yes"
grep -q 'add vss' "$TRIAL_LOG" && vgnd_recognized="yes"

cat > "$SUMMARY" <<EOF
# Sky130 Inverter Power-Net Pipeline Summary

| Item | Result |
| --- | --- |
| VPWR recognized as VDD | $vpwr_recognized |
| VGND recognized as VSS | $vgnd_recognized |
| Raw subckt | \`$subckt_line\` |
| Raw NMOS | \`$nmos_line\` |
| Raw PMOS | \`$pmos_line\` |
| Anonymous extracted nodes | $anon_nodes |
| Magic DRC error count | $drc_count |
| Raw extracted netlist preserved | yes |
| Connectivity LVS status | $lvs_match |
| Net renaming used | $net_renames_used |
| PEX summary status | generated |
| Parasitic capacitor count | $pex_caps |

## Key Outputs

- MAGICAL log: \`$MAGICAL_LOG\`
- MAGICAL trial log: \`$TRIAL_LOG\`
- Power-net config check: \`$POWERNET_CONFIG_REPORT\`
- Pinned-shapes GDS: \`$EXAMPLE_DIR/inverter_core.sky130.pinned_shapes.gds\`
- DRC log: \`$DRC_LOG\`
- Raw extracted netlist: \`$EXTRACTED_LVS\`
- Raw extracted netlist copy: \`$RAW_EXTRACTED_COPY\`
- LVS preparation report: \`$LVS_PREP_REPORT\`
- Connectivity source netlist: \`$CONNECTIVITY_SOURCE\`
- Connectivity extracted netlist: \`$CONNECTIVITY_EXTRACTED\`
- Netgen connectivity LVS report: \`$NETGEN_REPORT\`
- LVS result summary: \`$LVS_RESULT_SUMMARY\`
- PEX summary: \`$PEX_SUMMARY\`
EOF

echo "Summary written: $SUMMARY"
echo "RAW_NMOS=$nmos_line"
echo "ANON_NODES=$anon_nodes"
echo "DRC_COUNT=$drc_count"
echo "CONNECTIVITY_LVS_MATCH=$lvs_match"
echo "NET_RENAMES_USED=$net_renames_used"
echo "PEX_CAPS=$pex_caps"

[[ "$anon_nodes" == "none" ]] || fail "anonymous extracted nodes remain: $anon_nodes"
[[ "$lvs_match" == "yes" ]] || fail "LVS did not match"
