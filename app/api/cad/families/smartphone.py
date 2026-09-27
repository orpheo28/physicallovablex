"""Smartphone family (W21): slab phone on an ODM reference platform, lying on its back glass.

Frame (rounded slab, X = width, Y = height of the phone, Z = thickness), cover glass on the front (+Z), a camera bump
with lenses and a flash on the back, volume + power buttons on the right edge, a USB-C port and speaker holes on the
bottom edge. Origin: centre of the phone, back of the camera bump on z=0.
"""

from __future__ import annotations

import math  # noqa: F401 — used by the geometry block
from dataclasses import asdict, dataclass

from build123d import *  # noqa: F403 — the geometry block is also stand-alone seed code

from api.cad.families._common import clamp

NAME = "smartphone"
CATEGORY = "smartphone"
DESCRIPTION = "Smartphone: rounded slab frame, cover glass, rear camera bump with lenses + flash, buttons, USB-C."


@dataclass
class Params:
    width: float = 71.5             # X
    length: float = 147.0           # Y
    thickness: float = 8.2          # Z (frame, without the bump)
    corner_radius: float = 10.0
    bump_size: float = 30.0         # square camera island
    bump_height: float = 1.8
    lens_count: float = 2.0         # 1-3

    def clamped(self) -> "Params":
        return Params(
            width=clamp(self.width, 55, 90), length=clamp(self.length, 110, 180), thickness=clamp(self.thickness, 6, 14),
            corner_radius=clamp(self.corner_radius, 3, 16), bump_size=clamp(self.bump_size, 12, 45),
            bump_height=clamp(self.bump_height, 0.5, 5), lens_count=float(int(clamp(round(self.lens_count), 1, 3))),
        )


PRESETS = {"slab": Params(), "mini": Params(width=64, length=131, thickness=8.8, corner_radius=9, bump_size=24, lens_count=1)}


def default_params(variant: str = "slab") -> dict[str, float]:
    return asdict(PRESETS.get(variant, PRESETS["slab"]).clamped())


# === GEOMETRY ===
def lab(shape, role, n):
    shape.label = f"{role}.{n}"
    return shape


def build_parts(P):
    parts = []
    W, L, T, r = P["width"], P["length"], P["thickness"], P["corner_radius"]
    bh = P["bump_height"]
    z0 = bh  # frame sits on top of the bump height
    frame = Pos(0, 0, z0) * extrude(RectangleRounded(W, L, r), amount=T - 0.7)
    try:
        frame = fillet(frame.edges().group_by(Axis.Z)[0], radius=min(1.6, T * 0.2))
    except Exception:
        pass
    parts.append(lab(frame, "metal", 1))
    parts.append(lab(Pos(0, 0, z0 + T - 0.7) * extrude(RectangleRounded(W - 0.6, L - 0.6, r - 0.3), amount=0.7), "glass", 1))
    # camera island on the back (top-left seen from the back)
    s = P["bump_size"]
    bx, by = W / 2 - s / 2 - 5, L / 2 - s / 2 - 5
    parts.append(lab(Pos(bx, by, 0) * extrude(RectangleRounded(s, s, s * 0.25), amount=bh), "glass", 2))
    n = int(P["lens_count"])
    lr = s * (0.2 if n > 1 else 0.28)
    spots = [(bx - s * 0.2, by + s * 0.2), (bx - s * 0.2, by - s * 0.2), (bx + s * 0.2, by + s * 0.2)][:n] if n > 1 else [(bx, by)]
    for i, (x, y) in enumerate(spots, 1):
        parts.append(lab(Pos(x, y, -0.6) * Cylinder(lr, 1.2, align=(Align.CENTER, Align.CENTER, Align.MIN)), "metal", 1 + i))
        parts.append(lab(Pos(x, y, -0.8) * Cylinder(lr * 0.7, 0.4, align=(Align.CENTER, Align.CENTER, Align.MIN)), "glass", 2 + i))
    parts.append(lab(Pos(bx + s * 0.22, by - s * 0.22, -0.3) * Cylinder(s * 0.07, 0.6, align=(Align.CENTER, Align.CENTER, Align.MIN)), "diffuser", 1))
    # buttons on the right edge (+X): volume rocker + power
    parts.append(lab(Pos(W / 2 + 0.4, L * 0.18, z0 + T / 2) * Box(1.4, 24, 2.6), "button", 1))
    parts.append(lab(Pos(W / 2 + 0.4, L * 0.02, z0 + T / 2) * Box(1.4, 12, 2.6), "button", 2))
    # USB-C port + speaker grille on the bottom edge (-Y)
    parts.append(lab(Pos(0, -L / 2 + 0.4, z0 + T / 2) * Box(9, 1.2, 3.2), "port", 1))
    for i in range(5):
        parts.append(lab(Pos(12 + i * 3.2, -L / 2 + 0.3, z0 + T / 2) * Box(1.6, 0.8, 1.6), "coat", 1 + i))
    return parts
# === END GEOMETRY ===


def build(params: Params | dict | None = None):
    p = params if isinstance(params, Params) else Params(**{k: float(v) for k, v in (params or {}).items()
                                                               if k in Params.__dataclass_fields__})
    parts = build_parts(asdict(p.clamped()))
    return Compound(children=parts), parts
