"""GRPO warm-start and proxy-feedback archive support."""

from __future__ import annotations

import json
import shutil
import glob
from pathlib import Path
from typing import Any

from .config import HarnessConfig


class KnowledgeTransferArchive:
    """Stores good closure evidence for later GRPO/proxy warm starts."""

    def __init__(self, config: HarnessConfig):
        self.config = config
        self.archive_config = dict(config.data.get("knowledge_transfer", {}))

    @property
    def enabled(self) -> bool:
        return bool(self.archive_config.get("enabled", True))

    @property
    def archive_dir(self) -> Path:
        raw = self.archive_config.get(
            "archive_dir",
            f"generated/analog_harness/{self.config.design_id}/knowledge_transfer",
        )
        return self.config.resolve_path(str(raw))

    def warm_start_records(self) -> list[dict[str, Any]]:
        bank = self.archive_dir / "warm_start_bank.json"
        if not bank.is_file():
            return []
        try:
            payload = json.loads(bank.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        records = payload.get("records") if isinstance(payload, dict) else None
        return [record for record in records or [] if isinstance(record, dict)]

    def consider(self, state: dict[str, Any]) -> bool:
        if not self.enabled or not self._is_good_candidate(state):
            return False
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self._append_jsonl(self.archive_dir / "proxy_feedback_dataset.jsonl", self._feedback_record(state))
        self._write_warm_start_bank(state)
        self._preserve_model_artifacts(state)
        return True

    def rebuild_warm_start_bank(self, states: list[dict[str, Any]]) -> None:
        if not self.enabled:
            return
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        records = [
            self._warm_start_record(state)
            for state in states
            if self._is_good_candidate(state)
        ]
        records.sort(
            key=lambda item: float(item.get("reward", -1e9)) if isinstance(item.get("reward"), (int, float)) else -1e9,
            reverse=True,
        )
        limit = int(self.archive_config.get("max_records", 32))
        payload = {
            "design_id": self.config.design_id,
            "top_cell": self.config.top_cell,
            "records": records[: max(1, limit)],
        }
        (self.archive_dir / "warm_start_bank.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _is_good_candidate(self, state: dict[str, Any]) -> bool:
        if state.get("redesign_request"):
            return False
        reward = state.get("reward")
        min_reward = float(self.archive_config.get("min_reward", -0.25))
        if isinstance(reward, (int, float)) and float(reward) >= min_reward:
            return True
        closure_levels = set(self.archive_config.get("closure_levels", []))
        return str(state.get("closure_level")) in closure_levels

    def _write_warm_start_bank(self, state: dict[str, Any]) -> None:
        existing = self.warm_start_records()
        by_id = {str(record.get("candidate_id")): record for record in existing}
        record = self._warm_start_record(state)
        by_id[str(record["candidate_id"])] = record
        records = sorted(
            by_id.values(),
            key=lambda item: float(item.get("reward", -1e9)) if isinstance(item.get("reward"), (int, float)) else -1e9,
            reverse=True,
        )
        limit = int(self.archive_config.get("max_records", 32))
        payload = {
            "design_id": self.config.design_id,
            "top_cell": self.config.top_cell,
            "records": records[: max(1, limit)],
        }
        (self.archive_dir / "warm_start_bank.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _warm_start_record(state: dict[str, Any]) -> dict[str, Any]:
        return {
            "candidate_id": state.get("candidate_id"),
            "design_id": state.get("design_id"),
            "top_cell": state.get("top_cell"),
            "values": state.get("values"),
            "reward": state.get("reward"),
            "closure_level": state.get("closure_level"),
            "verification_scope": state.get("verification_scope"),
            "optimizer_source": state.get("optimizer_source"),
        }

    def _feedback_record(self, state: dict[str, Any]) -> dict[str, Any]:
        metrics: dict[str, Any] = {}
        verification_mask: dict[str, bool] = {}
        for packet in state.get("evidence", []):
            if not isinstance(packet, dict):
                continue
            metrics.update(packet.get("metrics") or {})
            fidelity = packet.get("fidelity")
            if isinstance(fidelity, str):
                verification_mask[fidelity] = packet.get("status") == "pass"
        return {
            "candidate_id": state.get("candidate_id"),
            "values": state.get("values"),
            "reward": state.get("reward"),
            "closure_level": state.get("closure_level"),
            "verification_scope": state.get("verification_scope"),
            "metrics": metrics,
            "verification_mask": verification_mask,
        }

    def _preserve_model_artifacts(self, state: dict[str, Any]) -> None:
        if not bool(self.archive_config.get("preserve_model_artifacts", True)):
            return
        copied: list[str] = []
        model_dir = self.archive_dir / "proxy_models"
        for raw_glob in self.archive_config.get("model_artifact_globs", []):
            for source in self._glob_model_artifacts(str(raw_glob)):
                if not source.is_file():
                    continue
                model_dir.mkdir(parents=True, exist_ok=True)
                target = model_dir / source.name
                shutil.copy2(source, target)
                copied.append(str(target))
        manifest = {
            "candidate_id": state.get("candidate_id"),
            "copied_model_artifacts": copied,
            "note": "No model artifact was copied if AnalogGym has not emitted a trained proxy/policy file yet.",
        }
        (self.archive_dir / "proxy_model_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _glob_model_artifacts(self, pattern: str) -> list[Path]:
        expanded = pattern.replace("{analog_gym_root}", str(self.config.analog_gym_root))
        expanded = expanded.replace("{archive_dir}", str(self.archive_dir))
        if not Path(expanded).is_absolute():
            expanded = str(self.config.repo_root / expanded)
        return [Path(item) for item in glob.glob(expanded, recursive=True)]

    @staticmethod
    def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
