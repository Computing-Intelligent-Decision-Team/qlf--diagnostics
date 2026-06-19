"""Sizing action legalizer and action-space helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SizingVariable:
    name: str
    param: str
    minimum: float
    maximum: float
    init: float
    step: float | None = None
    unit: str = ""
    kind: str = "device"
    instances: tuple[str, ...] = ()
    integer: bool = False

    @classmethod
    def from_config(cls, item: dict[str, Any]) -> "SizingVariable":
        return cls(
            name=str(item["name"]),
            param=str(item.get("param", item["name"])).lower(),
            minimum=float(item["min"]),
            maximum=float(item["max"]),
            init=float(item.get("init", item["min"])),
            step=None if item.get("step") in (None, "") else float(item["step"]),
            unit=str(item.get("unit", "")),
            kind=str(item.get("kind", "device")),
            instances=tuple(str(value).lower() for value in item.get("instances", [])),
            integer=bool(item.get("integer", False)),
        )


class SizingLegalizer:
    def __init__(self, variables: list[dict[str, Any]]):
        self.variables = [SizingVariable.from_config(item) for item in variables]
        self.by_name = {variable.name: variable for variable in self.variables}

    @property
    def action_dim(self) -> int:
        return len(self.variables)

    def initial_values(self) -> dict[str, float | int]:
        return {variable.name: self._snap(variable, variable.init) for variable in self.variables}

    def initial_normalized(self) -> list[float]:
        return [self.to_normalized(variable.name, self._snap(variable, variable.init)) for variable in self.variables]

    def legalize_normalized(self, action: list[float]) -> dict[str, float | int]:
        if len(action) != self.action_dim:
            raise ValueError(f"expected action_dim={self.action_dim}, got {len(action)}")
        values: dict[str, float | int] = {}
        for variable, raw in zip(self.variables, action):
            norm = min(1.0, max(-1.0, float(raw)))
            value = variable.minimum + (norm + 1.0) * 0.5 * (variable.maximum - variable.minimum)
            values[variable.name] = self._snap(variable, value)
        return values

    def legalize_values(self, values: dict[str, float | int]) -> dict[str, float | int]:
        merged = self.initial_values()
        merged.update(values)
        return {
            variable.name: self._snap(variable, float(merged[variable.name]))
            for variable in self.variables
        }

    def values_to_normalized(self, values: dict[str, float | int]) -> list[float]:
        legal = self.legalize_values(values)
        return [self.to_normalized(variable.name, legal[variable.name]) for variable in self.variables]

    def to_normalized(self, name: str, value: float | int) -> float:
        variable = self.by_name[name]
        if variable.maximum <= variable.minimum:
            return 0.0
        return 2.0 * ((float(value) - variable.minimum) / (variable.maximum - variable.minimum)) - 1.0

    def device_assignments(self, values: dict[str, float | int]) -> dict[str, dict[str, float | int]]:
        legal = self.legalize_values(values)
        assignments: dict[str, dict[str, float | int]] = {}
        for variable in self.variables:
            if variable.kind != "device":
                continue
            for instance in variable.instances:
                assignments.setdefault(instance, {})[variable.param] = legal[variable.name]
        return assignments

    def variable_units(self) -> dict[str, str]:
        return {variable.name: variable.unit for variable in self.variables}

    def param_units(self) -> dict[tuple[str, str], str]:
        units: dict[tuple[str, str], str] = {}
        for variable in self.variables:
            if variable.kind != "device":
                continue
            for instance in variable.instances:
                units[(instance, variable.param)] = variable.unit
        return units

    @staticmethod
    def _snap(variable: SizingVariable, value: float) -> float | int:
        clamped = min(variable.maximum, max(variable.minimum, float(value)))
        if variable.step:
            steps = round((clamped - variable.minimum) / variable.step)
            clamped = variable.minimum + steps * variable.step
            clamped = min(variable.maximum, max(variable.minimum, clamped))
        if variable.integer:
            return int(round(clamped))
        return round(float(clamped), 12)
