"""Shared helpers for the W4 agents (private module: not auto-imported by discovery)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from contracts.artifacts import Assumption, Label, LabeledValue

from api.llm import model_for

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

# Fixed category vocabulary (documented in README.md; W2/W3 use it for defaults).
CATEGORIES = (
    "lighting",
    "ble_accessory",
    "iot_sensor",
    "wearable",
    "audio",
    "input_device",
    "kitchen_appliance",
    "mechanical",
    "other",
)

TODAY_SOURCE_DATE = "2026-09-26"  # date of the research the sourced figures come from


def lv(value: float, unit: str, label: Label | str, source: str) -> LabeledValue:
    return LabeledValue(value=float(value), unit=unit, label=Label(label), source_or_assumption=source)


def estimate(value: float, unit: str, assumption: str) -> LabeledValue:
    return lv(value, unit, Label.estimate, assumption)


class AssumptionLog:
    """Collects the assumptions of one artifact with sequential ids."""

    def __init__(self, stage: int, prefix: str = "a"):
        self.stage = stage
        self.prefix = prefix
        self.items: list[Assumption] = []

    def add(self, text: str, label: Label | str = Label.estimate, source: str | None = None) -> None:
        if any(a.text == text for a in self.items):
            return
        self.items.append(
            Assumption(id=f"{self.prefix}{len(self.items) + 1}", text=text, label=Label(label), source=source, stage=self.stage)
        )


def llm_tag(route: str) -> str:
    return f"llm:{model_for(route)}"  # type: ignore[arg-type]


def as_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str, separators=(",", ":"))


def render_prompt(template: str, /, **values: Any) -> str:
    """Load prompts/<template>.md and replace {{key}} placeholders (JSON-dumping non-strings)."""
    text = (PROMPTS_DIR / f"{template}.md").read_text(encoding="utf-8")
    for key, val in values.items():
        text = text.replace("{{" + key + "}}", val if isinstance(val, str) else as_json(val))
    return text


def dump(model: Any, **kw: Any) -> Any:
    """Compact JSON-able view of a pydantic model (or list of them) for prompts."""
    if isinstance(model, list):
        return [dump(m, **kw) for m in model]
    return model.model_dump(mode="json", **kw)
