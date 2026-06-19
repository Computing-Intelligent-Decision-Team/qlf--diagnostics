"""Sizing optimizer adapters, including the AnalogGym GRPO bridge."""

from __future__ import annotations

import importlib
import json
import random
import sys
from pathlib import Path
from typing import Any

from .config import HarnessConfig
from .legalizer import SizingLegalizer
from .models import CandidateProposal, EvidencePacket


SCOPED_POSITIVE_EVIDENCE_STATUSES = {
    "formal_abstraction_pass",
    "formal_abstraction_with_full_gds_mos_pass",
    "formal_abstraction_with_gds_mos_bridge_pass",
}


class SizingOptimizerAdapter:
    def initialize(self, contract: dict[str, Any], history: list[dict[str, Any]]) -> None:
        raise NotImplementedError

    def propose(self, context: dict[str, Any], batch_size: int) -> list[CandidateProposal]:
        raise NotImplementedError

    def observe(self, candidate_id: str, evidence: list[EvidencePacket]) -> None:
        raise NotImplementedError

    def update_constraints(self, redesign_request: dict[str, Any]) -> None:
        raise NotImplementedError

    def warm_start(self, candidate_seeds: list[dict[str, Any]]) -> None:
        raise NotImplementedError

    def prepare_long_training_interface(self, archive_dir: Path, steps: int) -> dict[str, Any]:
        raise NotImplementedError


class AnalogGymGRPOAdapter(SizingOptimizerAdapter):
    """Bridge from the harness contract to AnalogGym's GRPO artifacts."""

    def __init__(self, config: HarnessConfig, legalizer: SizingLegalizer):
        self.config = config
        self.legalizer = legalizer
        opt_config = dict(config.data.get("optimizer", {}))
        self.random = random.Random(int(opt_config.get("random_seed", 152)))
        self.cold_start_sigma = float(opt_config.get("cold_start_sigma", 0.35))
        self.model_safe_repair_values = dict(opt_config.get("model_safe_repair_values", {}))
        self.backend_status: dict[str, Any] = {"backend": "analoggym_grpo", "imported_grpo": False}
        self.episode_cls: Any = None
        self.history: list[dict[str, Any]] = []
        self.observed: list[dict[str, Any]] = []
        self.seed_values: list[dict[str, float | int]] = []
        self.pending_values: list[dict[str, float | int]] = []

    def initialize(self, contract: dict[str, Any], history: list[dict[str, Any]]) -> None:
        self.history = list(history)
        analog_root = self.config.analog_gym_root
        self.backend_status["analog_gym_root"] = str(analog_root)
        latest_repair = self._latest_redesign_request(history)
        if latest_repair is not None:
            self.backend_status["last_redesign_request"] = latest_repair
        try:
            if str(analog_root) not in sys.path:
                sys.path.insert(0, str(analog_root))
            grpo = importlib.import_module("grpo")
            self.episode_cls = getattr(grpo, "Episode", None)
            self.backend_status["imported_grpo"] = self.episode_cls is not None
            self.backend_status["grpo_file"] = str(Path(getattr(grpo, "__file__", "")).resolve())
        except Exception as exc:  # pragma: no cover - optional local ML deps
            self.backend_status["import_error"] = str(exc)
        self.warm_start([item for item in history if item.get("values")])

    def propose(self, context: dict[str, Any], batch_size: int) -> list[CandidateProposal]:
        base_norm = self._base_normalized()
        proposals: list[CandidateProposal] = []
        for index in range(batch_size):
            if index == 0 and self._needs_model_safe_repair():
                values = self._model_safe_values()
                action = self.legalizer.values_to_normalized(values)
                proposal_mode = "model_safe_sizing_repair"
                self.pending_values.append(values)
                proposals.append(
                    CandidateProposal(
                        source="analoggym_grpo",
                        action_normalized=action,
                        values=values,
                        metadata={
                            "backend_status": dict(self.backend_status),
                            "proposal_mode": proposal_mode,
                            "context_keys": sorted(context.keys()),
                        },
                    )
                )
                continue
            if index == 0 and self._needs_layout_safe_repair():
                action = self.legalizer.initial_normalized()
                proposal_mode = "layout_safe_sizing_repair"
            elif index == 0 and not self.observed:
                action = list(base_norm)
                proposal_mode = "cold_start_grpo_contract"
            else:
                sigma = max(0.01, self.cold_start_sigma * (0.98 ** len(self.observed)))
                action = [
                    max(-1.0, min(1.0, value + self.random.gauss(0.0, sigma)))
                    for value in base_norm
                ]
                proposal_mode = "cold_start_grpo_contract"
            values = self.legalizer.legalize_normalized(action)
            self.pending_values.append(values)
            proposals.append(
                CandidateProposal(
                    source="analoggym_grpo",
                    action_normalized=self.legalizer.values_to_normalized(values),
                    values=values,
                    metadata={
                        "backend_status": dict(self.backend_status),
                        "proposal_mode": proposal_mode,
                        "context_keys": sorted(context.keys()),
                    },
                )
            )
        return proposals

    def observe(self, candidate_id: str, evidence: list[EvidencePacket]) -> None:
        reward = aggregate_reward(self.config.performance, evidence)
        performance = flatten_evidence(evidence)
        values = self.pending_values.pop(0) if self.pending_values else None
        record = {
            "candidate_id": candidate_id,
            "reward": reward,
            "performance": performance,
            "closure_level": performance.get("closure_level"),
            "verification_mask": performance.get("verification_mask", {}),
        }
        if values is not None:
            record["values"] = values
        if self.episode_cls is not None:
            record["grpo_episode"] = self.episode_cls(
                circuit_spec=self.config.design_id,
                reward=reward,
                performance=performance,
                evaluation_source="analog_harness",
            )
        self.observed.append(record)

    def update_constraints(self, redesign_request: dict[str, Any]) -> None:
        self.backend_status["last_redesign_request"] = dict(redesign_request)

    def _needs_layout_safe_repair(self) -> bool:
        request = self.backend_status.get("last_redesign_request")
        if not isinstance(request, dict):
            return False
        reasons = " ".join(str(item) for item in request.get("reasons", []))
        return "layout_verification" in reasons or "magic_drc" in reasons or "drc" in reasons.lower()

    def _needs_model_safe_repair(self) -> bool:
        request = self.backend_status.get("last_redesign_request")
        if not isinstance(request, dict):
            return False
        reasons = " ".join(str(item) for item in request.get("reasons", []))
        action = str(request.get("action", ""))
        return "sky130_model_bin_mismatch" in reasons or action == "propose_model_safe_sizing"

    def _model_safe_values(self) -> dict[str, float | int]:
        base = self.legalizer.initial_values()
        best = self._best_observed_values()
        if best is not None:
            base.update(best)
        elif self.seed_values:
            base.update(self.seed_values[-1])
        base.update(self.model_safe_repair_values)
        return self.legalizer.legalize_values(base)

    @staticmethod
    def _latest_redesign_request(history: list[dict[str, Any]]) -> dict[str, Any] | None:
        for state in reversed(history):
            request = state.get("redesign_request")
            if isinstance(request, dict):
                return request
        return None

    def warm_start(self, candidate_seeds: list[dict[str, Any]]) -> None:
        for seed in candidate_seeds:
            values = seed.get("values")
            if isinstance(values, dict):
                self.seed_values.append(self.legalizer.legalize_values(values))

    def prepare_long_training_interface(self, archive_dir: Path, steps: int = 300) -> dict[str, Any]:
        archive_dir.mkdir(parents=True, exist_ok=True)
        entrypoint = self.config.analog_gym_root / "main_AMP_grpo.py"
        warm_start_bank = archive_dir / "warm_start_bank.json"
        feedback_dataset = archive_dir / "proxy_feedback_dataset.jsonl"
        manifest_path = archive_dir / "grpo_warm_start_training_manifest.json"
        powershell_script = archive_dir / "run_grpo_warm_start_training.ps1"
        bash_script = archive_dir / "run_grpo_warm_start_training.sh"
        command = f"python {entrypoint.name}"
        manifest = {
            "design_id": self.config.design_id,
            "top_cell": self.config.top_cell,
            "analog_gym_root": str(self.config.analog_gym_root),
            "entrypoint": str(entrypoint),
            "requested_steps": int(steps),
            "warm_start_bank": str(warm_start_bank),
            "proxy_feedback_dataset": str(feedback_dataset),
            "backend_status": dict(self.backend_status),
            "status": "prepared_not_executed",
            "suggested_command": command,
            "environment": {
                "ANALOG_HARNESS_WARM_START_BANK": str(warm_start_bank),
                "ANALOG_HARNESS_PROXY_FEEDBACK_DATASET": str(feedback_dataset),
                "ANALOG_HARNESS_REQUESTED_STEPS": str(int(steps)),
                "ANALOG_HARNESS_DESIGN_ID": self.config.design_id,
            },
            "notes": [
                "This interface intentionally does not start long training.",
                "AnalogGym main_AMP_grpo.py currently owns its internal QUICK_CONFIG; use this manifest as the warm-start contract for a long-run wrapper or future AnalogGym patch.",
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        powershell_script.write_text(
            "\n".join(
                [
                    "$ErrorActionPreference = 'Stop'",
                    f"Set-Location -LiteralPath {json.dumps(str(self.config.analog_gym_root))}",
                    f"$env:ANALOG_HARNESS_WARM_START_BANK = {json.dumps(str(warm_start_bank))}",
                    f"$env:ANALOG_HARNESS_PROXY_FEEDBACK_DATASET = {json.dumps(str(feedback_dataset))}",
                    f"$env:ANALOG_HARNESS_REQUESTED_STEPS = {json.dumps(str(int(steps)))}",
                    f"$env:ANALOG_HARNESS_DESIGN_ID = {json.dumps(self.config.design_id)}",
                    "python main_AMP_grpo.py",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        bash_script.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env bash",
                    "set -euo pipefail",
                    f"cd {json.dumps(str(self.config.analog_gym_root))}",
                    f"export ANALOG_HARNESS_WARM_START_BANK={json.dumps(str(warm_start_bank))}",
                    f"export ANALOG_HARNESS_PROXY_FEEDBACK_DATASET={json.dumps(str(feedback_dataset))}",
                    f"export ANALOG_HARNESS_REQUESTED_STEPS={json.dumps(str(int(steps)))}",
                    f"export ANALOG_HARNESS_DESIGN_ID={json.dumps(self.config.design_id)}",
                    "python main_AMP_grpo.py",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        manifest["manifest"] = str(manifest_path)
        manifest["powershell_script"] = str(powershell_script)
        manifest["bash_script"] = str(bash_script)
        return manifest

    def _base_normalized(self) -> list[float]:
        best_values = self._best_observed_values()
        if best_values is not None:
            return self.legalizer.values_to_normalized(best_values)
        if self.seed_values:
            return self.legalizer.values_to_normalized(self.seed_values[-1])
        return self.legalizer.initial_normalized()

    def _best_observed_values(self) -> dict[str, float | int] | None:
        best_state = None
        best_reward = -float("inf")
        for state in [*self.history, *self.observed]:
            reward = state.get("reward")
            values = state.get("values")
            if isinstance(values, dict) and isinstance(reward, (int, float)) and reward > best_reward:
                best_reward = float(reward)
                best_state = values
        return best_state


def flatten_evidence(evidence: list[EvidencePacket]) -> dict[str, Any]:
    merged: dict[str, Any] = {
        "verification_mask": {},
        "verification_native_pass_mask": {},
        "verification_status_mask": {},
        "verification_scope_mask": {},
        "post_layout_metrics": {},
    }
    for packet in evidence:
        merged[f"{packet.stage}_status"] = packet.status
        merged["verification_mask"][packet.fidelity] = _evidence_status_is_positive(packet)
        merged["verification_native_pass_mask"][packet.fidelity] = packet.status == "pass"
        merged["verification_status_mask"][packet.fidelity] = packet.status
        merged["verification_scope_mask"][packet.fidelity] = packet.verification_scope
        merged.update(packet.metrics)
        for key, value in packet.metrics.items():
            merged[f"{packet.stage}_{key}"] = value
        if packet.stage in {"post_sim", "pvt_sim"}:
            merged["post_layout_metrics"][packet.stage] = dict(packet.metrics)
        for key, value in packet.physical_feedback.items():
            merged[f"physical_{key}"] = value
    merged["closure_level"] = closure_level_from_evidence(evidence)
    return merged


def _evidence_status_is_positive(packet: EvidencePacket) -> bool:
    if packet.status == "pass":
        return True
    if packet.status in SCOPED_POSITIVE_EVIDENCE_STATUSES:
        return str(packet.verification_scope).startswith("formal_passive_abstraction")
    return False


def closure_level_from_evidence(evidence: list[EvidencePacket]) -> str:
    statuses = {packet.stage: packet.status for packet in evidence}
    if statuses.get("pvt_sim") == "pass":
        return "L6_post_layout_pvt"
    if statuses.get("post_sim") == "pass":
        return "L5_post_layout_nominal"
    layout = next((packet for packet in evidence if packet.stage == "layout_verification"), None)
    if layout and layout.status == "pass":
        return "L4_layout_verified_mos_only"
    if statuses.get("pre_sim") in {"pass", "proxy_fallback"}:
        return "L1_pre_layout_nominal"
    return "L0_candidate_generated"


def aggregate_reward(performance_contract: dict[str, Any], evidence: list[EvidencePacket]) -> float:
    metrics: dict[str, Any] = {}
    physical_bonus = 0.0
    for packet in evidence:
        metrics.update(packet.metrics)
        if packet.stage == "layout_verification" and packet.status == "pass":
            physical_bonus += 0.25
        if packet.stage == "post_sim" and packet.status == "pass":
            physical_bonus += 0.15
        if packet.stage == "pvt_sim" and packet.status == "pass":
            physical_bonus += 0.2
    scores: list[float] = []
    for key, spec in performance_contract.items():
        if not isinstance(spec, dict) or key not in metrics:
            continue
        value = metrics.get(key)
        target = spec.get("target")
        if not isinstance(value, (int, float)) or not isinstance(target, (int, float)):
            continue
        objective = str(spec.get("objective", "max"))
        scores.append(_metric_score(float(value), float(target), objective))
    if not scores:
        return -1.0 + physical_bonus
    return sum(scores) / len(scores) + physical_bonus


def _metric_score(value: float, target: float, objective: str) -> float:
    denom = abs(value) + abs(target) + 1e-12
    if objective == "min":
        return min(0.0, (target - value) / denom)
    return min(0.0, (value - target) / denom)
