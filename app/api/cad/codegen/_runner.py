"""Sandbox child process (W19). Run ONLY by api.cad.codegen.sandbox as `python -I -B _runner.py <model.py> <out_dir>`.

Stand-alone on purpose (stdlib + build123d only; `-I` means no project path, no user site, no PYTHON* env).
Executes an AST-checked program with restricted builtins (imports limited to build123d and math), calls `build()`,
checks the parts are real solids, exports <out_dir>/model.{step,stl,glb} and writes <out_dir>/result.json.
"""

import builtins
import json
import sys
import time
import traceback

ALLOWED_MODULES = ("build123d", "math")
SAFE_BUILTINS = (
    "abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter", "float", "frozenset", "int", "isinstance",
    "issubclass", "iter", "len", "list", "map", "max", "min", "next", "pow", "print", "range", "reversed", "round",
    "set", "slice", "sorted", "str", "sum", "tuple", "zip", "True", "False", "None", "Exception", "ValueError",
    "TypeError", "IndexError", "KeyError", "ZeroDivisionError", "RuntimeError", "ArithmeticError", "StopIteration",
    "AssertionError", "NotImplementedError", "AttributeError", "object", "property", "staticmethod", "classmethod",
    "super", "hash", "id", "repr", "chr", "ord", "complex", "callable", "format",
)


def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level != 0 or name.split(".")[0] not in ALLOWED_MODULES:
        raise ImportError(f"import of {name!r} is not allowed (only build123d and math)")
    return __import__(name, globals, locals, fromlist, level)


def collect(result):
    """build() may return a shape, a list/tuple of shapes, or a dict name -> shape. Flattens plain Compounds."""
    from build123d import Compound, Shape

    items = list(result.items()) if isinstance(result, dict) else (
        [(None, s) for s in result] if isinstance(result, (list, tuple)) else [(None, result)])
    parts = []

    def add(name, s):
        if s is None:
            return
        if not isinstance(s, Shape):
            raise TypeError(f"build() returned a {type(s).__name__}, expected build123d solids")
        kids = list(s.children) if isinstance(s, Compound) and s.children else []
        if kids and not s.label:
            for k in kids:
                add(None, k)
            return
        if name and not s.label:
            s.label = str(name)
        parts.append(s)

    for name, s in items:
        add(name, s)
    return parts


SITES = {}  # W29: label -> [model.py lines of the frames that set it, innermost first] (part naming)


def trace_labels():
    from build123d import Shape

    orig = Shape.__setattr__

    def tracer(self, name, value):
        if name == "label" and isinstance(value, str) and value:
            f, lines = sys._getframe(1), []
            while f is not None:
                if f.f_code.co_filename == "model.py":
                    lines.append(f.f_lineno)
                f = f.f_back
            if lines:
                SITES[value] = lines
        orig(self, name, value)

    Shape.__setattr__ = tracer


def glb_tolerance(bbox_mm):
    """W29: viewer tessellation (mm, rad) — mirrors api.cad.build.glb_tolerance (this file is stand-alone)."""
    size = max(bbox_mm) if bbox_mm else 100.0
    return max(0.02, min(1.5, size / 2500.0)), 0.12


def main():
    code_path, out_dir = sys.argv[1], sys.argv[2]
    started = time.monotonic()
    out = {"ok": False, "error": None, "stage": "exec", "parts": []}
    try:
        src = open(code_path, encoding="utf-8").read()
        trace_labels()
        env_builtins = {n: getattr(builtins, n) for n in SAFE_BUILTINS if hasattr(builtins, n)}
        env_builtins["__import__"] = guarded_import
        ns = {"__builtins__": env_builtins, "__name__": "model"}
        exec(compile(src, "model.py", "exec"), ns)
        if not callable(ns.get("build")):
            raise NameError("the program must define a function build()")
        out["stage"] = "build"
        parts = collect(ns["build"]())
        out["stage"] = "validate"
        from build123d import Compound, export_gltf, export_step, export_stl

        if not parts:
            raise ValueError("build() returned no parts")
        rows, problems = [], []
        for i, p in enumerate(parts):
            label = p.label or f"body.{i + 1}"
            if "." not in label:
                label = f"{label}.{i + 1}"
            if label != p.label and p.label in SITES:
                SITES[label] = SITES[p.label]
            p.label = label
            solids = p.solids()
            vol = sum(abs(s.volume) for s in solids)
            if not solids or vol <= 1e-6:
                problems.append(f"part {label!r} has no solid volume (2D sketch/face or empty boolean?)")
                continue
            bb = p.bounding_box()
            valid = p.is_valid if not callable(p.is_valid) else p.is_valid()
            rows.append({"label": label, "role": label.split(".")[0], "volume_mm3": round(vol, 1), "valid": bool(valid),
                         "bbox_mm": [round(bb.size.X, 2), round(bb.size.Y, 2), round(bb.size.Z, 2)]})
        if problems:
            raise ValueError("; ".join(problems[:5]))
        if len(parts) > 400:
            raise ValueError(f"{len(parts)} parts: keep it under 400")
        asm = Compound(children=parts)
        asm.label = "product"
        bb = asm.bounding_box()
        out.update(parts=rows, bbox_mm=[round(bb.size.X, 2), round(bb.size.Y, 2), round(bb.size.Z, 2)],
                   bbox_min=[round(bb.min.X, 2), round(bb.min.Y, 2), round(bb.min.Z, 2)],
                   volume_mm3=round(sum(r["volume_mm3"] for r in rows), 1))
        out["label_sites"] = {r["label"]: SITES.get(r["label"], []) for r in rows}
        out["stage"] = "export"
        export_step(asm, f"{out_dir}/model.step")
        export_stl(asm, f"{out_dir}/model.stl", tolerance=0.05 * max(1.0, max(out["bbox_mm"]) / 400), angular_tolerance=0.2)
        lin, ang = glb_tolerance(out["bbox_mm"])
        export_gltf(asm, f"{out_dir}/model.glb", binary=True, linear_deflection=lin, angular_deflection=ang)
        out["ok"] = True
    except BaseException as e:  # noqa: BLE001 — everything goes back to the parent (and the LLM) as text
        tb = traceback.format_exception(type(e), e, e.__traceback__)
        frames = [f for f in traceback.extract_tb(e.__traceback__) if f.filename == "model.py"]
        out["error"] = f"{type(e).__name__}: {e}"[:1500]
        out["traceback"] = "".join(tb[-8:])[-3000:]
        out["user_traceback"] = "\n".join(f"model.py line {f.lineno}, in {f.name}: {(f.line or '').strip()}"
                                           for f in frames[-6:])
    out["seconds"] = round(time.monotonic() - started, 2)
    with open(f"{out_dir}/result.json", "w", encoding="utf-8") as f:
        json.dump(out, f)


if __name__ == "__main__":
    main()
