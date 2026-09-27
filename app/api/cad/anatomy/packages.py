"""Package table (W29): BOM line → body size for the illustrative internal layout.

    body_for(item, lcsc_part=None) -> Body | None     # None = not a PCB-mounted / internal body (shells, packaging…)

Size, in order: (1) the LCSC snapshot `package` string of the matched part (QFN-48(7x7), SOT-23-5, LGA14-(2.5x3),
0402…) → L × W × H from the JEDEC-style table below ("package from the LCSC snapshot"); (2) a known part number in
the line (MAX30102 → OESIP-14 5.6 × 3.3 × 1.55 mm, datasheet class); (3) a keyword rule for modules, batteries,
motors, connectors (USB-C receptacle 8.9 × 7.3 × 3.2 mm …) — always a stated estimate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# package family → (L, W, H) mm when the string carries no explicit size
PACKAGES: dict[str, tuple[float, float, float]] = {
    "0201": (0.6, 0.3, 0.3), "0402": (1.0, 0.5, 0.35), "0603": (1.6, 0.8, 0.45), "0805": (2.0, 1.25, 0.6),
    "1206": (3.2, 1.6, 0.6), "1210": (3.2, 2.5, 0.6), "SOT-23": (2.9, 1.3, 1.1), "SOT-23-5": (2.9, 1.6, 1.1),
    "SOT-23-6": (2.9, 1.6, 1.1), "SOT-223": (6.5, 3.5, 1.6), "SOT-89": (4.5, 2.5, 1.5), "SOD-123": (2.7, 1.6, 1.1),
    "SOD-323": (1.7, 1.25, 0.9), "SMA": (4.3, 2.6, 2.3), "SMB": (4.6, 3.6, 2.3), "SOIC-8": (4.9, 3.9, 1.5),
    "SOP-8": (4.9, 3.9, 1.5), "SOIC-14": (8.65, 3.9, 1.5), "SOIC-16": (9.9, 3.9, 1.5), "TSSOP-8": (3.0, 4.4, 1.1),
    "TSSOP-14": (5.0, 4.4, 1.1), "TSSOP-20": (6.5, 4.4, 1.1), "MSOP-8": (3.0, 3.0, 1.1), "QFN-16": (3.0, 3.0, 0.9),
    "QFN-20": (4.0, 4.0, 0.9), "QFN-24": (4.0, 4.0, 0.9), "QFN-28": (5.0, 5.0, 0.9), "QFN-32": (5.0, 5.0, 0.9),
    "QFN-40": (6.0, 6.0, 0.9), "QFN-48": (7.0, 7.0, 0.9), "QFN-64": (9.0, 9.0, 0.9), "DFN-6": (2.0, 2.0, 0.75),
    "DFN-8": (3.0, 3.0, 0.75), "LGA-14": (2.5, 3.0, 0.86), "LGA-16": (3.0, 3.0, 1.0), "LGA-8": (2.0, 2.0, 0.8),
    "OESIP-14": (5.6, 3.3, 1.55), "LQFP-32": (7.0, 7.0, 1.4), "TQFP-32": (7.0, 7.0, 1.2), "LQFP-48": (7.0, 7.0, 1.4),
    "LQFP-64": (10.0, 10.0, 1.4), "LQFP-100": (14.0, 14.0, 1.4), "BGA": (8.0, 8.0, 1.2), "WLCSP": (2.0, 2.0, 0.5),
    "USB-C": (8.9, 7.3, 3.2), "SMD-5032": (5.0, 3.2, 1.0), "SMD-3225": (3.2, 2.5, 0.8), "CR2032": (20.0, 20.0, 3.2),
}
# part number → package (datasheet class), for common chips the snapshot does not match
KNOWN_PN: list[tuple[re.Pattern, str]] = [
    (re.compile(r"max3010[12]|max8614", re.I), "OESIP-14"), (re.compile(r"ch58[23]", re.I), "QFN-48"),
    (re.compile(r"nrf52(832|840)", re.I), "QFN-48"), (re.compile(r"nrf52810|nrf52811", re.I), "QFN-32"),
    (re.compile(r"esp32-c3|esp32c3", re.I), "QFN-32"), (re.compile(r"qmi8658|bmi2\d\d|lsm6", re.I), "LGA-14"),
    (re.compile(r"hdc30\d\d|hdc20\d\d", re.I), "WLCSP"), (re.compile(r"tp4054|tp4056", re.I), "SOT-23-5"),
    (re.compile(r"xc6206|ap2112|me6211", re.I), "SOT-23"), (re.compile(r"atmega328p?-au", re.I), "TQFP-32"),
    (re.compile(r"stm32f4\d\d", re.I), "LQFP-64"), (re.compile(r"ao3400|si2302", re.I), "SOT-23"),
    (re.compile(r"ss14|ss34", re.I), "SMA"), (re.compile(r"drv8833|tb6612", re.I), "TSSOP-20"),
]
_DIMS = re.compile(r"(\d+(?:\.\d+)?)\s*[x×*]\s*(\d+(?:\.\d+)?)(?:\s*[x×*]\s*(\d+(?:\.\d+)?))?")


@dataclass
class Body:
    kind: str  # chip | passive | module | battery | motor | connector | antenna | coil | sensor | lens | cable | switch | board | other
    size: tuple[float, float, float]  # L × W × H mm (H = height above the board)
    package: str | None
    source: str  # the sizing rule, human-readable
    qty: int = 1
    shape: str = "box"  # box | cyl | pouch
    extras: dict = field(default_factory=dict)


def _norm_pkg(pkg: str) -> str:
    p = pkg.upper().replace("_", "-").replace(" ", "")
    p = re.sub(r"^(SOT23)", "SOT-23", p)
    p = re.sub(r"^(SOIC|SOP|TSSOP|MSOP|QFN|DFN|LGA|LQFP|TQFP|OESIP)-?(\d+)", r"\1-\2", p)
    return p


def package_size(pkg: str | None) -> tuple[float, float, float] | None:
    """L × W × H mm of a package string ('QFN-48(7x7)', 'LGA14-(2.5x3)', 'SOT-23-5', '0402', 'SMA_DO-214AC'…)."""
    if not pkg:
        return None
    p = _norm_pkg(pkg)
    base = None
    for k in sorted(PACKAGES, key=len, reverse=True):
        if p.startswith(k.upper()) or k.upper() in p:
            base = PACKAGES[k]
            break
    m = _DIMS.search(pkg)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        h = float(m.group(3)) if m.group(3) else (base[2] if base else 1.0)
        if 0.2 <= a <= 60 and 0.2 <= b <= 60:
            return (a, b, h)
    if base:
        return base
    if re.search(r"SOT", p):
        return PACKAGES["SOT-23"]
    if re.search(r"SOP|SOIC", p):
        return PACKAGES["SOIC-8"]
    if re.search(r"QFN|DFN", p):
        return PACKAGES["QFN-24"]
    return None


def _num(rx: str, text: str) -> float | None:
    m = re.search(rx, text, re.I)
    return float(m.group(1).replace(",", "")) if m else None


LIPO_WH_PER_L = 400.0  # Li-po pouch cell volumetric energy density (estimate, 350-500 Wh/L)


def battery_body(text: str) -> Body:
    mah = _num(r"(\d[\d,]*(?:\.\d+)?)\s*mAh", text)
    v = _num(r"(\d+(?:\.\d+)?)\s*V\b", text)
    s = _num(r"(\d)\s*S\b", text)
    wh = _num(r"(\d+(?:\.\d+)?)\s*Wh", text)
    if v is None:
        v = 3.7 * s if s else 3.7
    if wh is None and mah:
        wh = mah / 1000 * v
    if re.search(r"18650|21700|li-?ion.*pack|\b\d\s*S\b.*li-?ion|pack.*li-?ion", text, re.I) and (s or (v and v > 8)):
        cells = int(s or round(v / 3.6))
        return Body("battery", (65.0, 18.0, 18.0), None, f"{cells} × 18650 cells (Ø18 × 65 mm) for {v:g} V", qty=cells, shape="cyl",
                    extras={"cells": cells, "voltage": v, "wh": wh, "mah": mah})
    if wh is None:
        wh = 3.7 * 1.0  # 1000 mAh default
    vol_cm3 = wh / LIPO_WH_PER_L * 1000
    return Body("battery", (0, 0, 0), None, f"{wh:.2f} Wh ({(mah or wh / v * 1000):.0f} mAh at {v:g} V) ÷ {LIPO_WH_PER_L:.0f} Wh/L Li-po = "
                f"{vol_cm3:.2f} cm³", shape="pouch", extras={"volume_cm3": vol_cm3, "mah": mah, "voltage": v, "wh": wh})


RULES: list[tuple[re.Pattern, str, tuple[float, float, float], str]] = [
    (re.compile(r"^(custom |rigid |flex(ible)? )?pcb\b|^printed circuit", re.I), "board", (0, 0, 1.0), None),
    (re.compile(r"passive|resistor|capacitor|inductor", re.I), "passive", (1.0, 0.5, 0.35), "0402"),
    (re.compile(r"usb-?c", re.I), "connector", (8.9, 7.3, 3.2), "USB-C"),
    (re.compile(r"charging contact|pogo|contact pad", re.I), "connector", (2.5, 2.5, 0.6), None),
    (re.compile(r"antenna", re.I), "antenna", (12.0, 3.0, 0.6), None),
    (re.compile(r"microsd|sd card", re.I), "connector", (15.0, 11.0, 1.4), None),
    (re.compile(r"trigger|switch|button", re.I), "switch", (6.0, 6.0, 3.5), None),
    (re.compile(r"lidar", re.I), "module", (40.0, 40.0, 30.0), None),
    (re.compile(r"camera|image sensor|lens", re.I), "lens", (12.0, 12.0, 8.0), None),
    (re.compile(r"gimbal", re.I), "lens", (26.0, 26.0, 26.0), None),
    (re.compile(r"compute module|linux|soc module|vision", re.I), "module", (40.0, 30.0, 5.0), None),
    (re.compile(r"flight controller", re.I), "board", (36.0, 36.0, 6.0), None),
    (re.compile(r"\besc\b|motor driver|driver module", re.I), "board", (30.0, 30.0, 6.0), None),
    (re.compile(r"mainboard|main pcb|odm .*pcb|pcb assembly", re.I), "board", (0, 0, 1.0), None),
    (re.compile(r"display|touch", re.I), "module", (0, 0, 1.2), None),
    (re.compile(r"bldc vacuum|vacuum motor|high-speed bldc", re.I), "motor", (60.0, 60.0, 70.0), None),
    (re.compile(r"gearmotor|gear motor|dc motor", re.I), "motor", (25.0, 12.0, 12.0), None),
    (re.compile(r"servo", re.I), "motor", (23.0, 12.0, 22.0), None),
    (re.compile(r"brushless|outrunner|bldc", re.I), "motor", (28.0, 28.0, 16.0), None),
    (re.compile(r"solenoid|valve", re.I), "coil", (30.0, 30.0, 40.0), None),
    (re.compile(r"flash", re.I), "module", (20.0, 10.0, 6.0), None),
    (re.compile(r"ejector|exposure engine|film", re.I), "module", (0, 0, 0), None),
    (re.compile(r"speaker|microphone|audio|transducer", re.I), "module", (8.0, 6.0, 2.5), None),
    (re.compile(r"probe|soil", re.I), "sensor", (20.0, 8.0, 3.0), None),
    (re.compile(r"time-of-flight|tof\b", re.I), "chip", (4.4, 2.4, 1.0), "LGA-16"),
    (re.compile(r"flex", re.I), "cable", (20.0, 6.0, 0.3), None),
    (re.compile(r"regulator|converter|charger|controller|mcu|microcontroller|imu|sensor|driver|ic\b", re.I), "chip", (3.0, 3.0, 0.9), None),
]
NOT_INTERNAL = re.compile(r"shell|housing|enclosure|carton|packag|manual|guide|insert|screws?\b|fastener|strap|band\b|"
                          r"window|seal|glass|trim|adhesive|bezel|wand|floor head|dust bin|cyclone|filter|arms?\b|propell?er|"
                          r"guard|feet|chassis|wheel|gripper|cartridge|bracket|panel|solar|pv|module kit|cable gland|lens barrel",
                          re.I)


def body_for(item, lcsc_part=None) -> Body | None:
    text = f"{item.part} {item.description or ''} {item.manufacturer_pn or ''}"
    cat = str(getattr(item.category, "value", item.category))
    if cat == "packaging":
        return None
    if re.search(r"batter|li-?po|li-?ion|accu", item.part, re.I) and not re.search(r"management|protection board|charger|charge controller", item.part, re.I):
        return battery_body(text)
    if cat != "electronic" and NOT_INTERNAL.search(item.part):
        return None
    if cat == "electronic" and re.search(r"^solar|photovoltaic|pv ", item.part, re.I):
        return None
    qty = max(1, int(round(float(item.qty or 1))))
    if lcsc_part is not None and (sz := package_size(lcsc_part.package)) is not None:
        kind = "passive" if re.fullmatch(r"0[2468]0[1-5]|1206|1210", _norm_pkg(lcsc_part.package)[:4]) else "chip"
        return Body(kind, sz, lcsc_part.package, f"package {lcsc_part.package} (LCSC {lcsc_part.pn})", qty=qty)
    for rx, pkg in KNOWN_PN:
        if rx.search(text):
            return Body("sensor" if pkg == "OESIP-14" else "chip", PACKAGES[pkg], pkg, f"package {pkg} (datasheet class of the part number)", qty=qty)
    for rx, kind, size, pkg in RULES:
        if rx.search(text):
            if kind == "passive":
                return Body("passive", PACKAGES["0402"], "0402", "grouped 0402 passives (cluster, estimate)", qty=max(qty, 12))
            return Body(kind, size, pkg, f"{kind} size rule (estimate)" + (f", {pkg}" if pkg else ""), qty=qty,
                        shape="cyl" if kind in ("motor", "coil") else "box")
    if cat == "electronic":
        return Body("chip", (3.0, 3.0, 0.9), None, "generic IC size (estimate)", qty=qty)
    return None


__all__ = ["body_for", "package_size", "battery_body", "Body", "PACKAGES", "LIPO_WH_PER_L"]
