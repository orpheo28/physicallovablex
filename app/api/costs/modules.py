"""Module price model (W21c): complex parts and sub-assemblies priced as modules, never as a catalogue chip.

A flight controller, an ESC, a BLDC motor, a camera or display module, a battery pack, a LiDAR, a phone mainboard or a
vacuum floor head is not an LCSC part: `estimate(text, qty)` gives a typical 2026 trade price at ~2k units
(Estimate, assumption stated), else None. Battery packs are priced by energy (Wh parsed from the line, else a stated
default for the line's kind). Used by api/costs/engine.py when a BOM line has no price (or only a placeholder).
"""

from __future__ import annotations

import re

USD_PER_WH = 0.35  # Li-ion / Li-Po pack incl. cells, 2026 small-pack trade range $0.25-0.50/Wh
PACK_OVERHEAD = 2.0  # protection board, wiring, shrink per pack


def _num(rx: str, text: str) -> float | None:
    m = re.search(rx, text, re.I)
    return float(m.group(1).replace(",", ".")) if m else None


def battery(text: str) -> tuple[float, str] | None:
    if not re.search(r"batter|li-?po|li-?ion|\bpack\b|\bcell\b|18650|21700", text, re.I) or re.search(
            r"charg(er|ing) ic|management|bms|protection board|holder|contact|controller", text, re.I):
        return None
    mah = _num(r"(\d{2,6}(?:[.,]\d+)?)\s*mah", text)
    cells = _num(r"(\d)\s*s\b", text)
    volts = _num(r"(\d{1,2}(?:\.\d)?)\s*v\b", text) or (3.7 * cells if cells else None)
    low = text.lower()
    if mah is None:  # stated defaults per kind of product line
        mah, what = ((1500, "flight pack") if "flight" in low else (2500, "6S appliance pack") if re.search(r"6s|21\.6|vacuum", low)
                     else (5000, "robot pack") if "robot" in low or re.search(r"4s|14\.4", low) else (4000, "phone-class pack")
                     if "phone" in low else (2000, "generic pack"))
        volts = volts or (14.8 if "flight" in low else 21.6 if what.startswith("6S") else 14.4 if what == "robot pack" else 3.85 if "phone" in what else 3.7)
    else:
        what = "stated capacity"
        volts = volts or 3.7
    wh = mah / 1000 * volts
    usd = max(1.2, wh * USD_PER_WH + (PACK_OVERHEAD if wh > 5 else 0.4))
    return round(usd, 2), f"Battery priced by energy: {mah:.0f} mAh × {volts:.1f} V = {wh:.1f} Wh ({what}) × ${USD_PER_WH}/Wh + pack overhead"


# (regex on the line, USD per unit, what) — first match wins; specific modules before generic words
TABLE: list[tuple[str, float, str]] = [
    (r"flight controller", 18.0, "flight-controller board (STM32F4/F7 + IMU + baro)"),
    (r"4-in-1|\besc\b|speed controller", 22.0, "4-in-1 ESC, 20-35 A"),
    (r"high-speed bldc|vacuum motor|suction motor|digital motor", 28.0, "100k rpm BLDC suction motor with impeller"),
    (r"brushless|outrunner", 7.0, "small brushless outrunner motor"),
    (r"universal motor|ac motor|fan motor|motor with fan", 6.0, "AC/DC fan motor with impeller"),
    (r"gear ?motor", 4.5, "DC gearmotor with encoder"),
    (r"servo", 6.5, "robot joint servo"),
    (r"vibration motor|coin motor|haptic", 0.35, "coin vibration motor"),
    (r"propeller", 2.5, "propeller set"),
    (r"gimbal", 45.0, "2-axis gimbal + 4K camera module"),
    (r"compute module|linux|vision compute|\bsom\b", 35.0, "embedded Linux / vision compute module"),
    (r"lidar", 45.0, "2D LiDAR module"),
    (r"mainboard|main board|motherboard|reference board", 85.0, "phone-class mainboard (SoC + modem + memory), ODM"),
    (r"camera main pcb|image processing", 18.0, "camera ODM main board (ISP + MCU)"),
    (r"(\d{2,3})\s*mp|camera module|image sensor module|lens and image sensor|rgb camera", 8.0, "camera module (sensor + lens)"),
    (r"[5-7](\.\d)?\s*(inch|in\b|\")|display and touch|touch assembly|amoled", 32.0, "6-inch-class display + touch module"),
    (r"display|\blcd\b|\boled\b", 4.5, "small LCD/OLED display module"),
    (r"ejector|exposure engine|film transport", 12.0, "instant-film ejector / exposure mechanism"),
    (r"film cartridge|instant film", 8.0, "instant-film pack (in the box)"),
    (r"floor head", 12.0, "motorised floor head with brush roll"),
    (r"cyclone|dust bin", 6.0, "cyclone + clear bin moulding set"),
    (r"\bwand\b", 4.0, "aluminium wand"),
    (r"chassis|wheel set|wheeled base", 15.0, "drive chassis + wheels"),
    (r"arm and gripper|gripper", 18.0, "arm + gripper mechanics"),
    (r"heating element|heater|nichrome", 3.5, "heating element"),
    (r"thermal (safety )?cut|thermal fuse|cut-?out", 0.6, "thermal cut-out"),
    (r"mains|power cord|cord set", 2.2, "certified mains cord"),
    (r"solenoid|valve", 7.5, "1-inch solenoid valve"),
    (r"soil|moisture probe", 2.5, "capacitive soil-moisture probe"),
    (r"solar panel|pv panel", 6.0, "small 5 W PV panel"),
    (r"battery management|protection board|\bbms\b", 3.5, "BMS / protection board"),
    (r"charge controller|charger and dock|dock|charging interface", 5.0, "charger / dock"),
    (r"motor driver|motor control pcb|control pcb|controller pcb|power and airflow", 6.0, "motor / control PCBA"),
    (r"ble microcontroller|ble soc|nrf5|ch58|esp32|wi-?fi module", 1.8, "BLE / Wi-Fi SoC"),
    (r"microcontroller|\bmcu\b|atmega|stm32", 0.9, "microcontroller"),
    (r"\bimu\b|accelerometer|gyro", 1.1, "6-axis IMU"),
    (r"microsd|sd card", 3.0, "microSD card"),
    (r"video transmitter|\bvtx\b", 15.0, "digital video transmitter"),
    (r"gnss|\bgps\b", 6.0, "GNSS receiver module"),
    (r"antenna", 1.5, "antenna set"),
    (r"microphone|speaker|audio|transducer", 0.8, "audio transducer"),
    (r"flex", 1.2, "flex assembly"),
    (r"passive|assortment|grouped", 0.8, "passives group"),
    (r"pcb", 1.8, "PCB bare board + assembly"),
    (r"cover glass|glass", 4.5, "cover glass"),
    (r"carbon.?fib(re|er).*arm|folding arm", 2.0, "carbon-fibre arm"),
    (r"guard|landing", 3.0, "guards / landing feet"),
    (r"filter", 2.0, "washable filter"),
    (r"nozzle|bezel|lens barrel|trim", 1.2, "small moulded trim part"),
    (r"strap", 1.5, "silicone strap"),
    (r"bracket|light seal|duct|mount", 1.0, "internal brackets / seals"),
    (r"cable gland|seal", 1.0, "cable glands + seals"),
    (r"charging contact|contacts", 0.3, "charging contact"),
    (r"adhesive", 0.5, "adhesive set"),
    (r"screw|fastener", 0.03, "screw"),
    (r"manual|guide|documentation|leaflet", 0.3, "printed guide"),
    (r"carton|packag|box|insert", 1.5, "retail carton + insert"),
]


def estimate(text: str, qty: float = 1.0) -> tuple[float, str] | None:
    if (b := battery(text)) is not None:
        return b
    for rx, usd, what in TABLE:
        if re.search(rx, text or "", re.I):
            if what == "screw" and re.search(r"\bset\b|kit", text, re.I):
                return 1.0, "Module price model: fastener set ≈ USD 1 (typical 2026 trade price at ~2k units, not a quote)"
            return usd, f"Module price model: {what} ≈ USD {usd:g} (typical 2026 trade price at ~2k units, not a quote)"
    return None


__all__ = ["estimate", "battery", "TABLE"]
