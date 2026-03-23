import os
os.environ.setdefault("PYGLET_HEADLESS", "true")

import base64
import tempfile
import io

from typing import Any, Dict, List, Tuple
from utils.logging_utils import get_logger

logger = get_logger(__name__)

PREVIEW_SUPPORTED_EXT = {".stl", ".stp", ".step"}

def b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")

def png_placeholder(size: int, text: str = "preview unavailable") -> bytes:
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (size, size), (240, 240, 240))
    d = ImageDraw.Draw(img)
    msg = text[:120]
    d.text((12, size // 2 - 10), msg, fill=(60, 60, 60))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def render_trimesh_headless(mesh, size: int) -> bytes:
    import trimesh
    scene = mesh.scene() if hasattr(mesh, "scene") else trimesh.Scene(mesh)
    png = scene.save_image(resolution=(size, size), visible=False)
    if png is None:
        raise RuntimeError("trimesh.save_image returned None (no headless context)")
    return png

def render_previews_soft(mesh, size: int, views: int = 1) -> Tuple[List[bytes], Dict[str, Any]]:
    """
    Soft preview generation:
    - never raises
    - returns at least 1 PNG (placeholder if needed)
    """
    meta: Dict[str, Any] = {
        "backend": None,
        "errors": [],
        "views_requested": views,
        "views_generated": 0,
    }

    images: List[bytes] = []

    try:
        png = render_trimesh_headless(mesh, size)
        images = [png]
        meta["backend"] = "trimesh_pyglet_headless"
        meta["views_generated"] = 1
        return images, meta
    except Exception as e:
        meta["errors"].append({"backend": "trimesh_pyglet_headless", "error": repr(e)})

    # Final fallback: placeholder (always)
    images = [png_placeholder(size, "preview unavailable (headless render failed)")]
    meta["backend"] = "placeholder"
    meta["views_generated"] = 1
    return images, meta

def render_mesh_to_png_bytes(mesh, size: int, angles) -> bytes:
    """Render a trimesh mesh to PNG bytes (headless-friendly where possible)."""
    import trimesh

    scene = trimesh.Scene([mesh])
    logger.info("scene is made")
    # distance heuristic based on mesh bounds
    try:
        extents = mesh.extents
        max_dim = float(max(extents)) if extents is not None else 1.0
        distance = max(2.0, max_dim * 1.8)
    except Exception:
        distance = 2.0

    scene.set_camera(angles=angles, distance=distance)
    logger.info("camera is set")

    try:
        png = scene.save_image(resolution=(size, size), visible=False)
        if png is None:
            raise RuntimeError("trimesh scene.save_image() returned None")
    except Exception as e:
        return png_placeholder(size)
    logger.info("png is saved")
    return png

def load_mesh_from_uploaded_file(file_bytes: bytes, ext: str):
    """Load STL/STEP as a trimesh.Trimesh (STEP via CadQuery -> STL -> trimesh)."""
    ext = ext.lower()
    if ext == ".stl":
        import trimesh
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=True) as tf:
            tf.write(file_bytes)
            tf.flush()
            mesh = trimesh.load(tf.name, force="mesh")
        # trimesh may return a Scene; unify
        if hasattr(mesh, "dump"):
            # Scene
            mesh = mesh.dump(concatenate=True)
        return mesh

    if ext in {".stp", ".step"}:
        import cadquery as cq
        from cadquery import importers, exporters
        import trimesh
        import os

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tf_step:
            tf_step.write(file_bytes)
            tf_step.flush()
            step_path = tf_step.name

        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tf_stl:
            stl_path = tf_stl.name

        try:
            model = importers.importStep(step_path)
            exporters.export(model, stl_path, exportType=exporters.ExportTypes.STL)

            if not os.path.exists(stl_path) or os.path.getsize(stl_path) == 0:
                raise RuntimeError("CadQuery STL export produced empty file")

            mesh = trimesh.load(stl_path, force="mesh")
            if hasattr(mesh, "dump"):
                mesh = mesh.dump(concatenate=True)
            return mesh
        finally:
            for p in (step_path, stl_path):
                try:
                    os.unlink(p)
                except Exception:
                    pass

    raise ValueError(f"Unsupported extension: {ext}")

def generate_preview_images_sync(file_bytes: bytes, ext: str, size: int, views: int) -> list[bytes]:
    """CPU-bound preview generation (run in threadpool)."""
    import math
    mesh = load_mesh_from_uploaded_file(file_bytes, ext)

    # A few canonical camera angles (radians): iso + yaw variations
    angle_bank = [
        (0.65, 0.75, 0.0),      # iso-ish
        (0.35, 1.75, 0.0),      # rotated
        (0.20, 2.55, 0.0),      # more rotated
        (1.10, 0.20, 0.0),      # top-ish
    ]
    views = max(1, min(int(views), len(angle_bank)))
    out = []
    for i in range(views):
        out.append(render_mesh_to_png_bytes(mesh, size=size, angles=angle_bank[i]))
    return out