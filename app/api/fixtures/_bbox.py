"""Measured bounding box of a committed GLB (full product), for the cached examples' stage 3 overall_dimensions.

World-space min/max over every mesh primitive's POSITION accessor (min/max from the file), through the node
transforms (matrix or TRS). glTF is Y-up in metres (build123d export): returned as (length X, width Z, height Y) in mm.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


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


def glb_size_mm(path: Path | str) -> tuple[float, float, float]:
    from pygltflib import GLTF2

    g = GLTF2().load(str(path))
    pts: list[np.ndarray] = []

    def walk(i: int, parent: np.ndarray) -> None:
        node = g.nodes[i]
        m = parent @ _local(node)
        if node.mesh is not None:
            for prim in g.meshes[node.mesh].primitives:
                acc = g.accessors[prim.attributes.POSITION]
                lo, hi = acc.min, acc.max
                for cx in (lo[0], hi[0]):
                    for cy in (lo[1], hi[1]):
                        for cz in (lo[2], hi[2]):
                            pts.append((m @ np.array([cx, cy, cz, 1.0]))[:3])
        for c in node.children or []:
            walk(c, m)

    for root in g.scenes[g.scene or 0].nodes:
        walk(root, np.eye(4))
    a = np.array(pts)
    size = (a.max(axis=0) - a.min(axis=0)) * 1000.0
    return round(float(size[0]), 1), round(float(size[2]), 1), round(float(size[1]), 1)
