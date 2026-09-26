"""Disk cap for the deployed volume (Railway trial ≈ 0.5 GB). Owner: W9.

Generated CAD lives in FILES_DIR/<project_id>/ (~5-10 MB each). Keep the MAX_STORED_PROJECTS most recent folders (default 30,
by mtime) and delete the older ones; a pruned project just regenerates its files when stage 2/3 is re-run.
Prebuilt demo files live in the image (api/cad/prebuilt), not here, and `demo_*` / `_*` folders are never touched.
"""

from __future__ import annotations

import logging
import os
import shutil

from api.cad.build import files_root

log = logging.getLogger("housekeeping")


def prune_files(keep: int | None = None) -> list[str]:
    keep = int(os.getenv("MAX_STORED_PROJECTS", "30")) if keep is None else keep
    if keep <= 0:
        return []
    root = files_root()
    if not root.is_dir():
        return []
    dirs = [d for d in root.iterdir() if d.is_dir() and not d.name.startswith(("demo_", "_"))]
    dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    removed = []
    for d in dirs[keep:]:
        try:
            shutil.rmtree(d)
            removed.append(d.name)
        except OSError as e:
            log.warning("could not prune %s: %s", d, e)
    if removed:
        log.info("pruned %d old project file folders (keeping %d)", len(removed), keep)
    return removed
