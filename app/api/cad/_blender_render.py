"""Hero render of a material GLB with Blender Cycles — "Rendered from the CAD". Owner: W12. Offline only.

    blender -b -P api/cad/_blender_render.py -- <in.glb> <out.png> [size=1600] [samples=128]

Imports the GLB (build123d export: glTF +Y up → Blender Z up, same axes as the CAD), studio 3-point area lighting,
soft contact shadow on a shadow-catcher floor, warm neutral seamless background (#F7F6F3, composited after the
render so there is no horizon line), 3/4 camera auto-framed on the bounding box, Cycles + denoise.
Not in the live path: used to make api/cad/prebuilt/<id>/hero_dN.png. Runs inside Blender's Python only.
"""

from __future__ import annotations

import math
import sys

import bpy  # type: ignore[import-not-found]
import numpy as np
from mathutils import Vector  # type: ignore[import-not-found]

BG_SRGB = (0xF7 / 255, 0xF6 / 255, 0xF3 / 255)


def args() -> tuple[str, str, int, int]:
    a = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(a) < 2:
        raise SystemExit("usage: blender -b -P _blender_render.py -- in.glb out.png [size] [samples]")
    return a[0], a[1], int(a[2]) if len(a) > 2 else 1600, int(a[3]) if len(a) > 3 else 128


def bbox(objs) -> tuple[Vector, Vector]:
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def area_light(name: str, loc: Vector, target: Vector, size: float, power: float, shadow: bool = True) -> None:
    data = bpy.data.lights.new(name, type="AREA")
    data.shape, data.size, data.energy = "DISK", size, power
    data.use_shadow = shadow
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (target - loc).to_track_quat("-Z", "Y").to_euler()


def main() -> None:
    src, out, size, samples = args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    bpy.ops.import_scene.gltf(filepath=src)
    meshes = [o for o in scene.objects if o.type == "MESH"]
    lo, hi = bbox(meshes)
    center, dims = (lo + hi) / 2, hi - lo
    r = max(dims.length / 2, 1e-4)

    # shadow-catcher floor at the lowest point
    bpy.ops.mesh.primitive_plane_add(size=r * 60, location=(center.x, center.y, lo.z))
    bpy.context.active_object.is_shadow_catcher = True

    # camera: 3/4 front-right, slightly above, 70 mm lens, framed on the bounding sphere
    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens, cam_data.sensor_width = 70, 36
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    az, el = math.radians(35), math.radians(24)
    d = Vector((math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el)))
    fov = 2 * math.atan(18 / cam_data.lens)
    dist = r / math.sin(fov / 2) * 1.12
    aim = center + Vector((0, 0, -dims.z * 0.03))
    cam.location = aim + d * dist
    cam.rotation_euler = (aim - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam_data.clip_start, cam_data.clip_end = dist / 100, dist * 100
    scene.camera = cam

    # 3-point lighting, power scaled with distance² so every product size gets the same exposure
    k = dist**2
    def at(az_deg: float, el_deg: float, far: float) -> Vector:
        a, e = math.radians(az_deg), math.radians(el_deg)
        return center + Vector((math.cos(e) * math.sin(a), -math.cos(e) * math.cos(a), math.sin(e))) * dist * far

    area_light("key", at(-40, 45, 0.9), center, r * 2.2, 13 * k)
    area_light("fill", at(70, 20, 1.1), center, r * 3.0, 4 * k)
    area_light("rim", at(170, 50, 1.0), center, r * 1.6, 14 * k, shadow=False)

    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.55, 0.55, 0.54, 1.0)
    bg.inputs[1].default_value = 0.2  # soft ambient + reflections; hidden from camera (transparent film)
    scene.world = world

    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        scene.cycles.device = "GPU"
    except Exception:  # noqa: BLE001 — CPU is fine, just slower
        scene.cycles.device = "CPU"
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:  # noqa: BLE001 — look names differ across Blender versions
        pass
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    tmp = out + ".rgba.png"
    scene.render.filepath = tmp
    bpy.ops.render.render(write_still=True)

    # composite over the seamless background (shadow catcher alpha → soft contact shadow)
    img = bpy.data.images.load(tmp)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    a = px[..., 3:4]
    rgb = px[..., :3] * a + np.array(BG_SRGB, dtype=np.float32) * (1 - a) if not img.alpha_mode == "PREMUL" else px[..., :3] + np.array(BG_SRGB, dtype=np.float32) * (1 - a)
    res = np.concatenate([rgb, np.ones_like(a)], axis=2)
    final = bpy.data.images.new("hero", w, h, alpha=False)
    final.pixels[:] = res.ravel()
    final.filepath_raw = out
    final.file_format = "PNG"
    final.save()
    import os

    os.remove(tmp)
    print(f"hero render → {out} ({w}×{h}, {samples} spp)")


if __name__ == "__main__":
    main()
