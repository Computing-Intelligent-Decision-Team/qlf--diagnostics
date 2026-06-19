"""Persistent candidate state and evidence logging."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import EvidencePacket


class CandidateStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "evidence").mkdir(exist_ok=True)

    def next_candidate_id(self) -> str:
        max_idx = 0
        for path in self.root.glob("cand_*"):
            try:
                max_idx = max(max_idx, int(path.name.split("_", 1)[1]))
            except (IndexError, ValueError):
                continue
        return f"cand_{max_idx + 1:04d}"

    def append_evidence(self, packet: EvidencePacket) -> None:
        events_path = self.root / "evidence" / "events.jsonl"
        with events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(packet.to_dict(), sort_keys=True) + "\n")

        candidate_events = self.root / packet.candidate_id / "evidence.jsonl"
        candidate_events.parent.mkdir(parents=True, exist_ok=True)
        with candidate_events.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(packet.to_dict(), sort_keys=True) + "\n")

    def write_candidate_state(self, candidate_id: str, state: dict[str, Any]) -> None:
        candidate_dir = self.root / candidate_id
        candidate_dir.mkdir(parents=True, exist_ok=True)
        (candidate_dir / "state.json").write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def read_candidate_states(self) -> list[dict[str, Any]]:
        states: list[dict[str, Any]] = []
        for state_path in sorted(self.root.glob("cand_*/state.json")):
            states.append(json.loads(state_path.read_text(encoding="utf-8")))
        return states
