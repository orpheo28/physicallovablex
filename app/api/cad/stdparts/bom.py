"""Hardware BOM lines from placed standard parts (C1, CAD_DETAIL_LEVEL=pro).

    bom_lines(parts) -> [{"key", "part", "standard", "qty", "unit_price_usd", "price_label", "labels", …}]
    bom_items(lines, prefix="hw") -> [contracts.artifacts.BOMItem]   # mechanical, unit_cost_est = Estimate
    merge_into(spec_items, lines) -> spec BOM + hardware lines (skips kinds a template row already covers)
    family_lines(name, params) -> lines of a family at pro detail (stage 3 / costs, independent of the env var)
    hardware_names(parts) -> {label: part info}                        # node names for api.cad.glb.finalize

A placed standard part carries `std_meta` (api.cad.stdparts.hardware.StdPart.at). Identical parts (same BOM text)
merge into one line with their count; each line gets a stable id `hw<n>` that is also written on the GLB part nodes
(`bom_item_id`, `unit_price`) so the Studio can link a screw in the viewer to its BOM row.
"""

from __future__ import annotations

import re
from typing import Any

_LAYER = {"fastener": "fasteners", "component": "fasteners", "boss": "fasteners", "rib": "fasteners",
          "snap_fit": "fasteners", "weld_lip": "fasteners", "other": "exterior"}
_PART_ROLE = {"fastener": "fastener", "component": "component", "other": "other", "boss": "other", "rib": "other",
              "snap_fit": "other", "weld_lip": "other"}
_NOUN = {"boss": "Screw bosses", "rib": "Ribs", "snap_fit": "Snap-fit hooks", "weld_lip": "Weld energy director"}


def _meta(p) -> dict | None:
    m = getattr(p, "std_meta", None)
    return m if isinstance(m, dict) and m.get("kind") else None


def bom_lines(parts: list) -> list[dict[str, Any]]:
    lines: dict[str, dict[str, Any]] = {}
    for p in parts:
        m = _meta(p)
        if not m or not m.get("bom"):
            continue
        b = m["bom"]
        row = lines.setdefault(b["part"], {**b, "qty": 0, "labels": [], "size": m.get("size")})
        row["qty"] += 1
        row["labels"].append(p.label or "")
    out = sorted(lines.values(), key=lambda r: (r["kind"], r["part"]))
    for i, r in enumerate(out, 1):
        r["id"] = f"hw{i}"
        r["key"] = re.sub(r"[^a-z0-9]+", "_", r["part"].lower()).strip("_")[:60]
    return out


def bom_items(lines: list[dict[str, Any]], prefix: str = "hw") -> list:
    """BOMItems (category mechanical) — append them to the spec BOM; costs price them from unit_cost_est."""
    from contracts.artifacts import BOMCategory, BOMItem, LabeledValue

    out = []
    for i, r in enumerate(lines, 1):
        out.append(BOMItem(
            id=r.get("id") or f"{prefix}{i}", part=r["part"], category=BOMCategory.mechanical, qty=float(r["qty"]),
            description=f"Standard part ({r['standard']}), counted on the CAD: {r['qty']} placed",
            unit_cost_est=LabeledValue(value=r["unit_price_usd"], unit="USD", label="estimate",
                                       source_or_assumption=r["price_source"])))
    return out


# spec-BOM template rows that already stand for a hardware kind (family_mode.solid_bom): never count it twice
_ALREADY = {"fin_box": r"fin box", "leash_plug": r"leash", "wood_dowel": r"dowel", "cam_lock": r"cam", "wood_screw": r"wood screw",
            "gasket": r"gasket|seal"}


def merge_into(items: list, lines: list[dict[str, Any]]) -> list:
    """Spec BOM `items` + the hardware lines not already represented (same ids as the GLB nodes' bom_item_id)."""
    text = " ".join(str(getattr(i, "part", "")).lower() for i in items)
    keep = [r for r in lines if not (r["kind"] in _ALREADY and re.search(_ALREADY[r["kind"]], text))]
    return list(items) + bom_items(keep)


def family_lines(name: str, params: dict | None = None) -> list[dict[str, Any]]:
    """Hardware BOM lines of a W19/W21 family at pro detail, whatever CAD_DETAIL_LEVEL says (for stage 3 / costs)."""
    from api.cad import families

    mod = families.module(name)
    if not hasattr(mod, "pro_details"):
        return []
    P = families.params_for(name, **(params or {}))
    return bom_lines(mod.pro_details(P, mod.build_parts(P)))


def hardware_names(parts: list) -> dict[str, dict[str, Any]]:
    """label → {part_id, name, role, layer_id, params, source, count, std} for every part with std_meta. Parts of the
    same spec share one node (convention of api.cad.parts: a loop call site is one part, e.g. "M2 × 6 screws ×4")."""
    lines = {r["part"]: r for r in bom_lines(parts)}
    groups: dict[str, list] = {}
    for p in parts:
        m = _meta(p)
        if not m:
            continue
        key = m["bom"]["part"] if m.get("bom") else f"{m['kind']}:{m.get('group', '')}"
        groups.setdefault(key, []).append((p, m))
    out: dict[str, dict[str, Any]] = {}
    used: set[str] = set()
    for items in groups.values():
        m = items[0][1]
        n = len(items)
        if m.get("bom"):
            size = m.get("size") or ""
            ln = f" × {m.get('length_mm', 0):g}" if m.get("length_mm") else ""
            plural = "s" if n > 1 else ""
            what = {"screw": f"{size}{ln} {m.get('head', '')} screw{plural}", "pt_screw": f"{size}{ln} thread-forming screw{plural}",
                    "insert": f"{size} heat-set insert{plural}", "nut": f"{size} nut{plural}", "washer": f"{size} washer{plural}",
                    "bearing": f"Ball bearing{plural} {size}", "dowel_pin": f"Dowel pin{plural} {size}",
                    "wood_dowel": f"Beech dowel{plural} {size}", "wood_screw": f"Wood screw{plural} {size}",
                    "cam_lock": f"Cam lock{plural} (Minifix 15)", "magnet": f"Magnet{plural} {size}", "gear": f"Spur gear{plural} {size}",
                    "tripod_insert": "Tripod socket insert 1/4\"-20", "fin_box": f"Fin box{'es' if n > 1 else ''}", "leash_plug": "Leash plug", "gasket": f"Gasket{plural}"}.get(m["kind"])
            name = what or m["bom"]["part"].split(",")[0].split(" (")[0]
            name = name[0].upper() + name[1:]
            name = f"{name} ×{n}" if n > 1 else name
        else:
            name = m.get("name") or _NOUN.get(m["kind"], m["kind"].replace("_", " ").capitalize())
        pid = re.sub(r"[^a-z0-9]+", "_", name.lower().replace("×", "x")).strip("_") or "hardware"
        base, k = pid, 1
        while pid in used:
            k += 1
            pid = f"{base}_{k}"
        used.add(pid)
        line = lines.get(m["bom"]["part"]) if m.get("bom") else None
        std = {k2: v for k2, v in m.items() if k2 not in ("bom", "dfm")}
        if m.get("dfm"):
            std["dfm"] = m["dfm"]
        if line:
            std.update(bom_item_id=line["id"], unit_price=line["unit_price_usd"], price_label="estimate", qty=line["qty"])
        from api.cad.parts import LAYER_OF_ROLE, ROLES

        mrole = m.get("role", "fastener")
        role = mrole if mrole in ROLES else _PART_ROLE.get(mrole, "other")
        if m.get("bom"):  # purchased hardware (screws, inserts, bearings, gaskets…): the anatomy "fasteners" layer
            layer = "fasteners"
        elif mrole in ROLES and role not in ("fastener", "other"):
            layer = LAYER_OF_ROLE.get(role, "exterior")
        else:
            layer = _LAYER.get(mrole, "fasteners")
        for p, _ in items:
            out[p.label] = {"part_id": pid, "name": name, "role": role, "layer_id": layer,
                            "params": [], "source": "stdparts", "count": n, "std": std}
    return out


def node_extras(info: dict[str, Any]) -> dict[str, Any]:
    """PartMeta fields for the GLB node of a standard part (contracts.PartMeta forbids other keys): BOM link, unit
    price (Estimate), material, and the standard + size in `package` (e.g. "ISO 4762 M3 × 12")."""
    std = info.get("std") or {}
    out: dict[str, Any] = {}
    if std.get("bom_item_id"):
        out["bom_item_id"] = std["bom_item_id"]
        out["unit_price"] = {"value": std.get("unit_price"), "unit": "USD", "label": "estimate",
                             "source_or_assumption": "Catalogue order of magnitude at ~2,000 pcs (Estimate, not a quote)"}
    if std.get("material"):
        out["material"] = std["material"]
    if std.get("standard") and std.get("kind") not in ("boss", "rib", "snap_fit", "weld_lip", "feature"):
        size = str(std.get("size") or "")
        ln = f" × {std['length_mm']:g}" if std.get("length_mm") else ""
        out["package"] = f"{std['standard'].split(' (')[0]} {size}{ln}".strip()
    return out


def root_facts(info: dict[str, Any]) -> dict[str, Any]:
    """Everything we know about a standard part / DFM feature (GLB root extras `stdparts[part_id]`: free-form)."""
    std = {k: v for k, v in (info.get("std") or {}).items() if v is not None}
    return {"name": info["name"], "count": info.get("count", 1), "detail_level": "pro", **std}


__all__ = ["bom_lines", "bom_items", "merge_into", "family_lines", "hardware_names", "node_extras", "root_facts"]
