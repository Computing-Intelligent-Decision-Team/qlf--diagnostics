"""Common data structures for the analog closure harness."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


def utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass
class CandidateProposal:
    source: str
    action_normalized: list[float]
    values: dict[str, float | int]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CompiledCandidate:
    candidate_id: str
    candidate_dir: Path
    case_dir: Path
    out_dir: Path
    netlist_path: Path
    config_path: Path
    action_normalized: list[float]
    values: dict[str, float | int]
    assignments: dict[str, dict[str, float | int]]


@dataclass
class EvidencePacket:
    candidate_id: str
    stage: str
    fidelity: str
    status: str
    verification_scope: str
    metrics: dict[str, Any] = field(default_factory=dict)
    physical_feedback: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=utc_timestamp)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
