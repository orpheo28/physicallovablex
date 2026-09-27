"""Refine prompt → typed PATCH (W17). One LLM call (route "main", complete_json, strict schema), nothing else.

    propose(message, state) -> RefinePatch

The model only translates the founder's words into operations; every value is re-checked and clamped in
api.studio.apply (colour hex, material vocabulary, family ranges, price, quantities). It must never invent a
measurement: dimensions only when the founder states a number (or an exact relative change of a known one).
"""

from __future__ import annotations

import json
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from api.llm import complete_json

PATCH_TIMEOUT_S = 25.0


class _Op(BaseModel):
    model_config = ConfigDict(extra="ignore")


class SetColor(_Op):
    op: Literal["set_color"]
    hex: str = Field(description="sRGB '#RRGGBB'")
    name: str = Field(max_length=30, description="Colour name, e.g. 'Blush pink'")


class SetMaterial(_Op):
    op: Literal["set_material"]
    material: Literal["pc_abs", "aluminium", "stainless_steel", "tpu"] = Field(
        description="pc_abs = moulded plastic; aluminium = CNC metal; stainless_steel; tpu = soft-touch rubbery plastic")
    finish: str | None = Field(default=None, max_length=60, description="e.g. 'Soft-touch paint', 'Bead-blasted anodised'")


class SetDimensions(_Op):
    op: Literal["set_dimensions"]
    length: float | None = Field(default=None, description="mm; only if the founder gave it")
    width: float | None = Field(default=None, description="mm; only if the founder gave it")
    height: float | None = Field(default=None, description="mm (pod thickness / ring band width); only if given")


class SetShapeFamily(_Op):
    op: Literal["set_shape_family"]
    family: Literal["rounded_box", "puck", "slab", "wearable_band", "ring"]


class RegenerateGeometry(_Op):
    op: Literal["regenerate_geometry"]
    instruction: str = Field(max_length=300, description=(
        "The change of form in the founder's words, e.g. 'wider nose', 'add two storage baskets under the top', "
        "'make the dust bin bigger' — applied by editing the product's CAD program"))


class UpgradeBattery(_Op):
    op: Literal["upgrade_battery"]
    capacity_mah: float | None = Field(default=None, description="New capacity in mAh, only if the founder gave it")
    factor: float | None = Field(default=None, description="Capacity multiplier (e.g. 2 for 'double the battery'); default 1.5")


class AddFeature(_Op):
    op: Literal["add_feature"]
    name: str = Field(max_length=60)
    description: str = Field(default="", max_length=200)


class AddComponent(_Op):
    op: Literal["add_component"]
    part: str = Field(max_length=80, description="Generic part name, with a common part number if confident")
    category: Literal["electronic", "mechanical", "packaging"]
    qty: float = Field(default=1, gt=0)
    rationale: str = Field(default="", max_length=160)
    manufacturer_pn: str | None = Field(default=None, max_length=40)


class RemoveComponent(_Op):
    op: Literal["remove_component"]
    bom_item_id: str


class SetTargetPrice(_Op):
    op: Literal["set_target_price"]
    value: float = Field(gt=0)
    currency: Literal["USD", "EUR", "GBP"] = "USD"


class SetMarkets(_Op):
    op: Literal["set_markets"]
    markets: list[str] = Field(min_length=1, max_length=6, description="Codes: US, EU, UK, CA, AU")


class NoteRequirement(_Op):
    op: Literal["note_requirement"]
    text: str = Field(max_length=200)


PatchOp = Annotated[
    Union[SetColor, SetMaterial, SetDimensions, SetShapeFamily, RegenerateGeometry, UpgradeBattery, AddFeature, AddComponent,
          RemoveComponent, SetTargetPrice, SetMarkets, NoteRequirement],
    Field(discriminator="op"),
]


class RefinePatch(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ops: list[PatchOp] = Field(default_factory=list, max_length=10)
    summary: str = Field(default="", max_length=200, description="One short sentence describing the change")


SYSTEM = """You are the product engineer of a hardware studio. A founder refines their product by chatting. Translate
the founder's latest message into a PATCH: a list of typed operations on the current product. Rules:
- Only what the message asks for. No unrelated changes.
- Never invent a measurement: set_dimensions only with numbers the founder gave (or an exact relative change of a
  current value, e.g. '2 mm thinner'). A vague 'smaller'/'thinner' of the whole product without a number →
  note_requirement; a change to the form of one feature or part (nose, bin, arms…) → regenerate_geometry.
- A new capability (sensor, radio, haptics...) = add_feature AND add_component for the part(s) it needs (generic
  catalogue parts; give a manufacturer part number only when confident, e.g. MAX30102 for optical heart rate/SpO2).
- A change of form or a new physical part that the other operations cannot express ('wider nose', 'bigger bin',
  'add two storage baskets', 'foldable arms', 'rounder') → regenerate_geometry with the instruction in the founder's
  words (plus add_component for bought-in parts). Never use set_shape_family for that: set_shape_family only switches
  between the listed enclosure families (rounded_box, puck, slab, wearable_band, ring) of a small device.
- Longer flight time / battery life / runtime / autonomy → upgrade_battery (capacity_mah only if the founder gave it,
  factor for 'double' etc.; default 1.5×). Only claims you cannot model (e.g. '5-day battery' as a marketing target
  without a change) go to note_requirement.
- set_color needs a real sRGB hex. set_material only from the allowed list.
- Anything that cannot be modelled physically (claims, app features, battery life targets, waterproofing...) →
  note_requirement.
- remove_component uses the bom_item_id shown in the BOM."""

PROMPT = """Current product (version {version}):
{state}

Founder's message: "{message}"

Return the PATCH."""


def propose(message: str, state: dict, version: int) -> RefinePatch:
    prompt = PROMPT.format(version=version, state=json.dumps(state, indent=1, ensure_ascii=False), message=message.strip())
    return complete_json("main", prompt, RefinePatch, system=SYSTEM, max_tokens=1500, temperature=0.1,
                         timeout_s=PATCH_TIMEOUT_S)


__all__ = ["RefinePatch", "PatchOp", "SetColor", "SetMaterial", "SetDimensions", "SetShapeFamily", "RegenerateGeometry", "UpgradeBattery", "AddFeature",
           "AddComponent", "RemoveComponent", "SetTargetPrice", "SetMarkets", "NoteRequirement", "propose"]
