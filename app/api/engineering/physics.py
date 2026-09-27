"""Deterministic physics checks. Owner: W20.

Inputs: the measured CAD (bounding box and solid volume from the STEP), the mass (stage 3 weight), the BOM-derived
electronics architecture and the brief text. Pure formulas first (unit-tested with known answers), then
`physics_checks(pack, geo, arch, text)` → [EngineeringCheck] for the checks the category pack lists.

Every result carries value + unit + label + formula + pass/warn/fail against a threshold. A value computed only
from Measured inputs stays Measured; any Estimate input makes it an Estimate.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from contracts.artifacts import CheckVerdict, ElectronicsArchitecture, EngineeringCheck, LabeledValue

from api.engineering._util import G, est, first_number, label_of, lv, weakest
from api.engineering.electronics import battery_hours

RHO_AIR = 1.2  # kg/m³
H_NATURAL = 10.0  # W/m²K, natural convection + radiation, small enclosure


# --------------------------------------------------------------------------- pure formulas


def tip_angle_deg(base_half_width_m: float, com_height_m: float) -> float:
    """Static tip-over angle of a rigid body: atan(b / h), b = distance from the COM to the tipping edge."""
    return math.degrees(math.atan2(base_half_width_m, com_height_m))


def tip_push_force_n(mass_kg: float, base_half_width_m: float, push_height_m: float) -> float:
    """Horizontal force at height H that tips the body about its base edge: F = m g b / H."""
    return mass_kg * G * base_half_width_m / push_height_m


def litres(volume_cm3: float) -> float:
    return volume_cm3 / 1000.0


def buoyancy_kg(volume_l: float, rho: float = 1025.0) -> float:
    """Mass of displaced sea water when fully submerged (kg)."""
    return volume_l / 1000.0 * rho


def planing_speed_ms(displacement_kg: float, fn_volumetric: float = 2.0, rho: float = 1025.0) -> float:
    """Speed at which the volumetric Froude number Fn∇ = v / √(g ∇^(1/3)) reaches `fn_volumetric` (planing onset ≈ 2)."""
    vol = displacement_kg / rho
    return fn_volumetric * math.sqrt(G * vol ** (1 / 3))


def battery_life_h(capacity_mah: float, avg_ma: float, usable: float = 0.85) -> float:
    return capacity_mah * usable / avg_ma


def vacuum_operating_point(motor_w: float, efficiency: float, inlet_d_mm: float, loss_k: float = 4.0) -> dict[str, float]:
    """Air watts AW = η P; on a system curve p = k ½ρv² with Q = A v: AW = k ½ρ A v³ → v, Q, p."""
    aw = motor_w * efficiency
    area = math.pi * (inlet_d_mm / 2000.0) ** 2
    v = (2 * aw / (loss_k * RHO_AIR * area)) ** (1 / 3)
    q = area * v
    return {"air_watts": aw, "velocity_ms": v, "flow_ls": q * 1000, "pressure_pa": aw / q, "area_m2": area}


def hazen_williams_loss_bar(flow_lpm: float, pipe_id_mm: float, length_m: float, c: float = 140.0) -> float:
    """Friction loss (bar) of water in a pipe: h_f = 10.67 L Q^1.852 / (C^1.852 d^4.87), Q in m³/s, d in m."""
    q = flow_lpm / 60000.0
    d = pipe_id_mm / 1000.0
    hf = 10.67 * length_m * q ** 1.852 / (c ** 1.852 * d ** 4.87)
    return hf * 1000 * G / 1e5


def temperature_rise_k(power_w: float, surface_m2: float, h: float = H_NATURAL) -> float:
    return power_w / (h * surface_m2)


# --------------------------------------------------------------------------- inputs


@dataclass
class Geometry:
    length: LabeledValue  # mm
    width: LabeledValue
    height: LabeledValue
    mass: LabeledValue  # g
    volume: LabeledValue | None = None  # cm³ of solid material (measured on the STEP)
    shell: bool | None = None  # True: hollow moulded enclosure (CAD has a wall); False: solid body (e.g. a board hull)

    @property
    def dims_m(self) -> tuple[float, float, float]:
        return self.length.value / 1000, self.width.value / 1000, self.height.value / 1000

    @property
    def bbox_cm3(self) -> float:
        return self.length.value * self.width.value * self.height.value / 1000

    @property
    def dims_label(self) -> str:
        return weakest(self.length.label, self.width.label, self.height.label)


def _verdict(value: float, good: float, warn: float, higher_is_better: bool = True) -> CheckVerdict:
    if higher_is_better:
        return CheckVerdict.pass_ if value >= good else CheckVerdict.warn if value >= warn else CheckVerdict.fail
    return CheckVerdict.pass_ if value <= good else CheckVerdict.warn if value <= warn else CheckVerdict.fail


def _dims_inputs(geo: Geometry) -> list[LabeledValue]:
    return [geo.length, geo.width, geo.height]


# --------------------------------------------------------------------------- checks


def check_tip_over(geo: Geometry, p: dict) -> EngineeringCheck:
    length, width, height = geo.dims_m
    b = min(length, width) / 2
    ratio = float(p.get("com_ratio", 0.5))
    h = height * ratio
    ang = tip_angle_deg(b, h)
    good, warn = float(p.get("tip_min_deg", 15)), float(p.get("tip_warn_deg", 10))
    return EngineeringCheck(
        id="tip_over", name="Static tip-over angle (narrowest side)", domain="stability",
        value=est(ang, "deg", f"atan(b / h): b = min(L, W)/2 = {b * 1000:.0f} mm (Measured), h = {ratio:g} × H = {h * 1000:.0f} mm (centre-of-mass height ratio is an Estimate)", nd=1),
        threshold=f"≥ {good:g}° pass, ≥ {warn:g}° warn (design target, Estimate)", verdict=_verdict(ang, good, warn),
        formula="θ = atan(b / h_COM), rigid body on its base, least favourable direction", inputs=_dims_inputs(geo),
    )


def check_tip_push(geo: Geometry, p: dict) -> EngineeringCheck:
    length, width, height = geo.dims_m
    b = min(length, width) / 2
    m = geo.mass.value / 1000
    f = tip_push_force_n(m, b, height)
    good = float(p.get("push_min_n", 50))
    return EngineeringCheck(
        id="tip_push", name="Max horizontal load at the top edge before tipping (static)", domain="stability",
        value=lv(f, "N", weakest(geo.mass.label, geo.dims_label, "estimate"), f"m g b / H = {m:.2f} kg × 9.81 × {b * 1000:.0f} mm / {height * 1000:.0f} mm"),
        threshold=f"≥ {good:g} N pass, ≥ {good / 2:g} N warn (child pull, design target — confirm against the standard)",
        verdict=_verdict(f, good, good / 2), formula="F = m g b / H (tipping about the base edge, no wall anchor)",
        inputs=[geo.mass, *_dims_inputs(geo)], notes=["Supply a wall anti-tip strap whatever the result"],
    )


def check_mass(geo: Geometry, p: dict) -> EngineeringCheck:
    limit = float(p.get("mass_max_g", 2000))
    return EngineeringCheck(
        id="mass", name="Product mass", domain="mass", value=geo.mass,
        threshold=f"≤ {limit:g} g pass, ≤ {limit * 1.25:g} g warn (category comfort target, Estimate)",
        verdict=_verdict(geo.mass.value, limit, limit * 1.25, higher_is_better=False),
        formula="Stage 3 weight (measured enclosure volume × density + parts)", inputs=[geo.mass] + ([geo.volume] if geo.volume else []),
    )


def check_battery(arch: ElectronicsArchitecture | None, p: dict) -> EngineeringCheck | None:
    if arch is None or arch.battery_life is None:
        return None
    hours = battery_hours(arch) or 0.0
    target = float(p.get("battery_target_h", 24))
    tgt_txt = f"{target / 24:g} days" if target >= 72 else f"{target:g} h"
    return EngineeringCheck(
        id="battery_life", name="Battery life / runtime from the power budget", domain="power", value=arch.battery_life,
        threshold=f"≥ {tgt_txt} pass, ≥ 50% of it warn (category target, Estimate)", verdict=_verdict(hours, target, target / 2),
        formula="t = capacity × 85% usable / Σ(active × duty + sleep × (1 − duty))",
        inputs=[x for x in (arch.battery_capacity, arch.average_current) if x is not None],
    )


def sealing_checklist(bom_text: str, ip: int) -> list[str]:
    low = bom_text.lower()
    out = []
    if "usb" in low:
        out.append("USB-C port: use an IPX7/IPX8-rated sealed receptacle — or replace it with pogo pads / wireless charging")
    if re.search(r"button|switch|tactile", low):
        out.append("Buttons: over-moulded membrane or sealed tact switch (IP67 part), no open plunger")
    if re.search(r"buzzer|speaker|microphone|piezo|pressure", low):
        out.append("Acoustic / pressure port: ePTFE membrane vent (e.g. IP68-rated adhesive vent)")
    out.append("Housing seam: compressed gasket (25-30% squeeze) or ultrasonic weld; fasteners outside the sealed volume")
    if re.search(r"led|display|window|ppg|optical", low):
        out.append("Windows (LED/sensor/display): bonded with a continuous adhesive gasket, no press fit")
    if ip >= 67:
        out.append("Pressure-equalisation vent to avoid seal pumping with temperature cycles")
        out.append("Salt water: gold-plated or stainless contacts, no dissimilar metals in the wet area")
    return out


def check_ip(p: dict, bom_text: str) -> EngineeringCheck | None:
    ip = p.get("ip_target")
    if not ip:
        return None
    return EngineeringCheck(
        id="ip_rating", name="Ingress protection target", domain="ingress",
        value=est(float(ip), "IP code (IEC 60529)", f"Category target: {p.get('ip_detail', f'IP{ip}')}", nd=0),
        threshold=f"IP{ip} to be proven by test (IEC 60529) — design only at this stage", verdict=CheckVerdict.warn,
        formula="Target from the use environment; every opening in the BOM gets a sealing measure",
        notes=sealing_checklist(bom_text, int(ip)),
    )


def board_envelope(geo: Geometry, p: dict) -> LabeledValue:
    """Displaced volume of the board. A solid CAD body is Measured; a shell (hollow enclosure) falls back to bbox × shape coefficient."""
    solid = geo.shell is False or (geo.shell is None and geo.bbox_cm3 > 0 and geo.volume is not None and geo.volume.value / geo.bbox_cm3 >= 0.12)
    if geo.volume is not None and solid:
        return lv(litres(geo.volume.value), "L", label_of(geo.volume), f"Solid volume of the CAD body ({geo.volume.source_or_assumption})")
    k = float(p.get("shape_coeff", 0.6))
    return lv(litres(geo.bbox_cm3) * k, "L", "estimate",
              f"CAD is a shell: bbox {geo.length.value:g}×{geo.width.value:g}×{geo.height.value:g} mm (Measured) × {k:g} surfboard shape coefficient (Estimate)")


def rider_kg(text: str, p: dict) -> LabeledValue:
    kg = first_number(r"(\d{2,3})\s*kg", text or "")
    if kg and 30 <= kg <= 150:
        return est(kg, "kg", "Rider weight stated in the prompt")
    return est(float(p.get("rider_kg_default", 75)), "kg", "Default rider weight (no weight in the prompt)")


def surf_checks(geo: Geometry, p: dict, text: str) -> list[EngineeringCheck]:
    vol = board_envelope(geo, p)
    rider = rider_kg(text, p)
    board_kg = geo.mass.value / 1000
    rho = float(p.get("rho_sea", 1025))
    l_per_kg = vol.value / rider.value
    lmin, lwarn = float(p.get("litres_per_kg_min", 0.35)), float(p.get("litres_per_kg_warn", 0.3))
    lift = buoyancy_kg(vol.value, rho)
    margin = lift - board_kg - rider.value
    disp = rider.value + board_kg
    fn = float(p.get("fn_volumetric", 2.0))
    v = planing_speed_ms(disp, fn, rho)
    return [
        EngineeringCheck(
            id="board_volume", name="Board volume", domain="hydrodynamics", value=vol,
            threshold=f"Guild factor ≥ {lmin:g} L/kg of rider pass, ≥ {lwarn:g} warn (surf rule of thumb, Estimate)",
            verdict=_verdict(l_per_kg, lmin, lwarn), formula=f"V / rider = {vol.value:.1f} L / {rider.value:g} kg = {l_per_kg:.2f} L/kg",
            inputs=[vol, rider],
        ),
        EngineeringCheck(
            id="buoyancy", name="Static buoyancy margin with the rider on board", domain="hydrodynamics",
            value=lv(margin, "kg", weakest(vol.label, geo.mass.label, "estimate"), f"ρ V − m_board − m_rider = {lift:.1f} − {board_kg:.2f} − {rider.value:g} kg"),
            threshold="≥ 0 kg: floats the rider at rest (longboard/SUP); < 0: sinks at rest, paddle power needed (normal for shortboards)",
            verdict=CheckVerdict.pass_ if margin >= 0 else CheckVerdict.warn,
            formula=f"B = ρ_sea V, ρ_sea = {rho:g} kg/m³", inputs=[vol, geo.mass, rider],
        ),
        EngineeringCheck(
            id="planing_speed", name="Rough planing-onset speed", domain="hydrodynamics",
            value=est(v * 3.6, "km/h", f"Fn∇ = {fn:g} at displacement {disp:.1f} kg (rider + board)", nd=1),
            threshold="Information (lower = earlier planing); validate with a GPS ride log", verdict=CheckVerdict.info,
            formula="v = Fn∇ √(g ∇^(1/3)), ∇ = (m_rider + m_board) / ρ_sea (volumetric Froude number, Savitsky-style rough estimate)",
            inputs=[rider, geo.mass],
        ),
    ]


def vacuum_checks(bom_text: str, p: dict) -> list[EngineeringCheck]:
    motor_w = next((w for ln in bom_text.splitlines() if re.search(r"motor", ln, re.I) and (w := first_number(r"(\d{2,4})\s*w\b", ln))), None)
    w_label = "Motor power from the BOM line" if motor_w else "Category default motor class (no power in the BOM)"
    motor_w = motor_w or float(p.get("motor_w", 180))
    eff, d, k = float(p.get("motor_eff", 0.3)), float(p.get("inlet_d_mm", 36)), float(p.get("loss_k", 4.0))
    op = vacuum_operating_point(motor_w, eff, d, k)
    good, warn = float(p.get("aw_target", 100)), float(p.get("aw_warn", 60))
    motor = est(motor_w, "W", w_label)
    return [
        EngineeringCheck(
            id="air_watts", name="Suction power (air watts)", domain="airflow",
            value=est(op["air_watts"], "AW", f"{motor_w:g} W electrical × {eff:.0%} fan+motor efficiency", nd=0),
            threshold=f"≥ {good:g} AW pass (premium stick class at boost), ≥ {warn:g} warn", verdict=_verdict(op["air_watts"], good, warn),
            formula="AW = η × P_in", inputs=[motor],
        ),
        EngineeringCheck(
            id="airflow", name="Airflow at the operating point", domain="airflow",
            value=est(op["flow_ls"], "L/s", f"inlet Ø{d:g} mm, system loss coefficient k = {k:g}", nd=1),
            threshold="Information: ≥ 15 L/s picks up coarse debris on hard floors (rule of thumb)", verdict=CheckVerdict.pass_ if op["flow_ls"] >= 15 else CheckVerdict.warn,
            formula="AW = k ½ρ A v³ → v; Q = A v", inputs=[motor, est(d, "mm", "Inlet diameter, category default")],
            notes=[f"Inlet air speed ≈ {op['velocity_ms']:.0f} m/s; operating-point pressure ≈ {op['pressure_pa'] / 1000:.1f} kPa (sealed suction is higher)"],
        ),
    ]


def irrigation_checks(text: str, p: dict) -> list[EngineeringCheck]:
    low = (text or "").lower()
    zones = int(first_number(r"(\d{1,2})\s*(?:zones?|valves?|stations?)", low) or p.get("zones_default", 4))
    sprinkler = bool(re.search(r"sprinkler|lawn|pop-?up|rotor", low))
    zone_lpm = float(p.get("zone_lpm_sprinkler" if sprinkler else "zone_lpm_drip", 10 if sprinkler else 1.5))
    supply_lpm, supply_bar = float(p.get("supply_lpm", 20)), float(p.get("supply_bar", 3.0))
    d, run, c = float(p.get("pipe_id_mm", 13.6)), float(p.get("run_m", 30)), float(p.get("hazen_c", 140))
    loss = hazen_williams_loss_bar(zone_lpm, d, run, c) + float(p.get("valve_loss_bar", 0.3))
    at_emitter = supply_bar - loss
    min_bar = float(p.get("min_bar_sprinkler" if sprinkler else "min_bar_drip", 1.0))
    kind = "sprinkler" if sprinkler else "drip"
    zlv = est(zone_lpm, "L/min", f"Typical {kind} zone ({'pop-up sprinklers' if sprinkler else '≈ 45 emitters × 2 L/h'})", nd=1)
    supply = est(supply_lpm, "L/min", f"Garden tap supply assumption at {supply_bar:g} bar")
    return [
        EngineeringCheck(
            id="flow_per_zone", name=f"Flow per zone ({zones} zones, one open at a time)", domain="fluid", value=zlv,
            threshold=f"≤ supply {supply_lpm:g} L/min pass, ≤ 1.2 × supply warn", verdict=_verdict(zone_lpm, supply_lpm, supply_lpm * 1.2, higher_is_better=False),
            formula="Zone demand = emitters × emitter flow; sequential zones never add up", inputs=[zlv, supply],
            notes=[f"Daily water per zone at 20 min: {zone_lpm * 20:.0f} L"],
        ),
        EngineeringCheck(
            id="pressure_at_emitter", name="Pressure at the last emitter", domain="fluid",
            value=est(at_emitter, "bar", f"{supply_bar:g} bar − Hazen-Williams loss over {run:g} m of Ø{d:g} mm PE (C = {c:g}) − valve {p.get('valve_loss_bar', 0.3)} bar", nd=2),
            threshold=f"≥ {min_bar:g} bar pass ({kind} minimum), ≥ {min_bar * 0.7:.1f} warn", verdict=_verdict(at_emitter, min_bar, min_bar * 0.7),
            formula="p = p_supply − 10.67 L Q^1.852 / (C^1.852 d^4.87) × ρg − Δp_valve", inputs=[zlv, supply],
        ),
    ]


def hover_power_w(auw_kg: float, prop_d_m: float, rotors: int = 4, fom: float = 0.6, rho: float = RHO_AIR) -> float:
    """Shaft power to hover (momentum theory): P = n · T^1.5 / √(2ρA) / FoM, T = m g / n per rotor, A = π d²/4."""
    t = auw_kg * G / rotors
    area = math.pi * prop_d_m ** 2 / 4
    return rotors * t ** 1.5 / math.sqrt(2 * rho * area) / fom


EU_CLASSES = [(250, "C0"), (900, "C1"), (4000, "C2"), (25000, "C3")]  # MTOM strictly below (g), Regulation (EU) 2019/945
EU_CLASS_SOURCE = ("Regulation (EU) 2019/945, Annex Parts 1-4 (class C0: MTOM < 250 g; C1: < 900 g; C2: < 4 kg), "
                   "eur-lex.europa.eu CELEX:32019R0945, checked 2026-09-27")


def drone_class(mtom_g: float) -> str:
    return next((c for lim, c in EU_CLASSES if mtom_g < lim), "specific category")


def _drone_battery(bom_text: str, p: dict) -> tuple[float, int, str]:
    """(mAh, cells, note) from the BOM ('2S 2450 mAh', '7.4 V 3000 mAh'), else the category default."""
    for ln in bom_text.splitlines():
        if re.search(r"batter|li-?po|li-?ion|pack|cell", ln, re.I) and not re.search(r"charg|holder|bms|protect", ln, re.I):
            mah = first_number(r"(\d{3,5})\s*mah", ln)
            v = first_number(r"(\d{1,2}(?:\.\d)?)\s*v\b", ln)
            cells = int(first_number(r"(\d)\s*s\b", ln) or (round(v / 3.7) if v else p.get("battery_cells_default", 2)))
            if mah:
                return mah, max(1, cells), "from the BOM battery line"
            return float(p.get("battery_mah_default", 2450)), max(1, cells), "cell count from the BOM, category default capacity"
    return float(p.get("battery_mah_default", 2450)), int(p.get("battery_cells_default", 2)), "category default pack (no capacity in the BOM)"


def drone_checks(geo: Geometry, p: dict, text: str, bom_text: str, fam: dict | None = None) -> list[EngineeringCheck]:
    fam = fam or {}
    rotors = int(p.get("rotors", 4))
    prop_mm = float(fam.get("prop_diameter") or p.get("prop_d_mm", 152))
    mah, cells, bnote = _drone_battery(bom_text, p)
    wh = mah / 1000 * cells * 3.7
    batt_g = wh / float(p.get("battery_wh_per_kg", 180)) * 1000
    parts_g = rotors * (float(p.get("motor_g", 16)) + float(p.get("prop_g", 4)) + float(p.get("arm_g", 7))) \
        + float(p.get("gimbal_camera_g", 38)) + float(p.get("electronics_g", 24))
    stated = first_number(r"\b(\d{2,4})\s*g\b", text or "")
    if stated and 80 <= stated <= 5000:
        auw = est(stated, "g", "All-up weight target stated in the prompt")
    else:
        auw = lv(geo.mass.value + batt_g + parts_g, "g", "estimate",
                 f"Body shells {geo.mass.value:.0f} g ({label_of(geo.mass)}) + battery {batt_g:.0f} g ({wh:.1f} Wh at {p.get('battery_wh_per_kg', 180)} Wh/kg) "
                 f"+ {rotors} × (motor + prop + arm) + gimbal camera + electronics = {parts_g:.0f} g (category part weights, Estimate)", nd=0)
    thrust_each = first_number(r"(\d{2,5})\s*g\s*(?:of\s*)?thrust", bom_text) or float(p.get("motor_thrust_g", 300))
    twr = rotors * thrust_each / auw.value
    p_shaft = hover_power_w(auw.value / 1000, prop_mm / 1000, rotors, float(p.get("figure_of_merit", 0.6)))
    p_elec = p_shaft / float(p.get("drive_eff", 0.75))
    minutes = wh * float(p.get("usable_battery", 0.8)) / p_elec * 60
    tmin, twarn = float(p.get("flight_target_min", 25)), float(p.get("flight_warn_min", 15))
    cls = drone_class(auw.value)
    batt = est(wh, "Wh", f"{mah:.0f} mAh × {cells}S × 3.7 V ({bnote})", nd=1)
    return [
        EngineeringCheck(
            id="thrust_to_weight", name="Thrust-to-weight ratio", domain="flight",
            value=est(twr, "ratio", f"{rotors} × {thrust_each:.0f} g max static thrust per motor/prop (category default unless in the BOM) / {auw.value:.0f} g all-up weight", nd=2),
            threshold=f"≥ {p.get('twr_min', 2.0):g} pass (control margin in gusts), ≥ {p.get('twr_warn', 1.6):g} warn",
            verdict=_verdict(twr, float(p.get("twr_min", 2.0)), float(p.get("twr_warn", 1.6))),
            formula="TWR = n × T_max / (m g)", inputs=[auw], notes=["Confirm on a thrust stand with the final motor/prop pair"]),
        EngineeringCheck(
            id="hover_time", name="Hover flight time from battery energy and hover power", domain="power",
            value=est(minutes, "min", f"{wh:.1f} Wh × {p.get('usable_battery', 0.8):.0%} usable / {p_elec:.0f} W hover (electrical)", nd=1),
            threshold=f"≥ {tmin:g} min pass, ≥ {twarn:g} min warn (category target, Estimate)", verdict=_verdict(minutes, tmin, twarn),
            formula=f"P_hover = n T^1.5 / √(2ρA) / FoM / η_drive; T = m g / n, A = π d²/4 (d = {prop_mm:.0f} mm), FoM = {p.get('figure_of_merit', 0.6)}, η = {p.get('drive_eff', 0.75)}; t = E × usable / P",
            inputs=[auw, batt], notes=[f"Hover shaft power {p_shaft:.0f} W (momentum theory); forward flight and wind add 10-30 %"]),
        EngineeringCheck(
            id="drone_class", name="Regulatory class by take-off mass", domain="regulatory",
            value=lv(auw.value, "g", auw.label, f"All-up weight → EU class {cls}", nd=0),
            threshold=f"EU: C0 < 250 g, C1 < 900 g, C2 < 4 kg (Sourced: {EU_CLASS_SOURCE}). US: FAA registration and Remote ID above 250 g (0.55 lb), Part 107 for commercial use (to be confirmed per use)",
            verdict=CheckVerdict.pass_ if auw.value < 250 else CheckVerdict.info,
            formula="Class = lowest EU class whose MTOM limit the all-up weight is below",
            inputs=[auw], notes=[f"EU class {cls}" + (" — lightest class: fewest pilot requirements" if cls == "C0" else " — pilot registration + online training (A1/A3), see Regulation (EU) 2019/947"),
                                 "Class C0/C1 also need speed, geo-awareness and remote-ID features — keep the weight margin: every gram of battery counts"]),
    ]


def hair_dryer_checks(bom_text: str, text: str, p: dict) -> list[EngineeringCheck]:
    watts = next((w for ln in (bom_text + "\n" + text).splitlines() if re.search(r"heat|element|dryer|power", ln, re.I)
                  and (w := first_number(r"(\d{3,4})\s*w\b", ln))), None)
    w_note = "Heater power from the BOM / prompt" if watts else "Category default heater class (compact dryer)"
    heater = float(watts or p.get("heater_w", 1600))
    fan_w = float(p.get("fan_w", 60))
    q_ls = float(p.get("airflow_l_s", 13.0))
    if re.search(r"quiet|silent|low noise", text or "", re.I):
        q_ls *= 0.9
    rho, cp = RHO_AIR, 1005.0
    dt = heater / (rho * q_ls / 1000 * cp)
    t_out = float(p.get("inlet_c", 20)) + dt
    good, warn = float(p.get("outlet_max_c", 90)), float(p.get("outlet_warn_c", 110))
    power = est(heater + fan_w, "W", f"{heater:.0f} W heater ({w_note}) + {fan_w:.0f} W fan")
    flow = est(q_ls, "L/s", "Airflow of a compact BLDC fan at max speed (category default" + (", reduced 10 % for the quiet brief)" if "quiet" in (text or "").lower() else ")"), nd=1)
    return [
        EngineeringCheck(id="dryer_power", name="Rated power (mains)", domain="power", value=power,
                         threshold="≤ 2000 W pass (standard 10 A / 16 A socket), ≤ 2400 W warn", verdict=_verdict(power.value, 2000, 2400, higher_is_better=False),
                         formula="P = P_heater + P_fan", inputs=[power]),
        EngineeringCheck(id="dryer_airflow", name="Airflow at the nozzle", domain="airflow", value=flow,
                         threshold="Information: 10-16 L/s for compact dryers (rule of thumb); drying time falls with flow",
                         verdict=CheckVerdict.info, formula="Q from the fan curve at max speed (Estimate until measured)", inputs=[flow]),
        EngineeringCheck(id="outlet_temperature", name="Outlet air temperature at max heat", domain="thermal",
                         value=est(t_out, "°C", f"{p.get('inlet_c', 20)} °C inlet + {heater:.0f} W / (ρ {rho} kg/m³ × {q_ls:.1f} L/s × cp {cp:.0f} J/kgK)", nd=0),
                         threshold=f"≤ {good:g} °C pass (scalp comfort target), ≤ {warn:g} °C warn — limits per IEC 60335-2-23 to confirm",
                         verdict=_verdict(t_out, good, warn, higher_is_better=False),
                         formula="ΔT = P_heater / (ρ Q c_p), all heater power into the air stream", inputs=[power, flow],
                         notes=["Closed-loop NTC control at the outlet keeps the temperature below the target whatever the airflow"]),
    ]


def check_thermal(geo: Geometry, arch: ElectronicsArchitecture | None) -> EngineeringCheck | None:
    if arch is None:
        return None
    vbat = arch.battery_voltage.value if arch.battery_voltage else 3.7
    peak_ma = sum(line.active_current.value * (1 if line.duty_cycle.value >= 50 else line.duty_cycle.value / 100) for line in arch.power_budget)
    power_w = peak_ma / 1000 * vbat
    length, width, height = geo.dims_m
    area = 2 * (length * width + length * height + width * height)
    if area <= 0:
        return None
    dt = temperature_rise_k(power_w, area)
    return EngineeringCheck(
        id="thermal", name="Surface temperature rise at sustained load", domain="thermal",
        value=lv(dt, "K", weakest(geo.dims_label, "estimate"), f"{power_w:.2f} W dissipated / ({H_NATURAL:g} W/m²K × {area * 1e4:.0f} cm² bbox surface)", nd=1),
        threshold="≤ 15 K pass, ≤ 25 K warn (touch comfort target; limits per IEC 62368-1 / 60335-1 to confirm)",
        verdict=_verdict(dt, 15, 25, higher_is_better=False),
        formula="ΔT = P / (h A), all electrical power ends as heat, natural convection",
        inputs=[*_dims_inputs(geo), arch.average_current],
    )


def physics_checks(pack: dict, geo: Geometry, arch: ElectronicsArchitecture | None, text: str, bom_text: str,
                   fam: dict | None = None) -> list[EngineeringCheck]:
    """`fam`: parameters of the product-family CAD (W21), e.g. the drone's prop diameter."""
    p = pack.get("params", {})
    wanted = pack.get("checks", [])
    out: list[EngineeringCheck | None] = []
    for c in wanted:
        if c == "tip_over":
            out.append(check_tip_over(geo, p))
        elif c == "tip_push":
            out.append(check_tip_push(geo, p))
        elif c == "mass":
            out.append(check_mass(geo, p))
        elif c == "battery_life":
            out.append(check_battery(arch, p))
        elif c == "ip_rating":
            out.append(check_ip(p, bom_text))
        elif c == "thermal":
            out.append(check_thermal(geo, arch))
        elif c == "airflow":
            out += vacuum_checks(bom_text, p)
        elif c in ("board_volume",):
            out += surf_checks(geo, p, text)
        elif c == "irrigation_flow":
            out += irrigation_checks(text, p)
        elif c == "drone":
            out += drone_checks(geo, p, text, bom_text, fam)
        elif c == "hair_dryer":
            out += hair_dryer_checks(bom_text, text, p)
    return [c for c in out if c is not None]
