"""GLB finishing pass (W29): photoreal-ready viewer models with one named node per part.

    finalize(path, look, names=None, meta=None)   # OCCT export → finished GLB (idempotent: a finished GLB is recoloured)
    read_parts(path) -> [PartMeta dict]           # node extras of every part node
    set_extras(path, {part_id: extras})           # rewrite part extras (JSON chunk only, geometry untouched)
    material_for(role, look, override=None)       # glTF material dict (PBR + KHR extensions) for a material role

Conventions (contracts/api.md "3D parts & anatomy"): metres, +Y up; scene root "product" (identity) → one node per
part named `<part_id>` (translation = part bbox centre, extras = PartMeta) → one or more mesh children named
`<material role>.<n>` (the build123d label: the role picks the material). All node transforms are baked, so the
viewer can explode a part by moving its node alone.

Geometry: OCCT's per-face analytic normals are kept inside each face and averaged across face seams where the two
normals are within CREASE_DEG (tangent fillets become seamless, real edges stay sharp); vertices are welded on
(position, normal); OCCT's per-face UVs are dropped (no textures). Materials: metallic/roughness from the look plus
KHR_materials_clearcoat (gloss plastics, painted metal, glass), _sheen (LSR silicone, fabric), _transmission + _ior
(diffusers, clear parts, lenses), _specular (glass, plastics), _emissive_strength (LEDs).
"""

from __future__ import annotations

import json
import logging
import math
import os
import threading
from pathlib import Path
from typing import Any

import numpy as np

log = logging.getLogger("cad.glb")

PIPELINE = "w29-glb-1"
CREASE_DEG = 30.0
EXTENSIONS = ("KHR_materials_clearcoat", "KHR_materials_sheen", "KHR_materials_transmission", "KHR_materials_ior",
              "KHR_materials_specular", "KHR_materials_emissive_strength")

_COMP = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
_NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


# --------------------------------------------------------------------------- colour helpers


def _srgb(c: float) -> float:
    c = max(0.0, min(1.0, float(c)))
    return c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def linear_to_hex(rgb) -> str:
    return "#" + "".join(f"{round(_srgb(c) * 255):02X}" for c in list(rgb)[:3])


def hex_to_linear(hex_: str) -> list[float]:
    from api.cad.look import hex_to_linear as h

    return h(hex_)


# --------------------------------------------------------------------------- materials

# role -> extension recipe (applied on top of the look's metallic / roughness / colour)
_METAL_ROUGH = {"anodis": 0.35, "anodiz": 0.35, "brushed": 0.25, "polish": 0.1, "mirror": 0.08, "bead": 0.42, "sand": 0.42}


def _finish_text(look: dict, role: str) -> str:
    meta = look.get("_meta") or {}
    return f"{meta.get('finish', '')} {meta.get('material', '')}".lower() if role in ("body", "accent", "button") else ""


def material_for(role: str, look: dict, override: dict | None = None) -> dict:
    """glTF material (dict, pygltflib-compatible keys) for a material role of `look` (look.look_for / family_look).
    `override`: {colour_hex?, material?, finish?} of one part (W29 part edit)."""
    spec = dict(look.get(role) or look.get("body") or {})
    base = list(spec.get("baseColorFactor") or [0.8, 0.8, 0.8, 1.0])
    metallic = float(spec.get("metallicFactor", 0.0))
    rough = float(spec.get("roughnessFactor", 0.5))
    emissive = list(spec.get("emissiveFactor") or [0.0, 0.0, 0.0])
    name = spec.get("name") or role
    ext: dict[str, dict] = {}
    fin = _finish_text(look, role)
    kind = role
    if override:
        if override.get("colour_hex"):
            base = [*hex_to_linear(override["colour_hex"]), 1.0]
        if override.get("material"):
            from api.cad.parts import PART_MATERIALS

            pm = PART_MATERIALS.get(override["material"])
            if pm:
                kind, name = pm["kind"], pm["name"]
                metallic, rough = pm["metallic"], pm["roughness"]
                if not override.get("colour_hex") and pm.get("colour"):
                    base = [*hex_to_linear(pm["colour"]), 1.0]
        if override.get("finish"):
            fin = override["finish"].lower()
            name = f"{name} — {override['finish']}"
    alpha = base[3] if len(base) > 3 else 1.0

    def metal_rough(text: str, default: float) -> float:
        return next((v for k, v in _METAL_ROUGH.items() if k in text), default)

    if kind in ("metal", "steel", "port") or metallic >= 0.9:
        metallic = 1.0 if kind != "port" else metallic
        rough = metal_rough(f"{fin} {name}".lower(), 0.35 if kind == "metal" else (0.25 if kind == "steel" else rough))
        if any(k in fin for k in ("paint", "powder", "lacquer", "gloss")):
            ext["KHR_materials_clearcoat"] = {"clearcoatFactor": 0.6, "clearcoatRoughnessFactor": 0.12}
    elif kind in ("body", "accent", "button", "coat", "plastic"):
        if any(k in fin for k in ("soft-touch", "soft touch", "rubber", "tpu")):
            rough = 0.76
            ext["KHR_materials_specular"] = {"specularFactor": 0.35}
        elif any(k in fin for k in ("gloss", "polish", "spi-a", "piano", "lacquer")):
            rough = min(rough, 0.2)
            ext["KHR_materials_clearcoat"] = {"clearcoatFactor": 1.0, "clearcoatRoughnessFactor": 0.04}
        elif kind == "coat":  # powder coat / painted metal
            ext["KHR_materials_clearcoat"] = {"clearcoatFactor": 0.35, "clearcoatRoughnessFactor": 0.3}
        else:
            ext["KHR_materials_specular"] = {"specularFactor": 0.5}
    elif kind in ("strap", "silicone"):  # LSR silicone
        rough = 0.62
        ext["KHR_materials_sheen"] = {"sheenColorFactor": [min(1.0, c * 0.6 + 0.25) for c in base[:3]], "sheenRoughnessFactor": 0.55}
    elif kind == "fabric":
        rough = 0.92
        ext["KHR_materials_sheen"] = {"sheenColorFactor": [min(1.0, c * 0.8 + 0.2) for c in base[:3]], "sheenRoughnessFactor": 0.8}
    elif kind == "rubber":
        rough = 0.9
        ext["KHR_materials_sheen"] = {"sheenColorFactor": [0.12, 0.12, 0.12], "sheenRoughnessFactor": 0.9}
    elif kind == "diffuser":
        rough = 0.45
        ext["KHR_materials_transmission"] = {"transmissionFactor": 0.55}
        ext["KHR_materials_ior"] = {"ior": 1.49}
    elif kind == "clear":
        rough = 0.06
        ext["KHR_materials_transmission"] = {"transmissionFactor": 0.92}
        ext["KHR_materials_ior"] = {"ior": 1.58}
        ext["KHR_materials_specular"] = {"specularFactor": 1.0}
        alpha = 1.0
    elif kind in ("glass", "lens", "cell"):
        rough = min(rough, 0.06)
        ext["KHR_materials_clearcoat"] = {"clearcoatFactor": 1.0, "clearcoatRoughnessFactor": 0.02}
        ext["KHR_materials_ior"] = {"ior": 1.5}
        ext["KHR_materials_specular"] = {"specularFactor": 1.0}
    elif kind == "led":
        ext["KHR_materials_emissive_strength"] = {"emissiveStrength": 2.0}
        ext["KHR_materials_clearcoat"] = {"clearcoatFactor": 1.0, "clearcoatRoughnessFactor": 0.05}
    elif kind == "fin":
        rough = 0.22
        ext["KHR_materials_clearcoat"] = {"clearcoatFactor": 1.0, "clearcoatRoughnessFactor": 0.05}
        alpha = 1.0
    elif kind == "wood":
        ext["KHR_materials_clearcoat"] = {"clearcoatFactor": 0.4, "clearcoatRoughnessFactor": 0.25}
    base = [*base[:3], alpha]
    blend = alpha < 0.999
    return {"name": name, "role": role, "baseColorFactor": [round(float(c), 4) for c in base], "metallicFactor": round(metallic, 3),
            "roughnessFactor": round(rough, 3), "emissiveFactor": emissive, "alphaMode": "BLEND" if blend else "OPAQUE",
            "doubleSided": blend or "KHR_materials_transmission" in ext, "extensions": ext}


def _gltf_material(m: dict):
    from pygltflib import Material, PbrMetallicRoughness

    return Material(name=m["name"], pbrMetallicRoughness=PbrMetallicRoughness(
        baseColorFactor=m["baseColorFactor"], metallicFactor=m["metallicFactor"], roughnessFactor=m["roughnessFactor"]),
        emissiveFactor=m["emissiveFactor"], alphaMode=m["alphaMode"], doubleSided=m["doubleSided"],
        extensions=dict(m["extensions"]), extras={"role": m["role"]})


# --------------------------------------------------------------------------- reading


def _blob(g) -> bytes:
    b = g.binary_blob()
    return b if b is not None else b""


def _accessor(g, blob: bytes, idx: int) -> np.ndarray:
    acc = g.accessors[idx]
    bv = g.bufferViews[acc.bufferView]
    dt = np.dtype(_COMP[acc.componentType])
    nc = _NCOMP[acc.type]
    off = (bv.byteOffset or 0) + (acc.byteOffset or 0)
    stride = bv.byteStride or dt.itemsize * nc
    if stride == dt.itemsize * nc:
        a = np.frombuffer(blob, dtype=dt, count=acc.count * nc, offset=off).reshape(acc.count, nc)
    else:
        raw = np.frombuffer(blob, dtype=np.uint8, count=stride * (acc.count - 1) + dt.itemsize * nc, offset=off)
        a = np.lib.stride_tricks.as_strided(raw, shape=(acc.count, dt.itemsize * nc), strides=(stride, 1)).copy()
        a = a.view(dt).reshape(acc.count, nc)
    return a.astype(np.float64 if dt == np.float32 else np.int64)


def _local(node) -> np.ndarray:
    if node.matrix:
        return np.array(node.matrix, dtype=float).reshape(4, 4).T
    t = np.eye(4)
    if node.translation:
        t[:3, 3] = node.translation
    r = np.eye(4)
    if node.rotation:
        x, y, z, w = node.rotation
        r[:3, :3] = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    s = np.eye(4)
    if node.scale:
        s[0, 0], s[1, 1], s[2, 2] = node.scale
    return t @ r @ s


def _mesh_nodes(g) -> list[tuple[int, np.ndarray]]:
    out: list[tuple[int, np.ndarray]] = []

    def walk(i: int, parent: np.ndarray) -> None:
        node = g.nodes[i]
        m = parent @ _local(node)
        if node.mesh is not None:
            out.append((i, m))
        for c in node.children or []:
            walk(c, m)

    for root in g.scenes[g.scene or 0].nodes:
        walk(root, np.eye(4))
    return out


def is_finished(g) -> bool:
    return bool(g.asset and isinstance(g.asset.extras, dict) and g.asset.extras.get("pipeline") == PIPELINE)


# --------------------------------------------------------------------------- geometry


def smooth_normals(pos: np.ndarray, nrm: np.ndarray, crease_deg: float = CREASE_DEG) -> np.ndarray:
    """Average the normals of coincident vertices (face seams) that are within `crease_deg` of each other."""
    n = nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
    if len(pos) == 0:
        return n
    q = np.round(pos / 1e-6).astype(np.int64)  # 1 µm
    _, inv, counts = np.unique(q, axis=0, return_inverse=True, return_counts=True)
    inv = inv.reshape(-1)
    out = n.copy()
    cos = math.cos(math.radians(crease_deg))
    order = np.argsort(inv, kind="stable")
    sizes = counts[inv[order]]
    for s in np.unique(sizes):
        if s < 2:
            continue
        idx = order[sizes == s].reshape(-1, s)  # (groups, s) — vertices of one position, grouped by the sort
        v = n[idx]  # (G, s, 3)
        dots = np.einsum("gik,gjk->gij", v, v)
        acc = np.einsum("gij,gjk->gik", (dots > cos).astype(float), v)
        acc /= np.maximum(np.linalg.norm(acc, axis=2, keepdims=True), 1e-12)
        out[idx.reshape(-1)] = acc.reshape(-1, 3)
    return out


def weld(pos: np.ndarray, nrm: np.ndarray, tri: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    key = np.concatenate([np.round(pos / 1e-6), np.round(nrm * 1e4)], axis=1).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    t = inv[tri]
    keep = (t[:, 0] != t[:, 1]) & (t[:, 1] != t[:, 2]) & (t[:, 0] != t[:, 2])
    return pos[first], nrm[first], t[keep]


def _node_geometry(g, blob: bytes, mesh_idx: int, world: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ps, ns, ts, base = [], [], [], 0
    rot = world[:3, :3]
    for prim in g.meshes[mesh_idx].primitives:
        if prim.attributes.POSITION is None:
            continue
        p = _accessor(g, blob, prim.attributes.POSITION)[:, :3]
        if prim.attributes.NORMAL is not None:
            nn = _accessor(g, blob, prim.attributes.NORMAL)[:, :3]
        else:
            nn = np.zeros_like(p)
        if prim.indices is not None:
            t = _accessor(g, blob, prim.indices).reshape(-1, 3)
        else:
            t = np.arange(len(p)).reshape(-1, 3)
        p = p @ rot.T + world[:3, 3]
        nn = nn @ np.linalg.inv(rot)  # row vectors: n' = n · (R⁻¹) is the inverse-transpose normal matrix
        if not np.any(nn):  # no normals: flat face normals
            a, b, c = p[t[:, 0]], p[t[:, 1]], p[t[:, 2]]
            fn = np.cross(b - a, c - a)
            nn = np.zeros_like(p)
            for k in range(3):
                np.add.at(nn, t[:, k], fn)
        ps.append(p)
        ns.append(nn)
        ts.append(t + base)
        base += len(p)
    if not ps:
        return np.zeros((0, 3)), np.zeros((0, 3)), np.zeros((0, 3), dtype=np.int64)
    pos, nrm, tri = np.concatenate(ps), np.concatenate(ns), np.concatenate(ts)
    nrm = smooth_normals(pos, nrm)
    return weld(pos, nrm, tri)


# --------------------------------------------------------------------------- writing


class _Writer:
    def __init__(self) -> None:
        from pygltflib import GLTF2

        self.g = GLTF2()
        self.data = bytearray()

    def _view(self, arr: np.ndarray, target: int | None) -> int:
        from pygltflib import BufferView

        while len(self.data) % 4:
            self.data.append(0)
        off = len(self.data)
        b = arr.tobytes()
        self.data.extend(b)
        self.g.bufferViews.append(BufferView(buffer=0, byteOffset=off, byteLength=len(b), target=target))
        return len(self.g.bufferViews) - 1

    def accessor(self, arr: np.ndarray, kind: str, target: int | None, minmax: bool = False) -> int:
        from pygltflib import Accessor

        comp = {np.dtype(np.float32): 5126, np.dtype(np.uint16): 5123, np.dtype(np.uint32): 5125}[arr.dtype]
        v = self._view(arr, target)
        acc = Accessor(bufferView=v, componentType=comp, count=len(arr) if kind != "SCALAR" else arr.size, type=kind)
        if minmax:
            acc.min = [float(x) for x in arr.min(axis=0)]
            acc.max = [float(x) for x in arr.max(axis=0)]
        self.g.accessors.append(acc)
        return len(self.g.accessors) - 1

    def mesh(self, name: str, pos: np.ndarray, nrm: np.ndarray, tri: np.ndarray, material: int) -> int:
        from pygltflib import Attributes, Mesh, Primitive

        idx_t = np.uint16 if len(pos) < 65535 else np.uint32
        pa = self.accessor(pos.astype(np.float32), "VEC3", 34962, minmax=True)
        na = self.accessor(nrm.astype(np.float32), "VEC3", 34962)
        ia = self.accessor(tri.astype(idx_t).reshape(-1), "SCALAR", 34963)
        self.g.meshes.append(Mesh(name=name, primitives=[Primitive(attributes=Attributes(POSITION=pa, NORMAL=na), indices=ia,
                                                                   material=material)]))
        return len(self.g.meshes) - 1

    def save(self, path: Path) -> None:
        from pygltflib import Buffer

        self.g.buffers = [Buffer(byteLength=len(self.data))]
        self.g.set_binary_blob(bytes(self.data))
        _atomic_save(self.g, path)


def _atomic_save(g, path: Path | str) -> None:
    path = Path(path)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")  # never serve a half-written file
    g.save_binary(str(tmp))
    os.replace(tmp, path)


def _role_of(label: str) -> str:
    role = (label or "body").split(".")[0].replace("_shell", "")
    return {"top": "body", "bottom": "accent"}.get(role, role)


def _uses(mats: list[dict]) -> list[str]:
    return sorted({k for m in mats for k in m["extensions"]})


# --------------------------------------------------------------------------- public


def _look_from(g, mat_idx: int | None, role: str) -> dict:
    """In-place finishing (no look given): the GLB's own material for this node becomes the role's look."""
    if mat_idx is None or not g.materials or mat_idx >= len(g.materials):
        return {role: {"name": role, "baseColorFactor": [0.8, 0.8, 0.8, 1.0], "metallicFactor": 0.0, "roughnessFactor": 0.5}}
    m = g.materials[mat_idx]
    pbr = m.pbrMetallicRoughness
    spec = {"name": m.name or role, "baseColorFactor": list(pbr.baseColorFactor or [0.8, 0.8, 0.8, 1.0]) if pbr else [0.8, 0.8, 0.8, 1.0],
            "metallicFactor": pbr.metallicFactor if pbr and pbr.metallicFactor is not None else 0.0,
            "roughnessFactor": pbr.roughnessFactor if pbr and pbr.roughnessFactor is not None else 0.5,
            "emissiveFactor": list(m.emissiveFactor or [0.0, 0.0, 0.0])}
    return {role: spec, "body": spec}


def finalize(path: Path | str, look: dict | None, names: dict[str, dict] | None = None, meta: dict | None = None,
             overrides: dict[str, dict] | None = None) -> Path:
    """Rewrite the GLB at `path` in the W29 conventions. `names`: label → {part_id, name, role, …} (api.cad.parts);
    `meta`: product-level facts for the extras ({material, finish}); `overrides`: part_id → {colour_hex, material, finish}.
    A GLB that is already finished keeps its geometry and part ids and is only re-materialled (recolour path)."""
    from pygltflib import GLTF2, Asset, Node, Scene

    from api.cad import parts as parts_mod

    path = Path(path)
    g = GLTF2.load(str(path))
    if is_finished(g):
        return recolour(path, look, overrides=overrides) if look is not None else path
    blob = _blob(g)
    groups: dict[str, dict] = {}
    labels_seen: dict[str, int] = {}
    for ni, world in _mesh_nodes(g):
        label = g.nodes[ni].name or f"body.{ni}"
        if label in labels_seen:
            labels_seen[label] += 1
            label = f"{label}_{labels_seen[label]}"
        else:
            labels_seen[label] = 1
        info = (names or {}).get(label) or parts_mod.default_name(label)
        pos, nrm, tri = _node_geometry(g, blob, g.nodes[ni].mesh, world)
        if len(tri) == 0:
            continue
        grp = groups.setdefault(info["part_id"], {"info": info, "meshes": []})
        prims = g.meshes[g.nodes[ni].mesh].primitives
        src_mat = prims[0].material if prims and prims[0].material is not None else None
        grp["meshes"].append((label, pos, nrm, tri, src_mat))
    w = _Writer()
    mats: list[dict] = []
    mat_index: dict[str, int] = {}
    root = Node(name="product", children=[], extras={"pipeline": PIPELINE, "units": "m", "up": "+Y", "overrides": overrides or {}})
    w.g.nodes.append(root)
    parts_meta: list[dict] = []
    for pid, grp in groups.items():
        info = grp["info"]
        allp = np.concatenate([m[1] for m in grp["meshes"]])
        lo, hi = allp.min(axis=0), allp.max(axis=0)
        centre = (lo + hi) / 2
        ov = (overrides or {}).get(pid)
        pnode = Node(name=pid, translation=[float(x) for x in centre], children=[])
        first_role = _role_of(grp["meshes"][0][0])
        m0 = None
        for label, pos, nrm, tri, src_mat in grp["meshes"]:
            role = _role_of(label)
            lk = look if look is not None else _look_from(g, src_mat, role)
            key = json.dumps([role, ov, None if look is not None else src_mat], sort_keys=True)
            if key not in mat_index:
                mats.append(material_for(role if role in lk else "body", lk, ov))
                mat_index[key] = len(mats) - 1
            m0 = m0 or mats[mat_index[key]]
            mi = w.mesh(label, pos - centre, nrm, tri, mat_index[key])
            w.g.nodes.append(Node(name=label, mesh=mi))
            pnode.children.append(len(w.g.nodes) - 1)
        look_used = look if look is not None else _look_from(g, grp["meshes"][0][4], first_role)
        pm = parts_mod.part_meta(info, first_role, m0, lo * 1000, hi * 1000, look_used, meta, ov)
        pnode.extras = pm
        parts_meta.append(pm)
        if info.get("params"):
            root.extras.setdefault("part_params", {})[pid] = list(info["params"])
        w.g.nodes.append(pnode)
        root.children.append(len(w.g.nodes) - 1)
    w.g.scenes = [Scene(name="product", nodes=[0])]
    w.g.scene = 0
    w.g.materials = [_gltf_material(m) for m in mats]
    used = _uses(mats)
    w.g.extensionsUsed = used
    w.g.asset = Asset(version="2.0", generator="PhysicalLovableX W29 (build123d/OCCT + glb.finalize)",
                      extras={"pipeline": PIPELINE, "units": "m", "up": "+Y", "crease_deg": CREASE_DEG})
    w.save(path)
    return path


def recolour(path: Path | str, look: dict, overrides: dict[str, dict] | None = None) -> Path:
    """Finished GLB: new materials from `look` (+ per-part overrides); part extras colour / material / finish follow."""
    from pygltflib import GLTF2

    from api.cad import parts as parts_mod

    path = Path(path)
    g = GLTF2.load(str(path))
    mats: list[dict] = []
    mat_index: dict[str, int] = {}
    root = g.nodes[g.scenes[g.scene or 0].nodes[0]]
    rx = root.extras if isinstance(root.extras, dict) else {}
    if overrides is None:
        overrides = rx.get("overrides") or {}
    root.extras = {**rx, "overrides": overrides}
    for node in g.nodes:
        if not node.children or not isinstance(node.extras, dict) or "part_id" not in node.extras:
            continue
        pid = node.extras["part_id"]
        ov = overrides.get(pid)
        first = None
        for c in node.children:
            child = g.nodes[c]
            if child.mesh is None:
                continue
            role = _role_of(child.name or "body")
            key = json.dumps([role, ov], sort_keys=True)
            if key not in mat_index:
                mats.append(material_for(role if role in look else "body", look, ov))
                mat_index[key] = len(mats) - 1
            for prim in g.meshes[child.mesh].primitives:
                prim.material = mat_index[key]
            first = first or mats[mat_index[key]]
        if first is not None:
            node.extras = parts_mod.recoloured_meta(node.extras, first, look, ov)
    g.materials = [_gltf_material(m) for m in mats]
    g.extensionsUsed = _uses(mats)
    _atomic_save(g, path)
    return path


def read_parts(path: Path | str) -> list[dict]:
    from pygltflib import GLTF2

    g = GLTF2.load(str(path))
    return [dict(n.extras) for n in g.nodes if isinstance(n.extras, dict) and "part_id" in n.extras]


def root_extras(path: Path | str) -> dict:
    """Extras of the scene root: pipeline, overrides {part_id: {...}}, part_params {part_id: [P keys]}."""
    from pygltflib import GLTF2

    g = GLTF2.load(str(path))
    root = g.nodes[g.scenes[g.scene or 0].nodes[0]] if g.scenes and g.nodes else None
    return dict(root.extras) if root is not None and isinstance(root.extras, dict) else {}


def set_extras(path: Path | str, extras: dict[str, dict]) -> None:
    from pygltflib import GLTF2

    g = GLTF2.load(str(path))
    changed = False
    for n in g.nodes:
        if isinstance(n.extras, dict) and n.extras.get("part_id") in extras:
            new = extras[n.extras["part_id"]]
            if new != n.extras:
                n.extras = new
                changed = True
    if changed:
        _atomic_save(g, path)


def stats(path: Path | str) -> dict[str, Any]:
    """Size / triangle / node facts of a GLB (tests, reports)."""
    from pygltflib import GLTF2

    g = GLTF2.load(str(path))
    tris = sum(g.accessors[p.indices].count // 3 for m in g.meshes for p in m.primitives if p.indices is not None)
    return {"bytes": Path(path).stat().st_size, "triangles": tris, "parts": len(read_parts(path)),
            "extensions": list(g.extensionsUsed or []), "finished": is_finished(g)}


__all__ = ["finalize", "recolour", "read_parts", "set_extras", "material_for", "stats", "is_finished", "smooth_normals",
           "PIPELINE", "EXTENSIONS", "linear_to_hex"]


def part_roles(path: Path | str) -> dict[str, list[str]]:
    """part_id → material roles of its mesh children (e.g. {"top_shell": ["body"], "strap": ["fabric"]})."""
    from pygltflib import GLTF2

    g = GLTF2.load(str(path))
    out: dict[str, list[str]] = {}
    for n in g.nodes:
        if isinstance(n.extras, dict) and "part_id" in n.extras:
            out[n.extras["part_id"]] = [_role_of(g.nodes[c].name or "body") for c in (n.children or []) if g.nodes[c].mesh is not None]
    return out


def compose(out_path: Path | str, exterior_path: Path | str, items: list[dict], layer_of: dict[str, str] | None = None,
            skip: set[str] | None = None, replace: dict[str, dict] | None = None) -> list[dict]:
    """Anatomy GLB (W29): the exterior part nodes of `exterior_path` (same part ids, extras with the anatomy layer) +
    internal bodies `items` [{extras: PartMeta, material: material dict, mesh: (pos, nrm, tri) in mm, GLB axes}].
    `skip`: exterior part ids left out; `replace`: part id → {mesh, material?} (e.g. a board hull shown as its laminate).
    Returns the PartMeta of every node written."""
    from pygltflib import GLTF2, Asset, Node, Scene

    g = GLTF2.load(str(exterior_path))
    blob = _blob(g)
    w = _Writer()
    root = Node(name="product", children=[], extras={"pipeline": PIPELINE, "units": "m", "up": "+Y", "anatomy": True})
    w.g.nodes.append(root)
    mat_map: dict[int, int] = {}
    metas: list[dict] = []
    for node in g.nodes:
        if not (isinstance(node.extras, dict) and "part_id" in node.extras):
            continue
        pid = node.extras["part_id"]
        if skip and pid in skip:
            continue
        t = np.array(node.translation or [0.0, 0.0, 0.0])
        pnode = Node(name=pid, translation=[float(x) for x in t], children=[])
        extras = dict(node.extras)
        if layer_of and pid in layer_of:
            extras["layer_id"] = layer_of[pid]
        rep = (replace or {}).get(pid)
        if rep is not None:
            pos, nrm, tri = rep["mesh"]
            pos = pos / 1000.0 - t
            mi = len(w.g.materials)
            w.g.materials.append(_gltf_material(rep["material"]))
            me = w.mesh(f"{rep['material']['role']}.1", pos, nrm, tri, mi)
            w.g.nodes.append(Node(name=f"{rep['material']['role']}.1", mesh=me))
            pnode.children.append(len(w.g.nodes) - 1)
            extras.update(rep.get("extras") or {})
        else:
            for c in node.children or []:
                child = g.nodes[c]
                if child.mesh is None:
                    continue
                for prim in g.meshes[child.mesh].primitives:
                    pos = _accessor(g, blob, prim.attributes.POSITION)[:, :3]
                    nrm = _accessor(g, blob, prim.attributes.NORMAL)[:, :3]
                    tri = _accessor(g, blob, prim.indices).reshape(-1, 3)
                    if prim.material not in mat_map:
                        mat_map[prim.material] = len(w.g.materials)
                        w.g.materials.append(g.materials[prim.material])
                    me = w.mesh(child.name or "body.1", pos, nrm, tri, mat_map[prim.material])
                    w.g.nodes.append(Node(name=child.name or "body.1", mesh=me))
                    pnode.children.append(len(w.g.nodes) - 1)
        pnode.extras = extras
        metas.append(extras)
        w.g.nodes.append(pnode)
        root.children.append(len(w.g.nodes) - 1)
    for it in items:
        pos, nrm, tri = it["mesh"]
        pos = pos / 1000.0
        lo, hi = pos.min(axis=0), pos.max(axis=0)
        c = (lo + hi) / 2
        mi = len(w.g.materials)
        w.g.materials.append(_gltf_material(it["material"]))
        label = f"{it['material']['role']}.1"
        me = w.mesh(label, pos - c, nrm, tri, mi)
        w.g.nodes.append(Node(name=label, mesh=me))
        ex = dict(it["extras"])
        ex["measured_bbox_mm"] = [round(float(v) * 1000, 2) for v in hi - lo]
        ex["centroid_mm"] = [round(float(v) * 1000, 2) for v in c]
        w.g.nodes.append(Node(name=ex["part_id"], translation=[float(x) for x in c], children=[len(w.g.nodes) - 1], extras=ex))
        root.children.append(len(w.g.nodes) - 1)
        metas.append(ex)
    w.g.scenes = [Scene(name="anatomy", nodes=[0])]
    w.g.scene = 0
    used = set(g.extensionsUsed or [])
    for m in w.g.materials:
        used |= set((m.extensions or {}).keys())
    w.g.extensionsUsed = sorted(used)
    w.g.asset = Asset(version="2.0", generator="PhysicalLovableX W29 anatomy (illustrative internal layout — not a routed PCB)",
                      extras={"pipeline": PIPELINE, "units": "m", "up": "+Y", "anatomy": True})
    w.save(Path(out_path))
    return metas


def part_mesh(path: Path | str, part_id: str) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    """(pos mm, nrm, tri) of one part of a finished GLB, in GLB axes (world)."""
    from pygltflib import GLTF2

    g = GLTF2.load(str(path))
    blob = _blob(g)
    for node in g.nodes:
        if isinstance(node.extras, dict) and node.extras.get("part_id") == part_id:
            t = np.array(node.translation or [0.0, 0.0, 0.0])
            ps, ns, ts, base = [], [], [], 0
            for c in node.children or []:
                ch = g.nodes[c]
                if ch.mesh is None:
                    continue
                for prim in g.meshes[ch.mesh].primitives:
                    p = _accessor(g, blob, prim.attributes.POSITION)[:, :3] + t
                    ps.append(p * 1000.0)
                    ns.append(_accessor(g, blob, prim.attributes.NORMAL)[:, :3])
                    ts.append(_accessor(g, blob, prim.indices).reshape(-1, 3) + base)
                    base += len(p)
            if ps:
                return np.concatenate(ps), np.concatenate(ns), np.concatenate(ts)
    return None


def part_areas(path: Path | str) -> dict[str, float]:
    """part_id → surface area in mm² (triangles of its meshes) — shell-mass estimates (W29b)."""
    from pygltflib import GLTF2

    g = GLTF2.load(str(path))
    blob = _blob(g)
    out: dict[str, float] = {}
    for node in g.nodes:
        if not (isinstance(node.extras, dict) and "part_id" in node.extras):
            continue
        a = 0.0
        for c in node.children or []:
            ch = g.nodes[c]
            if ch.mesh is None:
                continue
            for prim in g.meshes[ch.mesh].primitives:
                p = _accessor(g, blob, prim.attributes.POSITION)[:, :3] * 1000.0
                t = _accessor(g, blob, prim.indices).reshape(-1, 3)
                a += float(np.linalg.norm(np.cross(p[t[:, 1]] - p[t[:, 0]], p[t[:, 2]] - p[t[:, 0]]), axis=1).sum() / 2)
        out[node.extras["part_id"]] = a
    return out
