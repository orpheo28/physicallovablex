"""Electronics architecture from the BOM. Owner: W20.

    architecture(bom, pack, text) -> ElectronicsArchitecture | None

Each electronic BOM line is classified into a block (MCU/SoC, sensor, radio, actuator, power...). The power tree,
a netlist-level connection list (MCU ↔ sensors ↔ radio ↔ power) and the power budget (typical datasheet-class
currents × the category's duty cycles) are derived in code; battery life = capacity × 85% usable / average current.
All figures are Estimates (typical currents, assumed duty cycles). No BOM electronics and none expected → None.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from contracts.artifacts import BOMItem, ElectronicsArchitecture, NetConnection, PowerBudgetLine, PowerNode

from api.engineering._util import est, first_number

USABLE = 0.85  # usable share of nameplate capacity (ageing, cut-off, temperature)
DRIVER_EFF = 0.9


@dataclass
class Block:
    id: str
    kind: str  # mcu | radio | imu | ppg | env | gnss | cellular | camera | lidar | display | led | led_power | buzzer | haptic
    #            | motor | valve | pump | moisture | flow | charger | regulator | battery | usb | mains | solar | button | antenna
    name: str
    part: str
    qty: float = 1.0
    active_ma: float = 0.0
    sleep_ua: float = 0.0
    bus: str = "gpio"
    signals: str = ""
    family: str | None = None
    extra: dict = field(default_factory=dict)


# (regex, kind, typical active mA, sleep µA, bus, signals, mcu family). Order matters: first match wins.
RULES: list[tuple[str, str, float, float, str, str, str | None]] = [
    # W21: phone-class application processors and large displays (ODM smartphone / camera platforms)
    (r"application processor|snapdragon|mediatek|dimensity|unisoc|exynos", "mcu", 250.0, 4000.0, "rf", "", "generic"),
    (r"\b[5-7](\.\d)?\s*(inch|in\b|\")", "display", 350.0, 0.0, "mipi", "MIPI DSI, backlight / AMOLED rails", None),
    (r"\bnrf5\d|ble soc|bluetooth soc|ble module|bluetooth module|\bble 5\b", "mcu", 5.3, 3.0, "rf", "", "nrf52"),
    (r"esp32|wi-?fi (module|soc)|wifi module", "mcu", 95.0, 10.0, "rf", "", "esp32"),
    (r"stm32|cortex-m|32-bit mcu|mcu 32", "mcu", 6.0, 2.0, "gpio", "", "stm32"),
    (r"attiny|atmega|8-bit|\bpy32\b|touch-dimming mcu", "mcu", 1.5, 1.0, "gpio", "", "avr"),
    (r"\bmcu\b|microcontroller|\bsoc\b|rp2040", "mcu", 6.0, 2.0, "gpio", "", "generic"),
    (r"\blte\b|cellular|cat-?m|nb-?iot|modem", "cellular", 90.0, 10.0, "uart", "TX, RX, PWRKEY", None),
    (r"gnss|\bgps\b", "gnss", 25.0, 15.0, "uart", "TX, RX, 1PPS", None),
    (r"\bppg\b|heart[- ]rate|optical hr|max86|afe44|spo2", "ppg", 1.2, 5.0, "i2c", "SDA, SCL, INT", None),
    (r"\bimu\b|accelerometer|gyroscope|gyro|lis2|lsm6|bmi\d|icm-", "imu", 0.5, 3.0, "i2c", "SDA, SCL, INT1", None),
    (r"\btof\b|vl53|lidar|distance sensor|cliff sensor", "lidar", 20.0, 5.0, "i2c", "SDA, SCL, XSHUT", None),
    (r"camera|image sensor", "camera", 150.0, 0.0, "spi", "SCK, MOSI, MISO, CS", None),
    (r"soil moisture|moisture sensor", "moisture", 5.0, 0.0, "adc", "AIN, EN", None),
    (r"flow sensor|flow meter", "flow", 3.0, 0.0, "gpio", "PULSE", None),
    (r"temperature|humidity|pressure sensor|barometer|bme\d|sht\d|environment", "env", 0.3, 0.5, "i2c", "SDA, SCL", None),
    (r"display|e-?ink|oled|\blcd\b|tft", "display", 8.0, 1.0, "spi", "SCK, MOSI, CS, DC, RST, BUSY", None),
    (r"motor driver|\besc\b|h-bridge|drv8", "driver", 0.0, 1.0, "pwm", "PWM, DIR", None),
    (r"solenoid|valve", "valve", 0.0, 0.0, "gpio", "IN1, IN2 (H-bridge)", None),
    (r"\bpump\b", "pump", 0.0, 0.0, "pwm", "PWM", None),
    (r"vibration motor|haptic|\berm\b|\blra\b", "haptic", 60.0, 0.0, "gpio", "EN", None),
    (r"motor|bldc", "motor", 0.0, 0.0, "pwm", "PWM, DIR, FG", None),
    (r"\bled\b.*\d(\.\d+)?\s*w\b|\d(\.\d+)?\s*w\b.*\bled\b|power led|led bar|2835|5630|cob", "led_power", 0.0, 0.0, "pwm", "PWM (MOSFET gate)", None),
    (r"\bled\b", "led", 2.0, 0.0, "gpio", "LED", None),
    (r"buzzer|piezo|speaker", "buzzer", 8.0, 0.0, "pwm", "PWM", None),
    (r"charger|charging ic|tp4056|\bbms\b|pmic|battery management", "charger", 0.0, 2.0, "power", "", None),
    (r"\bldo\b|regulator|buck|boost|dc-?dc", "regulator", 0.0, 5.0, "power", "", None),
    (r"cell|battery|li-?ion|li-?po|18650|21700|\baa\b|lifepo|coin", "battery", 0.0, 0.0, "power", "", None),
    (r"usb", "usb", 0.0, 0.0, "usb", "VBUS, D+, D-, CC1, CC2", None),
    (r"ac adapter|mains|power supply|ac-dc|wall plug", "mains", 0.0, 0.0, "power", "", None),
    (r"solar", "solar", 0.0, 0.0, "power", "", None),
    (r"button|switch|touch pad|tactile", "button", 0.0, 0.0, "gpio", "BTN (pull-up, wake)", None),
    (r"antenna", "antenna", 0.0, 0.0, "rf", "RF 2.4 GHz", None),
]
DEFAULT_DUTY = {"mcu": 5, "radio": 1, "imu": 100, "ppg": 100, "env": 5, "gnss": 5, "cellular": 0.5, "camera": 10, "lidar": 20,
                "display": 5, "led": 1, "led_power": 100, "buzzer": 0.1, "haptic": 0.1, "motor": 100, "valve": 0.1, "pump": 5,
                "moisture": 0.5, "flow": 1, "driver": 100}
LOADS = set(DEFAULT_DUTY)
SKIP = re.compile(r"\b(resistor|capacitor|mlcc|crystal|oscillator|passives?|inductor|ferrite|\bpcb\b|mcpcb|fpc|connector|header|pogo|esd|tvs|diode|mosfet|transistor)\b", re.I)
MOTOR_W_DEFAULT = {"vacuum": 180.0, "home_robot": 5.0}


def _watts(text: str) -> float | None:
    return first_number(r"(\d+(?:[.,]\d+)?)\s*w\b", text)


def classify(item: BOMItem) -> Block | None:
    """Block for one electronic BOM line; None for passives, PCBs, connectors and other non-functional lines."""
    if SKIP.search(item.part):
        return None
    text = f"{item.part} {item.description or ''} {item.manufacturer_pn or ''}".lower()
    for pattern, kind, act, slp, bus, sig, fam in RULES:
        if re.search(pattern, text, re.I):
            return Block(id="", kind=kind, name=item.part, part=item.part, qty=float(item.qty or 1), active_ma=act, sleep_ua=slp,
                         bus=bus, signals=sig, family=fam)
    return None


def _battery_params(blocks: list[Block], pack: dict) -> tuple[float | None, float, str, str]:
    """(capacity mAh or None, voltage, capacity note, voltage note)."""
    p = pack.get("params", {})
    bat = next((b for b in blocks if b.kind == "battery"), None)
    text = (bat.part if bat else "").lower()
    cap = first_number(r"(\d+(?:[.,]\d+)?)\s*mah", text)
    cap_note = f"Capacity from the BOM line '{bat.part}'" if cap else None
    if cap is None and (bat is not None or p.get("battery_mah_default")):
        cap = float(p.get("battery_mah_default") or 0) or None
        cap_note = f"Category default {cap:g} mAh (no capacity in the BOM) — confirm with the cell datasheet" if cap else None
    v = first_number(r"(\d+(?:[.,]\d+)?)\s*v\b", text)
    s_cells = first_number(r"(\d)\s*s\b", text)
    if v:
        v_note = f"Voltage from the BOM line '{bat.part}'"
    elif s_cells:
        v, v_note = 3.6 * s_cells, f"{s_cells:g}S Li-ion × 3.6 V nominal"
    elif re.search(r"li-?ion|li-?po|18650|21700", text):
        v, v_note = 3.7, "Li-ion/Li-Po nominal 3.7 V"
    else:
        v = float(p.get("battery_v_default", 3.7))
        v_note = f"Category default {v:g} V"
    return cap, float(v), cap_note or "", v_note


def architecture(bom: list[BOMItem], pack: dict, text: str = "") -> ElectronicsArchitecture | None:
    params = pack.get("params", {})
    elec = [b for b in bom if str(getattr(b.category, "value", b.category)) == "electronic"]
    implied = False
    blocks = [blk for it in elec if (blk := classify(it)) is not None]
    if not any(b.kind == "mcu" for b in blocks):
        typical = params.get("typical_electronics") or []
        if typical:
            implied = True
            blocks += [blk for t in typical if (blk := classify(BOMItem(id="x", part=t, category="electronic", qty=1))) is not None]
        elif not blocks:
            return None
        else:  # electronics without a controller (e.g. switch + LED): assume a small MCU for the budget
            implied = True
            blocks.append(Block(id="", kind="mcu", name="MCU (implied)", part="8-bit MCU (implied)", active_ma=1.5, sleep_ua=1.0, family="avr"))
    for i, b in enumerate(blocks):
        b.id = f"b{i + 1}"
    mcu = next(b for b in blocks if b.kind == "mcu")
    family = mcu.family or params.get("default_family", "generic")
    radio = []
    if family == "nrf52":
        radio = ["BLE 5"]
    elif family == "esp32":
        radio = ["Wi-Fi 2.4 GHz", "BLE 5"]
    radio += [{"cellular": "LTE-M / NB-IoT", "gnss": "GNSS (receive)"}[b.kind] for b in blocks if b.kind in ("cellular", "gnss")]

    cap, vbat, cap_note, v_note = _battery_params(blocks, pack)
    has_battery = any(b.kind == "battery" for b in blocks)
    duty = {**DEFAULT_DUTY, **(params.get("duty") or {})}
    src_note = "assumed typical architecture for the category (not in the BOM)" if implied else "from the BOM"

    # power-hungry loads: current at the battery from watts
    for b in blocks:
        w = _watts(b.part)
        if b.kind == "led_power":
            w_each = w or 0.2
            b.active_ma = w_each * b.qty / vbat / DRIVER_EFF * 1000
            b.extra["note"] = f"{b.qty:g} × {w_each:g} W / {vbat:g} V / {DRIVER_EFF:.0%} driver"
        elif b.kind in ("motor", "pump", "valve"):
            default_w = {"motor": MOTOR_W_DEFAULT.get(pack["key"], 3.0), "pump": 12.0, "valve": 3.0}[b.kind]
            w_each = w or default_w
            b.active_ma = w_each * b.qty / vbat / DRIVER_EFF * 1000
            b.extra["note"] = f"{b.qty:g} × {w_each:g} W{'' if w else ' (category default)'} / {vbat:g} V / {DRIVER_EFF:.0%} driver"

    # ---- power tree
    nodes: list[PowerNode] = []
    src = next((b for b in blocks if b.kind in ("usb", "mains", "solar")), None)
    src_id = None
    if src is not None:
        v = {"usb": 5.0, "mains": 12.0, "solar": 6.0}[src.kind]
        nodes.append(PowerNode(id="p_src", name=src.name, kind="source", parent=None, voltage=est(v, "V", f"{src.kind.upper()} input nominal")))
        src_id = "p_src"
    charger = next((b for b in blocks if b.kind == "charger"), None)
    parent = src_id
    if charger is not None:
        nodes.append(PowerNode(id="p_chg", name=charger.name, kind="charger", parent=src_id, voltage=est(vbat, "V", "Charges the cell; output = VBAT")))
        parent = "p_chg"
    if has_battery or cap:
        bat = next((b for b in blocks if b.kind == "battery"), None)
        nodes.append(PowerNode(id="p_bat", name=bat.name if bat else f"Battery {cap or '?'} mAh (category default)", kind="storage",
                               parent=parent, voltage=est(vbat, "V", v_note)))
        parent = "p_bat"
    reg = next((b for b in blocks if b.kind == "regulator"), None)
    logic_v = 1.8 if family == "nrf52" and vbat <= 3.0 else 3.3
    if reg is not None or vbat > 3.6:
        nodes.append(PowerNode(id="p_reg", name=reg.name if reg else f"{logic_v:g} V regulator (implied, VBAT {vbat:g} V)", kind="regulator",
                               parent=parent, voltage=est(logic_v, "V", "Logic rail for MCU and sensors")))
        logic_parent = "p_reg"
    else:
        logic_parent = parent
    for b in blocks:
        if b.kind in LOADS:
            on_vbat = b.kind in ("led_power", "motor", "pump", "valve", "haptic", "driver")
            nodes.append(PowerNode(id=f"p_{b.id}", name=b.name, kind="load", parent=parent if on_vbat else logic_parent,
                                   voltage=est(vbat if on_vbat else logic_v, "V", "VBAT (through its driver)" if on_vbat else "Logic rail")))

    # ---- netlist-level connections
    conns: list[NetConnection] = []
    for n in nodes:
        if n.parent:
            parent_name = next(x.name for x in nodes if x.id == n.parent)
            conns.append(NetConnection(source=parent_name, target=n.name, bus="power", signals=f"{n.voltage.value:g} V"))
    driver = next((b for b in blocks if b.kind == "driver"), None)
    for b in blocks:
        if b is mcu or b.kind in ("battery", "regulator", "mains", "solar"):
            continue
        if b.kind == "charger":
            conns.append(NetConnection(source=mcu.name, target=b.name, bus="gpio", signals="CHG_STAT, PGOOD"))
        elif b.kind == "antenna":
            conns.append(NetConnection(source=mcu.name, target=b.name, bus="rf", signals="RF (50 Ω matching network)"))
        elif b.kind in ("motor", "pump") and driver is not None:
            conns.append(NetConnection(source=driver.name, target=b.name, bus="power", signals="Motor phases / OUT1, OUT2"))
        elif b.kind == "led_power":
            conns.append(NetConnection(source=mcu.name, target=b.name, bus="pwm", signals="PWM → MOSFET/CC driver gate"))
        elif b.kind == "usb":
            conns.append(NetConnection(source=b.name, target=mcu.name, bus="usb" if family in ("esp32", "stm32") else "gpio",
                                       signals="D+, D- (DFU/serial)" if family in ("esp32", "stm32") else "VBUS_DET"))
        elif b.bus in ("i2c", "spi", "uart", "gpio", "pwm", "adc"):
            conns.append(NetConnection(source=mcu.name, target=b.name, bus=b.bus, signals=b.signals or b.bus.upper()))
    if has_battery:
        conns.append(NetConnection(source=mcu.name, target="Battery voltage divider", bus="adc", signals="VBAT_SENSE (fuel estimate)"))

    # ---- power budget
    lines: list[PowerBudgetLine] = []
    total = 0.0
    for b in blocks:
        if b.kind not in LOADS:
            continue
        d = float(duty.get(b.kind, 1.0))
        qty = 1.0 if b.kind in ("led_power", "motor", "pump", "valve") else max(1.0, b.qty if b.kind in ("led",) else 1.0)
        act = b.active_ma * qty
        avg = act * d / 100 + b.sleep_ua / 1000 * (1 - d / 100)
        total += avg
        act_note = b.extra.get("note") or f"Typical active current of a {b.kind.upper() if len(b.kind) <= 4 else b.kind} ({src_note})"
        lines.append(PowerBudgetLine(
            block=b.kind, part=b.name,
            active_current=est(act, "mA", act_note, nd=3),
            sleep_current=est(b.sleep_ua, "µA", "Typical sleep/standby current", nd=1),
            duty_cycle=est(d, "pct", f"Category duty cycle for '{b.kind}' ({pack['title']})", nd=3),
            average_current=est(avg, "mA", "active × duty + sleep × (1 − duty)", nd=4),
        ))
    for b in blocks:
        if b.kind in ("charger", "regulator"):
            total += b.sleep_ua / 1000
            lines.append(PowerBudgetLine(block=b.kind, part=b.name, active_current=est(0, "mA", "Pass-through part"),
                                         sleep_current=est(b.sleep_ua, "µA", "Typical quiescent current", nd=1),
                                         duty_cycle=est(100, "pct", "Always on"), average_current=est(b.sleep_ua / 1000, "mA", "Quiescent current", nd=4)))
    avg_lv = est(total, "mA", "Sum of the power-budget lines", nd=4)
    life = None
    if cap and total > 0:
        hours = cap * USABLE / total
        unit, val = ("days", hours / 24) if hours >= 72 else ("h", hours)
        life = est(val, unit, f"{cap:g} mAh × {USABLE:.0%} usable / {total:.4g} mA average", nd=2 if val < 10 else 1)
    mcu_part = mcu.part + (" (implied)" if implied and "(implied)" not in mcu.part else "")
    return ElectronicsArchitecture(
        mcu_family=family if family in ("nrf52", "esp32", "stm32", "avr", "generic") else "generic",
        mcu_part=mcu_part, radio=radio, power_tree=nodes, connections=conns, power_budget=lines, average_current=avg_lv,
        battery_voltage=est(vbat, "V", v_note) if (has_battery or cap) else None,
        battery_capacity=est(cap, "mAh", cap_note, nd=0) if cap else None,
        battery_life=life,
    )


def battery_hours(arch: ElectronicsArchitecture | None) -> float | None:
    if arch is None or arch.battery_life is None:
        return None
    return arch.battery_life.value * (24 if arch.battery_life.unit == "days" else 1)
