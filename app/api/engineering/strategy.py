"""Build strategy (W21): how a product of this category realistically gets built.

    build_strategy(category_key, solar=None) -> BuildStrategy

- full_design        mechanical / simple electronics (furniture, board, lamp, tracker): the founder designs every part.
- module_assembly    drone, irrigation, wearable, hair dryer, vacuum: the founder designs the product around bought-in,
                     pre-certified modules (motor + driver, battery pack, flight controller, heater + fan, BLE module).
- odm_customization  smartphone, camera, home robot: nobody designs these from scratch for a first product — find an ODM
                     with a close reference platform and customise it.

MOQ, entry cost and lead time are Estimates (industry ranges for a first production run, stated assumptions), never quotes.
"""

from __future__ import annotations

from contracts.artifacts import BuildStrategy

from api.engineering._util import est

KIND = {
    "furniture_baby": "full_design", "surfboard": "full_design", "lighting": "full_design", "tracker": "full_design",
    "generic": "full_design",
    "drone": "module_assembly", "irrigation": "module_assembly", "wearable": "module_assembly",
    "hair_dryer": "module_assembly", "vacuum": "module_assembly", "solar_roof": "module_assembly",
    "smartphone": "odm_customization", "camera": "odm_customization", "home_robot": "odm_customization",
}
TITLE = {"full_design": "Full design", "module_assembly": "Module assembly", "odm_customization": "ODM customisation"}
EXPLAIN = {
    "full_design": ("You design the whole product: every part, the BOM and (if any) the simple electronics are yours, and a "
                    "factory builds to your CAD and drawings. This is how mechanical products and simple electronics are made."),
    "module_assembly": ("You design the product around bought-in, pre-certified modules (e.g. motor + driver, battery pack, "
                        "radio module, heater + fan): your work is the architecture, the enclosure, the integration and the "
                        "software; the factory assembles the modules into your parts. Faster and cheaper than designing "
                        "every sub-system, and the modules' certifications carry part of the compliance."),
    "odm_customization": ("Not designed from scratch. Products like this need a modem / optics / autonomy stack and years of "
                          "certification work, so the realistic path is an ODM (original design manufacturer) with a close "
                          "reference platform: you customise the enclosure, colours, display, sensors and software, and the "
                          "ODM builds it on its certified base."),
}
ODM_PATH = [
    "Find an ODM with a close reference platform (size, chipset / modem bands or sensor, price tier) — shortlist 3 and get their reference designs",
    "Customise what differentiates the product: enclosure and CMF (colours, materials, finish), display, sensors, buttons, packaging",
    "Customise the software on the ODM's SDK / BSP (launcher, app policy, UI) and contract the update schedule",
    "Certifications: carried over where the RF / electrical design is unchanged (modular approvals), redone where you change it (new antenna area, metal back, new radio) — plus the product-level declaration in each market",
    "Engineering samples → pilot run (EVT/DVT/PVT) → mass production on the ODM line",
]

# category -> (customisable, from modules / platform, moq, entry USD, lead weeks, path, certifications note, assumptions)
TABLE: dict[str, dict] = {
    "furniture_baby": dict(custom=["Every panel, joint and dimension", "Wood species, lacquer, colours", "Pad, storage, accessories"],
                           fixed=["Fittings (cam locks, dowels) from catalogues"], moq=300, entry=12000, weeks=12,
                           path=["Freeze the CAD and nest the panels on 2440 × 1220 mm sheets", "Make 3 samples on a CNC router, test to EN 12221 / 16 CFR 1235", "Flat-pack packaging drop test", "First run of 300 units"],
                           cert="Child-care article testing (EN 12221, 16 CFR 1235) is on the full product: budget it once per design.",
                           why="CNC programmes + samples ≈ $4k, child-safety lab tests ≈ $5k, packaging dielines ≈ $1k, margin"),
    "surfboard": dict(custom=["Outline, rocker, rails, volume", "Laminate schedule, colours, fin setup"], fixed=["Foam blanks, fin boxes, fins from suppliers"],
                      moq=50, entry=6000, weeks=7, path=["Freeze the shape file (STEP) and send it to a CNC shaping machine", "Shape and glass 3 prototypes, ride-test", "First run of 50 boards at a glassing shop"],
                      cert="No mandatory certification for surfboards; EU General Product Safety Regulation applies.",
                      why="Shaping file + 3 prototypes ≈ $2.5k, glassing set-up, board bags; a moulded epoxy line needs ~300+ units"),
    "lighting": dict(custom=["Enclosure, diffuser, CMF", "LED board and driver (simple electronics)"], fixed=["LED driver IC and LEDs from catalogues"],
                     moq=1000, entry=25000, weeks=16, path=["Freeze CAD, order P20 steel moulds", "T1 samples → fixes → golden sample", "Safety + EMC tests", "First run"],
                     cert="Product-level tests (IEC 60598 / EMC) on your design.", why="2 moulds ≈ $15-20k, PCBA NRE, lab tests ≈ $5k"),
    "tracker": dict(custom=["Enclosure, CMF", "PCB around a pre-certified BLE module"], fixed=["BLE module (modular radio approval)"],
                    moq=2000, entry=30000, weeks=18, path=["Freeze CAD and PCB", "Moulds + pilot PCBA", "Radio / EMC with the module's modular approval", "First run"],
                    cert="Module's radio approval reused; product-level EMC and battery tests.", why="Moulds ≈ $15k, PCBA NRE ≈ $5k, certifications ≈ $8k"),
    "generic": dict(custom=["Enclosure, CMF", "Electronics around catalogue parts"], fixed=["Catalogue components"],
                    moq=1000, entry=30000, weeks=18, path=["Freeze CAD and PCB", "Moulds + pilot run", "Certifications", "First run"],
                    cert="Product-level safety / EMC tests on your design.", why="Moulds ≈ $15k, PCBA NRE, certifications ≈ $8k"),
    "drone": dict(custom=["Airframe, arms, fold mechanism, CMF", "Camera / gimbal choice, follow-me software, app"],
                  fixed=["Flight controller + ESC stack", "Motors and propellers", "Battery pack (IEC 62133-2 certified)", "Gimbal camera module", "Radio link module"],
                  moq=500, entry=80000, weeks=26, path=["Integrate an off-the-shelf flight controller + ESC + gimbal on your airframe", "Weight budget against the C-class limit", "C-class conformity (notified body) + radio tests", "Pilot run of 50, then 500"],
                  cert="EU class mark (Regulation (EU) 2019/945) by a notified body on the full aircraft; radio approvals of the link module reused.",
                  why="Airframe moulds ≈ $25k, integration engineering ≈ $25k, C-class + radio ≈ $20k, pilot run"),
    "irrigation": dict(custom=["Controller enclosure, UX, app and watering logic", "Kit composition (valves, probes)"], fixed=["Solenoid valves, soil probes, Wi-Fi/BLE module"],
                       moq=1000, entry=35000, weeks=18, path=["Choose valve + probe suppliers", "Controller enclosure moulds + PCBA around a certified radio module", "IP and radio tests", "First run"],
                       cert="Radio module approvals reused; IP rating and EMC on the controller.", why="Controller moulds ≈ $15k, PCBA NRE, IP + radio ≈ $8k"),
    "wearable": dict(custom=["Pod enclosure, strap, CMF", "Sensor choice, firmware, app, algorithms"], fixed=["BLE SoC module", "PPG / IMU sensor ICs", "Li-Po cell (certified)"],
                     moq=2000, entry=60000, weeks=24, path=["Design the pod around a BLE module + sensor reference designs", "Moulds (pod + LSR strap)", "Skin-contact + IP68 + radio tests", "Pilot run of 200, then 2000"],
                     cert="BLE module's modular approval reused; biocompatibility (ISO 10993), IP68 and battery tests on your product.",
                     why="Pod + strap moulds ≈ $25k, PCBA NRE ≈ $10k, tests ≈ $15k, pilot run"),
    "hair_dryer": dict(custom=["Body, nozzle, handle, CMF", "Controls, heat/speed profiles"], fixed=["Heater element + thermal cut-outs", "BLDC fan module", "Cord set (certified)"],
                       moq=2000, entry=70000, weeks=24, path=["Pick a heater + fan module supplier", "Heat-resistant PC moulds", "IEC 60335-2-23 safety + EMC tests", "First run"],
                       cert="Full appliance safety test (IEC 60335-1 / -2-23) on your design; certified cord set and cut-outs help.",
                       why="Moulds in heat-resistant PC ≈ $35k, safety lab ≈ $10k, fan/heater integration"),
    "vacuum": dict(custom=["Body, bin, floor head, CMF", "Airflow path, UX, firmware"], fixed=["BLDC suction motor + driver", "Battery pack with BMS", "Filters, brush bars"],
                   moq=3000, entry=150000, weeks=30, path=["Source the motor module and battery pack", "~15 moulds (body, bin, cyclone, head)", "IEC 60335-2-2 + battery + EMC tests", "Pilot run, then 3000"],
                   cert="Appliance safety on your product; battery pack certifications (IEC 62133-2, UN 38.3) from the pack supplier.",
                   why="~15 moulds ≈ $100k, motor/pack NRE, safety lab ≈ $15k"),
    "solar_roof": dict(custom=["Array layout, module choice, inverter and battery option"], fixed=["Certified PV modules, inverter, mounting system"],
                       moq=1, entry=0, weeks=6, path=["Roof survey (area, orientation, shading, structure)", "Design + grid-connection request", "Installation by a certified installer", "Commissioning and grid inspection"],
                       cert="Components carry their certifications; the installation follows national electrical rules (installer certification).",
                       why="Per installation; the cost is the turnkey price of the solar design"),
    "smartphone": dict(custom=["Enclosure and CMF (colours, materials, finish)", "Display size / type from the ODM's options", "Sensors and camera modules from the ODM's options", "Software: launcher, app policy (e.g. no social apps), UI"],
                       fixed=["Application processor + modem (reference board)", "RF / antenna design", "OS board-support package"],
                       moq=10000, entry=500000, weeks=44, path=ODM_PATH,
                       cert="Modem and radio approvals carried over only if the RF design is unchanged; SAR, carrier (PTCRB/GCF) and RED/FCC declarations for your model.",
                       why="ODM NRE for customisation ≈ $250-400k, certifications + carrier ≈ $100k, software ≈ $100k"),
    "camera": dict(custom=["Body, grip, CMF", "UI, shutter behaviour, film / print path choice", "Display and flash options"],
                   fixed=["Sensor + ISP + lens module (ODM)", "Image tuning", "Flash board"],
                   moq=3000, entry=120000, weeks=24, path=ODM_PATH,
                   cert="ODM module reports reused; product-level safety (IEC 62368-1), EMC / radio if Wi-Fi, battery.",
                   why="ODM customisation NRE ≈ $60k, body moulds ≈ $40k, certifications ≈ $20k"),
    "home_robot": dict(custom=["Shell and CMF", "Behaviours / skills on the ODM's autonomy stack", "Gripper / accessory choice"],
                       fixed=["Mobile base with drive, BMS and safety sensors", "Navigation (SLAM) and perception stack", "Compute module"],
                       moq=1000, entry=250000, weeks=36, path=ODM_PATH,
                       cert="Base-platform safety and radio reports reused; product-level safety (IEC 60335-1 / 62368-1), functional safety review of the arm.",
                       why="Platform licence + NRE ≈ $150k, shell moulds ≈ $60k, safety + certifications ≈ $40k"),
}


def build_strategy(category: str, solar=None) -> BuildStrategy:
    key = category if category in TABLE else "generic"
    kind = KIND.get(key, "full_design")
    t = TABLE[key]
    src = f"Typical first production run for this category ({t['why']}) — industry range, not a quote"
    entry_v = float(t["entry"])
    entry_note = src
    if key == "solar_roof" and solar is not None:
        entry_v = float(solar.install_cost.value)
        entry_note = f"Turnkey install cost of the solar design ({solar.install_cost.source_or_assumption})"
    unit = "USD"  # W21c: one currency per project
    moq_unit = "installation" if key == "solar_roof" else "units"
    return BuildStrategy(
        strategy=kind, title=TITLE[kind], explanation=EXPLAIN[kind], customisable=list(t["custom"]), not_customisable=list(t["fixed"]),
        moq=est(t["moq"], moq_unit, f"Typical minimum order for a first run in this category — {'per site' if key == 'solar_roof' else 'factory MOQ range'}", nd=0),
        entry_cost=est(entry_v, unit, entry_note, nd=0),
        lead_time=est(t["weeks"], "weeks", "Frozen design → first production units (tooling, samples, certification), typical", nd=0),
        path=list(t["path"]), certifications_note=t["cert"],
        assumptions=["Estimates for a first production run; real MOQs and NRE come from quotes",
                     "ODM figures assume an existing reference platform close to the brief" if kind == "odm_customization"
                     else "Module figures assume catalogue modules with their own certifications" if kind == "module_assembly"
                     else "Full-design figures assume tooling sized for the first run"],
    )


__all__ = ["build_strategy", "KIND"]
