"""Cable gland.

IP-rated cable gland: threaded body approximated by stacked rings, a hex wrench flat, a hex dome cap nut and a
rubber seal insert, all with a through bore for the cable. Shows `RegularPolygon` hex extrusion, `revolve` for the
dome, ring stacks for thread look, and a single bore subtracted from every part.
tags: cable gland, gland, hex nut, thread, seal, dome, revolve, regularpolygon, bore, ip67, connector, fitting
"""
import math

from build123d import *

P = {"thread_d": 20.0, "thread_len": 10.0, "pitch": 1.5, "hex_af": 24.0, "hex_h": 5.0, "dome_af": 22.0,
     "dome_h": 14.0, "bore": 9.0}


def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def hex_prism(af, h, z):
    # RegularPolygon radius is the circumradius: across-flats / cos(30 deg).
    return Pos(0, 0, z) * extrude(RegularPolygon(af / 2 / math.cos(math.pi / 6), 6), amount=h)


def build():
    R, Lt, p = P["thread_d"] / 2, P["thread_len"], P["pitch"]
    core = Cylinder(R - p * 0.6, Lt, align=(Align.CENTER, Align.CENTER, Align.MIN))
    n = int(Lt / p)
    crests = [Pos(0, 0, p * (i + 0.5)) * Cylinder(R, p * 0.5) for i in range(n)]  # rings read as thread
    thread = core + crests
    hexb = hex_prism(P["hex_af"], P["hex_h"], Lt)
    z1 = Lt + P["hex_h"]
    nut = hex_prism(P["dome_af"], P["dome_h"] * 0.5, z1)
    dome_prof = Plane.XZ * Polyline((0, 0), (P["dome_af"] / 2 - 0.5, 0), (P["dome_af"] / 2 - 0.5, P["dome_h"] * 0.5),
                                    (P["bore"] / 2 + 1.5, P["dome_h"]), (0, P["dome_h"]), close=True)
    nut = nut + Pos(0, 0, z1) * revolve(make_face(dome_prof), Axis.Z)
    seal = Pos(0, 0, z1 + P["dome_h"] - 1) * Cylinder(P["bore"] / 2 + 1.2, 2.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    bore = Cylinder(P["bore"] / 2, 200)
    body = (thread + hexb) - bore
    return [lab(body, "body", 1), lab(nut - bore, "accent", 1), lab(seal - Cylinder(P["bore"] / 2 - 0.8, 200), "rubber", 1)]
