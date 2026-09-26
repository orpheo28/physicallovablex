import type { DesignDirection } from "@/types/contracts";

/** Full-product GLB of a design direction (not the enclosure shells). */
export function directionGlb(projectId: string, d: Pick<DesignDirection, "id" | "glb_url"> | null | undefined, directionId?: string) {
  if (d?.glb_url) return d.glb_url;
  const id = d?.id ?? directionId;
  return id ? `/files/${projectId}/${id}.glb` : null;
}

/** AI concept render of a direction (illustrative — not the CAD); null until one was generated. */
export function directionRender(d: Pick<DesignDirection, "render_url">) {
  return d.render_url ?? null;
}

/** Still rendered from the CAD model, when the pipeline produced one. */
export function directionHero(projectId: string, directionId: string) {
  return `/files/${projectId}/hero_${directionId}.png`;
}
