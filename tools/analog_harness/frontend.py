"""Front-end sizing result discovery and reuse."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import HarnessConfig
from .legalizer import SizingLegalizer
from .models import CandidateProposal


CLOSURE_RANK = {
    "L0_candidate_generated": 0,
    "L1_pre_layout_nominal": 1,
    "L2_pre_layout_pvt": 2,
    "L3_physically_realizable": 3,
    "L4_layout_verified_mos_only": 4,
    "L5_post_layout_nominal": 5,
    "L6_post_layout_pvt": 6,
}


class FrontEndResultLoader:
    """Loads existing front-end sizing results before asking GRPO for new ones."""

    def __init__(self, config: HarnessConfig, legalizer: SizingLegalizer):
        self.config = config
        self.legalizer = legalizer
        self.frontend_config = dict(config.data.get("frontend_results", {}))

    @property
    def enabled(self) -> bool:
        return bool(self.frontend_config.get("enabled", True))

    def proposals(self, history: list[dict[str, Any]], max_count: int | None = None) -> list[CandidateProposal]:
        if not self.enabled:
            return []
        used_origins = self._used_origins(history)
        records = [
            record
            for record in self._iter_source_records()
            if record["origin_id"] not in used_origins
        ]
        records.sort(key=self._rank_tuple, reverse=True)
        limit = max_count if max_count is not None else int(self.frontend_config.get("max_candidates", 1))
        return [self._record_to_proposal(record) for record in records[: max(0, limit)]]

    def _iter_source_records(self) -> list[dict[str, Any]]:
        source_items = self.frontend_config.get("sources", [])
        records: list[dict[str, Any]] = []
        for raw_source in source_items:
            source = self.config.resolve_path(str(raw_source))
            if not source.exists():
                continue
            if source.is_file():
                records.extend(self._records_from_file(source))
            else:
                records.extend(self._records_from_dir(source))
        return records

    def _records_from_dir(self, source: Path) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        if (source / "state.json").is_file():
            records.extend(self._records_from_file(source / "state.json"))
        for state_path in sorted(source.glob("cand_*/state.json")):
            records.extend(self._records_from_file(state_path))
        for summary_path in sorted(source.glob("**/top_designs_summary.json")):
            records.extend(self._records_from_file(summary_path))
        return records

    def _records_from_file(self, source: Path) -> list[dict[str, Any]]:
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        raw_records = _candidate_records(payload)
        records: list[dict[str, Any]] = []
        for index, raw_record in enumerate(raw_records):
            if self._skip_record(raw_record):
                continue
            values = self._extract_values(raw_record)
            if values is None:
                continue
            origin_candidate = raw_record.get("candidate_id") or raw_record.get("rank") or index
            records.append(
                {
                    "origin_id": f"{source}:{origin_candidate}",
                    "source": str(source),
                    "values": values,
                    "reward": _to_float(raw_record.get("reward", raw_record.get("training_reward"))),
                    "closure_level": raw_record.get("closure_level", "L0_candidate_generated"),
                    "raw_record": raw_record,
                }
            )
        return records

    def _skip_record(self, record: dict[str, Any]) -> bool:
        if not bool(self.frontend_config.get("skip_repair_requested", True)):
            return False
        if record.get("redesign_request"):
            return True
        for packet in record.get("evidence", []):
            if not isinstance(packet, dict):
                continue
            if packet.get("stage") == "layout_verification" and packet.get("status") in {"fail", "unknown"}:
                return True
        return False

    def _record_to_proposal(self, record: dict[str, Any]) -> CandidateProposal:
        values = self.legalizer.legalize_values(record["values"])
        return CandidateProposal(
            source="frontend_result",
            action_normalized=self.legalizer.values_to_normalized(values),
            values=values,
            metadata={
                "frontend_origin_id": record["origin_id"],
                "frontend_source": record["source"],
                "frontend_reward": record.get("reward"),
                "frontend_closure_level": record.get("closure_level"),
                "proposal_mode": "reuse_frontend_result",
            },
        )

    def _extract_values(self, record: dict[str, Any]) -> dict[str, float | int] | None:
        values = record.get("values")
        if isinstance(values, dict):
            return self.legalizer.legalize_values(values)
        action_real = record.get("action_real")
        if isinstance(action_real, list) and len(action_real) == self.legalizer.action_dim:
            return self.legalizer.legalize_values(
                {variable.name: action_real[index] for index, variable in enumerate(self.legalizer.variables)}
            )
        action_norm = record.get("action_normalized")
        if isinstance(action_norm, list) and len(action_norm) == self.legalizer.action_dim:
            return self.legalizer.legalize_normalized([float(value) for value in action_norm])
        return None

    @staticmethod
    def _used_origins(history: list[dict[str, Any]]) -> set[str]:
        used: set[str] = set()
        for state in history:
            metadata = state.get("optimizer_metadata")
            if not isinstance(metadata, dict):
                continue
            origin = metadata.get("frontend_origin_id")
            if isinstance(origin, str):
                used.add(origin)
        return used

    @staticmethod
    def _rank_tuple(record: dict[str, Any]) -> tuple[float, int]:
        reward = record.get("reward")
        reward_value = float(reward) if isinstance(reward, (int, float)) else -1e9
        closure = CLOSURE_RANK.get(str(record.get("closure_level")), 0)
        return reward_value, closure


def _candidate_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    if "values" in payload or "action_real" in payload or "action_normalized" in payload:
        return [payload]
    for key in ("records", "candidates", "top_designs", "designs"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
