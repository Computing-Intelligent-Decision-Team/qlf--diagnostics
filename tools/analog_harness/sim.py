"""AnalogGym-template based nominal simulator wrapper."""

from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import HarnessConfig
from .models import CompiledCandidate, EvidencePacket


SUBCKT_RE = re.compile(r"^\s*\.subckt\s+(\S+)", re.IGNORECASE)
MAGIC_MOS_PARAM_RE = re.compile(
    r"\b(?P<name>l|w|ad|as|pd|ps)=(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)(?=\s|$)",
    re.IGNORECASE,
)
MODEL_BIN_RE = re.compile(
    r"^\s*\.model\s+(?P<name>sky130_fd_pr__(?P<device>[pn]fet_01v8)__model\.\d+)\s+[pn]mos",
    re.IGNORECASE,
)
MODEL_BOUND_RE = re.compile(r"\b(?P<key>lmin|lmax|wmin|wmax)\s*=\s*(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)")
SKY130_EXTERNAL_PARAM_RE = re.compile(
    r"\b(?P<name>mc_[A-Za-z0-9_]+|sky130_fd_pr__[pn]fet_01v8__[A-Za-z0-9_]+)\b",
    re.IGNORECASE,
)
SKY130_DIRECT_MODEL_LOCAL_DEFAULTS = {
    "l": "1u",
    "w": "1u",
    "mult": "1",
}
MAGICAL_NMOS_ALIASES = {"nmos", "nch", "nch_mac"}
MAGICAL_PMOS_ALIASES = {"pmos", "pch", "pch_mac"}
MAGICAL_RESISTOR_ALIASES = {"rppoly", "rppoly_m", "rppolywo_m", "rppolywo"}
MAGICAL_CAPACITOR_ALIASES = {"cfmom", "cfmom_2t"}


@dataclass(frozen=True)
class SimulationCorner:
    name: str
    model_corner: str = "tt"
    vdd: float = 1.8
    temp_c: float = 27.0
    vcm: float | None = None


@dataclass(frozen=True)
class Sky130ModelBin:
    lmin_um: float
    lmax_um: float
    wmin_um: float
    wmax_um: float
    model_name: str = ""
    model_lines: tuple[str, ...] = ()

    @property
    def center_l_um(self) -> float:
        return (self.lmin_um + self.lmax_um) * 0.5

    @property
    def center_w_um(self) -> float:
        return (self.wmin_um + self.wmax_um) * 0.5

    def contains_interior(self, l_um: float, w_um: float) -> bool:
        return self.lmin_um < l_um < self.lmax_um and self.wmin_um < w_um < self.wmax_um


def read_subckt_name(netlist: Path) -> str | None:
    """Return the first subckt name in a SPICE netlist."""

    for line in netlist.read_text(encoding="utf-8", errors="replace").splitlines():
        match = SUBCKT_RE.match(line)
        if match:
            return match.group(1)
    return None


class AnalogGymTemplateSimulator:
    """Writes SMC testbenches adapted from the AnalogGym AMP_DFCFC2 flow."""

    def __init__(self, config: HarnessConfig):
        self.config = config
        self.sim_config = dict(config.data.get("simulation", {}))
        self.ngspice = str(self.sim_config.get("ngspice_binary", "ngspice"))
        self.run_ngspice = bool(self.sim_config.get("run_ngspice", True))
        self.allow_proxy_fallback = bool(self.sim_config.get("allow_proxy_fallback", True))
        self.sky130_model_corner = str(self.sim_config.get("sky130_model_corner", "tt"))
        self.snap_sky130_model_bins = bool(self.sim_config.get("snap_sky130_mos_to_model_bins", True))
        self.direct_sky130_model_projection = bool(self.sim_config.get("project_sky130_primitives_to_direct_models", True))
        self.macro_projection_enabled = bool(self.sim_config.get("project_magical_macros_to_sky130", True))
        self.ac_stop_hz = float(self.sim_config.get("ac_stop_hz", 1.0e12))
        self.tran_stop_s = float(self.sim_config.get("tran_stop_s", 300.0e-9))
        self.tran_step_s = float(self.sim_config.get("tran_step_s", 1.0e-9))
        self.step_time_s = float(self.sim_config.get("step_time_s", 10.0e-9))
        self.settling_tolerance_fraction = float(self.sim_config.get("settling_tolerance_fraction", 0.01))
        self.pvt_config = dict(self.sim_config.get("pvt", {}))
        self.pvt_enabled = bool(self.pvt_config.get("enabled", False))
        raw_model_lib = self.sim_config.get("sky130_model_lib")
        self.sky130_model_lib = (
            config.resolve_path(str(raw_model_lib))
            if raw_model_lib
            else config.analog_gym_root / "simulation_files" / "sky130_pdk" / "libs.tech" / "ngspice" / "sky130.lib.spice"
        )
        self._model_bins_by_corner: dict[str, dict[str, list[Sky130ModelBin]]] = {}

    def evaluate_pre_layout(self, compiled: CompiledCandidate, skip_sim: bool = False) -> EvidencePacket:
        return self._evaluate(compiled, compiled.netlist_path, "pre_layout", "E0", skip_sim, stage="pre_sim")

    def evaluate_post_layout(
        self,
        compiled: CompiledCandidate,
        extracted_netlist: Path | None,
        skip_sim: bool = False,
    ) -> EvidencePacket:
        if extracted_netlist is None:
            return EvidencePacket(
                candidate_id=compiled.candidate_id,
                stage="post_sim",
                fidelity="E3",
                status="skipped",
                verification_scope=self.config.verification_scope,
                messages=["no extracted netlist available for post-layout simulation"],
            )
        return self._evaluate(compiled, extracted_netlist, "post_layout", "E3", skip_sim, stage="post_sim")

    def evaluate_post_layout_pvt(
        self,
        compiled: CompiledCandidate,
        extracted_netlist: Path | None,
        skip_sim: bool = False,
    ) -> EvidencePacket:
        if extracted_netlist is None:
            return EvidencePacket(
                candidate_id=compiled.candidate_id,
                stage="pvt_sim",
                fidelity="E4",
                status="skipped",
                verification_scope=self.config.verification_scope,
                messages=["no extracted netlist available for PVT simulation"],
            )
        corners = self._pvt_corners()
        if not corners:
            return EvidencePacket(
                candidate_id=compiled.candidate_id,
                stage="pvt_sim",
                fidelity="E4",
                status="skipped",
                verification_scope=self.config.verification_scope,
                messages=["no PVT corners configured"],
            )
        corner_packets: list[EvidencePacket] = []
        for corner in corners:
            packet = self._evaluate(
                compiled,
                extracted_netlist,
                f"post_layout_pvt/{corner.name}",
                "E4",
                skip_sim,
                stage="pvt_corner",
                corner=corner,
            )
            corner_packets.append(packet)
        return self._pvt_packet(compiled, corners, corner_packets)

    def _evaluate(
        self,
        compiled: CompiledCandidate,
        netlist: Path,
        phase: str,
        fidelity: str,
        skip_sim: bool,
        stage: str,
        corner: SimulationCorner | None = None,
    ) -> EvidencePacket:
        sim_dir = compiled.candidate_dir / "sim" / phase
        sim_dir.mkdir(parents=True, exist_ok=True)
        active_corner = corner or SimulationCorner(
            name=str(self.sky130_model_corner),
            model_corner=str(self.sky130_model_corner),
            vdd=float(self.sim_config.get("vdd", 1.8)),
            temp_c=float(self.sim_config.get("temp_c", 27.0)),
            vcm=self.sim_config.get("vcm"),
        )
        netlist_for_sim, projection_feedback = self._prepare_netlist_for_sim(sim_dir, netlist, active_corner)
        subckt_name = read_subckt_name(netlist_for_sim) or self.config.top_cell
        include_block, model_lib = self._include_block(
            netlist_for_sim,
            include_sky130_lib=not bool(projection_feedback.get("simulation_direct_model_projection")),
            corner=active_corner.model_corner,
        )
        acdc = self._write_acdc_testbench(sim_dir, netlist_for_sim, compiled, subckt_name, include_block, active_corner)
        tran = self._write_tran_testbench(sim_dir, netlist_for_sim, compiled, subckt_name, include_block, active_corner)

        artifacts = {
            "acdc_testbench": str(acdc),
            "tran_testbench": str(tran),
            "netlist": str(netlist),
            "simulation_netlist": str(netlist_for_sim),
            "instantiated_subckt": subckt_name,
            "simulation_corner": active_corner.name,
            "simulation_model_corner": active_corner.model_corner,
            "simulation_vdd": str(active_corner.vdd),
            "simulation_temp_c": str(active_corner.temp_c),
        }
        artifacts.update({key: str(value) for key, value in projection_feedback.items()})
        if model_lib is not None:
            artifacts["sky130_model_lib"] = str(model_lib)
        if skip_sim or not self.run_ngspice:
            metrics = self._proxy_metrics(compiled.values)
            return self._packet(compiled, stage, fidelity, "proxy_fallback", metrics, artifacts, ["ngspice execution skipped"])

        ngspice_path = shutil.which(self.ngspice)
        if ngspice_path is None:
            if not self.allow_proxy_fallback:
                return self._packet(compiled, stage, fidelity, "fail", {}, artifacts, ["ngspice not found"])
            metrics = self._proxy_metrics(compiled.values)
            return self._packet(compiled, stage, fidelity, "proxy_fallback", metrics, artifacts, ["ngspice not found; used deterministic proxy metrics"])

        messages: list[str] = []
        for circuit, log_name in ((acdc, "ACDC.log"), (tran, "Tran.log")):
            result = subprocess.run(
                [ngspice_path, "-b", "-o", log_name, circuit.name],
                cwd=sim_dir,
                check=False,
                capture_output=True,
                text=True,
            )
            artifacts[log_name] = str(sim_dir / log_name)
            if result.returncode != 0:
                messages.append(f"{circuit.name} failed with exit status {result.returncode}")

        metrics = self._parse_metrics(sim_dir, compiled.values)
        if messages:
            failure_feedback = self._failure_feedback(sim_dir)
            if self.allow_proxy_fallback:
                metrics = self._proxy_metrics(compiled.values)
                return self._packet(
                    compiled,
                    stage,
                    fidelity,
                    "proxy_fallback",
                    metrics,
                    artifacts,
                    messages + ["ngspice failure; used deterministic proxy metrics"],
                    failure_feedback,
                )
            return self._packet(compiled, stage, fidelity, "fail", metrics, artifacts, messages, failure_feedback)
        if not metrics:
            if self.allow_proxy_fallback:
                metrics = self._proxy_metrics(compiled.values)
                return self._packet(compiled, stage, fidelity, "proxy_fallback", metrics, artifacts, messages + ["metric files missing; used proxy metrics"])
            return self._packet(compiled, stage, fidelity, "fail", {}, artifacts, messages + ["metric files missing"])
        simulated_metric_fields = sorted(metrics)
        proxy_fields = self._fill_inferred_metrics(metrics, compiled.values)
        artifacts["simulated_metric_fields"] = ",".join(simulated_metric_fields)
        if proxy_fields:
            artifacts["proxy_metric_fields"] = ",".join(proxy_fields)
        return self._packet(compiled, stage, fidelity, "pass", metrics, artifacts, messages, projection_feedback)

    def _packet(
        self,
        compiled: CompiledCandidate,
        stage: str,
        fidelity: str,
        status: str,
        metrics: dict[str, Any],
        artifacts: dict[str, str],
        messages: list[str],
        physical_feedback: dict[str, Any] | None = None,
    ) -> EvidencePacket:
        feedback = {"simulation_template": "AnalogGym AMP_DFCFC2 adapted to SMC"}
        if physical_feedback:
            feedback.update(physical_feedback)
        return EvidencePacket(
            candidate_id=compiled.candidate_id,
            stage=stage,
            fidelity=fidelity,
            status=status,
            verification_scope=self.config.verification_scope,
            metrics=metrics,
            physical_feedback=feedback,
            artifacts=artifacts,
            messages=messages,
        )

    def _pvt_packet(
        self,
        compiled: CompiledCandidate,
        corners: list[SimulationCorner],
        corner_packets: list[EvidencePacket],
    ) -> EvidencePacket:
        corner_payload = [packet.to_dict() for packet in corner_packets]
        pvt_dir = compiled.candidate_dir / "sim" / "post_layout_pvt"
        pvt_dir.mkdir(parents=True, exist_ok=True)
        corner_evidence_path = pvt_dir / "corner_evidence.json"
        corner_evidence_path.write_text(
            json.dumps(corner_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        passed = [packet for packet in corner_packets if packet.status == "pass"]
        require_all = bool(self.pvt_config.get("require_all_corners", True))
        all_passed = len(passed) == len(corner_packets)
        any_passed = bool(passed)
        status = "pass" if (all_passed if require_all else any_passed) else "fail"
        metrics = self._aggregate_pvt_metrics(corner_packets)
        metrics["pvt_total_corners"] = len(corner_packets)
        metrics["pvt_passed_corners"] = len(passed)
        feedback = {
            "simulation_template": "AnalogGym AMP_DFCFC2 adapted to SMC",
            "pvt_require_all_corners": require_all,
            "pvt_corners": [corner.__dict__ for corner in corners],
            "pvt_corner_statuses": {corner.name: packet.status for corner, packet in zip(corners, corner_packets)},
        }
        messages: list[str] = []
        for corner, packet in zip(corners, corner_packets):
            if packet.status != "pass":
                messages.append(f"{corner.name}:{packet.status}")
                messages.extend(f"{corner.name}: {message}" for message in packet.messages)
        return EvidencePacket(
            candidate_id=compiled.candidate_id,
            stage="pvt_sim",
            fidelity="E4",
            status=status,
            verification_scope=self.config.verification_scope,
            metrics=metrics,
            physical_feedback=feedback,
            artifacts={
                "corner_evidence": str(corner_evidence_path),
                "corner_dirs": json.dumps(
                    {
                        corner.name: str(compiled.candidate_dir / "sim" / "post_layout_pvt" / corner.name)
                        for corner in corners
                    },
                    sort_keys=True,
                ),
            },
            messages=messages,
        )

    def _aggregate_pvt_metrics(self, corner_packets: list[EvidencePacket]) -> dict[str, float]:
        metrics: dict[str, float] = {}
        numeric_by_key: dict[str, list[float]] = {}
        for packet in corner_packets:
            if packet.status != "pass":
                continue
            for key, value in packet.metrics.items():
                if isinstance(value, (int, float)):
                    numeric_by_key.setdefault(key, []).append(float(value))
        for key, values in numeric_by_key.items():
            if not values:
                continue
            metrics[f"pvt_min_{key}"] = min(values)
            metrics[f"pvt_max_{key}"] = max(values)
            spec = self.config.performance.get(key, {})
            objective = str(spec.get("objective", "max")) if isinstance(spec, dict) else "max"
            metrics[key] = max(values) if objective == "min" else min(values)
        return metrics

    def _pvt_corners(self) -> list[SimulationCorner]:
        raw_corners = self.pvt_config.get("corners")
        if not raw_corners:
            raw_corners = [
                {"name": "tt_1v8_27C", "model_corner": "tt", "vdd": 1.8, "temp_c": 27.0},
                {"name": "ss_1v62_125C", "model_corner": "ss", "vdd": 1.62, "temp_c": 125.0},
                {"name": "ff_1v98_-25C", "model_corner": "ff", "vdd": 1.98, "temp_c": -25.0},
            ]
        corners: list[SimulationCorner] = []
        for item in raw_corners:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("model_corner") or f"corner_{len(corners)}")
            corners.append(
                SimulationCorner(
                    name=name,
                    model_corner=str(item.get("model_corner", item.get("corner", "tt"))),
                    vdd=float(item.get("vdd", 1.8)),
                    temp_c=float(item.get("temp_c", item.get("temp", 27.0))),
                    vcm=float(item["vcm"]) if "vcm" in item and item["vcm"] is not None else None,
                )
            )
        return corners

    def _write_acdc_testbench(
        self,
        sim_dir: Path,
        netlist: Path,
        compiled: CompiledCandidate,
        subckt_name: str,
        include_block: str,
        corner: SimulationCorner,
    ) -> Path:
        path = sim_dir / f"{self.config.top_cell}_ACDC.cir"
        ibias_ua = float(compiled.values.get("ibias_current_uA", 10.0))
        vcm = float(corner.vcm if corner.vcm is not None else corner.vdd * 0.5)
        text = f"""* ACDC testbench adapted from AnalogGym AMP_DFCFC2 for {self.config.top_cell}
{include_block}
.temp {corner.temp_c:.8g}
.param VDDVAL={corner.vdd:.8g}
.param VCM={vcm:.8g}
.param IBIAS={ibias_ua:.8g}u
.param CLOAD=100f
VDD vdda 0 {{VDDVAL}}
VGND gnda 0 0
IIB vdda ibias DC {{IBIAS}}
VINP vip 0 DC {{VCM}} AC 0.5
VINN vin 0 DC {{VCM}} AC -0.5
CLOAD vout 0 {{CLOAD}}
XU vdda gnda vin vip ibias vout {subckt_name}
.control
save all
.options savecurrents
set filetype=ascii
set units=degrees
op
let supply_current = abs(i(VDD))
let power_mw = {corner.vdd:.8g} * supply_current * 1000
wrdata {self.config.top_cell}_ACDC_POWER power_mw
ac dec 20 1 {self.ac_stop_hz:.8g}
meas ac dcgain_ find vdb(vout) at = 1
meas ac gain_bandwidth_product_ when vdb(vout)=0
meas ac phase_at_unity find vp(vout) when vdb(vout)=0
let phase_margin = 180 + phase_at_unity
wrdata {self.config.top_cell}_ACDC_AC dcgain_
wrdata {self.config.top_cell}_ACDC_GBW_PM gain_bandwidth_product_ phase_margin
wrdata {self.config.top_cell}_ACDC_SWEEP vdb(vout) vp(vout)
.endc
.end
"""
        path.write_text(text, encoding="utf-8")
        return path

    def _write_tran_testbench(
        self,
        sim_dir: Path,
        netlist: Path,
        compiled: CompiledCandidate,
        subckt_name: str,
        include_block: str,
        corner: SimulationCorner,
    ) -> Path:
        path = sim_dir / f"{self.config.top_cell}_Tran.cir"
        ibias_ua = float(compiled.values.get("ibias_current_uA", 10.0))
        vcm = float(corner.vcm if corner.vcm is not None else corner.vdd * 0.5)
        pulse_low = vcm - 0.005
        pulse_high = vcm + 0.005
        text = f"""* Transient testbench adapted from AnalogGym AMP_DFCFC2 for {self.config.top_cell}
{include_block}
.temp {corner.temp_c:.8g}
.param VDDVAL={corner.vdd:.8g}
.param VCM={vcm:.8g}
.param IBIAS={ibias_ua:.8g}u
.param CLOAD=100f
VDD vdda 0 {{VDDVAL}}
VGND gnda 0 0
IIB vdda ibias DC {{IBIAS}}
VINP vip 0 PULSE({pulse_low:.8g} {pulse_high:.8g} {self.step_time_s:.8g} 1n 1n 100n 200n)
VINN vin 0 DC {{VCM}}
CLOAD vout 0 {{CLOAD}}
XU vdda gnda vin vip ibias vout {subckt_name}
.control
tran {self.tran_step_s:.8g} {self.tran_stop_s:.8g}
wrdata {self.config.top_cell}_Tran v(vout)
.endc
.end
"""
        path.write_text(text, encoding="utf-8")
        return path

    def _parse_metrics(self, sim_dir: Path, values: dict[str, float | int]) -> dict[str, float]:
        metrics = self._parse_wrdata_metrics(sim_dir)
        metrics.update(
            {
                key: value
                for key, value in self._parse_sweep_metrics(sim_dir).items()
                if key not in metrics or key in {"GBW", "phase_margin"}
            }
        )
        tran_metrics = self._parse_tran_metrics(sim_dir)
        metrics.update({key: value for key, value in tran_metrics.items() if key not in metrics})
        if metrics:
            self._fill_derived_metrics(metrics, values)
            return metrics
        metrics_path = sim_dir / f"{self.config.top_cell}_harness_metrics.txt"
        if not metrics_path.is_file():
            return {}
        metrics = {}
        for line in metrics_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            try:
                metrics[key.strip()] = float(value.strip())
            except ValueError:
                continue
        return metrics

    def _parse_wrdata_metrics(self, sim_dir: Path) -> dict[str, float]:
        metrics: dict[str, float] = {}
        ac_rows = _read_numeric_rows(sim_dir / f"{self.config.top_cell}_ACDC_AC")
        if ac_rows and len(ac_rows[0]) >= 2:
            metrics["dcgain"] = abs(ac_rows[0][-1])
        gbw_pm_rows = _read_numeric_rows(sim_dir / f"{self.config.top_cell}_ACDC_GBW_PM")
        if gbw_pm_rows and len(gbw_pm_rows[0]) >= 4:
            metrics["GBW"] = abs(gbw_pm_rows[0][1])
            metrics["phase_margin"] = gbw_pm_rows[0][3]
        power_rows = _read_numeric_rows(sim_dir / f"{self.config.top_cell}_ACDC_POWER")
        if power_rows and len(power_rows[0]) >= 2:
            metrics["Power"] = abs(power_rows[0][-1])
        return metrics

    def _parse_sweep_metrics(self, sim_dir: Path) -> dict[str, float]:
        rows = _read_numeric_rows(sim_dir / f"{self.config.top_cell}_ACDC_SWEEP")
        if not rows:
            return {}
        sweep = _parse_ac_sweep_rows(rows)
        if not sweep:
            return {}
        metrics: dict[str, float] = {}
        first_freq, first_gain, _ = sweep[0]
        if first_freq >= 0:
            metrics["dcgain"] = abs(first_gain)
        crossing = _unity_gain_crossing(sweep)
        if crossing is not None:
            metrics["GBW"], metrics["phase_margin"] = crossing
        else:
            closest = min(sweep, key=lambda item: abs(item[1]))
            metrics["GBW_lower_bound"] = max(item[0] for item in sweep)
            metrics["GBW"] = metrics["GBW_lower_bound"]
            metrics["phase_margin_at_closest_unity"] = 180.0 + closest[2]
            metrics["phase_margin"] = metrics["phase_margin_at_closest_unity"]
        return metrics

    def _parse_tran_metrics(self, sim_dir: Path) -> dict[str, float]:
        rows = _read_numeric_rows(sim_dir / f"{self.config.top_cell}_Tran")
        settling = _settling_time_from_rows(rows, self.step_time_s, self.settling_tolerance_fraction)
        return {} if settling is None else {"settlingTime": settling}

    def _fill_inferred_metrics(
        self,
        metrics: dict[str, float],
        values: dict[str, float | int],
    ) -> list[str]:
        inferred = self._proxy_metrics(values)
        inferred_fields: list[str] = []
        for key in ("Power", "Active_Area", "settlingTime", "FOML", "FOMS"):
            if key not in metrics and key in inferred:
                metrics[key] = inferred[key]
                inferred_fields.append(key)
        return inferred_fields

    def _fill_derived_metrics(self, metrics: dict[str, float], values: dict[str, float | int]) -> None:
        gbw = metrics.get("GBW")
        power_mw = metrics.get("Power")
        if isinstance(gbw, (int, float)) and isinstance(power_mw, (int, float)) and power_mw > 0:
            power_w = float(power_mw) * 1.0e-3
            metrics.setdefault("FOML", float(gbw) * 100.0e-15 / max(power_w, 1e-15))
            metrics.setdefault("FOMS", float(gbw) / max(float(power_mw), 1e-15))

    @staticmethod
    def _failure_feedback(sim_dir: Path) -> dict[str, Any]:
        text_parts: list[str] = []
        for name in ("ACDC.log", "Tran.log"):
            path = sim_dir / name
            if path.is_file():
                text_parts.append(path.read_text(encoding="utf-8", errors="replace"))
        text = "\n".join(text_parts).lower()
        if "could not find a valid modelname" in text:
            return {
                "ngspice_failure_category": "sky130_model_bin_mismatch",
                "ngspice_failure_owner": "sizing_optimizer",
                "ngspice_failure_note": "Sky130 ngspice binned model did not cover at least one extracted MOS W/L.",
            }
        if "unknown subckt" in text:
            return {
                "ngspice_failure_category": "unknown_subckt",
                "ngspice_failure_owner": "eda_runtime",
            }
        return {"ngspice_failure_category": "ngspice_runtime_failure", "ngspice_failure_owner": "eda_runtime"}

    def _include_block(self, netlist: Path, include_sky130_lib: bool = True, corner: str | None = None) -> tuple[str, Path | None]:
        lines: list[str] = []
        model_lib: Path | None = None
        if include_sky130_lib and self._uses_sky130_primitives(netlist) and self.sky130_model_lib.is_file():
            model_lib = self.sky130_model_lib.resolve()
            model_lib_spice_path = str(model_lib).replace("\\", "/")
            lines.append(f'.lib "{model_lib_spice_path}" {corner or self.sky130_model_corner}')
        include_path = str(netlist).replace("\\", "/")
        lines.append(f'.include "{include_path}"')
        return "\n".join(lines), model_lib

    def _prepare_netlist_for_sim(
        self,
        sim_dir: Path,
        netlist: Path,
        corner: SimulationCorner,
    ) -> tuple[Path, dict[str, Any]]:
        text = netlist.read_text(encoding="utf-8", errors="replace")
        feedback: dict[str, Any] = {}
        if self.macro_projection_enabled:
            text, macro_feedback = project_magical_macros_to_sky130(
                text,
                dict(self.sim_config.get("macro_projection", {})),
            )
            feedback.update(macro_feedback)
        if "sky130_fd_pr__" not in text:
            if feedback:
                projected = sim_dir / f"{netlist.stem}.macro_projected{netlist.suffix}"
                projected.write_text(text, encoding="utf-8")
                return projected, feedback
            return netlist, {}
        normalized = sim_dir / f"{netlist.stem}.ngspice_units{netlist.suffix}"
        text = normalize_magic_extracted_units(text)
        if self.direct_sky130_model_projection:
            text, snapped_count, model_count = project_sky130_primitives_to_direct_models(text, self._model_bins(corner.model_corner))
            feedback["simulation_model_projection"] = "direct_nearest_sky130_bin"
            feedback["simulation_model_projection_snapped_mos"] = snapped_count
            feedback["simulation_direct_model_projection"] = True
            feedback["simulation_direct_model_count"] = model_count
        elif self.snap_sky130_model_bins:
            text, snapped_count = snap_magic_extracted_model_bins(text, self._model_bins(corner.model_corner))
            feedback["simulation_model_projection"] = "nearest_sky130_bin"
            feedback["simulation_model_projection_snapped_mos"] = snapped_count
        normalized.write_text(text, encoding="utf-8")
        return normalized, feedback

    def _model_bins(self, corner: str | None = None) -> dict[str, list[Sky130ModelBin]]:
        model_corner = str(corner or self.sky130_model_corner)
        if model_corner in self._model_bins_by_corner:
            return self._model_bins_by_corner[model_corner]
        pdk_root = self.sky130_model_lib.resolve().parents[2]
        spice_dir = pdk_root / "libs.ref" / "sky130_fd_pr" / "spice"
        self._model_bins_by_corner[model_corner] = {
            "sky130_fd_pr__pfet_01v8": parse_sky130_model_bins(
                _corner_model_path(spice_dir, "sky130_fd_pr__pfet_01v8", model_corner)
            ),
            "sky130_fd_pr__nfet_01v8": parse_sky130_model_bins(
                _corner_model_path(spice_dir, "sky130_fd_pr__nfet_01v8", model_corner)
            ),
        }
        return self._model_bins_by_corner[model_corner]

    @staticmethod
    def _uses_sky130_primitives(netlist: Path) -> bool:
        text = netlist.read_text(encoding="utf-8", errors="replace")
        return "sky130_fd_pr__" in text

    def _proxy_metrics(self, values: dict[str, float | int]) -> dict[str, float]:
        diff_w = float(values.get("diff_pair_w", 7.5))
        diff_l = float(values.get("diff_pair_l", 8.0))
        out_p_w = float(values.get("second_stage_pmos_w", 0.22))
        out_n_w = float(values.get("second_stage_nmos_w", 1.48))
        cap_nr = float(values.get("comp_cap_nr", 94))
        ibias_ua = float(values.get("ibias_current_uA", 10.0))
        gm_proxy = math.sqrt(max(diff_w * max(1.0, ibias_ua), 1e-9)) / max(diff_l, 0.1)
        load_balance = 1.0 / (1.0 + abs(out_p_w - out_n_w) / max(out_p_w + out_n_w, 1e-9))
        gbw = max(1e3, 1.0e6 * gm_proxy / max(cap_nr / 100.0, 0.2))
        return {
            "dcgain": 45.0 + 12.0 * math.log10(max(diff_w * diff_l, 1.0)),
            "GBW": gbw,
            "phase_margin": 45.0 + 28.0 * load_balance,
            "Power": 1.8 * ibias_ua / 1000.0,
            "Active_Area": self._area_proxy(values),
            "settlingTime": 2.2 / gbw,
            "FOML": gbw * 100e-15 / max(1.8 * ibias_ua * 1e-6, 1e-12),
            "FOMS": gbw / max(1.8 * ibias_ua, 1e-9),
        }

    @staticmethod
    def _area_proxy(values: dict[str, float | int]) -> float:
        area = 0.0
        for key, value in values.items():
            if key.endswith("_w"):
                prefix = key[:-2]
                length = float(values.get(prefix + "_l", 1.0))
                area += float(value) * length
            if key == "comp_cap_nr":
                area += float(value) * 0.05
            if key == "comp_res_series":
                area += float(value) * 0.02
        return max(area, 1e-9)


def _read_numeric_rows(path: Path) -> list[list[float]]:
    if not path.is_file():
        return []
    rows: list[list[float]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = [float(item) for item in line.split()]
        except ValueError:
            continue
        if row:
            rows.append(row)
    return rows


def _parse_ac_sweep_rows(rows: list[list[float]]) -> list[tuple[float, float, float]]:
    sweep: list[tuple[float, float, float]] = []
    for row in rows:
        if len(row) >= 4:
            freq, gain_db, phase = row[0], row[1], row[3]
        elif len(row) >= 3:
            freq, gain_db, phase = row[0], row[1], row[2]
        else:
            continue
        if freq > 0.0 and all(math.isfinite(value) for value in (freq, gain_db, phase)):
            sweep.append((freq, gain_db, phase))
    return sweep


def _unity_gain_crossing(sweep: list[tuple[float, float, float]]) -> tuple[float, float] | None:
    for left, right in zip(sweep, sweep[1:]):
        f0, g0, p0 = left
        f1, g1, p1 = right
        if g0 == 0.0:
            return f0, 180.0 + p0
        if (g0 > 0.0 >= g1) or (g0 < 0.0 <= g1):
            span = g1 - g0
            ratio = 0.0 if span == 0.0 else (0.0 - g0) / span
            if f0 > 0.0 and f1 > 0.0:
                log_freq = math.log10(f0) + ratio * (math.log10(f1) - math.log10(f0))
                freq = 10.0 ** log_freq
            else:
                freq = f0 + ratio * (f1 - f0)
            phase = p0 + ratio * (p1 - p0)
            return freq, 180.0 + phase
    return None


def _settling_time_from_rows(
    rows: list[list[float]],
    step_time_s: float,
    tolerance_fraction: float,
) -> float | None:
    wave = [(row[0], row[1]) for row in rows if len(row) >= 2 and row[0] >= step_time_s]
    if len(wave) < 3:
        return None
    final_value = wave[-1][1]
    initial_value = wave[0][1]
    tolerance = max(abs(final_value - initial_value) * tolerance_fraction, 1.0e-6)
    for index, (time_s, value) in enumerate(wave):
        if abs(value - final_value) <= tolerance and all(abs(item[1] - final_value) <= tolerance for item in wave[index:]):
            return max(0.0, time_s - step_time_s)
    return None


def normalize_magic_extracted_units(netlist_text: str) -> str:
    """Add ngspice units to Magic raw-extracted Sky130 MOS dimensions."""

    lines: list[str] = []
    for line in netlist_text.splitlines():
        stripped = line.lstrip()
        if not stripped.lower().startswith("x") or "sky130_fd_pr__" not in line:
            lines.append(line)
            continue
        lines.append(MAGIC_MOS_PARAM_RE.sub(_magic_mos_param_replacement, line))
    return "\n".join(lines) + "\n"


def _magic_mos_param_replacement(match: re.Match[str]) -> str:
    name = match.group("name")
    value = match.group("value")
    if float(value) == 0.0:
        return f"{name}={value}"
    unit = "p" if name.lower() in {"ad", "as"} else "u"
    return f"{name}={value}{unit}"


def project_magical_macros_to_sky130(
    netlist_text: str,
    options: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Project MAGICAL macro devices into ngspice-compatible Sky130 primitives."""

    projection_options = options or {}
    lines: list[str] = []
    projected_mos = 0
    projected_resistors = 0
    projected_capacitors = 0
    for line in netlist_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("*"):
            lines.append(line)
            continue
        tokens = stripped.replace("(", " ").replace(")", " ").split()
        if not tokens or not tokens[0].lower().startswith("x"):
            lines.append(line)
            continue
        model_index = _find_macro_model_index(tokens)
        if model_index is None:
            lines.append(line)
            continue
        model = tokens[model_index].lower()
        if model in MAGICAL_NMOS_ALIASES or model in MAGICAL_PMOS_ALIASES:
            if model_index < 5:
                lines.append(line)
                continue
            sky_model = "sky130_fd_pr__nfet_01v8" if model in MAGICAL_NMOS_ALIASES else "sky130_fd_pr__pfet_01v8"
            params = [_normalize_instance_param_token(token) for token in tokens[model_index + 1 :]]
            lines.append(" ".join([tokens[0], *tokens[1:model_index], sky_model, *params]))
            projected_mos += 1
            continue
        if model in MAGICAL_RESISTOR_ALIASES:
            if model_index < 3:
                lines.append(line)
                continue
            resistance = _estimate_macro_resistance(tokens[model_index + 1 :], projection_options)
            lines.append(f"R{tokens[0][1:]} {tokens[1]} {tokens[2]} {resistance:.8g}")
            projected_resistors += 1
            continue
        if model in MAGICAL_CAPACITOR_ALIASES:
            if model_index < 3:
                lines.append(line)
                continue
            capacitance = _estimate_macro_capacitance(tokens[model_index + 1 :], projection_options)
            lines.append(f"C{tokens[0][1:]} {tokens[1]} {tokens[2]} {capacitance:.8g}")
            projected_capacitors += 1
            continue
        lines.append(line)
    feedback: dict[str, Any] = {}
    total = projected_mos + projected_resistors + projected_capacitors
    if total:
        feedback.update(
            {
                "prelayout_macro_projection": True,
                "prelayout_projected_mos": projected_mos,
                "prelayout_projected_resistors": projected_resistors,
                "prelayout_projected_capacitors": projected_capacitors,
                "prelayout_projection_scope": "macro_to_sky130_approximation",
            }
        )
    return "\n".join(lines) + "\n", feedback


def _find_macro_model_index(tokens: list[str]) -> int | None:
    models = MAGICAL_NMOS_ALIASES | MAGICAL_PMOS_ALIASES | MAGICAL_RESISTOR_ALIASES | MAGICAL_CAPACITOR_ALIASES
    for index, token in enumerate(tokens[1:], start=1):
        if token.split("=", 1)[0].lower() in models:
            return index
    return None


def _normalize_instance_param_token(token: str) -> str:
    key = token.split("=", 1)[0].lower()
    if key == "multi":
        return "m=" + token.split("=", 1)[1] if "=" in token else token
    return token


def _estimate_macro_resistance(tokens: list[str], options: dict[str, Any]) -> float:
    params = _param_dict(tokens)
    sheet = float(options.get("rppolywo_sheet_ohms", 48.0))
    lr = _spice_value_to_si(params.get("lr", "1u"))
    wr = _spice_value_to_si(params.get("wr", "1u"))
    series = float(params.get("series", 1.0))
    return max(sheet * max(lr, 1e-12) / max(wr, 1e-12) * max(series, 1.0), 1e-3)


def _estimate_macro_capacitance(tokens: list[str], options: dict[str, Any]) -> float:
    params = _param_dict(tokens)
    unit_cap_f = float(options.get("cfmom_unit_cap_f", 1.0e-15))
    nr = float(params.get("nr", 1.0))
    multi = float(params.get("multi", params.get("m", 1.0)))
    return max(unit_cap_f * max(nr, 1.0) * max(multi, 1.0), 1e-18)


def _param_dict(tokens: list[str]) -> dict[str, str]:
    params: dict[str, str] = {}
    for token in tokens:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        params[key.lower()] = value
    return params


def _spice_value_to_si(value: str) -> float:
    match = re.match(r"^\s*(?P<number>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)(?P<unit>[A-Za-z]*)\s*$", str(value))
    if not match:
        return 0.0
    number = float(match.group("number"))
    unit = match.group("unit").lower()
    scale = {
        "f": 1e-15,
        "p": 1e-12,
        "n": 1e-9,
        "u": 1e-6,
        "m": 1e-3,
        "k": 1e3,
        "meg": 1e6,
        "g": 1e9,
    }.get(unit, 1.0)
    return number * scale


def parse_sky130_model_bins(path: Path) -> list[Sky130ModelBin]:
    bins: list[Sky130ModelBin] = []
    current: dict[str, float] | None = None
    current_name: str = ""
    current_lines: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        model_match = MODEL_BIN_RE.match(line)
        if model_match:
            _append_model_bin(bins, current, current_name, current_lines)
            current = {}
            current_name = model_match.group("name")
            current_lines = [line]
            continue
        if current is not None and line.strip().lower().startswith(".ends"):
            _append_model_bin(bins, current, current_name, current_lines)
            current = None
            current_name = ""
            current_lines = []
            continue
        if current is None:
            continue
        current_lines.append(line)
        for match in MODEL_BOUND_RE.finditer(line):
            current[match.group("key").lower()] = float(match.group("value"))
    _append_model_bin(bins, current, current_name, current_lines)
    return bins


def _append_model_bin(
    bins: list[Sky130ModelBin],
    bounds: dict[str, float] | None,
    model_name: str,
    model_lines: list[str],
) -> None:
    if not bounds:
        return
    required = ("lmin", "lmax", "wmin", "wmax")
    if not all(key in bounds for key in required):
        return
    bins.append(
        Sky130ModelBin(
            lmin_um=bounds["lmin"] * 1e6,
            lmax_um=bounds["lmax"] * 1e6,
            wmin_um=bounds["wmin"] * 1e6,
            wmax_um=bounds["wmax"] * 1e6,
            model_name=model_name,
            model_lines=tuple(model_lines),
        )
    )


def _corner_model_path(spice_dir: Path, device: str, corner: str) -> Path:
    corner_path = spice_dir / f"{device}__{corner}.pm3.spice"
    if corner_path.is_file():
        return corner_path
    return spice_dir / f"{device}.pm3.spice"


def snap_magic_extracted_model_bins(
    netlist_text: str,
    bins_by_device: dict[str, list[Sky130ModelBin]],
) -> tuple[str, int]:
    lines: list[str] = []
    snapped_count = 0
    for line in netlist_text.splitlines():
        stripped = line.lstrip()
        if not stripped.lower().startswith("x") or "sky130_fd_pr__" not in line:
            lines.append(line)
            continue
        projected, snapped = _snap_primitive_line(line, bins_by_device)
        lines.append(projected)
        snapped_count += int(snapped)
    return "\n".join(lines) + "\n", snapped_count


def project_sky130_primitives_to_direct_models(
    netlist_text: str,
    bins_by_device: dict[str, list[Sky130ModelBin]],
) -> tuple[str, int, int]:
    lines: list[str] = []
    model_definitions: dict[str, list[str]] = {}
    snapped_count = 0
    for line in netlist_text.splitlines():
        stripped = line.lstrip()
        if not stripped.lower().startswith("x") or "sky130_fd_pr__" not in line:
            lines.append(line)
            continue
        projected, snapped, alias, model_lines = _project_primitive_line_to_direct_model(line, bins_by_device)
        lines.append(projected)
        snapped_count += int(snapped)
        if alias and model_lines and alias not in model_definitions:
            model_definitions[alias] = _renamed_model_lines(alias, model_lines)
    if not model_definitions:
        return "\n".join(lines) + "\n", snapped_count, 0
    prelude = ["* Harness-generated direct Sky130 model projection for ngspice compatibility"]
    prelude.extend(_direct_model_compat_param_lines(model_definitions))
    for definition in model_definitions.values():
        prelude.extend(definition)
    return "\n".join(prelude + ["", *lines]) + "\n", snapped_count, len(model_definitions)


def _snap_primitive_line(
    line: str,
    bins_by_device: dict[str, list[Sky130ModelBin]],
) -> tuple[str, bool]:
    tokens = line.split()
    model_index = next((index for index, token in enumerate(tokens) if token in bins_by_device), None)
    if model_index is None:
        return line, False
    params: dict[str, str] = {}
    for token in tokens[model_index + 1 :]:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        params[key.lower()] = value
    if "l" not in params or "w" not in params:
        return line, False
    current_l = _spice_value_to_um(params["l"])
    current_w = _spice_value_to_um(params["w"])
    model_bins = bins_by_device[tokens[model_index]]
    if any(model_bin.contains_interior(current_l, current_w) for model_bin in model_bins):
        return line, False
    nearest = _nearest_model_bin(current_l, current_w, model_bins)
    if nearest is None:
        return line, False
    snapped = not (
        math.isclose(current_l, nearest.center_l_um, rel_tol=1e-6, abs_tol=1e-9)
        and math.isclose(current_w, nearest.center_w_um, rel_tol=1e-6, abs_tol=1e-9)
    )
    if not snapped:
        return line, False
    updated: list[str] = []
    for token in tokens:
        if token.lower().startswith("l="):
            updated.append(f"l={nearest.center_l_um:.8g}u")
        elif token.lower().startswith("w="):
            updated.append(f"w={nearest.center_w_um:.8g}u")
        else:
            updated.append(token)
    return " ".join(updated), True


def _project_primitive_line_to_direct_model(
    line: str,
    bins_by_device: dict[str, list[Sky130ModelBin]],
) -> tuple[str, bool, str | None, tuple[str, ...]]:
    tokens = line.split()
    model_index = next((index for index, token in enumerate(tokens) if token in bins_by_device), None)
    if model_index is None:
        return line, False, None, ()
    nodes = tokens[1:model_index]
    if len(nodes) != 4:
        return line, False, None, ()
    params: dict[str, str] = {}
    for token in tokens[model_index + 1 :]:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        params[key.lower()] = value
    if "l" not in params or "w" not in params:
        return line, False, None, ()
    current_l = _spice_value_to_um(params["l"])
    current_w = _spice_value_to_um(params["w"])
    selected = _containing_model_bin(current_l, current_w, bins_by_device[tokens[model_index]])
    snapped = False
    if selected is None:
        selected = _nearest_model_bin(current_l, current_w, bins_by_device[tokens[model_index]])
        snapped = selected is not None
    if selected is None or not selected.model_lines:
        return line, False, None, ()
    alias = _model_alias(tokens[model_index], selected)
    instance = "M" + tokens[0][1:]
    updated_params: list[str] = []
    for token in tokens[model_index + 1 :]:
        if snapped and token.lower().startswith("l="):
            updated_params.append(f"l={selected.center_l_um:.8g}u")
        elif snapped and token.lower().startswith("w="):
            updated_params.append(f"w={selected.center_w_um:.8g}u")
        elif token.lower().startswith("multi="):
            updated_params.append("m=" + token.split("=", 1)[1])
        elif token.lower().startswith("mult="):
            updated_params.append("m=" + token.split("=", 1)[1])
        else:
            updated_params.append(token)
    return " ".join([instance, *nodes, alias, *updated_params]), snapped, alias, selected.model_lines


def _containing_model_bin(l_um: float, w_um: float, bins: list[Sky130ModelBin]) -> Sky130ModelBin | None:
    for model_bin in bins:
        if model_bin.contains_interior(l_um, w_um):
            return model_bin
    return None


def _model_alias(device: str, model_bin: Sky130ModelBin) -> str:
    suffix = model_bin.model_name.rsplit(".", 1)[-1] if model_bin.model_name else "compat"
    short_device = device.replace("sky130_fd_pr__", "").replace("_01v8", "")
    return f"sky130_harness_{short_device}_{suffix}"


def _renamed_model_lines(alias: str, model_lines: tuple[str, ...]) -> list[str]:
    if not model_lines:
        return []
    renamed = [re.sub(r"^(\s*\.model\s+)\S+", rf"\1{alias}", model_lines[0], flags=re.IGNORECASE)]
    renamed.extend(model_lines[1:])
    return renamed


def _direct_model_compat_param_lines(model_definitions: dict[str, list[str]]) -> list[str]:
    """Define Sky130 corner parameters lost when copying selected .model blocks."""

    param_names: set[str] = set()
    for definition in model_definitions.values():
        for line in definition:
            for match in SKY130_EXTERNAL_PARAM_RE.finditer(line):
                name = match.group("name").lower()
                if "__model" not in name:
                    param_names.add(name)
    local_defaults = [
        f".param {name}={value}"
        for name, value in SKY130_DIRECT_MODEL_LOCAL_DEFAULTS.items()
    ]
    external_defaults = [f".param {name}=0" for name in sorted(param_names)]
    return local_defaults + external_defaults


def _nearest_model_bin(l_um: float, w_um: float, bins: list[Sky130ModelBin]) -> Sky130ModelBin | None:
    if not bins or l_um <= 0.0 or w_um <= 0.0:
        return None

    def score(model_bin: Sky130ModelBin) -> float:
        l_target = min(max(l_um, model_bin.lmin_um), model_bin.lmax_um)
        w_target = min(max(w_um, model_bin.wmin_um), model_bin.wmax_um)
        return abs(math.log(l_um / l_target)) + abs(math.log(w_um / w_target))

    return min(bins, key=score)


def _spice_value_to_um(value: str) -> float:
    match = re.match(r"^\s*(?P<number>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)(?P<unit>[A-Za-z]*)\s*$", value)
    if not match:
        return 0.0
    number = float(match.group("number"))
    unit = match.group("unit").lower()
    if unit in {"u", "um"}:
        return number
    if unit == "n":
        return number / 1000.0
    if unit == "m":
        return number * 1000.0
    if unit == "":
        return number
    return number
