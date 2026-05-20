#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

CASE_RUNNER="$SCRIPT_DIR/run_terminal_experiment_case.sh"
SUMMARY="$REPO_ROOT/docs/sky130_adapter/inverter_terminal_experiment_summary.md"

chmod +x "$CASE_RUNNER"

terminal_swap_output="$("$CASE_RUNNER" \
    "terminal-swap only" \
    "examples/inverter_sky130_try_terminal_swap" \
    "terminal_swap" \
    "default" \
    "docs/sky130_adapter/terminal_swap_experiment.md")"
printf "%s\n" "$terminal_swap_output"

powernet_output="$("$CASE_RUNNER" \
    "power-net only" \
    "examples/inverter_sky130_try_powernets" \
    "baseline" \
    "vpwr_vgnd" \
    "docs/sky130_adapter/powernet_recognition_experiment.md")"
printf "%s\n" "$powernet_output"

get_field() {
    local text="$1"
    local key="$2"
    printf "%s\n" "$text" | awk -F= -v k="$key" '$1 == k {print substr($0, length(k) + 2)}' | tail -n 1
}

ts_vpwr="$(get_field "$terminal_swap_output" VPWR_ISPOWER)"
ts_vgnd="$(get_field "$terminal_swap_output" VGND_ISPOWER)"
ts_vpwr_rec="$(get_field "$terminal_swap_output" VPWR_RECOGNIZED)"
ts_vgnd_rec="$(get_field "$terminal_swap_output" VGND_RECOGNIZED)"
ts_subckt="$(get_field "$terminal_swap_output" RAW_SUBCKT)"
ts_nmos="$(get_field "$terminal_swap_output" RAW_NMOS)"
ts_a="$(get_field "$terminal_swap_output" A_N15_EXISTS)"
ts_anon="$(get_field "$terminal_swap_output" ANON_EXISTS)"
ts_anon_nodes="$(get_field "$terminal_swap_output" ANON_NODES)"
ts_lvs="$(get_field "$terminal_swap_output" LVS_MATCH)"

pn_vpwr="$(get_field "$powernet_output" VPWR_ISPOWER)"
pn_vgnd="$(get_field "$powernet_output" VGND_ISPOWER)"
pn_vpwr_rec="$(get_field "$powernet_output" VPWR_RECOGNIZED)"
pn_vgnd_rec="$(get_field "$powernet_output" VGND_RECOGNIZED)"
pn_subckt="$(get_field "$powernet_output" RAW_SUBCKT)"
pn_nmos="$(get_field "$powernet_output" RAW_NMOS)"
pn_a="$(get_field "$powernet_output" A_N15_EXISTS)"
pn_anon="$(get_field "$powernet_output" ANON_EXISTS)"
pn_anon_nodes="$(get_field "$powernet_output" ANON_NODES)"
pn_lvs="$(get_field "$powernet_output" LVS_MATCH)"

combined_output=""
if [[ "$ts_anon" == "no" || "$pn_anon" == "no" ]]; then
    combined_output="$("$CASE_RUNNER" \
        "terminal-swap powernets" \
        "examples/inverter_sky130_try_terminal_swap_powernets" \
        "terminal_swap" \
        "vpwr_vgnd" \
        "docs/sky130_adapter/terminal_swap_powernet_combined_experiment.md")"
    printf "%s\n" "$combined_output"
fi

cb_vpwr="not run"
cb_vgnd="not run"
cb_vpwr_rec="not run"
cb_vgnd_rec="not run"
cb_subckt="not run"
cb_nmos="not run"
cb_anon="not run"
cb_anon_nodes="not run"
cb_lvs="not run"
if [[ -n "$combined_output" ]]; then
    cb_vpwr="$(get_field "$combined_output" VPWR_ISPOWER)"
    cb_vgnd="$(get_field "$combined_output" VGND_ISPOWER)"
    cb_vpwr_rec="$(get_field "$combined_output" VPWR_RECOGNIZED)"
    cb_vgnd_rec="$(get_field "$combined_output" VGND_RECOGNIZED)"
    cb_subckt="$(get_field "$combined_output" RAW_SUBCKT)"
    cb_nmos="$(get_field "$combined_output" RAW_NMOS)"
    cb_anon="$(get_field "$combined_output" ANON_EXISTS)"
    cb_anon_nodes="$(get_field "$combined_output" ANON_NODES)"
    cb_lvs="$(get_field "$combined_output" LVS_MATCH)"
fi

baseline_nmos="$(grep -E '^[[:space:]]*[Xx]0[[:space:]]+' "$REPO_ROOT/generated/sky130_lvs_pinned_shapes/inverter_core_extracted_pinned_shapes.spice" | head -n 1 || true)"
baseline_subckt="$(grep -E '^[[:space:]]*\.subckt[[:space:]]+inverter_core_flat' "$REPO_ROOT/generated/sky130_lvs_pinned_shapes/inverter_core_extracted_pinned_shapes.spice" | head -n 1 || true)"
baseline_a="yes"
if ! grep -q 'a_n15_90#' "$REPO_ROOT/generated/sky130_lvs_pinned_shapes/inverter_core_extracted_pinned_shapes.spice" 2>/dev/null; then
    baseline_a="no"
fi

combined_recommendation="not run"
if [[ -n "$combined_output" ]]; then
    combined_recommendation="run because one single-variable experiment improved raw extraction"
else
    combined_recommendation="not run; neither single-variable experiment removed a_n15_90#"
fi

mkdir -p "$(dirname "$SUMMARY")"
{
    echo "# Inverter Terminal Experiment Summary"
    echo
    echo "## Cases"
    echo
    echo "| Case | NMOS netlist | VPWR/VGND power recognition | Anaroute isPower | raw .subckt ports | raw NMOS extraction | anonymous internal nodes | normalized LVS | conclusion |"
    echo "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    echo "| baseline pinned_shapes | \`M0 (Y A VGND VGND)\` | no / no | False / False | \`$baseline_subckt\` | \`$baseline_nmos\` | $baseline_a: a_n15_90# | yes | baseline issue |"
    echo "| terminal-swap only | \`M0 (VGND A Y VGND)\` | $ts_vpwr_rec / $ts_vgnd_rec | $ts_vpwr / $ts_vgnd | \`$ts_subckt\` | \`$ts_nmos\` | $ts_anon: $ts_anon_nodes | $ts_lvs | terminal swap changes anonymous node but does not clean raw extraction |"
    echo "| power-net only | \`M0 (Y A VGND VGND)\` | $pn_vpwr_rec / $pn_vgnd_rec | $pn_vpwr / $pn_vgnd | \`$pn_subckt\` | \`$pn_nmos\` | $pn_anon: $pn_anon_nodes | $pn_lvs | power-net recognition fixes raw NFET connectivity in this trial |"
    echo "| combined optional | \`M0 (VGND A Y VGND)\` | $cb_vpwr_rec / $cb_vgnd_rec | $cb_vpwr / $cb_vgnd | \`$cb_subckt\` | \`$cb_nmos\` | $cb_anon: $cb_anon_nodes | $cb_lvs | $combined_recommendation |"
    echo
    echo "## Reports"
    echo
    echo "- Terminal-swap report: \`docs/sky130_adapter/terminal_swap_experiment.md\`"
    echo "- Power-net report: \`docs/sky130_adapter/powernet_recognition_experiment.md\`"
    echo "- Combined report: \`docs/sky130_adapter/terminal_swap_powernet_combined_experiment.md\`"
    echo
    echo "## Interpretation"
    echo
    if [[ "$ts_anon" == "no" ]]; then
        echo "- Terminal swap removed anonymous internal nodes; investigate D/S orientation and consider an explicit Sky130 MOS terminal mapping."
    else
        echo "- Terminal swap did not clean raw extraction; it replaced \`a_n15_90#\` with another anonymous node in this run, so D/S order alone is not sufficient."
    fi
    if [[ "$pn_vpwr_rec" == "yes" && "$pn_vgnd_rec" == "yes" ]]; then
        echo "- Power-net JSON fields are effective at the MAGICAL/placer level: VPWR and VGND generate power stripes."
    else
        echo "- Power-net JSON fields did not fully mark VPWR/VGND as power nets; check Params/MagicalDB schema or log."
    fi
    echo "- In these tiny inverter runs, Anaroute \`isPower\` remains False because PnR passes \`net.isPower() and not self.isSmallModule\`; power recognition is still visible through power-stripe generation."
    if [[ "$pn_anon" == "no" ]]; then
        echo "- Power-net recognition removed anonymous internal NMOS terminal nodes; next fix should focus on Sky130 adapter power-net configuration."
    else
        echo "- Power-net recognition did not remove anonymous internal nodes; it remains necessary but not sufficient."
    fi
    echo "- Keep \`normalize_lvs_netlists_inverter.py\` until raw Magic extraction no longer contains anonymous internal NMOS terminal nodes."
} > "$SUMMARY"

echo "Summary written: $SUMMARY"
