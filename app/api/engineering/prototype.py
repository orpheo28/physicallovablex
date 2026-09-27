"""Prototype path: enclosure print/CNC from the measured volume, 5-board PCBA quick-turn, dev-kit BOM, steps,
timeline and total. Owner: W20. All costs are Estimates (formulas shown) except LCSC-matched dev-kit lines (Sourced).
"""

from __future__ import annotations

from contracts.artifacts import BOMItem, DevKitLine, ElectronicsArchitecture, PrototypeCostLine, PrototypePath, SolarDesign

from api.costs import lcsc
from api.costs._common import lcsc_source
from api.engineering._util import est, label_of, lv

PCBA_BOARDS = 5
PCB_FAB_USD = {2: 5.0, 4: 30.0}  # 5 boards ≤ 100 × 100 mm, quick-turn class
PCBA_SETUP_USD = 25.0  # stencil + setup + engineering fee
SMALL_QTY_PREMIUM = 3.0  # unmatched parts bought in tens, not thousands
PCBA_SHIPPING_USD = 20.0
# dev kits: (LCSC part number if in the snapshot, name, fallback price USD)
DEVKITS = {
    "nrf52": ("C17209540", "Seeed Studio XIAO nRF52840 (BLE dev board)", 9.9),
    "esp32": (None, "ESP32-C3 / S3 DevKit (Wi-Fi + BLE dev board)", 9.0),
    "stm32": (None, "STM32 Nucleo-64 dev board", 15.0),
    "avr": (None, "ATtiny/ATmega Arduino-compatible board", 6.0),
    "generic": (None, "Arduino-compatible dev board", 10.0),
}
BREAKOUT_USD = 8.0  # carrier board / breakout for one chip


def _pcba(bom: list[BOMItem], layers: int) -> tuple[PrototypeCostLine, str]:
    parts = 0.0
    lines = 0
    for it in bom:
        if str(getattr(it.category, "value", it.category)) != "electronic":
            continue
        lines += 1
        n = max(1, int(round(it.qty * PCBA_BOARDS)))
        if it.lcsc_pn and (p := lcsc.price_at(it.lcsc_pn, n)) is not None:
            parts += p * n
        elif it.unit_cost_est is not None:
            parts += it.unit_cost_est.value * SMALL_QTY_PREMIUM * n
        else:
            parts += 0.3 * SMALL_QTY_PREMIUM * n
    fab = PCB_FAB_USD.get(layers, 5.0)
    total = PCBA_SETUP_USD + fab + parts + PCBA_SHIPPING_USD
    note = (f"{PCBA_BOARDS} boards: setup/stencil {PCBA_SETUP_USD:g} + {layers}-layer fab {fab:g} + parts {parts:.2f} "
            f"(LCSC price at {PCBA_BOARDS}× qty where matched, else BOM estimate × {SMALL_QTY_PREMIUM:g}) + shipping {PCBA_SHIPPING_USD:g} USD")
    return PrototypeCostLine(item=f"PCBA quick-turn ({PCBA_BOARDS} boards, {lines} BOM lines)", amount=est(total, "USD", note, nd=0)), note


def _devkit(arch: ElectronicsArchitecture | None) -> list[DevKitLine]:
    if arch is None:
        return []
    pn, name, fallback = DEVKITS.get(arch.mcu_family, DEVKITS["generic"])
    out = []
    part = lcsc.get_part(pn) if pn else None
    if part is not None:
        out.append(DevKitLine(part=name, role="MCU + radio dev board", lcsc_pn=part.pn, unit_price=lv(part.price(1), "USD", "sourced", lcsc_source(part.pn))))
    else:
        out.append(DevKitLine(part=name, role="MCU + radio dev board", unit_price=est(fallback, "USD", "Typical distributor price for this dev board class")))
    for line in arch.power_budget:
        if line.block in ("mcu", "charger", "regulator"):
            continue
        match = lcsc.best_match(line.part, None, 5, part=line.part)
        if match is not None:
            out.append(DevKitLine(part=f"{line.part} → {match.mfr} on a breakout", role=line.block, lcsc_pn=match.pn,
                                  unit_price=lv(match.price(1), "USD", "sourced", lcsc_source(match.pn) + f" (chip only; add ~{BREAKOUT_USD:g} USD breakout)")))
        else:
            out.append(DevKitLine(part=f"{line.part} (module / breakout)", role=line.block,
                                  unit_price=est(BREAKOUT_USD, "USD", "Typical hobby breakout/module price, not in the LCSC snapshot")))
    return out


def prototype_path(pack: dict, volume_cm3, bom: list[BOMItem], arch: ElectronicsArchitecture | None,
                   solar: SolarDesign | None = None) -> PrototypePath:
    proto = pack["prototype"]
    units = int(proto.get("units", 3))
    lines: list[PrototypeCostLine] = []
    if solar is not None:  # site install: the "prototype" is a pilot installation
        lines.append(PrototypeCostLine(item=f"Pilot installation {solar.peak_power.value:g} kWp", amount=solar.install_cost))
        lines.append(PrototypeCostLine(item="Site survey + structural check", amount=est(round(450 * 1.08), "USD", "Installer survey visit + engineer note, 450 EUR typical × 1.08 USD/EUR (Estimate)", nd=0)))
        total = sum(line.amount.value for line in lines)
        return PrototypePath(
            enclosure_method=proto["method"], enclosure_volume=est(0, "cm³", "Not applicable (site install)"), units=1, cost_lines=lines,
            assembly_steps=list(proto["steps"]), timeline_weeks=est(6, "weeks", "Survey 1 + permits/grid request 3-4 (runs in parallel with procurement) + install 1 + commissioning 1"),
            total_cost=est(total, "USD", "Pilot installation + survey", nd=0),
        )
    vol = volume_cm3
    if "usd_per_litre" in proto:  # surfboard: priced per litre of board
        litres = vol.value / 1000
        cost = proto["setup_usd"] + proto["usd_per_litre"] * litres
        note = f"{proto['setup_usd']} USD glassing/finishing + {proto['usd_per_litre']} USD/L × {litres:.1f} L"
    else:
        per = float(proto.get("usd_per_cm3", 0.3))
        cost = units * (proto.get("setup_usd", 20) + per * vol.value)
        note = f"{units} × ({proto.get('setup_usd', 20)} USD setup + {per} USD/cm³ × {vol.value:.1f} cm³ {label_of(vol)} volume)"
    lines.append(PrototypeCostLine(item=f"Enclosure: {proto['method']}", amount=est(cost, "USD", note, nd=0)))
    devkit = _devkit(arch)
    steps = list(proto["steps"])
    if arch is not None:
        layers = 4 if any("4-layer" in (b.part or "").lower() for b in bom) or arch.mcu_family == "nrf52" else 2
        pcba, _ = _pcba(bom, layers)
        lines.append(pcba)
        dk = sum(d.unit_price.value for d in devkit)
        lines.append(PrototypeCostLine(item="Dev-kit bring-up set (firmware before the PCBA arrives)", amount=est(dk, "USD", "Sum of the dev-kit BOM lines", nd=0)))
        lines.append(PrototypeCostLine(item="Batteries, cables, fasteners, consumables", amount=est(40, "USD", "Flat allowance", nd=0)))
        weeks, tl = 4.0, "Design freeze 0.5 + PCBA quick-turn incl. shipping 2 + integration 1 + test 0.5 (enclosure and firmware on the dev kit run in parallel)"
        steps.append("PCB layout: next step (human or text-to-PCB) — the schematic follows the power tree and connection list above")
    else:
        weeks, tl = 3.0, "Design freeze 0.5 + build 1.5 + test 1"
    total = sum(line.amount.value for line in lines)
    return PrototypePath(
        enclosure_method=proto["method"], enclosure_volume=vol, units=units, cost_lines=lines, devkit_bom=devkit,
        assembly_steps=steps, timeline_weeks=est(weeks, "weeks", tl, nd=1), total_cost=est(total, "USD", "Sum of the prototype cost lines", nd=0),
    )
