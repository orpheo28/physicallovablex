import * as THREE from "three";
import { toCreasedNormals } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import type { PartMeta } from "@/lib/parts";
import type { SceneInfo, SceneNode } from "@/lib/partsMock";

/**
 * A loaded product, ready for the stage: cloned (the GLB cache is shared), turned +Y up, centred on its bbox,
 * one entry per part (W29 node extras, or the root's children for an older GLB).
 */
export type PartNode = {
  id: string;
  object: THREE.Object3D;
  meshes: THREE.Mesh[];
  /** The object's own position at load; explode offsets are added to it. */
  base: THREE.Vector3;
  /** World (centred) → the object's parent frame, rotation only. */
  toLocal: THREE.Quaternion;
  /** Material of each mesh as loaded (cloned per viewer, so previews never leak into the cache). */
  orig: Map<THREE.Mesh, THREE.Material | THREE.Material[]>;
  meta: PartMeta | null;
  synthetic: boolean;
  /** Current explode offset (world, metres), damped toward its target every frame. */
  offset: THREE.Vector3;
  centroid: THREE.Vector3;
  /** The centroid in the object's own frame (labels hang from it). */
  local: THREE.Vector3;
  radius: number;
};

export type Indexed = { root: THREE.Group; parts: Map<string, PartNode>; info: SceneInfo; legacy: boolean; radius: number; size: THREE.Vector3; center: THREE.Vector3 };

type GLTFLike = { scene: THREE.Object3D; parser: { json: { nodes?: { name?: string; extras?: Record<string, unknown> }[] }; associations: Map<object, { nodes?: number }> } };

const hex = (c: THREE.Color) => `#${c.getHexString().toUpperCase()}`;

/** Build the stage's copy of a GLB. Older GLBs (no PartMeta extras) come from a Z-up CAD export: they are stood up. */
export function indexGltf(gltf: GLTFLike): Indexed {
  const json = gltf.parser.json;
  // Tag the originals with their glTF node name (the loader sanitises names), so the clone keeps it in userData.
  gltf.scene.traverse((o) => {
    const idx = gltf.parser.associations.get(o)?.nodes;
    if (idx !== undefined && json.nodes?.[idx]?.name) o.userData.__node = json.nodes[idx].name;
  });
  const clone = gltf.scene.clone(true);
  let withMeta = 0;
  clone.traverse((o) => void (typeof o.userData.part_id === "string" && withMeta++));
  const legacy = withMeta === 0;

  const root = new THREE.Group();
  const orient = new THREE.Group();
  if (legacy) orient.rotation.x = -Math.PI / 2;
  orient.add(clone);
  root.add(orient);
  root.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(orient);
  // Older GLBs are centred on their bbox; W29 GLBs keep their own frame (the anatomy cameras are written in it).
  const center = legacy ? new THREE.Vector3() : box.getCenter(new THREE.Vector3());
  if (legacy) orient.position.sub(box.getCenter(new THREE.Vector3()));
  root.updateMatrixWorld(true);

  // Part nodes: every node carrying a part_id; else the product root's direct children (or each mesh).
  let candidates: THREE.Object3D[] = [];
  if (!legacy) clone.traverse((o) => typeof o.userData.part_id === "string" && candidates.push(o));
  else {
    let top: THREE.Object3D = clone;
    while (top.children.length === 1 && !(top.children[0] as THREE.Mesh).isMesh && top.children[0].children.length) top = top.children[0];
    candidates = top.children.length ? [...top.children] : [top];
  }

  const parts = new Map<string, PartNode>();
  const nodes: SceneNode[] = [];
  const q = new THREE.Quaternion();
  for (const o of candidates) {
    const meshes: THREE.Mesh[] = [];
    o.traverse((m) => (m as THREE.Mesh).isMesh && meshes.push(m as THREE.Mesh));
    if (!meshes.length) continue;
    const id = legacy ? String(o.userData.__node ?? o.name ?? `part_${parts.size + 1}`) : String(o.userData.part_id);
    if (parts.has(id)) continue;
    const orig = new Map<THREE.Mesh, THREE.Material | THREE.Material[]>();
    for (const m of meshes) {
      m.material = Array.isArray(m.material) ? m.material.map((x) => x.clone()) : m.material.clone();
      orig.set(m, m.material);
      smoothIfFaceted(m);
    }
    const b = new THREE.Box3().setFromObject(o);
    const s = b.getSize(new THREE.Vector3());
    const c = b.getCenter(new THREE.Vector3());
    (o.parent ?? root).getWorldQuaternion(q);
    const mat = (Array.isArray(meshes[0].material) ? meshes[0].material[0] : meshes[0].material) as THREE.MeshStandardMaterial;
    const meta = legacy ? null : (o.userData as unknown as PartMeta);
    parts.set(id, {
      id,
      object: o,
      meshes,
      base: o.position.clone(),
      toLocal: q.clone().invert(),
      orig,
      meta,
      synthetic: false,
      offset: new THREE.Vector3(),
      centroid: c,
      local: o.worldToLocal(c.clone()),
      radius: s.length() / 2,
    });
    nodes.push({ id, raw: id, material: mat?.name ?? "", colour: mat?.color ? hex(mat.color) : "#CCCCCC", bbox: [s.x * 1000, s.y * 1000, s.z * 1000], centroid: [c.x * 1000, c.y * 1000, c.z * 1000] });
  }
  const size = box.getSize(new THREE.Vector3());
  return { root, parts, info: { nodes, bbox: [size.x * 1000, size.y * 1000, size.z * 1000] }, legacy, radius: size.length() / 2, size, center };
}

/** CAD tessellations sometimes arrive with one normal per triangle: re-smooth them with a 30° crease angle. */
function smoothIfFaceted(m: THREE.Mesh) {
  const g = m.geometry as THREE.BufferGeometry;
  const n = g.getAttribute("normal");
  if (!n) {
    m.geometry = toCreasedNormals(g, Math.PI / 6);
    return;
  }
  if (g.index || n.count < 30) return;
  let flat = 0;
  const tris = Math.min(200, Math.floor(n.count / 3));
  for (let t = 0; t < tris; t++) {
    const i = t * 3;
    const same = (a: number, b: number) => n.getX(a) === n.getX(b) && n.getY(a) === n.getY(b) && n.getZ(a) === n.getZ(b);
    if (same(i, i + 1) && same(i, i + 2)) flat++;
  }
  if (flat / tris > 0.9) m.geometry = toCreasedNormals(g, Math.PI / 6);
}

/** Meshes for anatomy parts that the loaded GLB does not contain (the local illustrative internals). */
export function addSynthetic(ix: Indexed, metas: PartMeta[]) {
  for (const p of metas) {
    if (ix.parts.has(p.part_id)) continue;
    const [x, y, z] = p.measured_bbox_mm.map((v) => Math.max(v, 0.2) / 1000);
    const round = p.role === "battery" ? Math.min(x, y, z) * 0.35 : p.role === "pcb" ? 0 : Math.min(x, y, z) * 0.12;
    const geo = p.role === "motor" ? new THREE.CylinderGeometry(x / 2, x / 2, y, 40) : roundedBox(x, y, z, round);
    const material = new THREE.MeshPhysicalMaterial({
      color: new THREE.Color(p.colour_hex),
      roughness: p.role === "battery" ? 0.38 : p.role === "pcb" ? 0.55 : p.role === "motor" ? 0.3 : 0.42,
      metalness: p.role === "battery" || p.role === "motor" ? 0.75 : p.role === "connector" ? 1 : 0.05,
      clearcoat: p.role === "pcb" ? 0.6 : p.role === "component" ? 0.3 : 0,
      clearcoatRoughness: 0.35,
    });
    const mesh = new THREE.Mesh(geo, material);
    mesh.name = p.part_id;
    mesh.position.set(p.centroid_mm[0] / 1000, p.centroid_mm[1] / 1000, p.centroid_mm[2] / 1000);
    ix.root.add(mesh);
    const orig = new Map<THREE.Mesh, THREE.Material | THREE.Material[]>([[mesh, material]]);
    ix.parts.set(p.part_id, {
      id: p.part_id,
      object: mesh,
      meshes: [mesh],
      base: mesh.position.clone(),
      toLocal: new THREE.Quaternion(),
      orig,
      meta: p,
      synthetic: true,
      offset: new THREE.Vector3(),
      centroid: mesh.position.clone(),
      local: new THREE.Vector3(),
      radius: Math.hypot(x, y, z) / 2,
    });
  }
}

function roundedBox(w: number, h: number, d: number, r: number) {
  if (r <= 0) return new THREE.BoxGeometry(w, h, d);
  const s = new THREE.Shape();
  const x = -w / 2;
  const z = -d / 2;
  r = Math.min(r, w / 2, d / 2);
  s.moveTo(x + r, z);
  s.lineTo(x + w - r, z);
  s.quadraticCurveTo(x + w, z, x + w, z + r);
  s.lineTo(x + w, z + d - r);
  s.quadraticCurveTo(x + w, z + d, x + w - r, z + d);
  s.lineTo(x + r, z + d);
  s.quadraticCurveTo(x, z + d, x, z + d - r);
  s.lineTo(x, z + r);
  s.quadraticCurveTo(x, z, x + r, z);
  const bevel = Math.min(r * 0.5, h * 0.25);
  const g = new THREE.ExtrudeGeometry(s, { depth: Math.max(h - 2 * bevel, h * 0.2), bevelEnabled: true, bevelThickness: bevel, bevelSize: bevel * 0.8, bevelSegments: 3, curveSegments: 6 });
  g.rotateX(Math.PI / 2);
  g.center();
  return g;
}

/** X-ray shell: faint body, brighter fresnel edge (12-18 % at face-on). */
export function xrayMaterial(dark: boolean) {
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    uniforms: { color: { value: new THREE.Color(dark ? "#C9D2DC" : "#4A4946") }, base: { value: dark ? 0.02 : 0.1 }, edge: { value: dark ? 0.17 : 0.38 } },
    vertexShader: `varying vec3 vN; varying vec3 vV;
      void main(){ vec4 mv = modelViewMatrix * vec4(position, 1.0); vV = normalize(-mv.xyz); vN = normalize(normalMatrix * normal); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `uniform vec3 color; uniform float base; uniform float edge; varying vec3 vN; varying vec3 vV;
      void main(){ float f = pow(1.0 - abs(dot(normalize(vN), normalize(vV))), 2.2); gl_FragColor = vec4(color, base + f * edge); }`,
  });
}

/** Roles that form the outside of the product (ghosted in X-ray). */
export const SHELL_ROLES = new Set(["shell_top", "shell_bottom", "strap", "frame", "window", "lens", "diffuser", "button", "arm", "other"]);

export function isShell(p: PartNode): boolean {
  if (p.synthetic) return false;
  const m = p.meta;
  if (!m) return true;
  return m.label === "measured" || SHELL_ROLES.has(m.role);
}

/** Critically damped step toward `to` (frame-rate independent). Returns true while still moving. */
export function dampV(v: THREE.Vector3, to: THREE.Vector3, lambda: number, dt: number, eps: number): boolean {
  const k = 1 - Math.exp(-lambda * dt);
  v.lerp(to, k);
  if (v.distanceTo(to) < eps) {
    v.copy(to);
    return false;
  }
  return true;
}
