"""Tiny numpy mesh primitives for the anatomy bodies (W29). Units mm, GLB axes (+Y up); returned arrays are
(positions, normals, triangles) with hard edges on boxes and smooth sides on cylinders."""

from __future__ import annotations

import math

import numpy as np


def box(size, centre) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    sx, sy, sz = (max(float(v), 0.05) / 2 for v in size)
    cx, cy, cz = (float(v) for v in centre)
    faces = [((1, 0, 0), [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)]),
             ((-1, 0, 0), [(-1, -1, 1), (-1, 1, 1), (-1, 1, -1), (-1, -1, -1)]),
             ((0, 1, 0), [(-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1)]),
             ((0, -1, 0), [(-1, -1, 1), (-1, -1, -1), (1, -1, -1), (1, -1, 1)]),
             ((0, 0, 1), [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]),
             ((0, 0, -1), [(1, -1, -1), (-1, -1, -1), (-1, 1, -1), (1, 1, -1)])]
    pos, nrm, tri = [], [], []
    for n, quad in faces:
        b = len(pos)
        for x, y, z in quad:
            pos.append((cx + x * sx, cy + y * sy, cz + z * sz))
            nrm.append(n)
        tri += [(b, b + 1, b + 2), (b, b + 2, b + 3)]
    return np.array(pos, float), np.array(nrm, float), np.array(tri, np.int64)


def rounded_slab(size, centre, radius: float, seg: int = 6) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Rounded-rectangle prism (footprint X × Z, thickness Y) — PCBs, pouch cells."""
    sx, sy, sz = (float(v) for v in size)
    r = max(0.0, min(radius, sx / 2 - 0.01, sz / 2 - 0.01))
    if r < 0.05:
        return box(size, centre)
    cx, cy, cz = (float(v) for v in centre)
    ring = []
    for qx, qz, a0 in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ox, oz = qx * (sx / 2 - r), qz * (sz / 2 - r)
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            ring.append((ox + r * math.cos(a), oz + r * math.sin(a), math.cos(a), math.sin(a)))
    n = len(ring)
    pos, nrm, tri = [], [], []
    for yy, ny in ((sy / 2, 1.0), (-sy / 2, -1.0)):  # caps (fan)
        b = len(pos)
        pos.append((cx, cy + yy, cz))
        nrm.append((0, ny, 0))
        for x, z, _, _ in ring:
            pos.append((cx + x, cy + yy, cz + z))
            nrm.append((0, ny, 0))
        for i in range(n):
            j = (i + 1) % n
            tri.append((b, b + 1 + j, b + 1 + i) if ny > 0 else (b, b + 1 + i, b + 1 + j))
    b = len(pos)  # sides
    for x, z, nx, nz in ring:
        pos += [(cx + x, cy + sy / 2, cz + z), (cx + x, cy - sy / 2, cz + z)]
        nrm += [(nx, 0, nz), (nx, 0, nz)]
    for i in range(n):
        j = (i + 1) % n
        a, bb, c, d = b + 2 * i, b + 2 * i + 1, b + 2 * j, b + 2 * j + 1
        tri += [(a, c, bb), (bb, c, d)]
    return np.array(pos, float), np.array(nrm, float), np.array(tri, np.int64)


def cylinder(p0, p1, radius: float, seg: int = 20, caps: bool = True) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Cylinder from p0 to p1 (mm) — cells, motors, cables, coils."""
    a, b = np.array(p0, float), np.array(p1, float)
    axis = b - a
    L = float(np.linalg.norm(axis))
    if L < 1e-6:
        axis, L = np.array([0.0, 1.0, 0.0]), 0.1
        b = a + axis * L
    u = axis / L
    ref = np.array([1.0, 0, 0]) if abs(u[0]) < 0.9 else np.array([0, 0, 1.0])
    e1 = np.cross(u, ref)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(u, e1)
    pos, nrm, tri = [], [], []
    for i in range(seg):
        t = 2 * math.pi * i / seg
        d = math.cos(t) * e1 + math.sin(t) * e2
        pos += [a + d * radius, b + d * radius]
        nrm += [d, d]
    for i in range(seg):
        j = (i + 1) % seg
        tri += [(2 * i, 2 * j, 2 * i + 1), (2 * i + 1, 2 * j, 2 * j + 1)]
    if caps:
        for c, s in ((a, -1.0), (b, 1.0)):
            base = len(pos)
            pos.append(c)
            nrm.append(u * s)
            for i in range(seg):
                t = 2 * math.pi * i / seg
                pos.append(c + (math.cos(t) * e1 + math.sin(t) * e2) * radius)
                nrm.append(u * s)
            for i in range(seg):
                j = (i + 1) % seg
                tri.append((base, base + 1 + i, base + 1 + j) if s > 0 else (base, base + 1 + j, base + 1 + i))
    return np.array(pos, float), np.array(nrm, float), np.array(tri, np.int64)


def merge(*meshes) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ps, ns, ts, base = [], [], [], 0
    for p, n, t in meshes:
        ps.append(p)
        ns.append(n)
        ts.append(t + base)
        base += len(p)
    return np.concatenate(ps), np.concatenate(ns), np.concatenate(ts)
