"""Curated part names for the recorded showcase programs (W29) — deterministic overrides of api.cad.parts' heuristics.

Keyed by the program signature (sha1 of the code without its `P = {...}` dict, so parameter edits keep the names).
Each rule: (label regex, part_id, name, role); `{i}` in part_id / name = the rule's index function of the label number.
"""

from __future__ import annotations

import ast
import hashlib
import re
from typing import Callable

Rule = tuple[str, str, str, str, Callable[[int], int] | None]


def signature(code: str) -> str:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ""
    lines = code.splitlines()
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "P" for t in node.targets):
            for ln in range(node.lineno - 1, (node.end_lineno or node.lineno)):
                lines[ln] = ""
    return hashlib.sha1("\n".join(lines).encode()).hexdigest()[:16]


_VACUUM: list[Rule] = [
    (r"accent\.1$", "floor_head", "Floor head housing", "other", None),
    (r"rubber\.1$", "brush_roll", "Brush roll", "other", None),
    (r"clear\.1$", "floor_head_window", "Floor head window", "window", None),
    (r"rubber\.[23]$", "rear_wheels", "Rear wheels", "other", None),
    (r"metal\.1$", "swivel_joint", "Swivel joint", "frame", None),
    (r"accent\.2$", "swivel_neck", "Swivel neck", "frame", None),
    (r"metal\.2$", "wand", "Aluminium wand", "frame", None),
    (r"accent\.3$", "release_collar", "Wand release collar", "other", None),
    (r"button\.1$", "wand_release", "Wand release button", "button", None),
    (r"clear\.2$", "dust_bin", "Clear dust bin", "window", None),
    (r"fabric\.1$", "filter", "Washable filter", "other", None),
    (r"accent\.4$", "bin_base", "Bin base ring", "other", None),
    (r"button\.2$", "bin_release", "Bin release catch", "button", None),
    (r"rubber\.4$", "bin_seal", "Bin seal", "other", None),
    (r"metal\.3$", "cyclone_shroud", "Cyclone shroud", "other", None),
    (r"accent\.(1\d|[2-9]\d)$", "cyclones", "Cyclone cones", "other", None),
    (r"body\.1$", "cyclone_core", "Cyclone core", "other", None),
    (r"coat\.1$", "exhaust_cap", "Exhaust cap", "other", None),
    (r"body\.2$", "motor_pod", "Motor pod", "motor", None),
    (r"coat\.2$", "motor_vent", "Motor vent", "other", None),
    (r"metal\.4$", "motor_cap", "Motor cap", "other", None),
    (r"body\.3$", "pistol_grip", "Pistol grip", "other", None),
    (r"body\.4$", "grip_bridge", "Grip bridge", "frame", None),
    (r"button\.3$", "trigger", "Trigger", "button", None),
    (r"accent\.5$", "battery_pack", "Battery pack", "battery", None),
    (r"coat\.3$", "battery_base", "Battery base plate", "other", None),
    (r"body\.5$", "battery_strut", "Battery strut", "frame", None),
    (r"led\.1$", "charge_light", "Charge indicator", "diffuser", None),
]

_DRONE: list[Rule] = [
    (r"body\.1$", "fuselage", "Fuselage shell", "shell_top", None),
    (r"coat\.1$", "nose_panel", "Nose panel", "other", None),
    (r"glass\.1\d$", "tracking_windows", "Visual-tracking windows", "window", None),
    (r"metal\.[1-4]$", "hinge_{i}", "Folding hinge {i}", "fastener", lambda k: k),
    (r"coat\.1[1-4]$", "arm_{i}", "Carbon arm {i}", "arm", lambda k: k - 10),
    (r"metal\.2[1-4]$", "motor_{i}", "Brushless motor {i}", "motor", lambda k: k - 20),
    (r"coat\.3[1-4]$", "prop_{i}", "Propeller {i}", "prop", lambda k: k - 30),
    (r"coat\.4[2-9]$", "prop_{i}", "Propeller {i}", "prop", lambda k: (k - 40) // 2),
    (r"rubber\.[1-4]$", "landing_legs", "Landing legs", "frame", None),
    (r"rubber\.1[1-4]$", "landing_legs", "Landing legs", "frame", None),
    (r"accent\.1$", "battery_pack", "Battery pack", "battery", None),
    (r"led\.1$", "battery_light", "Battery status light", "diffuser", None),
    (r"metal\.40$", "gimbal_yoke", "Gimbal yoke", "component", None),
    (r"coat\.5\d$", "gimbal_yoke", "Gimbal yoke", "component", None),
    (r"coat\.60$", "gimbal_camera", "Gimbal camera", "component", None),
    (r"metal\.61$", "camera_lens", "Camera lens", "lens", None),
    (r"glass\.1$", "camera_lens", "Camera lens", "lens", None),
]

# signature → rules (both recorded vacuum programs share their structure; the drone has one)
CURATED: dict[str, list[Rule]] = {}


def _register(code_signature: str, rules: list[Rule]) -> None:
    CURATED[code_signature] = rules


def apply(code: str, names: dict[str, dict]) -> dict[str, dict]:
    rules = CURATED.get(signature(code))
    if not rules:
        return names
    from api.cad.parts import LAYER_OF_ROLE

    out = dict(names)
    for label in list(names) or []:
        for rx, pid, name, role, idx in rules:
            if re.match(rx, label):
                try:
                    k = int(label.split(".", 1)[1].split("_")[0])
                except (IndexError, ValueError):
                    k = 0
                i = idx(k) if idx else None
                out[label] = {**names.get(label, {}), "part_id": pid.format(i=i), "name": name.format(i=i), "role": role,
                              "layer_id": LAYER_OF_ROLE.get(role, "exterior"), "source": "curated"}
                break
    return out


def _bootstrap() -> None:
    from pathlib import Path

    base = Path(__file__).resolve().parent / "prebuilt"
    for rel, rules in (("showcase_stick_vacuum/model_v1.py", _VACUUM), ("showcase_stick_vacuum/model_v2.py", _VACUUM),
                       ("showcase_drone_follow/model_v1.py", _DRONE)):
        f = base / rel
        if f.is_file():
            _register(signature(f.read_text(encoding="utf-8")), rules)


_bootstrap()
