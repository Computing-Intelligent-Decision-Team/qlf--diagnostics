#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOCKER_IMAGE="${DOCKER_IMAGE:-jayl940712/magical:latest}"

DEFAULT_SKY130A="/home/to/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A"
SKY130A="${SKY130A:-$DEFAULT_SKY130A}"
MAGICRC="$SKY130A/libs.tech/magic/sky130A.magicrc"

OUT_DIR="$REPO_ROOT/generated/sky130_native_trial/inverter"
WORK_DIR="$OUT_DIR/work"
BUILD_DIR="$REPO_ROOT/generated/sky130_native_trial/anaroute_build"
BUILD_TEMP="$REPO_ROOT/generated/sky130_native_trial/anaroute_cmake_build"
EXPORT_MAP="$REPO_ROOT/generated/sky130PDK_native_trial/sky130_anaroute_gds_export.map"
SUMMARY="$OUT_DIR/summary.md"
BUILD_LOG="$OUT_DIR/anaroute_build.log"
MAGICAL_LOG="$OUT_DIR/magical_native_export.log"
LAYER_LOG="$OUT_DIR/native_gds_layers.txt"
DRC_TCL="$OUT_DIR/magic_native_drc.tcl"
DRC_LOG="$OUT_DIR/magic_native_drc.log"
EXTRACT_TCL="$OUT_DIR/magic_native_extract.tcl"
EXTRACT_LOG="$OUT_DIR/magic_native_extract.log"
NATIVE_GDS="$OUT_DIR/inverter_core.native.route.gds"
WRITER_REPORT="$NATIVE_GDS.export_map_report.md"

if [[ -d "$REPO_ROOT/generated/sky130_native_trial" && ! -w "$REPO_ROOT/generated/sky130_native_trial" ]]; then
    command -v docker >/dev/null 2>&1 || {
        echo "error: Docker is required to repair generated native trial directory ownership." >&2
        exit 1
    }
    docker run --rm \
        -v "$REPO_ROOT:/MAGICAL" \
        "$DOCKER_IMAGE" \
        bash -lc "chown -R $(id -u):$(id -g) /MAGICAL/generated/sky130_native_trial" >/dev/null 2>&1 || true
fi

mkdir -p "$OUT_DIR" "$WORK_DIR"

fail_summary() {
    local stage="$1"
    local message="$2"
    {
        echo "# Native Sky130 Inverter Export Trial"
        echo
        echo "| Field | Value |"
        echo "| --- | --- |"
        echo "| STATUS | FAIL |"
        echo "| FAILED_STAGE | $stage |"
        echo "| MESSAGE | $message |"
        echo "| EXPORT_MAP | $EXPORT_MAP |"
        echo "| Native route GDS | $NATIVE_GDS |"
    } > "$SUMMARY"
    echo "FAIL[$stage]: $message" >&2
    exit 1
}

require_file() {
    [[ -f "$1" ]] || fail_summary "$2" "required file not found: $1"
}

command -v docker >/dev/null 2>&1 || fail_summary "setup" "Docker is required for MAGICAL placement/routing."
command -v magic >/dev/null 2>&1 || fail_summary "setup" "magic command not found in PATH."
require_file "$MAGICRC" "setup"

echo "RUN: generate Anaroute export map"
python3 "$SCRIPT_DIR/generate_anaroute_gds_export_map.py" >/dev/null || fail_summary "export_map" "failed to generate $EXPORT_MAP"
require_file "$EXPORT_MAP" "export_map"

cp "$REPO_ROOT/examples/inverter_sky130_try/inverter_sky130_name_test.sp" "$WORK_DIR/inverter_sky130_name_test.sp"
cat > "$WORK_DIR/inverter_native_trial.json" <<'JSON'
{
    "spectre_netlist" : "inverter_sky130_name_test.sp",
    "resultDir" : "./",
    "techfile" : "../../../sky130PDK_trial/sky130.techfile",
    "simple_tech_file" : "../../../sky130PDK_trial/sky130.techfile.simple",
    "lef" : "../../../sky130PDK_trial/sky130.lef",
    "vddNetNames" : ["VPWR"],
    "vssNetNames" : ["VGND"]
}
JSON

echo "RUN: build AnaroutePy from current source into generated native trial dir"
docker run --rm \
    -v "$REPO_ROOT:/MAGICAL" \
    "$DOCKER_IMAGE" \
    bash -lc "cd /MAGICAL/anaroute && python3.7 setup.py build_ext --build-lib /MAGICAL/generated/sky130_native_trial/anaroute_build --build-temp /MAGICAL/generated/sky130_native_trial/anaroute_cmake_build" \
    > "$BUILD_LOG" 2>&1 || fail_summary "anaroute_build" "failed to build AnaroutePy; see $BUILD_LOG"
require_file "$BUILD_DIR/anaroutePy.cpython-37m-x86_64-linux-gnu.so" "anaroute_build"

echo "RUN: MAGICAL placement/routing with MAGICAL_GDS_EXPORT_MAP"
docker run --rm \
    -v "$REPO_ROOT:/MAGICAL" \
    "$DOCKER_IMAGE" \
    bash -lc "export PYTHONPATH=/MAGICAL/generated/sky130_native_trial/anaroute_build:/usr/local/lib/python3.7/site-packages:/MAGICAL/flow/python:\${PYTHONPATH:-}; export MAGICAL_GDS_EXPORT_MAP=/MAGICAL/generated/sky130PDK_native_trial/sky130_anaroute_gds_export.map; cd /MAGICAL/generated/sky130_native_trial/inverter/work && rm -rf inverter_core.route.gds inverter_core.place.gds inverter_core.ioPin gds && mkdir -p gds && python3.7 /MAGICAL/flow/python/Magical.py inverter_native_trial.json" \
    > "$MAGICAL_LOG" 2>&1 || fail_summary "magical_native_export" "MAGICAL native export trial failed; see $MAGICAL_LOG"

require_file "$WORK_DIR/inverter_core.route.gds" "magical_native_export"
cp "$WORK_DIR/inverter_core.route.gds" "$NATIVE_GDS"
if [[ -f "$WORK_DIR/inverter_core.route.gds.export_map_report.md" ]]; then
    cp "$WORK_DIR/inverter_core.route.gds.export_map_report.md" "$WRITER_REPORT"
fi

echo "RUN: inspect native GDS layers"
python3 "$SCRIPT_DIR/inspect_gds_layers.py" \
    --gds "$NATIVE_GDS" \
    --export-map "$REPO_ROOT/generated/sky130PDK_trial/sky130_gds_export_map.yaml" \
    --no-report > "$LAYER_LOG" || fail_summary "inspect_layers" "failed to inspect native GDS layers"

python3 - "$REPO_ROOT" "$NATIVE_GDS" <<'PY' || fail_summary "inspect_layers" "native GDS does not contain required Phase 1 Sky130 layer/datatype pairs"
import sys
from pathlib import Path
repo = Path(sys.argv[1])
sys.path.insert(0, str(repo / "tools/sky130_adapter"))
from inspect_gds_layers import inspect_gds

required = {(65, 20), (66, 20), (66, 44), (67, 20), (67, 44), (68, 20)}
uses = {(use.layer, use.datatype) for use in inspect_gds(Path(sys.argv[2]))}
missing = sorted(required - uses)
if missing:
    print(f"missing required pairs: {missing}")
    sys.exit(1)
PY

cat > "$DRC_TCL" <<EOF
puts "SKY130_NATIVE_EXPORT_DRC: reading native route GDS"
gds read generated/sky130_native_trial/inverter/inverter_core.native.route.gds
if {[catch {load inverter_core_flat} load_error]} {
    puts stderr "ERROR: failed to load inverter_core_flat"
    puts stderr \$load_error
    quit -noprompt
}
drc euclidean on
drc style drc(full)
drc check
set count [drc list count total]
puts "SKY130_NATIVE_EXPORT_DRC_COUNT \$count"
quit -noprompt
EOF

echo "RUN: Magic DRC on native route GDS"
set +e
(cd "$REPO_ROOT" && magic -dnull -noconsole -rcfile "$MAGICRC" < "$DRC_TCL" > "$DRC_LOG" 2>&1)
drc_status=$?
set -e
DRC_COUNT="$(grep -Eo 'SKY130_NATIVE_EXPORT_DRC_COUNT [0-9]+' "$DRC_LOG" | awk '{print $2}' | tail -n 1 || true)"
[[ -n "$DRC_COUNT" ]] || DRC_COUNT="unknown"
DRC_GDS_READ_ERRORS="$(grep -c 'Unknown layer/datatype' "$DRC_LOG" || true)"

cat > "$EXTRACT_TCL" <<EOF
puts "SKY130_NATIVE_EXPORT_EXTRACT: reading native route GDS"
gds read generated/sky130_native_trial/inverter/inverter_core.native.route.gds
if {[catch {load inverter_core_flat} load_error]} {
    puts stderr "ERROR: failed to load inverter_core_flat"
    puts stderr \$load_error
    quit -noprompt
}
extract do local
extract all
ext2spice lvs
ext2spice cthresh 0
ext2spice -o generated/sky130_native_trial/inverter/inverter_core_native_extracted.spice
quit -noprompt
EOF

echo "RUN: Magic extraction probe on native route GDS"
set +e
(cd "$REPO_ROOT" && magic -dnull -noconsole -rcfile "$MAGICRC" < "$EXTRACT_TCL" > "$EXTRACT_LOG" 2>&1)
extract_status=$?
set -e
EXTRACT_GDS_READ_ERRORS="$(grep -c 'Unknown layer/datatype' "$EXTRACT_LOG" || true)"

RAW_SUBCKT="$(grep -E '^\\.subckt[[:space:]]+inverter_core_flat' "$OUT_DIR/inverter_core_native_extracted.spice" | head -n 1 || true)"
[[ -n "$RAW_SUBCKT" ]] || RAW_SUBCKT="not_found"

{
    echo "# Native Sky130 Inverter Export Trial"
    echo
    echo "| Field | Value |"
    echo "| --- | --- |"
    echo "| STATUS | PASS |"
    echo "| TOP_CELL | inverter_core |"
    echo "| MAGICAL_GDS_EXPORT_MAP | $EXPORT_MAP |"
    echo "| NATIVE_ROUTE_GDS | $NATIVE_GDS |"
    echo "| WRITER_EXPORT_MAP_REPORT | $WRITER_REPORT |"
    echo "| REMAP_GDS_TO_SKY130_USED | no |"
    echo "| REQUIRED_PHASE1_PAIRS_PRESENT | yes |"
    echo "| MAGIC_DRC_EXIT_STATUS | $drc_status |"
    echo "| MAGIC_DRC_COUNT | $DRC_COUNT |"
    echo "| MAGIC_DRC_GDS_READ_ERRORS | $DRC_GDS_READ_ERRORS |"
    echo "| MAGIC_EXTRACT_EXIT_STATUS | $extract_status |"
    echo "| MAGIC_EXTRACT_GDS_READ_ERRORS | $EXTRACT_GDS_READ_ERRORS |"
    echo "| RAW_SUBCKT | $RAW_SUBCKT |"
    echo
    echo "## Key Outputs"
    echo
    echo "- Build log: \`$BUILD_LOG\`"
    echo "- MAGICAL log: \`$MAGICAL_LOG\`"
    echo "- Layer inspection: \`$LAYER_LOG\`"
    echo "- Magic DRC Tcl/log: \`$DRC_TCL\`, \`$DRC_LOG\`"
    echo "- Magic extraction Tcl/log: \`$EXTRACT_TCL\`, \`$EXTRACT_LOG\`"
} > "$SUMMARY"

echo "Summary written: $SUMMARY"
if [[ "$drc_status" -ne 0 ]]; then
    echo "NOTE: Magic DRC command exited with $drc_status; see $DRC_LOG" >&2
fi
if [[ "$extract_status" -ne 0 ]]; then
    echo "NOTE: Magic extraction command exited with $extract_status; see $EXTRACT_LOG" >&2
fi
