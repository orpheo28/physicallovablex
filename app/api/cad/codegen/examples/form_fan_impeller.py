"""Axial fan impeller with twisted blades.

A ducted fan rotor: each blade is a loft() through SlotOverall (thin stadium) sections placed on Plane.YZ offsets along the radius, each section rotated about the radial axis (twist) with Rot(0, 0, angle); the blade is then copied around the hub with Rot about Z. An outer shroud ring ties the tips.
tags: fan, impeller, rotor, blades, twist, loft, sections, polar pattern, hub, shroud, cooling, airflow
"""
import math

from build123d import *

P = {"blades": 7, "hub_r": 18.0, "hub_h": 18.0, "tip_r": 55.0, "root_pitch": 50.0, "tip_pitch": 22.0,
     "chord_root": 20.0, "chord_tip": 30.0, "thickness": 2.0, "shroud_t": 2.5}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build():
    hr, tr, hh = P["hub_r"], P["tip_r"], P["hub_h"]
    stations = 4
    sections = []
    for i in range(stations):
        f = i / (stations - 1)
        r = hr - 2 + (tr - hr + 3) * f  # overlap the hub and the shroud slightly
        pitch = P["root_pitch"] + (P["tip_pitch"] - P["root_pitch"]) * f
        chord = P["chord_root"] + (P["chord_tip"] - P["chord_root"]) * f
        # Plane.YZ.offset(r): section plane perpendicular to the radial X axis; local y is global Z.
        # SlotOverall, not Ellipse: lofting twisted Ellipse sections yields a corrupt (even negative-volume) solid
        sections.append(Plane.YZ.offset(r) * Pos(0, hh / 2) * Rot(0, 0, pitch) * SlotOverall(chord, P["thickness"]))
    blade = loft(sections)

    blades = [Rot(0, 0, i * 360 / P["blades"]) * blade for i in range(P["blades"])]
    hub = Cylinder(hr, hh, align=(Align.CENTER, Align.CENTER, Align.MIN))
    try:
        hub = fillet(hub.edges().group_by(Axis.Z)[-1], radius=4)
    except Exception:
        pass
    rotor = hub + blades
    shroud = Cylinder(tr + P["shroud_t"], hh, align=(Align.CENTER, Align.CENTER, Align.MIN)) - Cylinder(tr, 100)
    return [lab(rotor, "body", 1), lab(shroud, "accent", 1)]
