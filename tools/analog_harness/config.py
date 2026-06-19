"""Configuration loading for the analog closure harness."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]


def _expand_path_tokens(value: str, repo_root: Path, analog_gym_root: Path | None = None) -> str:
    expanded = os.path.expandvars(value)
    expanded = expanded.replace("{repo_root}", str(repo_root))
    if analog_gym_root is not None:
        expanded = expanded.replace("{analog_gym_root}", str(analog_gym_root))
    return expanded


@dataclass(frozen=True)
class HarnessConfig:
    """Thin typed wrapper around the harness YAML config."""

    path: Path
    data: dict[str, Any]
    repo_root: Path = REPO_ROOT

    @property
    def design_id(self) -> str:
        return str(self.data["design_id"])

    @property
    def top_cell(self) -> str:
        return str(self.data["top_cell"])

    @property
    def variables(self) -> list[dict[str, Any]]:
        return list(self.data.get("sizing_variables", []))

    @property
    def performance(self) -> dict[str, Any]:
        return dict(self.data.get("performance", {}))

    @property
    def verification_scope(self) -> str:
        return str(self.data.get("verification", {}).get("scope", "unknown"))

    @property
    def run_dir(self) -> Path:
        return self.resolve_path(self.data.get("paths", {}).get("runs_dir", "generated/analog_harness"))

    @property
    def analog_gym_root(self) -> Path:
        raw = self.data.get("paths", {}).get("analog_gym_root", "../Analoggym_opt_moo_Mahalanobis_paper")
        return self.resolve_path(raw)

    @property
    def source_netlist(self) -> Path:
        return self.resolve_path(self.data["paths"]["source_netlist"])

    @property
    def source_config(self) -> Path:
        return self.resolve_path(self.data["paths"]["source_config"])

    def resolve_path(self, value: str | os.PathLike[str], base: Path | None = None) -> Path:
        raw = _expand_path_tokens(str(value), self.repo_root, self._analog_root_if_known())
        path = Path(raw).expanduser()
        if path.is_absolute():
            return path.resolve()
        return ((base or self.repo_root) / path).resolve()

    def _analog_root_if_known(self) -> Path | None:
        paths = self.data.get("paths", {})
        raw = paths.get("analog_gym_root")
        if not raw:
            return None
        expanded = _expand_path_tokens(str(raw), self.repo_root, None)
        path = Path(expanded).expanduser()
        if path.is_absolute():
            return path.resolve()
        return (self.repo_root / path).resolve()


def load_harness_config(path: str | os.PathLike[str]) -> HarnessConfig:
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = (REPO_ROOT / config_path).resolve()
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    _validate_config(data, config_path)
    return HarnessConfig(path=config_path, data=data)


def _validate_config(data: dict[str, Any], path: Path) -> None:
    required = ("design_id", "top_cell", "paths", "ports", "sizing_variables")
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"{path} missing required keys: {', '.join(missing)}")
    paths = data.get("paths", {})
    for key in ("source_netlist", "source_config"):
        if key not in paths:
            raise ValueError(f"{path} paths.{key} is required")
    if not isinstance(data.get("sizing_variables"), list) or not data["sizing_variables"]:
        raise ValueError(f"{path} sizing_variables must be a non-empty list")
