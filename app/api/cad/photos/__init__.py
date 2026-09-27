"""AI product photography (W27): reference-based photos of OUR CAD + e-commerce listing kit. Doc: docs/PHOTOGRAPHY.md.

- shots.py  — shot library (hero_studio, packshot_white, lifestyle, in_hand_scale, detail_macro) + category → scene table
- engine.py — render_product_photo(project_id, version, shot, reference_png), reference lookup, labels, jobs, stage 13
- routes.py — register(router): POST /projects/{id}/versions/{n}/photo, POST /projects/{id}/photos/kit, GET /projects/{id}/photos
"""
