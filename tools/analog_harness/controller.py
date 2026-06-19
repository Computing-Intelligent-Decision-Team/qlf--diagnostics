"""Top-level adaptive closure harness controller."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .archive import KnowledgeTransferArchive
from .config import HarnessConfig
from .frontend import FrontEndResultLoader
from .layout import LayoutVerificationAdapter, classify_passive_aware_evidence
from .legalizer import SizingLegalizer
from .models import EvidencePacket
from .optimizer import AnalogGymGRPOAdapter, aggregate_reward, closure_level_from_evidence
from .sim import AnalogGymTemplateSimulator
from .spice import SpiceCandidateCompiler
from .state import CandidateStore


PASSIVE_EVIDENCE_STATUS_RANK = {
    "skipped": 0,
    "unsupported": 1,
    "formal_abstraction_pass": 2,
    "formal_abstraction_with_gds_mos_bridge_pass": 3,
    "pass": 4,
}


class HarnessController:
    def __init__(self, config: HarnessConfig):
        self.config = config
        self.legalizer = SizingLegalizer(config.variables)
        self.store = CandidateStore(config.run_dir)
        self.compiler = SpiceCandidateCompiler(config, self.legalizer)
        self.simulator = AnalogGymTemplateSimulator(config)
        self.layout = LayoutVerificationAdapter(config)
        self.optimizer = AnalogGymGRPOAdapter(config, self.legalizer)
        self.frontend_loader = FrontEndResultLoader(config, self.legalizer)
        self.archive = KnowledgeTransferArchive(config)

    def run(
        self,
        max_candidates: int,
        batch_size: int = 1,
        layout_budget: int = 1,
        skip_layout: bool = False,
        skip_sim: bool = False,
        use_frontend_results: bool = True,
        force_sizing: bool = False,
        archive_good_models: bool = True,
    ) -> dict[str, Any]:
        history = self.store.read_candidate_states()
        self.optimizer.initialize(self._contract(), history)
        self.optimizer.warm_start(self.archive.warm_start_records())
        frontend_queue = (
            self.frontend_loader.proposals(history)
            if use_frontend_results and not force_sizing
            else []
        )
        completed: list[dict[str, Any]] = []
        layout_runs = 0
        force_optimizer_next = bool(force_sizing)
        while len(completed) < max_candidates:
            remaining = max_candidates - len(completed)
            context = {
                "completed_candidates": len(history) + len(completed),
                "frontend_candidates_available": len(frontend_queue),
                "force_optimizer_next": force_optimizer_next,
            }
            if frontend_queue and not force_optimizer_next:
                proposals = [frontend_queue.pop(0)]
            else:
                proposals = self.optimizer.propose(context, min(batch_size, remaining))
                force_optimizer_next = False
            for proposal in proposals:
                candidate_id = self.store.next_candidate_id()
                compiled = self.compiler.compile(candidate_id, proposal.values, proposal.action_normalized)
                evidence: list[EvidencePacket] = []

                pre = self.simulator.evaluate_pre_layout(compiled, skip_sim=skip_sim)
                evidence.append(pre)
                self.store.append_evidence(pre)

                if not skip_layout and layout_runs < layout_budget:
                    layout = self.layout.run(compiled, skip_layout=False)
                    evidence.append(layout)
                    self.store.append_evidence(layout)
                    layout_runs += 1
                    passive_probe = self.layout.passive_aware_probe(compiled, layout)
                    if passive_probe.status != "skipped":
                        evidence.append(passive_probe)
                        self.store.append_evidence(passive_probe)

                    extracted = None
                    if layout.status == "pass" and layout.artifacts.get("raw_extracted_netlist"):
                        extracted = Path(layout.artifacts["raw_extracted_netlist"])
                    post = self.simulator.evaluate_post_layout(compiled, extracted, skip_sim=skip_sim)
                    evidence.append(post)
                    self.store.append_evidence(post)
                    if post.status == "pass" and self.simulator.pvt_enabled:
                        pvt = self.simulator.evaluate_post_layout_pvt(compiled, extracted, skip_sim=skip_sim)
                        evidence.append(pvt)
                        self.store.append_evidence(pvt)
                elif skip_layout:
                    layout = self.layout.run(compiled, skip_layout=True)
                    evidence.append(layout)
                    self.store.append_evidence(layout)

                self.optimizer.observe(candidate_id, evidence)
                reward = aggregate_reward(self.config.performance, evidence)
                redesign_request = self._redesign_request(evidence, reward)
                if redesign_request is not None:
                    if redesign_request.get("owner") == "sizing_optimizer":
                        self.optimizer.update_constraints(redesign_request)
                        force_optimizer_next = True
                state = self._candidate_state(candidate_id, proposal, compiled, evidence, reward, redesign_request)
                self.store.write_candidate_state(candidate_id, state)
                if archive_good_models:
                    self.archive.consider(state)
                completed.append(state)
                if len(completed) >= max_candidates:
                    break

        summary = self.summarize()
        summary["new_candidates"] = len(completed)
        return summary

    def summarize(self) -> dict[str, Any]:
        states = self.store.read_candidate_states()
        best = None
        normalized_states = [self._state_with_current_scores(state) for state in states]
        for state in normalized_states:
            if best is None or float(state.get("reward", -1e9)) >= float(best.get("reward", -1e9)):
                best = state
        best_passive = self._packet_by_stage(best, "passive_aware_lvs") if best else None
        best_passive_metrics = best_passive.get("metrics", {}) if best_passive else {}
        best_passive_physical = best_passive.get("physical_feedback", {}) if best_passive else {}
        summary = {
            "design_id": self.config.design_id,
            "top_cell": self.config.top_cell,
            "run_dir": str(self.config.run_dir),
            "verification_scope": self.config.verification_scope,
            "candidate_count": len(states),
            "best_candidate": None if best is None else best.get("candidate_id"),
            "best_reward": None if best is None else best.get("reward"),
            "best_closure_level": None if best is None else best.get("closure_level"),
            "best_passive_aware_status": None if best_passive is None else best_passive.get("status"),
            "best_passive_aware_scope": None
            if best_passive is None
            else best_passive.get("verification_scope"),
            "best_passive_lvs_evidence_scope": best_passive_metrics.get("passive_lvs_evidence_scope"),
            "best_segmented_resistor_chain_formalized": best_passive_metrics.get(
                "passive_requirement_segmented_resistor_chain_formalized"
            ),
            "best_cfmom_plate_coupling_formalized": best_passive_metrics.get(
                "passive_requirement_cfmom_plate_coupling_formalized"
            ),
            "best_passive_lvs_primitive_abstractions": best_passive_metrics.get(
                "passive_lvs_primitive_abstractions"
            ),
            "best_route_bridge_trial_status": best_passive_metrics.get(
                "passive_resistor_variant_best_route_bridge_trial_status"
            ),
            "best_route_bridge_drc_count": best_passive_metrics.get(
                "passive_resistor_variant_best_route_bridge_drc_count"
            ),
            "best_route_bridge_mos_connectivity_status": best_passive_metrics.get(
                "passive_resistor_variant_best_route_bridge_mos_connectivity_status"
            ),
            "best_route_bridge_formal_passive_lvs_netgen_status": best_passive_metrics.get(
                "passive_resistor_variant_best_route_bridge_formal_passive_lvs_netgen_status"
            ),
            "best_full_passive_inclusive_gds_lvs_proven": best_passive_metrics.get(
                "full_passive_inclusive_gds_lvs_proven",
                best_passive_physical.get("full_passive_inclusive_gds_lvs_proven"),
            ),
            "best_native_passive_device_recognition_status": best_passive_metrics.get(
                "native_passive_device_recognition_status",
                best_passive_physical.get("native_passive_device_recognition_status"),
            ),
            "best_native_passive_device_recognition_claimed": best_passive_metrics.get(
                "native_passive_device_recognition_claimed",
                best_passive_physical.get("native_passive_device_recognition_claimed"),
            ),
            "best_native_passive_device_recognition_missing_instances": best_passive_metrics.get(
                "native_passive_device_recognition_missing_instances",
                best_passive_physical.get("native_passive_device_recognition_missing_instances"),
            ),
            "best_native_passive_device_recognition_blockers": best_passive_metrics.get(
                "native_passive_device_recognition_blockers",
                best_passive_physical.get("native_passive_device_recognition_blockers"),
            ),
            "best_native_passive_capability_source_model_native_status": best_passive_metrics.get(
                "native_passive_capability_source_model_native_status"
            ),
            "best_native_passive_capability_direct_source_model_support": best_passive_metrics.get(
                "native_passive_capability_direct_source_model_support"
            ),
            "best_native_passive_capability_unsupported_source_models": best_passive_metrics.get(
                "native_passive_capability_unsupported_source_models"
            ),
            "best_native_passive_capability_retarget_available": best_passive_metrics.get(
                "native_passive_capability_retarget_available"
            ),
            "best_native_passive_capability_retarget_map": best_passive_metrics.get(
                "native_passive_capability_retarget_map"
            ),
            "best_native_passive_capability_requires_geometry_replacement": best_passive_metrics.get(
                "native_passive_capability_requires_geometry_replacement"
            ),
            "best_native_passive_capability_can_fix_current_gds_by_layer_remap_only": best_passive_metrics.get(
                "native_passive_capability_can_fix_current_gds_by_layer_remap_only"
            ),
            "best_native_passive_capability_device_generation_source_status": best_passive_metrics.get(
                "native_passive_capability_device_generation_source_status"
            ),
            "best_native_passive_retarget_trial_status": best_passive_metrics.get(
                "native_passive_retarget_trial_status"
            ),
            "best_native_resistor_chain_status": best_passive_metrics.get(
                "native_resistor_chain_status"
            ),
            "best_native_resistor_chain_netgen_status": best_passive_metrics.get(
                "native_resistor_chain_netgen_status"
            ),
            "best_native_resistor_chain_device_count": best_passive_metrics.get(
                "native_resistor_chain_device_count"
            ),
            "best_native_resistor_chain_model": best_passive_metrics.get(
                "native_resistor_chain_model"
            ),
            "best_native_capacitor_device_recognition_status": best_passive_metrics.get(
                "native_capacitor_device_recognition_status"
            ),
            "best_native_passive_retarget_missing_native_source_passive_instances": (
                best_passive_metrics.get(
                    "native_passive_retarget_missing_native_source_passive_instances"
                )
            ),
            "best_native_passive_retarget_full_native_passive_lvs_ready": best_passive_metrics.get(
                "native_passive_retarget_full_native_passive_lvs_ready"
            ),
            "best_native_passive_retarget_full_native_passive_lvs_proven": best_passive_metrics.get(
                "native_passive_retarget_full_native_passive_lvs_proven",
                best_passive_physical.get("native_passive_retarget_full_native_passive_lvs_proven"),
            ),
            "best_native_cap_gencell_extraction_status": best_passive_metrics.get(
                "native_cap_gencell_extraction_status"
            ),
            "best_native_cap_gencell_model": best_passive_metrics.get("native_cap_gencell_model"),
            "best_native_cap_gencell_recognized_device_count": best_passive_metrics.get(
                "native_cap_gencell_recognized_device_count"
            ),
            "best_native_cap_replacement_status": best_passive_metrics.get(
                "native_cap_replacement_status"
            ),
            "best_native_cap_replacement_cell_name": best_passive_metrics.get(
                "native_cap_replacement_cell_name"
            ),
            "best_native_cap_replacement_terminal_bridge_status": best_passive_metrics.get(
                "native_cap_replacement_terminal_bridge_status"
            ),
            "best_native_cap_replacement_top_gds_merge_status": best_passive_metrics.get(
                "native_cap_replacement_top_gds_merge_status"
            ),
            "best_native_cap_replacement_bridge_mode": best_passive_metrics.get(
                "native_cap_replacement_bridge_mode"
            ),
            "best_native_cap_replacement_full_gds": best_passive_metrics.get(
                "native_cap_replacement_full_gds"
            ),
            "best_native_cap_replacement_extract_status": best_passive_metrics.get(
                "native_cap_replacement_extract_status"
            ),
            "best_native_cap_replacement_drc_status": best_passive_metrics.get(
                "native_cap_replacement_drc_status"
            ),
            "best_native_cap_replacement_drc_count": best_passive_metrics.get(
                "native_cap_replacement_drc_count"
            ),
            "best_native_cap_replacement_native_passive_netgen_status": best_passive_metrics.get(
                "native_cap_replacement_native_passive_netgen_status"
            ),
            "best_native_cap_replacement_native_capacitor_device_count": best_passive_metrics.get(
                "native_cap_replacement_native_capacitor_device_count"
            ),
            "best_native_cap_full_gds_trial_status": best_passive_metrics.get(
                "native_cap_full_gds_trial_status"
            ),
            "best_native_cap_full_gds_trial_summary_json": best_passive_metrics.get(
                "native_cap_full_gds_trial_summary_json"
            ),
            "best_native_cap_replacement_full_native_capacitor_lvs_ready": best_passive_metrics.get(
                "native_cap_replacement_full_native_capacitor_lvs_ready"
            ),
            "best_native_cap_replacement_remaining_gates": best_passive_metrics.get(
                "native_cap_replacement_remaining_gates"
            ),
            "best_passive_evidence_backfilled_from_artifacts": None
            if best is None
            else best.get("passive_evidence_backfilled_from_artifacts", False),
            "knowledge_transfer_archive": str(self.archive.archive_dir),
        }
        for state in normalized_states:
            if state.get("passive_evidence_backfilled_from_artifacts"):
                self.store.write_candidate_state(str(state["candidate_id"]), state)
        self.archive.rebuild_warm_start_bank(normalized_states)
        self._write_summary_markdown(summary, normalized_states)
        return summary

    def prepare_grpo_training(self, steps: int = 300) -> dict[str, Any]:
        history = self.store.read_candidate_states()
        self.optimizer.initialize(self._contract(), history)
        self.optimizer.warm_start(self.archive.warm_start_records())
        manifest = self.optimizer.prepare_long_training_interface(self.archive.archive_dir, max(1, int(steps)))
        return manifest

    def _contract(self) -> dict[str, Any]:
        return {
            "design_id": self.config.design_id,
            "top_cell": self.config.top_cell,
            "action_dim": self.legalizer.action_dim,
            "variables": [variable.__dict__ for variable in self.legalizer.variables],
            "performance": self.config.performance,
            "verification_scope": self.config.verification_scope,
        }

    def _candidate_state(
        self,
        candidate_id: str,
        proposal: Any,
        compiled: Any,
        evidence: list[EvidencePacket],
        reward: float,
        redesign_request: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return {
            "candidate_id": candidate_id,
            "design_id": self.config.design_id,
            "top_cell": self.config.top_cell,
            "optimizer_source": proposal.source,
            "optimizer_metadata": proposal.metadata,
            "action_normalized": proposal.action_normalized,
            "values": proposal.values,
            "assignments": compiled.assignments,
            "reward": reward,
            "closure_level": closure_level_from_evidence(evidence),
            "redesign_request": redesign_request,
            "verification_scope": self.config.verification_scope,
            "artifacts": {
                "candidate_dir": str(compiled.candidate_dir),
                "case_dir": str(compiled.case_dir),
                "layout_out_dir": str(compiled.out_dir),
                "netlist": str(compiled.netlist_path),
                "config": str(compiled.config_path),
            },
            "evidence": [packet.to_dict() for packet in evidence],
        }

    def _redesign_request(self, evidence: list[EvidencePacket], reward: float) -> dict[str, Any] | None:
        repair_threshold = float(self.config.data.get("policy", {}).get("sizing_repair_reward_threshold", -0.05))
        failing_packets = [packet for packet in evidence if packet.status == "fail"]
        model_bin_failures = [
            packet
            for packet in evidence
            if packet.stage == "post_sim"
            and packet.status in {"fail", "proxy_fallback"}
            and packet.physical_feedback.get("ngspice_failure_category") == "sky130_model_bin_mismatch"
        ]
        if model_bin_failures:
            return {
                "owner": "sizing_optimizer",
                "action": "propose_model_safe_sizing",
                "reasons": ["post_sim:sky130_model_bin_mismatch"],
                "latest_closure_level": closure_level_from_evidence(evidence),
                "verification_scope": self.config.verification_scope,
            }
        layout_failures = [
            packet
            for packet in evidence
            if packet.stage == "layout_verification" and packet.status in {"fail", "unknown"}
        ]
        runtime_failures = [
            packet
            for packet in layout_failures
            if bool(packet.physical_feedback.get("runtime_failure"))
        ]
        if runtime_failures:
            reasons = []
            for packet in runtime_failures:
                failed_stage = packet.physical_feedback.get("failed_stage")
                message = packet.physical_feedback.get("message")
                reasons.append(": ".join(str(item) for item in (failed_stage, message) if item))
            return {
                "owner": "eda_runtime",
                "action": "fix_eda_environment",
                "reasons": reasons or ["layout runtime failed before DRC/LVS metrics were produced"],
                "latest_closure_level": closure_level_from_evidence(evidence),
                "verification_scope": self.config.verification_scope,
            }
        if reward >= repair_threshold and not failing_packets and not layout_failures:
            return None
        reasons: list[str] = []
        if reward < repair_threshold:
            reasons.append(f"reward {reward:.6g} below threshold {repair_threshold:.6g}")
        reasons.extend(f"{packet.stage}:{packet.status}" for packet in failing_packets)
        reasons.extend(f"{packet.stage}:{packet.status}" for packet in layout_failures)
        return {
            "owner": "sizing_optimizer",
            "action": "propose_repaired_sizing",
            "reasons": reasons,
            "latest_closure_level": closure_level_from_evidence(evidence),
            "verification_scope": self.config.verification_scope,
        }

    def _write_summary_markdown(self, summary: dict[str, Any], states: list[dict[str, Any]]) -> None:
        lines = [
            "# Analog Harness Summary",
            "",
            "| Field | Value |",
            "| --- | --- |",
        ]
        for key, value in summary.items():
            lines.append(f"| {key} | {value} |")
        lines.extend(["", "## Candidates", "", "| Candidate | Reward | Closure | Scope |"])
        lines.append("| --- | ---: | --- | --- |")
        for state in states:
            lines.append(
                f"| {state.get('candidate_id')} | {state.get('reward')} | "
                f"{state.get('closure_level')} | {state.get('verification_scope')} |"
            )
        self.config.run_dir.mkdir(parents=True, exist_ok=True)
        (self.config.run_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (self.config.run_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _state_with_current_scores(self, state: dict[str, Any]) -> dict[str, Any]:
        state = self._state_with_passive_artifact_evidence(state)
        packets = [
            EvidencePacket(**packet)
            for packet in state.get("evidence", [])
            if isinstance(packet, dict)
        ]
        if not packets:
            return state
        normalized = dict(state)
        normalized["closure_level"] = closure_level_from_evidence(packets)
        normalized["reward"] = aggregate_reward(self.config.performance, packets)
        return normalized

    def _state_with_passive_artifact_evidence(self, state: dict[str, Any]) -> dict[str, Any]:
        packet = self._passive_packet_from_artifacts(state)
        if packet is None:
            return state
        evidence = [item for item in state.get("evidence", []) if isinstance(item, dict)]
        current = next((item for item in evidence if item.get("stage") == "passive_aware_lvs"), None)
        if current is not None and _passive_packet_is_current_or_better(current, packet):
            return state
        replaced = False
        updated_evidence: list[dict[str, Any]] = []
        for item in evidence:
            if item.get("stage") == "passive_aware_lvs":
                updated_evidence.append(packet.to_dict())
                replaced = True
            else:
                updated_evidence.append(item)
        if not replaced:
            inserted = False
            updated_evidence = []
            for item in evidence:
                updated_evidence.append(item)
                if item.get("stage") == "layout_verification":
                    updated_evidence.append(packet.to_dict())
                    inserted = True
            if not inserted:
                updated_evidence.append(packet.to_dict())
        normalized = dict(state)
        normalized["evidence"] = updated_evidence
        normalized["passive_evidence_backfilled_from_artifacts"] = True
        return normalized

    def _passive_packet_from_artifacts(self, state: dict[str, Any]) -> EvidencePacket | None:
        candidate_id = str(state.get("candidate_id") or "")
        if not candidate_id:
            return None
        candidate_dir = self._candidate_dir_from_state(state)
        if candidate_dir is None:
            return None
        variant_dir = candidate_dir / "layout_passive_existing_gds" / "resistor_remap_variants"
        resistor_summary_path = variant_dir / "resistor_remap_variant_probe_summary.json"
        evidence_summary_path = variant_dir / "passive_lvs_evidence_summary.json"
        capability_summary_path = (
            variant_dir / "native_passive_capability" / "native_passive_capability_summary.json"
        )
        native_retarget_summary_path = (
            variant_dir / "native_passive_retarget_trial" / "native_passive_retarget_summary.json"
        )
        cap_gencell_summary_path = (
            variant_dir / "native_cap_gencell_probe" / "native_cap_gencell_summary.json"
        )
        cap_replacement_summary_path = (
            variant_dir / "native_cap_replacement_candidate" / "native_cap_replacement_summary.json"
        )
        cap_full_gds_trial_summary_path = (
            variant_dir / "native_cap_full_gds_trial" / "native_cap_full_gds_trial_summary.json"
        )
        if not cap_full_gds_trial_summary_path.is_file():
            cap_full_gds_trial_summary_path = (
                variant_dir
                / "native_cap_full_gds_trial_m4outside"
                / "native_passive_retarget"
                / "native_passive_retarget_summary.json"
            )
        if not resistor_summary_path.is_file():
            return None
        try:
            resistor_summary = json.loads(resistor_summary_path.read_text(encoding="utf-8"))
            evidence_summary = (
                json.loads(evidence_summary_path.read_text(encoding="utf-8"))
                if evidence_summary_path.is_file()
                else {}
            )
            capability_summary = (
                json.loads(capability_summary_path.read_text(encoding="utf-8"))
                if capability_summary_path.is_file()
                else {}
            )
            native_retarget_summary = (
                json.loads(native_retarget_summary_path.read_text(encoding="utf-8"))
                if native_retarget_summary_path.is_file()
                else {}
            )
            cap_gencell_summary = (
                json.loads(cap_gencell_summary_path.read_text(encoding="utf-8"))
                if cap_gencell_summary_path.is_file()
                else {}
            )
            cap_replacement_summary = (
                json.loads(cap_replacement_summary_path.read_text(encoding="utf-8"))
                if cap_replacement_summary_path.is_file()
                else {}
            )
            cap_full_gds_trial_summary = (
                json.loads(cap_full_gds_trial_summary_path.read_text(encoding="utf-8"))
                if cap_full_gds_trial_summary_path.is_file()
                else {}
            )
        except (OSError, json.JSONDecodeError):
            return None
        if isinstance(capability_summary, dict) and capability_summary:
            resistor_summary = dict(resistor_summary)
            resistor_summary.update(
                {
                    "native_passive_capability_probe_status": "pass",
                    "native_passive_capability_source_model_native_status": capability_summary.get(
                        "source_model_native_status"
                    ),
                    "native_passive_capability_direct_source_model_support": capability_summary.get(
                        "direct_source_model_support"
                    ),
                    "native_passive_capability_unsupported_source_models": capability_summary.get(
                        "unsupported_source_models"
                    ),
                    "native_passive_capability_retarget_available": capability_summary.get(
                        "native_retarget_available"
                    ),
                    "native_passive_capability_retarget_map": capability_summary.get(
                        "native_retarget_map"
                    ),
                    "native_passive_capability_requires_geometry_replacement": capability_summary.get(
                        "native_retarget_requires_geometry_replacement"
                    ),
                    "native_passive_capability_can_fix_current_gds_by_layer_remap_only": capability_summary.get(
                        "can_fix_current_gds_by_layer_remap_only"
                    ),
                    "native_passive_capability_device_generation_source_status": capability_summary.get(
                        "device_generation_source_status"
                    ),
                    "native_passive_capability_summary_json": str(capability_summary_path),
                    "native_passive_capability_report": str(
                        capability_summary_path.with_name("native_passive_capability_report.md")
                    ),
                    "native_passive_capability_log": str(
                        capability_summary_path.with_name("native_passive_capability.log")
                    ),
                }
            )
        if isinstance(native_retarget_summary, dict) and native_retarget_summary:
            resistor_summary = dict(resistor_summary)
            native_netgen = native_retarget_summary.get("native_resistor_chain_netgen")
            if not isinstance(native_netgen, dict):
                native_netgen = {}
            resistor_summary.update(
                {
                    "native_passive_retarget_trial_status": native_retarget_summary.get("status"),
                    "native_passive_retarget_summary_json": str(native_retarget_summary_path),
                    "native_passive_retarget_report": str(
                        native_retarget_summary_path.with_name("native_passive_retarget_report.md")
                    ),
                    "native_passive_retarget_log": str(
                        native_retarget_summary_path.with_name("native_passive_retarget.log")
                    ),
                    "native_resistor_chain_status": native_retarget_summary.get(
                        "native_resistor_chain_status"
                    ),
                    "native_resistor_chain_source_instance": native_retarget_summary.get(
                        "native_resistor_chain_source_instance"
                    ),
                    "native_resistor_chain_device_count": native_retarget_summary.get(
                        "native_resistor_chain_device_count"
                    ),
                    "native_resistor_chain_model": native_retarget_summary.get(
                        "native_resistor_chain_model"
                    ),
                    "native_resistor_chain_netgen_status": native_retarget_summary.get(
                        "native_resistor_chain_netgen_status"
                    ),
                    "native_resistor_chain_netgen_report": native_netgen.get("report"),
                    "native_resistor_chain_netgen_log": native_netgen.get("log"),
                    "native_capacitor_device_recognition_status": native_retarget_summary.get(
                        "native_capacitor_device_recognition_status"
                    ),
                    "native_capacitor_devices": native_retarget_summary.get("native_capacitor_devices"),
                    "native_passive_retarget_missing_native_source_passive_instances": (
                        native_retarget_summary.get("missing_native_source_passive_instances")
                    ),
                    "native_passive_retarget_full_native_passive_lvs_ready": native_retarget_summary.get(
                        "full_native_passive_lvs_ready"
                    ),
                    "native_passive_retarget_full_native_passive_lvs_proven": native_retarget_summary.get(
                        "full_native_passive_lvs_proven"
                    ),
                    "native_passive_retarget_source_native_passive_netlist": native_retarget_summary.get(
                        "source_native_passive_netlist"
                    ),
                    "native_passive_retarget_candidate_native_passive_netlist": native_retarget_summary.get(
                        "candidate_native_passive_netlist"
                    ),
                }
            )
        if isinstance(cap_gencell_summary, dict) and cap_gencell_summary:
            resistor_summary = dict(resistor_summary)
            resistor_summary.update(
                {
                    "native_cap_gencell_probe_status": cap_gencell_summary.get(
                        "native_cap_gencell_extraction_status"
                    ),
                    "native_cap_gencell_extraction_status": cap_gencell_summary.get(
                        "native_cap_gencell_extraction_status"
                    ),
                    "native_cap_gencell_model": cap_gencell_summary.get("model"),
                    "native_cap_gencell_cell_name": cap_gencell_summary.get("cell_name"),
                    "native_cap_gencell_recognized_device_count": cap_gencell_summary.get(
                        "recognized_native_capacitor_device_count"
                    ),
                    "native_cap_gencell_devices": cap_gencell_summary.get("native_capacitor_devices"),
                    "native_cap_gencell_summary_json": str(cap_gencell_summary_path),
                    "native_cap_gencell_report": str(
                        cap_gencell_summary_path.with_name("native_cap_gencell_report.md")
                    ),
                    "native_cap_gencell_log": str(
                        cap_gencell_summary_path.with_name("native_cap_gencell.log")
                    ),
                    "native_cap_gencell_magic_log": cap_gencell_summary.get("log"),
                    "native_cap_gencell_spice": cap_gencell_summary.get("spice"),
                    "native_cap_gencell_mag": cap_gencell_summary.get("mag"),
                    "native_cap_gencell_gds": cap_gencell_summary.get("gds"),
                    "native_cap_gencell_ext": cap_gencell_summary.get("ext"),
                }
            )
        if isinstance(cap_replacement_summary, dict) and cap_replacement_summary:
            resistor_summary = dict(resistor_summary)
            resistor_summary.update(
                {
                    "native_cap_replacement_status": cap_replacement_summary.get("status"),
                    "native_cap_replacement_summary_json": str(cap_replacement_summary_path),
                    "native_cap_replacement_report": str(
                        cap_replacement_summary_path.with_name("native_cap_replacement_report.md")
                    ),
                    "native_cap_replacement_cell_name": cap_replacement_summary.get(
                        "replacement_cell_name"
                    ),
                    "native_cap_replacement_gds": cap_replacement_summary.get("replacement_gds"),
                    "native_cap_replacement_spice": cap_replacement_summary.get("replacement_spice"),
                    "native_cap_replacement_magic_log": cap_replacement_summary.get(
                        "replacement_magic_log"
                    ),
                    "native_cap_replacement_terminal_bridge_status": cap_replacement_summary.get(
                        "terminal_bridge_status"
                    ),
                    "native_cap_replacement_top_gds_merge_status": cap_replacement_summary.get(
                        "top_gds_merge_status"
                    ),
                    "native_cap_replacement_full_native_capacitor_lvs_ready": cap_replacement_summary.get(
                        "full_native_capacitor_lvs_ready"
                    ),
                    "native_cap_replacement_remaining_gates": cap_replacement_summary.get(
                        "remaining_gates"
                    ),
                }
            )
        if isinstance(cap_full_gds_trial_summary, dict) and cap_full_gds_trial_summary:
            resistor_summary = dict(resistor_summary)
            full_trial = cap_full_gds_trial_summary
            if full_trial.get("schema_version") == "sky130_native_passive_retarget_trial.v1":
                full_trial = {
                    "status": "pass" if full_trial.get("full_native_passive_lvs_proven") else "incomplete",
                    "native_capacitor_device_recognition_status": full_trial.get(
                        "native_capacitor_device_recognition_status"
                    ),
                    "native_capacitor_device_count": full_trial.get("native_capacitor_device_count"),
                    "native_capacitor_devices": full_trial.get("native_capacitor_devices"),
                    "native_resistor_chain_status": full_trial.get("native_resistor_chain_status"),
                    "native_resistor_chain_device_count": full_trial.get(
                        "native_resistor_chain_device_count"
                    ),
                    "native_passive_netgen_status": full_trial.get("native_passive_netgen_status"),
                    "full_native_passive_lvs_ready": full_trial.get("full_native_passive_lvs_ready"),
                    "full_native_passive_lvs_proven": full_trial.get(
                        "full_native_passive_lvs_proven"
                    ),
                    "verification_scope": "full_passive_inclusive_gds_lvs"
                    if full_trial.get("full_native_passive_lvs_proven")
                    else "native_cap_full_gds_trial",
                    "native_passive_netgen": full_trial.get("native_passive_netgen"),
                }
            full_proven = bool(full_trial.get("full_native_passive_lvs_proven"))
            native_netgen = full_trial.get("native_passive_netgen")
            if not isinstance(native_netgen, dict):
                native_netgen = {}
            resistor_summary.update(
                {
                    "native_cap_full_gds_trial_status": full_trial.get("status"),
                    "native_cap_full_gds_trial_summary_json": str(cap_full_gds_trial_summary_path),
                    "native_cap_replacement_terminal_bridge_status": full_trial.get(
                        "terminal_bridge_status",
                        resistor_summary.get("native_cap_replacement_terminal_bridge_status"),
                    ),
                    "native_cap_replacement_top_gds_merge_status": full_trial.get(
                        "top_gds_merge_status",
                        resistor_summary.get("native_cap_replacement_top_gds_merge_status"),
                    ),
                    "native_cap_replacement_bridge_mode": full_trial.get("bridge_mode"),
                    "native_cap_replacement_full_gds": full_trial.get("merged_gds"),
                    "native_cap_replacement_extract_status": full_trial.get("magic_extract_status"),
                    "native_cap_replacement_drc_status": full_trial.get("drc_status"),
                    "native_cap_replacement_drc_count": full_trial.get("drc_count"),
                    "native_cap_replacement_native_passive_netgen_status": full_trial.get(
                        "native_passive_netgen_status"
                    ),
                    "native_cap_replacement_native_capacitor_device_count": full_trial.get(
                        "native_capacitor_device_count"
                    ),
                    "native_cap_replacement_full_native_capacitor_lvs_ready": full_proven,
                    "native_cap_replacement_remaining_gates": [] if full_proven else resistor_summary.get(
                        "native_cap_replacement_remaining_gates"
                    ),
                    "native_capacitor_device_recognition_status": full_trial.get(
                        "native_capacitor_device_recognition_status"
                    ),
                    "native_capacitor_devices": full_trial.get("native_capacitor_devices"),
                    "native_passive_retarget_missing_native_source_passive_instances": []
                    if full_proven
                    else resistor_summary.get(
                        "native_passive_retarget_missing_native_source_passive_instances"
                    ),
                    "native_passive_retarget_trial_status": full_trial.get(
                        "native_passive_retarget_status"
                    )
                    or ("native_passive_retarget_ready" if full_proven else resistor_summary.get(
                        "native_passive_retarget_trial_status"
                    )),
                    "native_passive_retarget_full_native_passive_lvs_ready": full_trial.get(
                        "full_native_passive_lvs_ready"
                    ),
                    "native_passive_retarget_full_native_passive_lvs_proven": full_trial.get(
                        "full_native_passive_lvs_proven"
                    ),
                    "native_passive_netgen_status": full_trial.get("native_passive_netgen_status"),
                    "native_passive_netgen_report": native_netgen.get("report"),
                    "native_passive_netgen_log": native_netgen.get("log"),
                    "full_passive_inclusive_gds_lvs_proven": full_proven,
                    "full_passive_inclusive_gds_native_lvs_status": "pass" if full_proven else None,
                    "native_passive_device_recognition_status": "pass" if full_proven else None,
                    "native_passive_device_recognition_claimed": full_proven,
                    "native_passive_device_recognition_missing_instances": [] if full_proven else None,
                    "native_passive_device_recognition_blockers": {} if full_proven else None,
                }
            )
        classification = classify_passive_aware_evidence(
            resistor_variant_summary=resistor_summary,
            fallback_reason="No formal passive LVS evidence could be backfilled from artifacts.",
            fallback_scope=self.config.verification_scope,
        )
        if classification["packet_status"] == "unsupported":
            return None
        requirements = evidence_summary.get("requirements", {})
        if not isinstance(requirements, dict):
            requirements = {}
        route_requirements = evidence_summary.get("route_bridge_requirements", {})
        if not isinstance(route_requirements, dict):
            route_requirements = {}
        metrics = self._passive_artifact_metrics(
            resistor_summary=resistor_summary,
            evidence_summary=evidence_summary,
            classification=classification,
            requirements=requirements,
            route_requirements=route_requirements,
            evidence_summary_path=evidence_summary_path,
        )
        artifacts = self._passive_artifact_paths(resistor_summary, evidence_summary, evidence_summary_path)
        return EvidencePacket(
            candidate_id=candidate_id,
            stage="passive_aware_lvs",
            fidelity="E2P",
            status=classification["packet_status"],
            verification_scope=classification["verification_scope"],
            metrics=metrics,
            physical_feedback={
                "passive_aware_requested": True,
                "passive_aware_status": classification["passive_aware_status"],
                "passive_aware_reason": classification["reason"],
                "passive_aware_verification_scope_detail": classification["verification_scope_detail"],
                "formal_passive_abstraction_ready": classification["formal_passive_abstraction_ready"],
                "formal_passive_only_lvs_match": classification["formal_passive_only_lvs_match"],
                "hybrid_mos_reference_passive_lvs_match": classification[
                    "hybrid_mos_reference_passive_lvs_match"
                ],
                "full_passive_inclusive_gds_lvs_proven": classification[
                    "full_passive_inclusive_gds_lvs_proven"
                ],
                "native_passive_device_recognition_claimed": bool(
                    metrics.get("native_passive_device_recognition_claimed")
                ),
                "native_resistor_chain_netgen_status": resistor_summary.get(
                    "native_resistor_chain_netgen_status"
                ),
                "native_capacitor_device_recognition_status": resistor_summary.get(
                    "native_capacitor_device_recognition_status"
                ),
                "native_cap_gencell_extraction_status": resistor_summary.get(
                    "native_cap_gencell_extraction_status"
                ),
                "native_passive_retarget_full_native_passive_lvs_proven": bool(
                    resistor_summary.get("native_passive_retarget_full_native_passive_lvs_proven", False)
                ),
                "all_source_passives_have_candidate": classification["all_source_passives_have_candidate"],
                "passive_evidence_source": "backfilled_from_artifacts",
            },
            artifacts=artifacts,
            messages=[classification["reason"]],
        )

    def _candidate_dir_from_state(self, state: dict[str, Any]) -> Path | None:
        artifacts = state.get("artifacts", {})
        if isinstance(artifacts, dict) and artifacts.get("candidate_dir"):
            return Path(str(artifacts["candidate_dir"]))
        candidate_id = state.get("candidate_id")
        if candidate_id:
            return self.config.run_dir / str(candidate_id)
        return None

    @staticmethod
    def _passive_artifact_metrics(
        resistor_summary: dict[str, Any],
        evidence_summary: dict[str, Any],
        classification: dict[str, Any],
        requirements: dict[str, Any],
        route_requirements: dict[str, Any],
        evidence_summary_path: Path,
    ) -> dict[str, Any]:
        native_claimed = bool(
            resistor_summary.get("native_passive_device_recognition_claimed")
            or evidence_summary.get("native_passive_device_recognition_claimed")
        )
        native_status = (
            resistor_summary.get("native_passive_device_recognition_status")
            or evidence_summary.get("native_passive_device_recognition_status")
            or resistor_summary.get("best_native_passive_device_recognition_status")
        )
        if native_claimed:
            native_missing = resistor_summary.get("native_passive_device_recognition_missing_instances")
            if native_missing is None:
                native_missing = []
            native_blockers = resistor_summary.get("native_passive_device_recognition_blockers")
            if native_blockers is None:
                native_blockers = {}
        else:
            native_missing = (
                resistor_summary.get("native_passive_device_recognition_missing_instances")
                or evidence_summary.get("native_passive_device_recognition_missing_instances")
                or resistor_summary.get("best_native_passive_device_recognition_missing_instances")
            )
            native_blockers = (
                resistor_summary.get("native_passive_device_recognition_blockers")
                or evidence_summary.get("native_passive_device_recognition_blockers")
                or resistor_summary.get("best_native_passive_device_recognition_blockers")
            )
        metrics = {
            "passive_aware_status": classification["passive_aware_status"],
            "passive_aware_verification_scope_detail": classification["verification_scope_detail"],
            "formal_passive_abstraction_ready": classification["formal_passive_abstraction_ready"],
            "formal_passive_only_lvs_match": classification["formal_passive_only_lvs_match"],
            "hybrid_mos_reference_passive_lvs_match": classification[
                "hybrid_mos_reference_passive_lvs_match"
            ],
            "full_passive_inclusive_gds_lvs_proven": classification[
                "full_passive_inclusive_gds_lvs_proven"
            ],
            "native_passive_device_recognition_status": native_status,
            "native_passive_device_recognition_claimed": native_claimed,
            "native_passive_device_recognition_missing_instances": native_missing,
            "native_passive_device_recognition_blockers": native_blockers,
            "passive_lvs_evidence_status": evidence_summary.get("status")
            or resistor_summary.get("formal_passive_lvs_evidence_status"),
            "passive_lvs_evidence_pass": evidence_summary.get("formal_passive_lvs_evidence_pass")
            or resistor_summary.get("formal_passive_lvs_evidence_pass"),
            "passive_lvs_evidence_scope": evidence_summary.get("verification_scope")
            or resistor_summary.get("formal_passive_lvs_evidence_scope"),
            "passive_lvs_evidence_failed_requirements": evidence_summary.get("failed_requirements")
            or resistor_summary.get("formal_passive_lvs_evidence_failed_requirements"),
            "passive_lvs_primitive_abstractions": evidence_summary.get(
                "lvs_primitive_abstractions"
            ),
            "passive_lvs_evidence_summary_json": str(evidence_summary_path),
            "source_passive_primitive_counts": evidence_summary.get("source_passive_primitive_counts"),
            "candidate_passive_primitive_counts": evidence_summary.get(
                "candidate_passive_primitive_counts"
            ),
            "native_passive_capability_probe_status": resistor_summary.get(
                "native_passive_capability_probe_status"
            ),
            "native_passive_capability_source_model_native_status": resistor_summary.get(
                "native_passive_capability_source_model_native_status"
            ),
            "native_passive_capability_direct_source_model_support": resistor_summary.get(
                "native_passive_capability_direct_source_model_support"
            ),
            "native_passive_capability_unsupported_source_models": resistor_summary.get(
                "native_passive_capability_unsupported_source_models"
            ),
            "native_passive_capability_retarget_available": resistor_summary.get(
                "native_passive_capability_retarget_available"
            ),
            "native_passive_capability_retarget_map": resistor_summary.get(
                "native_passive_capability_retarget_map"
            ),
            "native_passive_capability_requires_geometry_replacement": resistor_summary.get(
                "native_passive_capability_requires_geometry_replacement"
            ),
            "native_passive_capability_can_fix_current_gds_by_layer_remap_only": resistor_summary.get(
                "native_passive_capability_can_fix_current_gds_by_layer_remap_only"
            ),
            "native_passive_capability_device_generation_source_status": resistor_summary.get(
                "native_passive_capability_device_generation_source_status"
            ),
            "native_passive_retarget_trial_status": resistor_summary.get(
                "native_passive_retarget_trial_status"
            ),
            "native_resistor_chain_status": resistor_summary.get("native_resistor_chain_status"),
            "native_resistor_chain_source_instance": resistor_summary.get(
                "native_resistor_chain_source_instance"
            ),
            "native_resistor_chain_device_count": resistor_summary.get(
                "native_resistor_chain_device_count"
            ),
            "native_resistor_chain_model": resistor_summary.get("native_resistor_chain_model"),
            "native_resistor_chain_netgen_status": resistor_summary.get(
                "native_resistor_chain_netgen_status"
            ),
            "native_capacitor_device_recognition_status": resistor_summary.get(
                "native_capacitor_device_recognition_status"
            ),
            "native_capacitor_devices": resistor_summary.get("native_capacitor_devices"),
            "native_passive_retarget_missing_native_source_passive_instances": resistor_summary.get(
                "native_passive_retarget_missing_native_source_passive_instances"
            ),
            "native_passive_retarget_full_native_passive_lvs_ready": resistor_summary.get(
                "native_passive_retarget_full_native_passive_lvs_ready"
            ),
            "native_passive_retarget_full_native_passive_lvs_proven": resistor_summary.get(
                "native_passive_retarget_full_native_passive_lvs_proven"
            ),
            "native_cap_gencell_probe_status": resistor_summary.get("native_cap_gencell_probe_status"),
            "native_cap_gencell_extraction_status": resistor_summary.get(
                "native_cap_gencell_extraction_status"
            ),
            "native_cap_gencell_model": resistor_summary.get("native_cap_gencell_model"),
            "native_cap_gencell_cell_name": resistor_summary.get("native_cap_gencell_cell_name"),
            "native_cap_gencell_recognized_device_count": resistor_summary.get(
                "native_cap_gencell_recognized_device_count"
            ),
            "native_cap_gencell_devices": resistor_summary.get("native_cap_gencell_devices"),
            "native_cap_replacement_status": resistor_summary.get("native_cap_replacement_status"),
            "native_cap_replacement_cell_name": resistor_summary.get(
                "native_cap_replacement_cell_name"
            ),
            "native_cap_replacement_terminal_bridge_status": resistor_summary.get(
                "native_cap_replacement_terminal_bridge_status"
            ),
            "native_cap_replacement_top_gds_merge_status": resistor_summary.get(
                "native_cap_replacement_top_gds_merge_status"
            ),
            "native_cap_replacement_bridge_mode": resistor_summary.get(
                "native_cap_replacement_bridge_mode"
            ),
            "native_cap_replacement_full_gds": resistor_summary.get(
                "native_cap_replacement_full_gds"
            ),
            "native_cap_replacement_extract_status": resistor_summary.get(
                "native_cap_replacement_extract_status"
            ),
            "native_cap_replacement_drc_status": resistor_summary.get(
                "native_cap_replacement_drc_status"
            ),
            "native_cap_replacement_drc_count": resistor_summary.get(
                "native_cap_replacement_drc_count"
            ),
            "native_cap_replacement_native_passive_netgen_status": resistor_summary.get(
                "native_cap_replacement_native_passive_netgen_status"
            ),
            "native_cap_replacement_native_capacitor_device_count": resistor_summary.get(
                "native_cap_replacement_native_capacitor_device_count"
            ),
            "native_cap_full_gds_trial_status": resistor_summary.get(
                "native_cap_full_gds_trial_status"
            ),
            "native_cap_full_gds_trial_summary_json": resistor_summary.get(
                "native_cap_full_gds_trial_summary_json"
            ),
            "native_cap_replacement_full_native_capacitor_lvs_ready": resistor_summary.get(
                "native_cap_replacement_full_native_capacitor_lvs_ready"
            ),
            "native_cap_replacement_remaining_gates": resistor_summary.get(
                "native_cap_replacement_remaining_gates"
            ),
        }
        for key, value in requirements.items():
            metrics[f"passive_requirement_{key}"] = value
        for key, value in route_requirements.items():
            metrics[f"passive_route_bridge_requirement_{key}"] = value
        for key in (
            "best_route_bridge_trial_status",
            "best_route_bridge_trial_summary_json",
            "best_route_bridge_injection_status",
            "best_route_bridge_count",
            "best_route_bridge_drc_count",
            "best_route_bridge_mos_connectivity_status",
            "best_route_bridge_formal_passive_lvs_prepare_status",
            "best_route_bridge_formal_passive_lvs_netgen_status",
            "best_route_bridge_formal_passive_lvs_result_summary",
            "best_passive_abs_netgen_status",
            "best_hybrid_mos_passive_lvs_trial_netgen_status",
            "best_passive_aware_lvs_trial_netgen_status",
            "best_all_source_passives_have_candidate",
            "best_missing_source_passive_instances",
            "best_native_passive_device_recognition_status",
            "best_native_passive_device_recognition_claimed",
            "best_native_passive_device_recognition_missing_instances",
            "best_native_passive_device_recognition_blockers",
        ):
            metrics[f"passive_resistor_variant_{key}"] = resistor_summary.get(key)
        return metrics

    @staticmethod
    def _passive_artifact_paths(
        resistor_summary: dict[str, Any],
        evidence_summary: dict[str, Any],
        evidence_summary_path: Path,
    ) -> dict[str, str]:
        artifacts = {"passive_lvs_evidence_summary_json": str(evidence_summary_path)}
        for artifact_key, summary_key in (
            ("passive_lvs_evidence_report", "formal_passive_lvs_evidence_report"),
            ("passive_lvs_evidence_log", "formal_passive_lvs_evidence_log"),
            ("native_passive_capability_summary_json", "native_passive_capability_summary_json"),
            ("native_passive_capability_report", "native_passive_capability_report"),
            ("native_passive_capability_log", "native_passive_capability_log"),
            ("native_passive_retarget_summary_json", "native_passive_retarget_summary_json"),
            ("native_passive_retarget_report", "native_passive_retarget_report"),
            ("native_passive_retarget_log", "native_passive_retarget_log"),
            (
                "native_passive_retarget_source_native_passive_netlist",
                "native_passive_retarget_source_native_passive_netlist",
            ),
            (
                "native_passive_retarget_candidate_native_passive_netlist",
                "native_passive_retarget_candidate_native_passive_netlist",
            ),
            ("native_resistor_chain_netgen_report", "native_resistor_chain_netgen_report"),
            ("native_resistor_chain_netgen_log", "native_resistor_chain_netgen_log"),
            ("native_cap_gencell_summary_json", "native_cap_gencell_summary_json"),
            ("native_cap_gencell_report", "native_cap_gencell_report"),
            ("native_cap_gencell_log", "native_cap_gencell_log"),
            ("native_cap_gencell_magic_log", "native_cap_gencell_magic_log"),
            ("native_cap_gencell_spice", "native_cap_gencell_spice"),
            ("native_cap_gencell_mag", "native_cap_gencell_mag"),
            ("native_cap_gencell_gds", "native_cap_gencell_gds"),
            ("native_cap_gencell_ext", "native_cap_gencell_ext"),
            ("native_cap_replacement_summary_json", "native_cap_replacement_summary_json"),
            ("native_cap_replacement_report", "native_cap_replacement_report"),
            ("native_cap_replacement_gds", "native_cap_replacement_gds"),
            ("native_cap_replacement_spice", "native_cap_replacement_spice"),
            ("native_cap_replacement_magic_log", "native_cap_replacement_magic_log"),
            ("native_cap_full_gds_trial_summary_json", "native_cap_full_gds_trial_summary_json"),
            ("native_cap_replacement_full_gds", "native_cap_replacement_full_gds"),
            ("native_passive_netgen_report", "native_passive_netgen_report"),
            ("native_passive_netgen_log", "native_passive_netgen_log"),
            ("passive_resistor_variant_best_route_bridge_trial_summary_json", "best_route_bridge_trial_summary_json"),
            ("passive_resistor_variant_best_route_bridge_formal_passive_lvs_result_summary", "best_route_bridge_formal_passive_lvs_result_summary"),
            ("passive_resistor_variant_best_passive_abs_lvs_result_summary", "best_passive_abs_lvs_result_summary"),
            ("passive_resistor_variant_best_hybrid_mos_passive_lvs_trial_result_summary", "best_hybrid_mos_passive_lvs_trial_result_summary"),
        ):
            value = resistor_summary.get(summary_key)
            if value:
                artifacts[artifact_key] = str(value)
        for artifact_key, summary_key in (
            ("source_passive_abstraction_netlist", "source_passive_abstraction_netlist"),
            ("candidate_passive_abstraction_netlist", "candidate_passive_abstraction_netlist"),
            ("passive_only_lvs_result_summary", "passive_only_lvs_result_summary"),
            ("hybrid_lvs_result_summary", "hybrid_lvs_result_summary"),
            ("full_gds_lvs_result_summary", "full_gds_lvs_result_summary"),
            ("route_bridge_lvs_result_summary", "route_bridge_lvs_result_summary"),
            ("route_bridge_trial_summary", "route_bridge_trial_summary"),
        ):
            value = evidence_summary.get(summary_key)
            if value:
                artifacts[artifact_key] = str(value)
        return artifacts

    @staticmethod
    def _packet_by_stage(state: dict[str, Any] | None, stage: str) -> dict[str, Any] | None:
        if state is None:
            return None
        for packet in state.get("evidence", []):
            if isinstance(packet, dict) and packet.get("stage") == stage:
                return packet
        return None


def _passive_status_rank(status: str) -> int:
    return PASSIVE_EVIDENCE_STATUS_RANK.get(status, 1 if status.endswith("_pass") else 0)


def _passive_packet_is_current_or_better(current: dict[str, Any], candidate: EvidencePacket) -> bool:
    current_rank = _passive_status_rank(str(current.get("status")))
    candidate_rank = _passive_status_rank(candidate.status)
    if current_rank > candidate_rank:
        return True
    if current_rank < candidate_rank:
        return False
    current_metrics = current.get("metrics", {})
    if not isinstance(current_metrics, dict):
        current_metrics = {}
    for key in (
        "passive_lvs_primitive_abstractions",
        "native_passive_device_recognition_status",
        "native_passive_device_recognition_missing_instances",
        "native_passive_device_recognition_blockers",
        "native_passive_capability_source_model_native_status",
        "native_passive_capability_retarget_available",
        "native_passive_capability_retarget_map",
        "native_passive_capability_device_generation_source_status",
        "native_passive_retarget_trial_status",
        "native_resistor_chain_netgen_status",
        "native_capacitor_device_recognition_status",
        "native_passive_retarget_full_native_passive_lvs_proven",
        "native_cap_gencell_extraction_status",
        "native_cap_replacement_status",
        "native_cap_replacement_terminal_bridge_status",
        "native_cap_replacement_top_gds_merge_status",
        "native_cap_replacement_bridge_mode",
        "native_cap_replacement_full_gds",
        "native_cap_replacement_drc_count",
        "native_cap_replacement_native_passive_netgen_status",
        "native_cap_full_gds_trial_status",
        "full_passive_inclusive_gds_lvs_proven",
    ):
        if candidate.metrics.get(key) and candidate.metrics.get(key) != current_metrics.get(key):
            return False
    return True
