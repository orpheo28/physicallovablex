"""Part naming + metadata (W29): which build123d label is which product part, deterministically.

    names_from_source(source, sites) -> {label: info}   # AI / family program + label call sites → semantic parts
    trace_labels(filename) (context manager)            # in-process builds: records label → call-site lines
    default_name(label) -> info                         # no program: from the material role alone
    part_meta(info, …) -> PartMeta dict                 # node extras of a finished GLB (api.cad.glb)
    PART_MATERIALS                                      # material keys accepted by POST /parts/{id}/edit

A part label is `<material role>.<n>` (body, accent, rubber, glass…). The semantic part (strap, top shell, dust bin,
propeller) comes from the program that drew it: the variable passed to the labeller (`lab(strap - opening, …)` →
strap), else the nearest comment above the call (`# clear bin + cyclone shroud` → bin), else the material role. Parts
drawn by one call site in a loop are one part (10 cyclone cones = "Cyclones"), except props / motors / arms, which
stay separate (a viewer spins each prop). The P-dict keys each part depends on (data flow of the program) are its
editable parameters.
"""

from __future__ import annotations

import ast
import io
import re
import sys
import threading
import tokenize
from contextlib import contextmanager
from typing import Any

# --------------------------------------------------------------------------- materials for part edits

# key → viewer material + physical facts (density g/cm³, cost key of api.costs.engine.PRICE_KG)
PART_MATERIALS: dict[str, dict[str, Any]] = {
    "pc_abs": {"name": "PC/ABS (UL94 V-0)", "kind": "body", "metallic": 0.0, "roughness": 0.5, "density": 1.15, "price_key": "pc/abs"},
    "aluminium": {"name": "Aluminium 6063-T5 (anodised)", "kind": "metal", "metallic": 1.0, "roughness": 0.35, "density": 2.70,
                  "price_key": "aluminium", "colour": "#C8CACD"},
    "stainless_steel": {"name": "Stainless steel 316L (brushed)", "kind": "steel", "metallic": 1.0, "roughness": 0.25,
                        "density": 8.0, "price_key": "stainless", "colour": "#C9CBCE"},
    "tpu": {"name": "TPU (soft-touch, Shore 85A)", "kind": "body", "metallic": 0.0, "roughness": 0.76, "density": 1.20, "price_key": "tpu"},
    "lsr_silicone": {"name": "Liquid silicone rubber (LSR)", "kind": "strap", "metallic": 0.0, "roughness": 0.62, "density": 1.15,
                     "price_key": "silicone"},
    "fabric": {"name": "Woven nylon webbing", "kind": "fabric", "metallic": 0.0, "roughness": 0.92, "density": 1.14, "price_key": "nylon"},
    "glass": {"name": "Chemically strengthened glass", "kind": "glass", "metallic": 0.0, "roughness": 0.04, "density": 2.5,
              "price_key": None, "colour": "#0B0D10"},
    "clear_pc": {"name": "Clear polycarbonate", "kind": "clear", "metallic": 0.0, "roughness": 0.06, "density": 1.2,
                 "price_key": "pc", "colour": "#E6ECF2"},
}
SHELL_MATERIALS = ["pc_abs", "aluminium", "stainless_steel", "tpu"]
STRAP_MATERIALS = ["lsr_silicone", "fabric", "tpu"]
WINDOW_MATERIALS = ["glass", "clear_pc"]

ROLES = ("shell_top", "shell_bottom", "strap", "button", "window", "lens", "diffuser", "frame", "arm", "prop", "motor", "pcb",
         "component", "battery", "antenna", "connector", "cable", "fastener", "other")

# material role (label prefix) → (semantic role, noun) when nothing better is known
MATERIAL_ROLE_DEFAULT: dict[str, tuple[str, str]] = {
    "body": ("shell_top", "Body"), "accent": ("shell_bottom", "Lower body"), "metal": ("frame", "Metal part"),
    "steel": ("frame", "Steel part"), "coat": ("other", "Dark part"), "rubber": ("other", "Rubber part"),
    "diffuser": ("diffuser", "Light diffuser"), "led": ("diffuser", "Status light"), "button": ("button", "Button"),
    "port": ("connector", "USB-C port"), "glass": ("window", "Glass window"), "clear": ("window", "Clear window"),
    "wood": ("frame", "Wood part"), "fabric": ("strap", "Soft pad"), "cell": ("other", "PV cells"), "fin": ("other", "Fin"),
    "roof": ("other", "Roof (context)"), "wall": ("other", "Wall (context)"), "strap": ("strap", "Strap"),
    "top": ("shell_top", "Top shell"), "bottom": ("shell_bottom", "Bottom shell"),
}

# keyword → (semantic role, canonical noun). Order matters: first hit in the variable name, then in the comment.
KEYWORDS: list[tuple[str, str, str]] = [
    (r"strap|band|loop|leash|wristband", "strap", "Strap"),
    (r"propell?er|props?|blades?|rotors?", "prop", "Propeller"),
    (r"motors?|stator|bldc", "motor", "Motor"),
    (r"arms?|booms?", "arm", "Arm"),
    (r"batter(y|ies)|batt|accu", "battery", "Battery pack"),
    (r"antenna", "antenna", "Antenna"),
    (r"usb|ports?|connector|jack|socket|plug", "connector", "Connector"),
    (r"cables?|wires?|cord|hose", "cable", "Cable"),
    (r"screws?|bolts?|nuts?|fasteners?|hinges?|pins?|rivets?", "fastener", "Fastener"),
    (r"triggers?|buttons?|keys?|switch(es)?|shutter|dial|knob|crown", "button", "Button"),
    (r"lens(es)?|optic", "lens", "Lens"),
    (r"diffuser|leds?|status|indicator|light|glow|emitters?", "diffuser", "Light"),
    (r"pcb|board_?pcb|mainboard", "pcb", "PCB"),
    (r"sensor|window|screen|display|viewfinder|visor|glass", "window", "Window"),
    (r"bin|canister|tank|reservoir|cup|bowl", "window", "Bin"),
    (r"cyclones?|cones?", "other", "Cyclone"),
    (r"gimbal|camera|cam", "component", "Camera"),
    (r"wheels?|tyres?|tires?|roll(er)?s?|brush", "other", "Wheel"),
    (r"fins?|fin_?box", "other", "Fin"),
    (r"stringer", "frame", "Stringer"),
    (r"skids?|legs?|feet|foot|stand|kickstand", "frame", "Leg"),
    (r"frame|chassis|rails?|wand|tube|rod|mast|pole|stem|neck|spine|shaft", "frame", "Frame"),
    (r"handle|grip", "other", "Handle"),
    (r"head|nozzle|nose|tail|deck|hull|core", "other", "Body"),
    (r"lid|cover|cap|upper|top|roof", "shell_top", "Top shell"),
    (r"lower|bottom|base|tray|floor|underside", "shell_bottom", "Bottom shell"),
    (r"shell|housing|body|pod|enclosure|case|casing", "shell_top", "Housing"),
]
_KW = [(re.compile(rf"^(?:{rx})$"), role, noun) for rx, role, noun in KEYWORDS]
_KW_TEXT = [(re.compile(rf"\b(?:{rx})\b"), role, noun) for rx, role, noun in KEYWORDS]
_GENERIC_VARS = {"s", "p", "c", "b", "x", "part", "shape", "solid", "obj", "piece", "item", "geom", "result", "tmp", "a", "o",
                 "m", "e", "t", "n", "i", "k", "sh", "pt", "q", "mesh", "d", "f", "g", "h", "r", "u", "v", "w", "y", "z"}
SEPARATE = {"prop", "motor", "arm"}
DISTINCT = {"led", "port", "button", "glass", "clear", "diffuser", "cell", "fin", "rubber", "wood", "roof", "wall", "steel"}  # one part per label even from a loop call site

LAYER_OF_ROLE = {"strap": "strap", "shell_top": "shell_top", "button": "shell_top", "window": "shell_top", "lens": "shell_top",
                 "diffuser": "shell_top", "shell_bottom": "shell_bottom", "frame": "frame", "arm": "frame", "prop": "propulsion",
                 "motor": "propulsion", "battery": "power", "pcb": "electronics", "component": "electronics",
                 "antenna": "electronics", "connector": "electronics", "cable": "electronics", "fastener": "fasteners",
                 "other": "exterior"}


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
    return s or "part"


def _tokens(name: str) -> list[str]:
    name = re.sub(r"([a-z])([A-Z])", r"\1_\2", name or "")
    return [t for t in re.split(r"[^a-zA-Z0-9]+", name.lower()) if t]


def _kw_var(var: str | None) -> tuple[str, str] | None:
    toks = _tokens(var or "")
    for rx, role, noun in _KW:  # keyword order wins over token order: "motor_vent" → motor
        if any(rx.match(t) for t in toks):
            return role, noun
    return None


def _kw_text(text: str | None) -> tuple[str, str] | None:
    low = (text or "").lower()
    best = None
    for rx, role, noun in _KW_TEXT:
        m = rx.search(low)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), role, noun)
    return (best[1], best[2]) if best else None


def _humanize(var: str) -> str:
    t = _tokens(var)
    return (" ".join(t)).capitalize() if t else "Part"


def default_name(label: str) -> dict[str, Any]:
    mrole = (label or "body").split(".")[0].replace("_shell", "")
    role, noun = MATERIAL_ROLE_DEFAULT.get(mrole, ("other", mrole.replace("_", " ").capitalize() or "Part"))
    n = (label.split(".", 1)[1] if "." in label else "1").split("_")[0]
    name = noun if n in ("1", "") else f"{noun} {n}"
    return {"part_id": slug(label.replace(".", "_")), "name": name, "role": role, "layer_id": LAYER_OF_ROLE.get(role, "exterior"),
            "params": [], "source": "label"}


# W2 / W17 viewer assemblies (api/cad/look.py, api/cad/wearables.py): fixed labels
FIXED_NAMES: dict[str, tuple[str, str, str]] = {
    "body.1": ("shell_top", "Top shell", "shell_top"), "accent.1": ("shell_bottom", "Bottom shell", "shell_bottom"),
    "top_shell": ("shell_top", "Top shell", "shell_top"), "bottom_shell": ("shell_bottom", "Bottom shell", "shell_bottom"),
    "strap.1": ("strap", "Strap", "strap"), "button.1": ("button", "Button", "button"), "led.1": ("status_light", "Status light", "diffuser"),
    "port.1": ("usb_c_port", "USB-C port", "connector"), "diffuser.1": ("diffuser", "Light diffuser", "diffuser"),
    "steel.1": ("bowl", "Stainless bowl", "other"),
}


def fixed_names(labels: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    feet = [lb for lb in labels if lb.startswith("rubber.")]
    for lb in labels:
        if lb in FIXED_NAMES:
            pid, name, role = FIXED_NAMES[lb]
            out[lb] = {"part_id": pid, "name": name, "role": role, "layer_id": LAYER_OF_ROLE[role], "params": [], "source": "fixed"}
        elif lb in feet:
            out[lb] = {"part_id": "feet", "name": "Rubber feet", "role": "other", "layer_id": "shell_bottom", "params": [],
                       "source": "fixed"}
    return out


# --------------------------------------------------------------------------- label call sites


_trace_lock = threading.RLock()


@contextmanager
def trace_labels(filename: str):
    """Record `label → [lines in filename]` (innermost frame first) for every `shape.label = …` while building."""
    from build123d import Shape

    sites: dict[str, list[int]] = {}
    with _trace_lock:
        orig = Shape.__setattr__

        def tracer(self, name, value):  # noqa: ANN001
            if name == "label" and isinstance(value, str) and value:
                f, lines = sys._getframe(1), []
                while f is not None:
                    if f.f_code.co_filename == filename:
                        lines.append(f.f_lineno)
                    f = f.f_back
                if lines:
                    sites[value] = lines
            orig(self, name, value)

        Shape.__setattr__ = tracer
        try:
            yield sites
        finally:
            Shape.__setattr__ = orig


class _Site:
    __slots__ = ("lineno", "end", "role", "var", "deps", "comment")

    def __init__(self, lineno, end, role, var, deps, comment):
        self.lineno, self.end, self.role, self.var, self.deps, self.comment = lineno, end, role, var, deps, comment


_SHAPE_FUNCS = re.compile(r"^(extrude|loft|revolve|sweep|fillet|chamfer|mirror|split|offset|scale|soft\w*|rod|tube|lab\w*|"
                          r"make_\w+|round\w*|shell\w*|box\w*|cyl\w*|[A-Z]\w*)$")


def _call_name(c: ast.Call) -> str:
    f = c.func
    return f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")


def _is_shape_expr(e: ast.AST | None) -> bool:
    """An expression that builds a solid (a call to a build123d class / shape helper somewhere in it)."""
    return e is not None and any(isinstance(n, ast.Call) and _SHAPE_FUNCS.match(_call_name(n)) for n in ast.walk(e))


def _lead_name(e: ast.AST | None, shapes: set[str] | None = None) -> str | None:
    """Variable that carries the part: `strap - opening` → strap, `soft(motor, 8)` → motor, `Pos(..) * x` → x.
    Only names bound to a shape count (`rod(top, bottom, 17)` → none: top / bottom are points)."""
    if e is None:
        return None
    if isinstance(e, ast.Name):
        return e.id if shapes is None or e.id in shapes else None
    if isinstance(e, ast.BinOp):
        return _lead_name(e.left, shapes) or _lead_name(e.right, shapes)
    if isinstance(e, ast.Call):
        for a in e.args[:1]:
            n = _lead_name(a, shapes)
            if n:
                return n
    if isinstance(e, ast.Attribute):
        return _lead_name(e.value, shapes)
    return None


class _Analyser:
    def __init__(self, source: str):
        self.tree = ast.parse(source)
        self.comments: dict[int, str] = {}
        try:
            for tok in tokenize.generate_tokens(io.StringIO(source).readline):
                if tok.type == tokenize.COMMENT:
                    self.comments[tok.start[0]] = tok.string.lstrip("#").strip()
        except (tokenize.TokenError, IndentationError):
            pass
        self.pkeys = self._pkeys()
        self.shapes: set[str] = set()
        self.sites: list[_Site] = []
        for fn in [n for n in ast.walk(self.tree) if isinstance(n, ast.FunctionDef)]:
            self._fn = fn
            self._body(fn.body, {})

    def _pkeys(self) -> dict[str, float]:
        for node in self.tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "P" for t in node.targets) \
                    and isinstance(node.value, ast.Dict):
                out = {}
                for k, v in zip(node.value.keys, node.value.values):
                    if isinstance(k, ast.Constant) and isinstance(k.value, str):
                        try:
                            val = ast.literal_eval(v)
                        except ValueError:
                            continue
                        if isinstance(val, (int, float)) and not isinstance(val, bool):
                            out[k.value] = float(val)
                return out
        return {}

    def _deps(self, e: ast.AST | None, env: dict[str, set[str]]) -> set[str]:
        out: set[str] = set()
        if e is None:
            return out
        for n in ast.walk(e):
            if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id in ("P", "p", "params"):
                s = n.slice
                if isinstance(s, ast.Constant) and isinstance(s.value, str):
                    out.add(s.value)
            elif isinstance(n, ast.Name) and n.id in env:
                out |= env[n.id]
        return out

    def _assign(self, target: ast.AST, value: ast.AST | None, env: dict[str, set[str]]) -> None:
        if isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, (ast.Tuple, ast.List)) and len(target.elts) == len(value.elts):
            for t, v in zip(target.elts, value.elts):
                self._assign(t, v, env)
            return
        d = self._deps(value, env)
        shape = _is_shape_expr(value) or (isinstance(value, ast.Name) and value.id in self.shapes) or (
            isinstance(value, ast.BinOp) and (_lead_name(value, self.shapes) is not None))
        for n in ast.walk(target):
            if isinstance(n, ast.Name):
                env[n.id] = set(d)
                if shape and isinstance(target, ast.Name):
                    self.shapes.add(n.id)

    def _comment_before(self, line: int) -> str | None:
        lo = max(self._fn.lineno, line - 30)
        for ln in range(line, lo - 1, -1):
            if ln in self.comments:
                return self.comments[ln]
        return None

    def _scan(self, stmt: ast.AST, env: dict[str, set[str]], target_name: str | None = None) -> None:
        for n in ast.walk(stmt):
            if isinstance(n, ast.Call) and len(n.args) >= 2:
                role = next((a.value for a in n.args[1:3] if isinstance(a, ast.Constant) and isinstance(a.value, str)), None)
                if role is None or not re.fullmatch(r"[a-z_]+", role):
                    continue
                first = n.args[0]
                var = _lead_name(first, self.shapes)
                if var is not None and target_name and var in _GENERIC_VARS:
                    var = target_name
                self.sites.append(_Site(n.lineno, n.end_lineno or n.lineno, role, var, self._deps(first, env),
                                        self._comment_before(n.lineno)))
        if isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                if isinstance(t, ast.Attribute) and t.attr == "label" and isinstance(stmt.value, ast.Constant) \
                        and isinstance(stmt.value.value, str):  # (an f-string label is the labeller helper itself)
                    role = stmt.value.value.split(".")[0]
                    self.sites.append(_Site(stmt.lineno, stmt.end_lineno or stmt.lineno, role, _lead_name(t.value, self.shapes),
                                            self._deps(t.value, env), self._comment_before(stmt.lineno)))

    def _body(self, body: list[ast.stmt], env: dict[str, set[str]]) -> None:
        for st in body:
            if isinstance(st, ast.FunctionDef):
                continue
            if isinstance(st, (ast.For, ast.AsyncFor)):
                self._scan(st.iter, env)
                self._assign(st.target, st.iter, env)
                self._body(st.body, env)
                self._body(st.orelse, env)
            elif isinstance(st, (ast.If, ast.While)):
                self._scan(st.test, env)
                self._body(st.body, env)
                self._body(st.orelse, env)
            elif isinstance(st, (ast.With,)):
                self._body(st.body, env)
            elif isinstance(st, ast.Try):
                self._body(st.body, env)
                for h in st.handlers:
                    self._body(h.body, env)
                self._body(st.orelse, env)
                self._body(st.finalbody, env)
            elif isinstance(st, ast.Assign):
                tname = st.targets[0].id if len(st.targets) == 1 and isinstance(st.targets[0], ast.Name) else None
                self._scan(st, env, tname)
                for t in st.targets:
                    self._assign(t, st.value, env)
            elif isinstance(st, ast.AugAssign):
                self._scan(st, env)
                if isinstance(st.target, ast.Name):
                    env[st.target.id] = env.get(st.target.id, set()) | self._deps(st.value, env)
            elif isinstance(st, ast.AnnAssign) and st.value is not None:
                self._scan(st, env)
                self._assign(st.target, st.value, env)
            else:
                self._scan(st, env)

    def site_for(self, label: str, lines: list[int]) -> _Site | None:
        role = label.split(".")[0]
        for ln in lines:
            hits = [s for s in self.sites if s.lineno <= ln <= s.end and (s.role is None or s.role == role)]
            if hits:
                return min(hits, key=lambda s: s.end - s.lineno)
        return None


def names_from_source(source: str, sites: dict[str, list[int]], labels: list[str] | None = None,
                      param_keys: set[str] | None = None) -> dict[str, dict[str, Any]]:
    """label → {part_id, name, role, layer_id, params, source}. Labels without a site get default_name().
    `param_keys`: the editable parameter names (default: the program's top-level `P = {...}` numeric keys)."""
    try:
        an = _Analyser(source)
    except SyntaxError:
        return {}
    if param_keys is not None:
        an.pkeys = {k: 0.0 for k in param_keys}
    labels = list(labels or sites)
    raw: dict[str, tuple[_Site | None, tuple[str, str]]] = {}
    for lb in labels:
        site = an.site_for(lb, sites.get(lb) or [])
        mrole = lb.split(".")[0]
        hit = None
        if site is not None:
            hit = _kw_var(site.var) if site.var and site.var not in _GENERIC_VARS else None
            if hit is None and mrole in DISTINCT:
                hit = MATERIAL_ROLE_DEFAULT[mrole]
            hit = hit or _kw_text(site.comment)
        if hit is None:
            hit = MATERIAL_ROLE_DEFAULT.get(mrole, ("other", mrole.capitalize()))
        raw[lb] = (site, hit)
    # a material role that always means the same thing beats a vague keyword
    out: dict[str, dict[str, Any]] = {}
    by_site: dict[tuple, list[str]] = {}
    for lb, (site, (role, noun)) in raw.items():
        key = (site.lineno, site.end) if site is not None else ("label", lb)
        by_site.setdefault(key, []).append(lb)
    used: dict[str, int] = {}

    def unique(pid: str) -> str:
        used[pid] = used.get(pid, 0) + 1
        return pid if used[pid] == 1 else f"{pid}_{used[pid]}"

    for key, lbs in by_site.items():
        site, (role, noun) = raw[lbs[0]]
        var = site.var if site is not None else None
        name = noun
        if var and var not in _GENERIC_VARS and len(_tokens(var)) > 1 and _kw_var(var):
            name = _humanize(var)
        params = sorted((site.deps if site is not None else set()) & set(an.pkeys))
        if len(lbs) > 1 and role not in SEPARATE:
            plural = name if name.endswith("s") else (name[:-1] + "ies" if name.endswith("y") else name + "s")
            pid = unique(slug(plural))
            for lb in lbs:
                out[lb] = {"part_id": pid, "name": plural, "role": role, "layer_id": LAYER_OF_ROLE.get(role, "exterior"),
                           "params": params, "source": "program", "count": len(lbs)}
        else:
            for i, lb in enumerate(sorted(lbs, key=_label_n)):
                nm = f"{name} {i + 1}" if len(lbs) > 1 else name
                out[lb] = {"part_id": unique(slug(nm)), "name": nm, "role": role, "layer_id": LAYER_OF_ROLE.get(role, "exterior"),
                           "params": params, "source": "program"}
    from api.cad.partnames_curated import apply as curated

    out = curated(source, out)
    # disambiguate repeated names ("Frame", "Frame") with their number
    seen: dict[str, int] = {}
    for info in out.values():
        seen[info["name"]] = seen.get(info["name"], 0) + 1
    counters: dict[str, int] = {}
    done: set[str] = set()
    for lb, info in out.items():
        if seen[info["name"]] > 1 and info["part_id"] not in done and info.get("count") is None and info.get("source") != "curated":
            base = info["name"]
            counters[base] = counters.get(base, 0) + 1
            info["name"] = f"{base} {counters[base]}"
        done.add(info["part_id"])
    return out


def _label_n(lb: str) -> float:
    try:
        return float(lb.split(".", 1)[1])
    except (IndexError, ValueError):
        return 0.0


def program_params(source: str) -> dict[str, float]:
    try:
        return _Analyser(source).pkeys
    except SyntaxError:
        return {}


# --------------------------------------------------------------------------- PartMeta (node extras)


def _material_text(info: dict, first_role: str, mat: dict, look: dict, meta: dict | None, ov: dict | None) -> tuple[str, str | None]:
    lm = look.get("_meta") or {}
    if ov and ov.get("material") in PART_MATERIALS:
        return PART_MATERIALS[ov["material"]]["name"], ov.get("finish") or lm.get("finish") if first_role in ("body", "accent") else ov.get("finish")
    if first_role in ("body", "accent", "button"):
        return (meta or {}).get("material") or lm.get("material_text") or mat["name"], (ov or {}).get("finish") or lm.get("finish") or None
    return mat["name"], (ov or {}).get("finish")


def material_options(role: str, first_role: str) -> list[str]:
    if role == "strap" or first_role in ("fabric", "strap"):
        return list(STRAP_MATERIALS)
    if first_role in ("body", "accent", "coat", "metal", "steel") and role in ("shell_top", "shell_bottom", "frame", "other", "arm"):
        return list(SHELL_MATERIALS)
    if first_role in ("glass", "clear") or role in ("window", "lens"):
        return list(WINDOW_MATERIALS)
    return []


def part_meta(info: dict, first_role: str, mat: dict, lo_mm, hi_mm, look: dict, meta: dict | None, ov: dict | None) -> dict:
    from api.cad.glb import linear_to_hex

    material, finish = _material_text(info, first_role, mat, look, meta, ov)
    role = info["role"] if info["role"] in ROLES else "other"
    if role == "strap" and not (ov or {}).get("material") and first_role in ("fabric", "strap", "rubber", "body", "accent"):
        material = PART_MATERIALS["lsr_silicone"]["name"] if first_role != "fabric" or "strap" in info["name"].lower() else material
    colour_editable = first_role not in ("led", "cell", "roof", "wall", "port")
    return {
        "part_id": info["part_id"], "name": info["name"], "role": role, "layer_id": info.get("layer_id") or LAYER_OF_ROLE.get(role, "exterior"),
        "material": material, "finish": finish, "colour_hex": (ov or {}).get("colour_hex") or linear_to_hex(mat["baseColorFactor"]),
        "measured_bbox_mm": [round(float(h - l), 2) for l, h in zip(lo_mm, hi_mm)],
        "centroid_mm": [round(float(h + l) / 2, 2) for l, h in zip(lo_mm, hi_mm)],
        "label": "measured", "bom_item_id": None, "lcsc_pn": None, "package": None, "unit_price": None, "editable": [],
        "colour_editable": colour_editable, "material_options": material_options(role, first_role),
    }


def recoloured_meta(extras: dict, mat: dict, look: dict, ov: dict | None) -> dict:
    from api.cad.glb import linear_to_hex

    out = dict(extras)
    out["colour_hex"] = (ov or {}).get("colour_hex") or linear_to_hex(mat["baseColorFactor"])
    lm = look.get("_meta") or {}
    role = mat.get("role", "body")
    if ov and ov.get("material") in PART_MATERIALS:
        out["material"] = PART_MATERIALS[ov["material"]]["name"]
    elif role in ("body", "accent", "button"):
        out["material"] = lm.get("material_text") or out.get("material")
    if ov and ov.get("finish"):
        out["finish"] = ov["finish"]
    elif role in ("body", "accent", "button") and lm.get("finish"):
        out["finish"] = lm.get("finish")
    return out


__all__ = ["names_from_source", "trace_labels", "default_name", "fixed_names", "part_meta", "recoloured_meta",
           "program_params", "PART_MATERIALS", "SHELL_MATERIALS", "ROLES", "LAYER_OF_ROLE", "slug"]
