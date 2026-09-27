"""Shot library for AI product photos (W27). Prompts direct light, surface, lens and framing ONLY.

With a reference image (viewer capture or Blender render of the CAD) the prompt never re-describes the product: the
image carries its identity, the words carry the photography (principles: astorie.ai product-photography prompts,
pebblely.com — name the light source and its quality, a concrete surface, lens, framing, contact shadow, ≤ 3 props).
Every reference prompt ends with PRESERVE. Without a reference (text-only fallback) the product is described from the
design direction (same fields as api/cad/renders.build_prompt) and the same photography directions follow.

    shot_prompt(shot, category, reference=True)        -> prompt text
    fallback_prompt(shot, category, product_text)      -> prompt text (no reference)
    SHOTS[shot].aspect_ratio / .staged                 -> "4:5" | "1:1", staged scene?
"""

from __future__ import annotations

from dataclasses import dataclass

PRESERVE = ("Preserve the exact geometry, proportions, colours, materials and details of the referenced product. "
            "No added text, logos, watermarks or extra objects unless stated.")
PRESERVE_TEXT = ("Keep exactly the proportions, colours and materials described above. "
                 "No added text, logos, watermarks or extra objects unless stated.")


@dataclass(frozen=True)
class Shot:
    key: str
    title: str
    aspect_ratio: str
    staged: bool
    direction: str  # {scene} / {scale} placeholders filled from the category table


SHOTS: dict[str, Shot] = {
    "hero_studio": Shot(
        "hero_studio", "Studio hero", "4:5", False,
        "Re-photograph the product from the reference image as a premium studio hero shot. "
        "Surface: warm paper seamless background (#F4F1EA) sweeping into the floor, no horizon line. "
        "Light: large soft key light from camera left at 45°, bounce fill from the right, a subtle rim light "
        "tracing the top edges; all lights and bounce cards are off-camera, no studio equipment visible. Lens: 100 mm macro look at f/8, the same three-quarter camera angle as the reference, "
        "product centred with generous negative space. Soft natural contact shadow directly under the product. "
        "True-to-life colour, matte surfaces stay matte, crisp edges, vertical 4:5 frame."),
    "packshot_white": Shot(
        "packshot_white", "White packshot", "1:1", False,
        "Marketplace main image of the product from the reference image (Amazon / Shopify compliant). "
        "Surface: pure infinite white seamless background (#FFFFFF), no floor line, no props. "
        "Light: even soft wrap-around light from two large off-camera softboxes left and right plus a top fill, no "
        "hard shadows, only a faint contact shadow. Lens: 85 mm look at f/11, three-quarter view, product centred and filling about "
        "85% of the square 1:1 frame, fully in frame, edge-to-edge sharp."),
    "lifestyle": Shot(
        "lifestyle", "Lifestyle", "4:5", True,
        "Place the product from the reference image in this scene: {scene}. "
        "Light: natural light that belongs to the scene, direction and colour temperature consistent on the product "
        "and its surroundings, realistic shadows grounding it. Lens: 50 mm look at f/2.8, the product in sharp focus at "
        "its real-world scale, the background softly out of focus, calm editorial mood, at most 2-3 props, vertical 4:5 "
        "frame. Stated extra objects: only the scene elements named above; any person is anonymous with no face visible."),
    "in_hand_scale": Shot(
        "in_hand_scale", "In hand / scale", "4:5", True,
        "Show the product from the reference image {scale}, so its real size is obvious. "
        "Hands and forearms only (no face, no body beyond what is stated), natural skin tones, neutral light warm-grey "
        "seamless background. Light: soft window light from camera left with a gentle fill. Lens: 85 mm look at f/4, "
        "the product in sharp focus, vertical 4:5 frame. Stated extra objects: the hands only."),
    "detail_macro": Shot(
        "detail_macro", "Detail macro", "1:1", False,
        "Extreme close-up of a characteristic edge, joint or surface area of the product from the reference image, "
        "showing the material and its texture. Light: soft raking light from the side revealing the finish, a small "
        "specular highlight along one edge. Lens: 100 mm macro at f/2.8, shallow depth of field, the rest of the "
        "product and the warm neutral background falling to a soft blur, square 1:1 frame."),
}

LISTING_KIT = ("packshot_white", "lifestyle", "in_hand_scale", "detail_macro")

# category (api/engineering/category.py pack key) → (lifestyle scene, in-hand / scale action). Scenes name the place and
# light only — never the product.
SCENES: dict[str, tuple[str, str]] = {
    "wearable": ("worn on the wrist of a kitesurfer on a sandy beach at golden hour, kite lines and the sea softly "
                 "blurred behind, wet skin and a few water droplets, no face visible",
                 "worn on a wrist, the hand and forearm only"),
    "furniture_baby": ("a calm Scandinavian nursery in soft morning daylight from a window, pale oak floor, a folded muslin "
                       "blanket and a small green plant nearby, no baby",
                       "with an adult hand resting on its top edge, the forearm only"),
    "vacuum": ("the floor of a bright modern apartment, light oak parquet, the edge of a sofa and a wool rug softly out "
               "of focus, afternoon daylight",
               "with one hand gripping the handle, the forearm only"),
    "solar_roof": ("installed on the pitched clay-tile roof of a white Basque-style house in Biarritz at midday, clear "
                   "blue sky, crisp sunlight",
                   "with a gloved installer's hand resting on the frame, the forearm only"),
    "drone": ("in flight above a rugged Atlantic coastline on a bright afternoon, surf below and a kitesurfer tiny in the "
              "distance, motion-blurred propellers",
              "held in an open palm, the hand only"),
    "irrigation": ("in a small lush garden bed with lavender and lawn, early-morning sun, fine droplets on the leaves",
                   "with one hand adjusting it, the forearm only"),
    "surfboard": ("lying on the sand of a beach at golden hour, gentle waves rolling in behind",
                  "carried under one arm, the body cropped at the shoulders, no face"),
    "hair_dryer": ("a bright modern bathroom vanity, pale marble counter, a folded white towel, soft window light",
                   "held in one hand, the forearm only"),
    "home_robot": ("the floor of a bright family living room with three scattered wooden toys, soft afternoon light",
                   "with an adult hand placing a wooden block next to it, the forearm only"),
    "camera": ("a sunlit café table with a cup of coffee and two blank-backed instant prints lying face down",
               "held in two hands, the hands only"),
    "smartphone": ("a linen tablecloth by a window with a paperback book and a cup of tea, soft morning light, the screen off",
                   "held in one hand, the hand only, screen off"),
    "lighting": ("a calm home-office desk at dusk, warm ambient light, a notebook and a pencil",
                 "with one hand touching its top, the hand only"),
    "tracker": ("a wooden entry table next to a set of keys and a leather wallet, soft daylight",
                "held between two fingers, the hand only"),
    "generic": ("a clean modern living space on a light oak surface, soft natural daylight from a window",
                "held in one hand, the hand only"),
}


def scene_for(category: str | None) -> tuple[str, str]:
    return SCENES.get(category or "generic", SCENES["generic"])


def _fill(shot: Shot, category: str | None) -> str:
    scene, scale = scene_for(category)
    return shot.direction.format(scene=scene, scale=scale)


def shot_prompt(shot: str, category: str | None) -> str:
    """Reference prompt: photography directions only + PRESERVE. Contains no product description."""
    return f"{_fill(SHOTS[shot], category)}\n{PRESERVE}"


def fallback_prompt(shot: str, category: str | None, product_text: str) -> str:
    """Text-only prompt (no reference image): the product described from the design, then the same photography."""
    direction = _fill(SHOTS[shot], category).replace(
        "the same three-quarter camera angle as the reference", "a three-quarter view from slightly above").replace(
        "the product from the reference image", "the product").replace(
        "the reference image", "the description").replace("from the reference", "")
    return f"Professional product photograph. The product: {product_text}\n{direction}\n{PRESERVE_TEXT}"


__all__ = ["SHOTS", "LISTING_KIT", "SCENES", "PRESERVE", "Shot", "scene_for", "shot_prompt", "fallback_prompt"]
