#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOCKER_IMAGE="${DOCKER_IMAGE:-jayl940712/magical:latest}"

LEGACY_DEFAULT_SKY130A="/home/to/.ciel/ciel/sky130/versions/7b70722e33c03fcb5dabcf4d479fb0822d9251c9/sky130A"

resolve_sky130a() {
    if [[ -n "${SKY130A:-}" ]]; then
        echo "$SKY130A"
        return
    fi

    local candidate
    for candidate in \
        "$REPO_ROOT/../Analoggym_opt_moo_Mahalanobis_paper/mosfet_model/sky130_pdk" \
        "$REPO_ROOT/../Analoggym_opt_moo_Mahalanobis_paper/simulation_files/sky130_pdk" \
        "$LEGACY_DEFAULT_SKY130A" \
        "/usr/local/share/pdk/sky130A" \
        "/usr/share/pdk/sky130A" \
        "/opt/pdk/sky130A"
    do
        if [[ -f "$candidate/libs.tech/magic/sky130A.magicrc" && -f "$candidate/libs.tech/netgen/sky130A_setup.tcl" ]]; then
            echo "$candidate"
            return
        fi
    done

    echo "$LEGACY_DEFAULT_SKY130A"
}

SKY130A="$(resolve_sky130a)"
MAGICRC="$SKY130A/libs.tech/magic/sky130A.magicrc"
NETGEN_SETUP="$SKY130A/libs.tech/netgen/sky130A_setup.tcl"

usage() {
    cat <<'EOF'
Usage:
  run_sky130_case_pipeline.sh \
    --case-dir <dir> \
    --top-cell <cell> \
    --magical-netlist <file> \
    --config <file> \
    --vdd <net> \
    --vss <net> \
    --out-dir <dir> \
    [--raw-netlist <file>] \
    [--convert-xschem yes|no] \
    [--case-name <name>] \
    [--output-node <net>]

Paths may be absolute or relative to the repository root. File paths under
--case-dir may be passed as basenames.
EOF
}

CASE_DIR_ARG=""
CASE_NAME=""
TOP_CELL=""
RAW_NETLIST_ARG=""
MAGICAL_NETLIST_ARG=""
CONFIG_ARG=""
VDD_NET=""
VSS_NET=""
OUT_DIR_ARG=""
CONVERT_XSCHEM="no"
OUTPUT_NODE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --case-dir) CASE_DIR_ARG="$2"; shift 2 ;;
        --case-name) CASE_NAME="$2"; shift 2 ;;
        --top-cell) TOP_CELL="$2"; shift 2 ;;
        --raw-netlist) RAW_NETLIST_ARG="$2"; shift 2 ;;
        --magical-netlist) MAGICAL_NETLIST_ARG="$2"; shift 2 ;;
        --config) CONFIG_ARG="$2"; shift 2 ;;
        --vdd) VDD_NET="$2"; shift 2 ;;
        --vss) VSS_NET="$2"; shift 2 ;;
        --out-dir) OUT_DIR_ARG="$2"; shift 2 ;;
        --convert-xschem) CONVERT_XSCHEM="$2"; shift 2 ;;
        --output-node) OUTPUT_NODE="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "error: unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
done

[[ -n "$CASE_DIR_ARG" ]] || { echo "error: --case-dir is required" >&2; exit 2; }
[[ -n "$TOP_CELL" ]] || { echo "error: --top-cell is required" >&2; exit 2; }
[[ -n "$MAGICAL_NETLIST_ARG" ]] || { echo "error: --magical-netlist is required" >&2; exit 2; }
[[ -n "$CONFIG_ARG" ]] || { echo "error: --config is required" >&2; exit 2; }
[[ -n "$VDD_NET" ]] || { echo "error: --vdd is required" >&2; exit 2; }
[[ -n "$VSS_NET" ]] || { echo "error: --vss is required" >&2; exit 2; }
[[ -n "$OUT_DIR_ARG" ]] || { echo "error: --out-dir is required" >&2; exit 2; }
[[ "$CONVERT_XSCHEM" == "yes" || "$CONVERT_XSCHEM" == "no" ]] || { echo "error: --convert-xschem must be yes or no" >&2; exit 2; }

resolve_dir() {
    local path="$1"
    if [[ "$path" = /* ]]; then
        echo "$path"
    else
        echo "$REPO_ROOT/$path"
    fi
}

resolve_case_file() {
    local path="$1"
    if [[ "$path" = /* ]]; then
        echo "$path"
    elif [[ "$path" == */* ]]; then
        echo "$REPO_ROOT/$path"
    else
        echo "$CASE_DIR/$path"
    fi
}

rel_to_repo() {
    local path="$1"
    python3 - "$REPO_ROOT" "$path" <<'PY'
import os
import sys
root, path = sys.argv[1:3]
print(os.path.relpath(path, root))
PY
}

CASE_DIR="$(resolve_dir "$CASE_DIR_ARG")"
OUT_DIR="$(resolve_dir "$OUT_DIR_ARG")"
MAGICAL_NETLIST="$(resolve_case_file "$MAGICAL_NETLIST_ARG")"
CONFIG="$(resolve_case_file "$CONFIG_ARG")"
RAW_NETLIST=""
if [[ -n "$RAW_NETLIST_ARG" ]]; then
    RAW_NETLIST="$(resolve_case_file "$RAW_NETLIST_ARG")"
fi
[[ -n "$CASE_NAME" ]] || CASE_NAME="$TOP_CELL"

MAGIC_CELL="${TOP_CELL}_flat"
SUMMARY="$OUT_DIR/summary.md"
CONVERT_LOG="$OUT_DIR/convert.log"
POWERNET_CONFIG_REPORT="$OUT_DIR/powernet_config_check.md"
PDK_LINE_ENDING_REPORT="$OUT_DIR/pdk_line_endings.txt"
PDK_LINE_ENDING_ERR="$OUT_DIR/pdk_line_endings.err"
MAGICAL_LOG="$OUT_DIR/magical_place_route.log"
MAGICAL_RUN_LOG="$CASE_DIR/run_${TOP_CELL}_trial.log"
REMAP_REPORT="$OUT_DIR/gds_remap_report.md"
LABEL_REPORT="$OUT_DIR/pin_label_report.md"
SHAPE_REPORT="$OUT_DIR/pin_shape_report.md"
LOCAL_POWER_STRIPE_REPORT="$OUT_DIR/local_power_stripe_report.md"
LOCAL_POWER_STRIPE_SUMMARY="$OUT_DIR/local_power_stripe_summary.json"
DRC_TCL="$OUT_DIR/magic_drc.tcl"
DRC_LOG="$OUT_DIR/magic_drc.log"
MAGIC_TCL="$OUT_DIR/magic_extract.tcl"
MAGIC_LOG="$OUT_DIR/magic_extract.log"
EXTRACTED_LVS="$OUT_DIR/${TOP_CELL}_extracted.spice"
LVS_PREP_REPORT="$OUT_DIR/lvs_preparation_report.md"
NETGEN_LOG="$OUT_DIR/netgen_lvs.log"
NETGEN_REPORT="$OUT_DIR/netgen_lvs_report.out"
NETGEN_TCL="$OUT_DIR/netgen_lvs.tcl"
LVS_RESULT_SUMMARY="$OUT_DIR/lvs_result_summary.md"
PEX_SUMMARY="$OUT_DIR/pex_summary.md"
MAGICAL_SANITIZE_PLACE_GDS_FOR_ROUTER="${MAGICAL_SANITIZE_PLACE_GDS_FOR_ROUTER:-0}"
MAGICAL_SKIP_ROUTER_PARSE_GDS="${MAGICAL_SKIP_ROUTER_PARSE_GDS:-0}"
MAGICAL_SKIP_TOP_POWER_ROUTE="${MAGICAL_SKIP_TOP_POWER_ROUTE:-0}"
MAGICAL_POWER_STRIPE_EXTRA_GRID="${MAGICAL_POWER_STRIPE_EXTRA_GRID:-0}"
MAGICAL_POWER_STRIPE_EXTRA_DBU="${MAGICAL_POWER_STRIPE_EXTRA_DBU:-0}"
MAGICAL_DISABLE_POWER_STRIPE="${MAGICAL_DISABLE_POWER_STRIPE:-0}"
MAGICAL_SPLIT_POWER_STRIPE_AROUND_PASSIVES="${MAGICAL_SPLIT_POWER_STRIPE_AROUND_PASSIVES:-0}"
MAGICAL_POWER_STRIPE_PASSIVE_KEEP_OUT_DBU="${MAGICAL_POWER_STRIPE_PASSIVE_KEEP_OUT_DBU:-400}"
MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_LAYERS="${MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_LAYERS:-}"
MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_MARGIN_DBU="${MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_MARGIN_DBU:-400}"
MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_LAYERS="${MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_LAYERS:-$MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_LAYERS}"
MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_BOX_DBU="${MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_BOX_DBU:-}"
MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_MARGIN_DBU="${MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_MARGIN_DBU:-0}"
MAGICAL_PASSIVE_PLACEMENT_OFFSET_X_DBU="${MAGICAL_PASSIVE_PLACEMENT_OFFSET_X_DBU:-0}"
MAGICAL_PASSIVE_PLACEMENT_OFFSET_Y_DBU="${MAGICAL_PASSIVE_PLACEMENT_OFFSET_Y_DBU:-0}"
MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES="${MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES:-0}"
MAGICAL_LOCAL_VDD_STRIPE_HEIGHT_DBU="${MAGICAL_LOCAL_VDD_STRIPE_HEIGHT_DBU:-400}"
MAGICAL_LOCAL_VDD_STRIPE_Y_DBU="${MAGICAL_LOCAL_VDD_STRIPE_Y_DBU:-}"
MAGICAL_LOCAL_VDD_STRIPE_ACTIVE_KEEP_OUT_DBU="${MAGICAL_LOCAL_VDD_STRIPE_ACTIVE_KEEP_OUT_DBU:-0}"
MAGICAL_LOCAL_VDD_STRIPE_EXCLUDE_X_DBU="${MAGICAL_LOCAL_VDD_STRIPE_EXCLUDE_X_DBU:-}"
MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE="${MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE:-0}"
MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_BOX_DBU="${MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_BOX_DBU:-}"
MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_EXCLUDE_X_DBU="${MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_EXCLUDE_X_DBU:-}"
MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_AUTO_EXCLUDE="${MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_AUTO_EXCLUDE:-1}"
MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_AUTO_EXCLUDE_MARGIN_DBU="${MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_AUTO_EXCLUDE_MARGIN_DBU:-100}"
LAYOUT_INPUT_MODE="source"
LAYOUT_PROJECTION_CASE_DIR=""
LAYOUT_PROJECTION_CONFIG=""
LAYOUT_PROJECTION_NETLIST=""
LAYOUT_PROJECTION_DROPPED_PASSIVES="0"

mkdir -p "$OUT_DIR"

summary_fail() {
    local stage="$1"
    local message="$2"
    {
        echo "# Sky130 Case Pipeline Summary"
        echo
        echo "| Field | Value |"
        echo "| --- | --- |"
        echo "| CASE_NAME | $CASE_NAME |"
        echo "| TOP_CELL | $TOP_CELL |"
        echo "| VDD_NET | $VDD_NET |"
        echo "| VSS_NET | $VSS_NET |"
        echo "| SKY130A | $SKY130A |"
        echo "| STATUS | FAIL |"
        echo "| FAILED_STAGE | $stage |"
        echo "| MESSAGE | $message |"
    } > "$SUMMARY"
    echo "FAIL[$stage]: $message" >&2
    exit 1
}

require_file() {
    [[ -f "$1" ]] || summary_fail "$2" "required file not found: $1"
}

summary_field() {
    local path="$1"
    local field="$2"
    awk -F'|' -v key="$field" '
        function trim(s) {
            gsub(/^[ \t]+|[ \t]+$/, "", s)
            return s
        }
        NF >= 3 {
            name = trim($2)
            value = trim($3)
            if (name == key) {
                print value
                exit
            }
        }
    ' "$path"
}

command -v docker >/dev/null 2>&1 || summary_fail "setup" "Docker is required for MAGICAL placement/routing stage."
command -v magic >/dev/null 2>&1 || summary_fail "setup" "magic command not found in PATH"

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
    summary_fail "setup" "IC netgen-lvs not found in PATH; install netgen-lvs or provide an IC Netgen 1.x command."
fi

require_file "$CONFIG" "setup"
set +e
CONNECTIVITY_LVS_PROJECTION="$(python3 "$SCRIPT_DIR/sky130_case_pipeline_helpers.py" connectivity-projection --config "$CONFIG" 2>"$OUT_DIR/connectivity_projection_config.err")"
projection_config_status=$?
python3 "$SCRIPT_DIR/sky130_case_pipeline_helpers.py" lvs-renames --config "$CONFIG" > "$OUT_DIR/lvs_renames.txt" 2>"$OUT_DIR/lvs_renames.err"
renames_config_status=$?
EXPERIMENTAL_PASSIVE_REMAP="$(python3 "$SCRIPT_DIR/sky130_case_pipeline_helpers.py" experimental-passive-remap --config "$CONFIG" 2>"$OUT_DIR/experimental_passive_remap.err")"
passive_remap_config_status=$?
set -e
if [[ "$projection_config_status" -ne 0 ]]; then
    summary_fail "setup" "invalid connectivityLvsProjection config; see $OUT_DIR/connectivity_projection_config.err"
fi
if [[ "$renames_config_status" -ne 0 ]]; then
    summary_fail "setup" "invalid lvsNetRenames config; see $OUT_DIR/lvs_renames.err"
fi
if [[ "$passive_remap_config_status" -ne 0 ]]; then
    summary_fail "setup" "invalid experimentalPassiveRemap config; see $OUT_DIR/experimental_passive_remap.err"
fi
mapfile -t LVS_RENAMES < "$OUT_DIR/lvs_renames.txt"

require_file "$MAGICRC" "setup"
require_file "$NETGEN_SETUP" "setup"
if [[ "$CONVERT_XSCHEM" == "yes" ]]; then
    [[ -n "$RAW_NETLIST" ]] || summary_fail "setup" "--raw-netlist is required when --convert-xschem yes"
    require_file "$RAW_NETLIST" "setup"
else
    require_file "$MAGICAL_NETLIST" "setup"
fi

if [[ "$CONVERT_XSCHEM" == "yes" ]]; then
    echo "RUN: convert xschem Sky130 netlist"
    python3 "$SCRIPT_DIR/convert_xschem_sky130_netlist.py" \
        --input "$RAW_NETLIST" \
        --output "$MAGICAL_NETLIST" \
        --global-port "$VSS_NET" \
        > "$CONVERT_LOG" 2>&1 || summary_fail "convert" "xschem-to-MAGICAL conversion failed; see $CONVERT_LOG"
fi
require_file "$MAGICAL_NETLIST" "setup"

echo "RUN: check explicit power-net config"
set +e
python3 "$SCRIPT_DIR/sky130_case_pipeline_helpers.py" check-power-nets \
    --config "$CONFIG" \
    --vdd "$VDD_NET" \
    --vss "$VSS_NET" \
    > "$POWERNET_CONFIG_REPORT" 2>&1
power_check_status=$?
set -e
if [[ "$power_check_status" -ne 0 ]]; then
    summary_fail "power_config" "config does not contain requested vddNetNames/vssNetNames; see $POWERNET_CONFIG_REPORT"
fi

if [[ "${SKY130_LVS_PROJECTION_RUN:-0}" != "1" && "$CONNECTIVITY_LVS_PROJECTION" == "mos_only" ]]; then
    echo "RUN: prepare MOS-only layout input projection"
    LAYOUT_PROJECTION_CASE_DIR="$OUT_DIR/layout_mos_projection_case"
    LAYOUT_PROJECTION_CONFIG_NAME="layout_mos_projection.json"
    LAYOUT_PROJECTION_NETLIST_NAME="${TOP_CELL}_layout_mos_only.sp"
    LAYOUT_PROJECTION_SETUP_LOG="$OUT_DIR/layout_mos_projection_setup.log"

    rm -rf "$LAYOUT_PROJECTION_CASE_DIR"
    mkdir -p "$LAYOUT_PROJECTION_CASE_DIR"
    python3 "$SCRIPT_DIR/sky130_case_pipeline_helpers.py" write-mos-projection \
        --source "$MAGICAL_NETLIST" \
        --config "$CONFIG" \
        --case-dir "$LAYOUT_PROJECTION_CASE_DIR" \
        --netlist-name "$LAYOUT_PROJECTION_NETLIST_NAME" \
        --config-name "$LAYOUT_PROJECTION_CONFIG_NAME" \
        > "$LAYOUT_PROJECTION_SETUP_LOG" \
        || summary_fail "layout_mos_projection_setup" "failed to generate MOS-only layout case; see $LAYOUT_PROJECTION_SETUP_LOG"

    LAYOUT_PROJECTION_DROPPED_PASSIVES="$(awk -F= '/^dropped_passives=/ {print $2}' "$LAYOUT_PROJECTION_SETUP_LOG" | tail -n 1)"
    [[ -n "$LAYOUT_PROJECTION_DROPPED_PASSIVES" ]] || LAYOUT_PROJECTION_DROPPED_PASSIVES="unknown"
    LAYOUT_PROJECTION_NETLIST="$LAYOUT_PROJECTION_CASE_DIR/$LAYOUT_PROJECTION_NETLIST_NAME"
    LAYOUT_PROJECTION_CONFIG="$LAYOUT_PROJECTION_CASE_DIR/$LAYOUT_PROJECTION_CONFIG_NAME"
    CASE_DIR="$LAYOUT_PROJECTION_CASE_DIR"
    MAGICAL_NETLIST="$LAYOUT_PROJECTION_NETLIST"
    CONFIG="$LAYOUT_PROJECTION_CONFIG"
    MAGICAL_RUN_LOG="$CASE_DIR/run_${TOP_CELL}_trial.log"
    LAYOUT_INPUT_MODE="mos_only_projection"
fi

echo "RUN: validate MAGICAL PDK line endings"
set +e
python3 "$SCRIPT_DIR/sky130_case_pipeline_helpers.py" pdk-line-endings \
    --config "$CONFIG" \
    > "$PDK_LINE_ENDING_REPORT" 2>"$PDK_LINE_ENDING_ERR"
pdk_line_ending_status=$?
set -e
if [[ "$pdk_line_ending_status" -ne 0 ]]; then
    summary_fail "setup" "invalid MAGICAL PDK techfile/LEF paths or CRLF line endings; CRLF breaks Anaroute parseTechfile/parseGds; see $PDK_LINE_ENDING_REPORT and $PDK_LINE_ENDING_ERR"
fi

CASE_REL="$(rel_to_repo "$CASE_DIR")"
CONFIG_BASE="$(basename "$CONFIG")"

echo "RUN: MAGICAL placement/routing in Docker"
docker run --rm \
    -v "$REPO_ROOT:/MAGICAL" \
    -e MAGICAL_SANITIZE_PLACE_GDS_FOR_ROUTER="$MAGICAL_SANITIZE_PLACE_GDS_FOR_ROUTER" \
    -e MAGICAL_SKIP_ROUTER_PARSE_GDS="$MAGICAL_SKIP_ROUTER_PARSE_GDS" \
    -e MAGICAL_SKIP_TOP_POWER_ROUTE="$MAGICAL_SKIP_TOP_POWER_ROUTE" \
    -e MAGICAL_POWER_STRIPE_EXTRA_GRID="$MAGICAL_POWER_STRIPE_EXTRA_GRID" \
    -e MAGICAL_POWER_STRIPE_EXTRA_DBU="$MAGICAL_POWER_STRIPE_EXTRA_DBU" \
    -e MAGICAL_DISABLE_POWER_STRIPE="$MAGICAL_DISABLE_POWER_STRIPE" \
    -e MAGICAL_SPLIT_POWER_STRIPE_AROUND_PASSIVES="$MAGICAL_SPLIT_POWER_STRIPE_AROUND_PASSIVES" \
    -e MAGICAL_POWER_STRIPE_PASSIVE_KEEP_OUT_DBU="$MAGICAL_POWER_STRIPE_PASSIVE_KEEP_OUT_DBU" \
    -e MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_LAYERS="$MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_LAYERS" \
    -e MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_MARGIN_DBU="$MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_MARGIN_DBU" \
    -e MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_LAYERS="$MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_LAYERS" \
    -e MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_BOX_DBU="$MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_BOX_DBU" \
    -e MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_MARGIN_DBU="$MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_MARGIN_DBU" \
    -e MAGICAL_PASSIVE_PLACEMENT_OFFSET_X_DBU="$MAGICAL_PASSIVE_PLACEMENT_OFFSET_X_DBU" \
    -e MAGICAL_PASSIVE_PLACEMENT_OFFSET_Y_DBU="$MAGICAL_PASSIVE_PLACEMENT_OFFSET_Y_DBU" \
    -e MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES="$MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES" \
    -e MAGICAL_LOCAL_VDD_STRIPE_HEIGHT_DBU="$MAGICAL_LOCAL_VDD_STRIPE_HEIGHT_DBU" \
    -e MAGICAL_LOCAL_VDD_STRIPE_Y_DBU="$MAGICAL_LOCAL_VDD_STRIPE_Y_DBU" \
    -e MAGICAL_LOCAL_VDD_STRIPE_ACTIVE_KEEP_OUT_DBU="$MAGICAL_LOCAL_VDD_STRIPE_ACTIVE_KEEP_OUT_DBU" \
    -e MAGICAL_LOCAL_VDD_STRIPE_EXCLUDE_X_DBU="$MAGICAL_LOCAL_VDD_STRIPE_EXCLUDE_X_DBU" \
    "$DOCKER_IMAGE" \
    bash -lc "export PYTHONPATH=/usr/local/lib/python3.7/site-packages:/MAGICAL/flow/python:\${PYTHONPATH:-}; cd /MAGICAL/${CASE_REL} && rm -rf ${TOP_CELL}.route.gds ${TOP_CELL}.place.gds ${TOP_CELL}.ioPin gds && mkdir -p gds && python3.7 /MAGICAL/flow/python/Magical.py ${CONFIG_BASE} > run_${TOP_CELL}_trial.log 2>&1" \
    > "$MAGICAL_LOG" 2>&1 || summary_fail "magical_place_route" "MAGICAL failed; see $MAGICAL_LOG and $MAGICAL_RUN_LOG"

ROUTE_GDS="$CASE_DIR/${TOP_CELL}.route.gds"
IOPIN="$CASE_DIR/${TOP_CELL}.ioPin"
SKY130_GDS="$CASE_DIR/${TOP_CELL}.sky130.gds"
PINNED_GDS="$CASE_DIR/${TOP_CELL}.sky130.pinned.gds"
PINNED_SHAPES_GDS="$CASE_DIR/${TOP_CELL}.sky130.pinned_shapes.gds"
ARTIFACT_MAGICAL_RUN_LOG="$OUT_DIR/run_${TOP_CELL}_trial.log"
ARTIFACT_IOPIN="$OUT_DIR/${TOP_CELL}.ioPin"
ARTIFACT_ROUTE_GDS="$OUT_DIR/${TOP_CELL}.route.gds"
ARTIFACT_SKY130_GDS="$OUT_DIR/${TOP_CELL}.sky130.gds"
ARTIFACT_PINNED_GDS="$OUT_DIR/${TOP_CELL}.sky130.pinned.gds"
ARTIFACT_PINNED_SHAPES_GDS="$OUT_DIR/${TOP_CELL}.sky130.pinned_shapes.gds"
ARTIFACT_GENERATED_GDS_DIR="$OUT_DIR/gds"

require_file "$ROUTE_GDS" "magical_output"
require_file "$IOPIN" "magical_output"
if [[ -f "$MAGICAL_RUN_LOG" ]]; then
    cp "$MAGICAL_RUN_LOG" "$ARTIFACT_MAGICAL_RUN_LOG"
fi

echo "RUN: remap GDS"
remap_args=(
    --input-gds "$ROUTE_GDS"
    --output-gds "$SKY130_GDS"
    --report "$REMAP_REPORT"
)
if [[ "$EXPERIMENTAL_PASSIVE_REMAP" == "yes" ]]; then
    remap_args+=(--allow-experimental)
fi
python3 "$SCRIPT_DIR/remap_gds_to_sky130.py" "${remap_args[@]}" >/dev/null || summary_fail "gds_remap" "GDS remap failed"

echo "RUN: add Sky130 pin labels"
python3 "$SCRIPT_DIR/add_sky130_pin_labels_from_iopin.py" \
    --input-gds "$SKY130_GDS" \
    --iopin "$IOPIN" \
    --output-gds "$PINNED_GDS" \
    --report "$LABEL_REPORT" \
    --cell "$MAGIC_CELL" \
    --netlist "$MAGICAL_NETLIST" \
    --top-cell "$TOP_CELL" \
    --only-top-ports >/dev/null || summary_fail "pin_labels" "pin label postprocess failed"

echo "RUN: add Sky130 pin shapes"
python3 "$SCRIPT_DIR/add_sky130_pin_shapes_from_iopin.py" \
    --input-gds "$PINNED_GDS" \
    --iopin "$IOPIN" \
    --output-gds "$PINNED_SHAPES_GDS" \
    --report "$SHAPE_REPORT" \
    --cell "$MAGIC_CELL" \
    --netlist "$MAGICAL_NETLIST" \
    --top-cell "$TOP_CELL" \
    --only-top-ports >/dev/null || summary_fail "pin_shapes" "pin shape postprocess failed"

if [[ "$MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE" == "1" ]]; then
    [[ -n "$MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_BOX_DBU" ]] || summary_fail "local_power_stripe" "MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_BOX_DBU is required"
    echo "RUN: add post-route local VDD stripe"
    POST_ROUTE_PINNED_SHAPES_GDS="$CASE_DIR/${TOP_CELL}.sky130.pinned_shapes.local_power.gds"
    local_power_args=(
        --input-gds "$PINNED_SHAPES_GDS"
        --output-gds "$POST_ROUTE_PINNED_SHAPES_GDS"
        --cell "$MAGIC_CELL"
        --net "$VDD_NET"
        --box "$MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_BOX_DBU"
        --exclude-x "$MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_EXCLUDE_X_DBU"
        --auto-exclude-margin-dbu "$MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_AUTO_EXCLUDE_MARGIN_DBU"
        --report "$LOCAL_POWER_STRIPE_REPORT"
        --summary-json "$LOCAL_POWER_STRIPE_SUMMARY"
    )
    if [[ "$MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_AUTO_EXCLUDE" == "1" ]]; then
        local_power_args+=(--auto-exclude-same-layer-crossings)
    fi
    python3 "$SCRIPT_DIR/add_local_power_stripe_to_gds.py" "${local_power_args[@]}" >/dev/null || summary_fail "local_power_stripe" "post-route local power stripe injection failed"
    PINNED_SHAPES_GDS="$POST_ROUTE_PINNED_SHAPES_GDS"
fi

cp "$IOPIN" "$ARTIFACT_IOPIN"
cp "$ROUTE_GDS" "$ARTIFACT_ROUTE_GDS"
cp "$SKY130_GDS" "$ARTIFACT_SKY130_GDS"
cp "$PINNED_GDS" "$ARTIFACT_PINNED_GDS"
cp "$PINNED_SHAPES_GDS" "$ARTIFACT_PINNED_SHAPES_GDS"
if [[ -d "$CASE_DIR/gds" ]]; then
    rm -rf "$ARTIFACT_GENERATED_GDS_DIR"
    cp -R "$CASE_DIR/gds" "$ARTIFACT_GENERATED_GDS_DIR"
fi

PINNED_SHAPES_REL="$(rel_to_repo "$ARTIFACT_PINNED_SHAPES_GDS")"

cat > "$DRC_TCL" <<EOF
puts "SKY130_CASE_DRC: reading pinned-shapes GDS"
gds read $PINNED_SHAPES_REL
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
(cd "$REPO_ROOT" && magic -dnull -noconsole -rcfile "$MAGICRC" < "$DRC_TCL" > "$DRC_LOG" 2>&1) || summary_fail "magic_drc" "Magic DRC command failed; see $DRC_LOG"

drc_count="$(awk '/Total DRC errors found:/ {print $NF}' "$DRC_LOG" | tail -n 1)"
[[ -n "$drc_count" ]] || drc_count="unknown"

if [[ "${SKY130_LVS_PROJECTION_RUN:-0}" != "1" && "$CONNECTIVITY_LVS_PROJECTION" == "mos_only" ]]; then
    echo "RUN: MOS-only connectivity LVS projection"
    PROJECTION_CASE_DIR="$OUT_DIR/lvs_mos_projection_case"
    PROJECTION_OUT_DIR="$OUT_DIR/lvs_mos_projection"
    PROJECTION_RUN_LOG="$OUT_DIR/lvs_mos_projection_pipeline.log"
    PROJECTION_CONFIG_NAME="mos_only_projection.json"
    PROJECTION_NETLIST_NAME="${TOP_CELL}_mos_only.sp"

    rm -rf "$PROJECTION_CASE_DIR" "$PROJECTION_OUT_DIR"
    mkdir -p "$PROJECTION_CASE_DIR" "$PROJECTION_OUT_DIR"
    python3 "$SCRIPT_DIR/sky130_case_pipeline_helpers.py" write-mos-projection \
        --source "$MAGICAL_NETLIST" \
        --config "$CONFIG" \
        --case-dir "$PROJECTION_CASE_DIR" \
        --netlist-name "$PROJECTION_NETLIST_NAME" \
        --config-name "$PROJECTION_CONFIG_NAME" \
        > "$OUT_DIR/lvs_mos_projection_setup.log" \
        || summary_fail "mos_only_projection_setup" "failed to generate MOS-only projection case; see $OUT_DIR/lvs_mos_projection_setup.log"

    projection_case_rel="$(rel_to_repo "$PROJECTION_CASE_DIR")"
    projection_out_rel="$(rel_to_repo "$PROJECTION_OUT_DIR")"
    projection_args=(
        --case-name "${CASE_NAME}_mos_lvs_projection"
        --case-dir "$projection_case_rel"
        --top-cell "$TOP_CELL"
        --magical-netlist "$PROJECTION_NETLIST_NAME"
        --config "$PROJECTION_CONFIG_NAME"
        --vdd "$VDD_NET"
        --vss "$VSS_NET"
        --out-dir "$projection_out_rel"
        --convert-xschem no
    )
    if [[ -n "$OUTPUT_NODE" ]]; then
        projection_args+=(--output-node "$OUTPUT_NODE")
    fi

    set +e
    SKY130_LVS_PROJECTION_RUN=1 "$SCRIPT_DIR/run_sky130_case_pipeline.sh" "${projection_args[@]}" > "$PROJECTION_RUN_LOG" 2>&1
    projection_status=$?
    set -e
    if [[ "$projection_status" -ne 0 ]]; then
        summary_fail "mos_only_projection_lvs" "MOS-only projection pipeline failed; see $PROJECTION_RUN_LOG"
    fi

    projection_summary="$PROJECTION_OUT_DIR/summary.md"
    require_file "$projection_summary" "mos_only_projection_lvs"
    projection_lvs_match="$(summary_field "$projection_summary" CONNECTIVITY_LVS_MATCH)"
    if [[ "$projection_lvs_match" != "yes" ]]; then
        summary_fail "mos_only_projection_lvs" "MOS-only projection LVS did not pass; see $projection_summary"
    fi

    raw_subckt_ports="$(summary_field "$projection_summary" RAW_SUBCKT_PORTS)"
    [[ -n "$raw_subckt_ports" ]] || raw_subckt_ports="unknown"
    anon_nodes="$(summary_field "$projection_summary" ANONYMOUS_NODES)"
    [[ -n "$anon_nodes" ]] || anon_nodes="unknown"
    netgen_status="$(summary_field "$projection_summary" NETGEN_EXIT_STATUS)"
    [[ -n "$netgen_status" ]] || netgen_status="unknown"
    net_renames_used="$(summary_field "$projection_summary" NET_RENAMES_USED)"
    [[ -n "$net_renames_used" ]] || net_renames_used="unknown"
    pex_caps="$(summary_field "$projection_summary" PEX_CAPS)"
    [[ -n "$pex_caps" ]] || pex_caps="unknown"
    pex_total="$(summary_field "$projection_summary" PEX_TOTAL_CAP_FF)"
    [[ -n "$pex_total" ]] || pex_total="unknown"

    cat > "$SUMMARY" <<EOF
# Sky130 Case Pipeline Summary

| Field | Value |
| --- | --- |
| CASE_NAME | $CASE_NAME |
| TOP_CELL | $TOP_CELL |
| VDD_NET | $VDD_NET |
| VSS_NET | $VSS_NET |
| SKY130A | $SKY130A |
| MAGICAL_RESULT | pass |
| LAYOUT_INPUT_MODE | $LAYOUT_INPUT_MODE |
| LAYOUT_PROJECTION_DROPPED_PASSIVES | $LAYOUT_PROJECTION_DROPPED_PASSIVES |
| MAGICAL_SANITIZE_PLACE_GDS_FOR_ROUTER | $MAGICAL_SANITIZE_PLACE_GDS_FOR_ROUTER |
| MAGICAL_SKIP_ROUTER_PARSE_GDS | $MAGICAL_SKIP_ROUTER_PARSE_GDS |
| MAGICAL_SKIP_TOP_POWER_ROUTE | $MAGICAL_SKIP_TOP_POWER_ROUTE |
| MAGICAL_POWER_STRIPE_EXTRA_GRID | $MAGICAL_POWER_STRIPE_EXTRA_GRID |
| MAGICAL_POWER_STRIPE_EXTRA_DBU | $MAGICAL_POWER_STRIPE_EXTRA_DBU |
| MAGICAL_DISABLE_POWER_STRIPE | $MAGICAL_DISABLE_POWER_STRIPE |
| MAGICAL_SPLIT_POWER_STRIPE_AROUND_PASSIVES | $MAGICAL_SPLIT_POWER_STRIPE_AROUND_PASSIVES |
| MAGICAL_POWER_STRIPE_PASSIVE_KEEP_OUT_DBU | $MAGICAL_POWER_STRIPE_PASSIVE_KEEP_OUT_DBU |
| MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_LAYERS | ${MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_LAYERS:-none} |
| MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_MARGIN_DBU | $MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_MARGIN_DBU |
| MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_LAYERS | ${MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_LAYERS:-none} |
| MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_BOX_DBU | ${MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_BOX_DBU:-none} |
| MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_MARGIN_DBU | $MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_MARGIN_DBU |
| MAGICAL_PASSIVE_PLACEMENT_OFFSET_X_DBU | $MAGICAL_PASSIVE_PLACEMENT_OFFSET_X_DBU |
| MAGICAL_PASSIVE_PLACEMENT_OFFSET_Y_DBU | $MAGICAL_PASSIVE_PLACEMENT_OFFSET_Y_DBU |
| MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES | $MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES |
| MAGICAL_LOCAL_VDD_STRIPE_HEIGHT_DBU | $MAGICAL_LOCAL_VDD_STRIPE_HEIGHT_DBU |
| MAGICAL_LOCAL_VDD_STRIPE_Y_DBU | ${MAGICAL_LOCAL_VDD_STRIPE_Y_DBU:-auto} |
| MAGICAL_LOCAL_VDD_STRIPE_ACTIVE_KEEP_OUT_DBU | $MAGICAL_LOCAL_VDD_STRIPE_ACTIVE_KEEP_OUT_DBU |
| MAGICAL_LOCAL_VDD_STRIPE_EXCLUDE_X_DBU | ${MAGICAL_LOCAL_VDD_STRIPE_EXCLUDE_X_DBU:-none} |
| MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE | $MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE |
| MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_BOX_DBU | ${MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_BOX_DBU:-none} |
| MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_EXCLUDE_X_DBU | ${MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_EXCLUDE_X_DBU:-none} |
| MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_AUTO_EXCLUDE | $MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_AUTO_EXCLUDE |
| MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_AUTO_EXCLUDE_MARGIN_DBU | $MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_AUTO_EXCLUDE_MARGIN_DBU |
| GDS_REMAP_RESULT | pass |
| EXPERIMENTAL_PASSIVE_REMAP | $EXPERIMENTAL_PASSIVE_REMAP |
| PIN_LABEL_RESULT | pass |
| PIN_SHAPE_RESULT | pass |
| DRC_COUNT | $drc_count |
| LVS_MODE | mos_only_projection |
| RAW_SUBCKT_PORTS | $raw_subckt_ports |
| ANONYMOUS_NODES | $anon_nodes |
| CONNECTIVITY_LVS_MATCH | yes |
| NETGEN_EXIT_STATUS | $netgen_status |
| NET_RENAMES_USED | $net_renames_used |
| PEX_CAPS | $pex_caps |
| PEX_TOTAL_CAP_FF | $pex_total |
| PEX_OUTPUT_NODE | ${OUTPUT_NODE:-none} |

## KEY_OUTPUTS

- Case directory: \`$CASE_DIR\`
- Source/MAGICAL netlist: \`$MAGICAL_NETLIST\`
- Config: \`$CONFIG\`
- Layout projection case directory: \`$LAYOUT_PROJECTION_CASE_DIR\`
- Layout projection netlist: \`$LAYOUT_PROJECTION_NETLIST\`
- Layout projection config: \`$LAYOUT_PROJECTION_CONFIG\`
- MAGICAL log: \`$MAGICAL_LOG\`
- MAGICAL run log: \`$ARTIFACT_MAGICAL_RUN_LOG\`
- ioPin: \`$ARTIFACT_IOPIN\`
- Route GDS: \`$ARTIFACT_ROUTE_GDS\`
- Sky130 remapped GDS: \`$ARTIFACT_SKY130_GDS\`
- Pinned-shapes GDS: \`$ARTIFACT_PINNED_SHAPES_GDS\`
- Generated GDS directory: \`$ARTIFACT_GENERATED_GDS_DIR\`
- DRC log: \`$DRC_LOG\`
- MOS-only projection setup: \`$OUT_DIR/lvs_mos_projection_setup.log\`
- MOS-only projection run log: \`$PROJECTION_RUN_LOG\`
- MOS-only projection case directory: \`$PROJECTION_CASE_DIR\`
- MOS-only projection output directory: \`$PROJECTION_OUT_DIR\`
- MOS-only projection summary: \`$projection_summary\`
EOF

    echo "Summary written: $SUMMARY"
    echo "CASE_NAME=$CASE_NAME"
    echo "TOP_CELL=$TOP_CELL"
    echo "LVS_MODE=mos_only_projection"
    echo "RAW_SUBCKT_PORTS=$raw_subckt_ports"
    echo "ANONYMOUS_NODES=$anon_nodes"
    echo "DRC_COUNT=$drc_count"
    echo "CONNECTIVITY_LVS_MATCH=yes"
    echo "NET_RENAMES_USED=$net_renames_used"
    echo "PEX_CAPS=$pex_caps"
    echo "PEX_TOTAL_CAP_FF=$pex_total"
    exit 0
fi

cat > "$MAGIC_TCL" <<EOF
puts "SKY130_CASE_LVS: reading pinned-shapes GDS"
gds read $PINNED_SHAPES_REL
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
(cd "$REPO_ROOT" && magic -dnull -noconsole -rcfile "$MAGICRC" < "$MAGIC_TCL" > "$MAGIC_LOG" 2>&1) || summary_fail "magic_extract" "Magic extraction command failed; see $MAGIC_LOG"

found_spice=""
for candidate in "$REPO_ROOT/${MAGIC_CELL}.spice" "$REPO_ROOT/${MAGIC_CELL}.sp"; do
    if [[ -f "$candidate" ]]; then
        found_spice="$candidate"
        break
    fi
done
[[ -n "$found_spice" ]] || summary_fail "magic_extract" "Magic did not produce ${MAGIC_CELL}.spice"
mv "$found_spice" "$EXTRACTED_LVS"
if [[ -f "$REPO_ROOT/${MAGIC_CELL}.ext" ]]; then
    mv "$REPO_ROOT/${MAGIC_CELL}.ext" "$OUT_DIR/${MAGIC_CELL}.ext"
fi

echo "RUN: prepare raw/connectivity LVS netlists"
lvs_prepare_args=(
    --source "$MAGICAL_NETLIST"
    --extracted "$EXTRACTED_LVS"
    --out-dir "$OUT_DIR"
    --prefix "$TOP_CELL"
    --report "$LVS_PREP_REPORT"
)
for rename in "${LVS_RENAMES[@]}"; do
    lvs_prepare_args+=(--rename "$rename")
done
python3 "$SCRIPT_DIR/prepare_lvs_netlists.py" "${lvs_prepare_args[@]}" >/dev/null || summary_fail "lvs_prepare" "LVS preparation failed"

CONNECTIVITY_SOURCE="$OUT_DIR/${TOP_CELL}_source.connectivity.spice"
CONNECTIVITY_EXTRACTED="$OUT_DIR/${TOP_CELL}_extracted.connectivity.spice"
RAW_EXTRACTED_COPY="$OUT_DIR/${TOP_CELL}_extracted.raw.spice"

echo "RUN: Netgen connectivity LVS"
cat > "$NETGEN_TCL" <<EOF
lvs {$CONNECTIVITY_SOURCE $TOP_CELL} {$CONNECTIVITY_EXTRACTED $MAGIC_CELL} {$NETGEN_SETUP} {$NETGEN_REPORT}
quit
EOF
set +e
"$NETGEN_CMD" -batch source "$NETGEN_TCL" > "$NETGEN_LOG" 2>&1
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
pex_args=(
    --input "$RAW_EXTRACTED_COPY"
    --output "$PEX_SUMMARY"
)
if [[ -n "$OUTPUT_NODE" ]]; then
    pex_args+=(--output-node "$OUTPUT_NODE")
fi
python3 "$SCRIPT_DIR/summarize_magic_pex.py" "${pex_args[@]}" >/dev/null || summary_fail "pex_summary" "PEX summary failed"

subckt_line="$(grep -E "^[[:space:]]*\\.subckt[[:space:]]+${MAGIC_CELL}" "$EXTRACTED_LVS" | head -n 1 || true)"
raw_subckt_ports="$(python3 "$SCRIPT_DIR/sky130_case_pipeline_helpers.py" subckt-ports --line "$subckt_line")"
anon_nodes="$(grep -Eo 'a_[[:alnum:]_]+#|w_[[:alnum:]_]+#' "$EXTRACTED_LVS" | sort -u | paste -sd ',' - || true)"
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
elif grep -q "Circuits match uniquely" "$NETGEN_REPORT" && grep -q "Netlists match uniquely" "$NETGEN_REPORT"; then
    lvs_match="yes"
fi
net_renames_used="no"
grep -q 'Net rename enabled: no' "$LVS_PREP_REPORT" || net_renames_used="yes"
pipeline_status="PASS"
failed_stage="none"
pipeline_message="none"
if [[ "$lvs_match" != "yes" ]]; then
    pipeline_status="FAIL"
    failed_stage="connectivity_lvs"
    pipeline_message="Connectivity LVS did not pass; see $LVS_RESULT_SUMMARY"
fi

cat > "$SUMMARY" <<EOF
# Sky130 Case Pipeline Summary

| Field | Value |
| --- | --- |
| CASE_NAME | $CASE_NAME |
| TOP_CELL | $TOP_CELL |
| VDD_NET | $VDD_NET |
| VSS_NET | $VSS_NET |
| SKY130A | $SKY130A |
| STATUS | $pipeline_status |
| FAILED_STAGE | $failed_stage |
| MESSAGE | $pipeline_message |
| MAGICAL_RESULT | pass |
| LAYOUT_INPUT_MODE | $LAYOUT_INPUT_MODE |
| LAYOUT_PROJECTION_DROPPED_PASSIVES | $LAYOUT_PROJECTION_DROPPED_PASSIVES |
| MAGICAL_SANITIZE_PLACE_GDS_FOR_ROUTER | $MAGICAL_SANITIZE_PLACE_GDS_FOR_ROUTER |
| MAGICAL_SKIP_ROUTER_PARSE_GDS | $MAGICAL_SKIP_ROUTER_PARSE_GDS |
| MAGICAL_SKIP_TOP_POWER_ROUTE | $MAGICAL_SKIP_TOP_POWER_ROUTE |
| MAGICAL_POWER_STRIPE_EXTRA_GRID | $MAGICAL_POWER_STRIPE_EXTRA_GRID |
| MAGICAL_POWER_STRIPE_EXTRA_DBU | $MAGICAL_POWER_STRIPE_EXTRA_DBU |
| MAGICAL_DISABLE_POWER_STRIPE | $MAGICAL_DISABLE_POWER_STRIPE |
| MAGICAL_SPLIT_POWER_STRIPE_AROUND_PASSIVES | $MAGICAL_SPLIT_POWER_STRIPE_AROUND_PASSIVES |
| MAGICAL_POWER_STRIPE_PASSIVE_KEEP_OUT_DBU | $MAGICAL_POWER_STRIPE_PASSIVE_KEEP_OUT_DBU |
| MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_LAYERS | ${MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_LAYERS:-none} |
| MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_MARGIN_DBU | $MAGICAL_ROUTER_PASSIVE_OBSTRUCTION_MARGIN_DBU |
| MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_LAYERS | ${MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_LAYERS:-none} |
| MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_BOX_DBU | ${MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_BOX_DBU:-none} |
| MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_MARGIN_DBU | $MAGICAL_ROUTER_LOCAL_VDD_OBSTRUCTION_MARGIN_DBU |
| MAGICAL_PASSIVE_PLACEMENT_OFFSET_X_DBU | $MAGICAL_PASSIVE_PLACEMENT_OFFSET_X_DBU |
| MAGICAL_PASSIVE_PLACEMENT_OFFSET_Y_DBU | $MAGICAL_PASSIVE_PLACEMENT_OFFSET_Y_DBU |
| MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES | $MAGICAL_ADD_LOCAL_VDD_STRIPE_BELOW_PASSIVES |
| MAGICAL_LOCAL_VDD_STRIPE_HEIGHT_DBU | $MAGICAL_LOCAL_VDD_STRIPE_HEIGHT_DBU |
| MAGICAL_LOCAL_VDD_STRIPE_Y_DBU | ${MAGICAL_LOCAL_VDD_STRIPE_Y_DBU:-auto} |
| MAGICAL_LOCAL_VDD_STRIPE_ACTIVE_KEEP_OUT_DBU | $MAGICAL_LOCAL_VDD_STRIPE_ACTIVE_KEEP_OUT_DBU |
| MAGICAL_LOCAL_VDD_STRIPE_EXCLUDE_X_DBU | ${MAGICAL_LOCAL_VDD_STRIPE_EXCLUDE_X_DBU:-none} |
| MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE | $MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE |
| MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_BOX_DBU | ${MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_BOX_DBU:-none} |
| MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_EXCLUDE_X_DBU | ${MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_EXCLUDE_X_DBU:-none} |
| MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_AUTO_EXCLUDE | $MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_AUTO_EXCLUDE |
| MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_AUTO_EXCLUDE_MARGIN_DBU | $MAGICAL_POST_ROUTE_LOCAL_VDD_STRIPE_AUTO_EXCLUDE_MARGIN_DBU |
| GDS_REMAP_RESULT | pass |
| EXPERIMENTAL_PASSIVE_REMAP | $EXPERIMENTAL_PASSIVE_REMAP |
| PIN_LABEL_RESULT | pass |
| PIN_SHAPE_RESULT | pass |
| DRC_COUNT | $drc_count |
| LVS_MODE | full_extraction |
| RAW_SUBCKT_PORTS | $raw_subckt_ports |
| ANONYMOUS_NODES | $anon_nodes |
| CONNECTIVITY_LVS_MATCH | $lvs_match |
| NETGEN_EXIT_STATUS | $netgen_status |
| NET_RENAMES_USED | $net_renames_used |
| PEX_CAPS | $pex_caps |
| PEX_TOTAL_CAP_FF | $pex_total |
| PEX_OUTPUT_NODE | ${OUTPUT_NODE:-none} |

## KEY_OUTPUTS

- Case directory: \`$CASE_DIR\`
- Source/MAGICAL netlist: \`$MAGICAL_NETLIST\`
- Config: \`$CONFIG\`
- Layout projection case directory: \`$LAYOUT_PROJECTION_CASE_DIR\`
- Layout projection netlist: \`$LAYOUT_PROJECTION_NETLIST\`
- Layout projection config: \`$LAYOUT_PROJECTION_CONFIG\`
- MAGICAL log: \`$MAGICAL_LOG\`
- MAGICAL run log: \`$ARTIFACT_MAGICAL_RUN_LOG\`
- ioPin: \`$ARTIFACT_IOPIN\`
- Route GDS: \`$ARTIFACT_ROUTE_GDS\`
- Sky130 remapped GDS: \`$ARTIFACT_SKY130_GDS\`
- Pinned-shapes GDS: \`$ARTIFACT_PINNED_SHAPES_GDS\`
- Generated GDS directory: \`$ARTIFACT_GENERATED_GDS_DIR\`
- DRC log: \`$DRC_LOG\`
- Raw extracted netlist: \`$EXTRACTED_LVS\`
- Raw extracted netlist copy: \`$RAW_EXTRACTED_COPY\`
- Connectivity source netlist: \`$CONNECTIVITY_SOURCE\`
- Connectivity extracted netlist: \`$CONNECTIVITY_EXTRACTED\`
- LVS preparation report: \`$LVS_PREP_REPORT\`
- Netgen connectivity LVS report: \`$NETGEN_REPORT\`
- LVS result summary: \`$LVS_RESULT_SUMMARY\`
- PEX summary: \`$PEX_SUMMARY\`
EOF

echo "Summary written: $SUMMARY"
echo "CASE_NAME=$CASE_NAME"
echo "TOP_CELL=$TOP_CELL"
echo "RAW_SUBCKT_PORTS=$raw_subckt_ports"
echo "ANONYMOUS_NODES=$anon_nodes"
echo "DRC_COUNT=$drc_count"
echo "CONNECTIVITY_LVS_MATCH=$lvs_match"
echo "NET_RENAMES_USED=$net_renames_used"
echo "PEX_CAPS=$pex_caps"
echo "PEX_TOTAL_CAP_FF=$pex_total"

if [[ "$lvs_match" != "yes" ]]; then
    echo "FAIL[connectivity_lvs]: $pipeline_message" >&2
    exit 1
fi
