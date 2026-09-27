"""Synthetic projects for the engineering layer (W20): one per target use case, built on the tracker-card fixtures
with the geometry, weight (incl. a 'measured' STEP volume) and BOM of that product. Used by tests/test_engineering.py
and to print sample outputs."""

from __future__ import annotations

import json
from pathlib import Path

from contracts.artifacts import BOMItem, BriefArtifact, Project, SpecArtifact

from api.stages.registry import StageContext

FIX = Path(__file__).resolve().parent.parent / "api" / "fixtures" / "tracker_card"

E, M = "electronic", "mechanical"
CASES: dict[str, dict] = {
    "kitesurf_wearable": {
        "prompt": "Whoop-style wearable for kitesurfers: heart rate, jump height and session log, waterproof strap",
        "category": "wearable", "dims": (44, 30, 12), "g": 32, "cm3": 6.5,
        "bom": [(E, "BLE 5 SoC nRF52840"), (E, "6-axis IMU LSM6DSO accelerometer gyroscope"), (E, "PPG heart-rate sensor MAX86141"),
                (E, "Barometric pressure sensor BMP390 (jump height)"), (E, "Li-Po cell 150 mAh 3.7V"), (E, "Li-Po charger IC"),
                (E, "LDO 3.3V regulator"), (E, "Vibration motor"), (E, "Chip antenna 2.4 GHz"), (M, "Silicone strap")],
    },
    "baby_changing_table": {
        "prompt": "Baby changing table with a fold-down activity panel for toddlers",
        "category": "mechanical", "dims": (800, 550, 950), "g": 24000, "cm3": 18000,
        "bom": [(M, "Birch plywood side panels"), (M, "Changing mat 800 × 500"), (M, "Soft-close hinges"), (M, "Anti-tip wall strap")],
    },
    "home_robot": {
        "prompt": "Next-gen home robot that tidies kids' toys, with a camera and arm",
        "category": "other", "dims": (400, 350, 900), "g": 12000, "cm3": 3000,
        "bom": [(E, "ESP32-S3 Wi-Fi module"), (E, "6-axis IMU accelerometer gyroscope"), (E, "ToF distance sensor VL53L1X (cliff)"),
                (E, "Camera module OV2640"), (E, "Drive motor 15W", 2), (E, "Motor driver DRV8833"), (E, "Li-ion pack 4S 5000 mAh 14.4V"),
                (E, "BMS 4S"), (E, "Buck converter 3.3V"), (M, "PA12 shell")],
    },
    "stick_vacuum": {
        "prompt": "Dyson-style cordless stick vacuum with cyclone and LCD",
        "category": "kitchen_appliance", "dims": (250, 120, 1100), "g": 2600, "cm3": 900,
        "bom": [(E, "Suction BLDC motor 200W"), (E, "BLDC motor driver"), (E, "STM32 MCU 32-bit"), (E, "Li-ion pack 6S 2600 mAh 25.2V"),
                (E, "BMS 6S"), (E, "Status LED", 3), (E, "LCD display 1.3 inch"), (M, "Cyclone body PC")],
    },
    "smart_irrigation": {
        "prompt": "Smart irrigation controller for 6 zones of drip lines, Wi-Fi app, soil moisture",
        "category": "iot_sensor", "dims": (140, 100, 60), "g": 320, "cm3": 90,
        "bom": [(E, "ESP32-C3 Wi-Fi module"), (E, "Latching solenoid valve driver H-bridge"), (E, "Latching solenoid valve 3W"),
                (E, "Soil moisture sensor capacitive"), (E, "Flow sensor hall"), (E, "2x AA lithium 3000 mAh 3V"), (E, "Buck-boost converter 3.3V"),
                (M, "ASA housing with O-ring")],
    },
    "rooftop_solar": {
        "prompt": "Rooftop solar array for a house in Biarritz, 35 m2 south-facing roof",
        "category": "other", "dims": (1722, 1134, 30), "g": 21500, "cm3": 12000,
        "bom": [(M, "PV module 430 W"), (M, "Mounting rails"), (E, "String inverter 5 kW")],
    },
    "surfboard": {
        "prompt": "Hydrodynamic surfboard, 6'0 shortboard for a 78 kg rider",
        "category": "mechanical", "dims": (1830, 500, 62), "g": 2800, "cm3": 30000,
        "bom": [(M, "EPS foam blank"), (M, "Epoxy resin + glass cloth"), (M, "Fin boxes FCS II", 3), (M, "Vent plug")],
    },
}


def _bom(rows) -> list[BOMItem]:
    out = []
    for i, row in enumerate(rows, 1):
        cat, part = row[0], row[1]
        qty = row[2] if len(row) > 2 else 1
        out.append(BOMItem(id=f"{cat[0]}{i}", part=part, category=cat, qty=qty))
    return out


def ctx_for(name: str, pid: str | None = None) -> StageContext:
    c = CASES[name]
    pid = pid or f"p_eng_{name}"
    brief = json.loads((FIX / "01_brief.json").read_text())
    brief.update(project_id=pid, prompt=c["prompt"], product_name=name.replace("_", " ").title(), one_liner=c["prompt"],
                 category=c["category"], key_features=[], fallback=False)
    spec = json.loads((FIX / "03_cad_spec.json").read_text())
    L, W, H = c["dims"]
    for k, v in zip(("length", "width", "height"), (L, W, H)):
        spec["overall_dimensions"][k].update(value=v)
    spec.update(project_id=pid, fallback=False, cad_files=[], bom=[b.model_dump() for b in _bom(c["bom"])],
                weight={"value": c["g"], "unit": "g", "label": "estimate",
                        "source_or_assumption": f"Enclosure volume {c['cm3']} cm³ (measured) × density + parts"})
    project = Project(id=pid, name=name, mode="idea", prompt=c["prompt"], example="tracker_card")
    return StageContext(project=project, stage=0, artifacts={1: BriefArtifact.model_validate(brief), 3: SpecArtifact.model_validate(spec)})
