"""
orchestrator.py
===============
Ties all three pipeline stages together into a single run_pipeline() call.

Pipeline:
  1. Face Detection  (face_detector.py)
  2. Web/Social Search  (web_searcher.py)
  3. Blockchain Store + Verify  (blockchain_verifier.py)

Each stage's result is collected under result["steps"][stage_name].
On any hard failure the pipeline stops early and sets result["error"].
"""

import base64
import logging
import os
import time

from .face_detector       import detect_and_encode_face
from .web_searcher        import search_face_on_web
from .blockchain_verifier import store_on_chain, verify_on_chain

logger = logging.getLogger(__name__)


def _encode_image_b64(path: str) -> str | None:
    """Read an image file and return a data-URI string for embedding in JSON/HTML."""
    try:
        with open(path, "rb") as fh:
            data = base64.b64encode(fh.read()).decode()
        ext = os.path.splitext(path)[1].lstrip(".").lower() or "jpeg"
        return f"data:image/{ext};base64,{data}"
    except Exception:
        return None


def run_pipeline(image_path: str) -> dict:
    """
    Execute the full Face ID → Web Search → Blockchain pipeline.

    Parameters
    ----------
    image_path : absolute or relative path to the input face image

    Returns
    -------
    {
      "success": bool,
      "error":   str | None,
      "duration_seconds": float,
      "steps": {
        "face_detection":    {...},
        "web_search":        {...},
        "blockchain_store":  {...},
        "blockchain_verify": {...},
      }
    }
    """
    t_start = time.time()
    result = {
        "success": False,
        "error":   None,
        "duration_seconds": 0,
        "steps": {},
    }

    # -------------------------------------------------------------------------
    # Stage 1 — Face Detection
    # -------------------------------------------------------------------------
    logger.info("=== Stage 1: Face Detection ===")
    face_result = detect_and_encode_face(image_path)

    # Attach a base64 preview of the cropped face for the frontend
    if face_result.get("success") and face_result.get("cropped_path"):
        face_result["cropped_b64"] = _encode_image_b64(face_result["cropped_path"])

    result["steps"]["face_detection"] = face_result

    if not face_result["success"]:
        result["error"] = face_result.get("error", "Face detection failed")
        result["duration_seconds"] = round(time.time() - t_start, 2)
        return result

    # -------------------------------------------------------------------------
    # Stage 2 — Web / Social Media Search
    # -------------------------------------------------------------------------
    logger.info("=== Stage 2: Web/Social Media Search ===")
    search_result = search_face_on_web(
        face_result["cropped_path"],
        face_result["encoding"],
    )
    result["steps"]["web_search"] = search_result

    if not search_result["success"]:
        result["error"] = search_result.get("error", "Web search failed")
        result["duration_seconds"] = round(time.time() - t_start, 2)
        return result

    # -------------------------------------------------------------------------
    # Stage 3a — Blockchain: Store
    # -------------------------------------------------------------------------
    logger.info("=== Stage 3a: Blockchain Store ===")
    best = search_result["best_match"]
    content_data = {
        "url":           best["link"],
        "title":         best["title"],
        "source":        best["source"],
        "similarity":    best["similarity"],
        "search_image":  search_result["hosted_url"],
        "searched_at":   int(time.time()),
    }
    store_result = store_on_chain(content_data)
    result["steps"]["blockchain_store"] = store_result

    # -------------------------------------------------------------------------
    # Stage 3b — Blockchain: Verify
    # -------------------------------------------------------------------------
    if store_result.get("success") and store_result.get("content_hash"):
        logger.info("=== Stage 3b: Blockchain Verify ===")
        verify_result = verify_on_chain(store_result["content_hash"])
        result["steps"]["blockchain_verify"] = verify_result

    result["success"] = store_result.get("success", False)
    result["duration_seconds"] = round(time.time() - t_start, 2)
    return result
