"""
face_detector.py
================
Step 1 of the pipeline: detect a face in the input image, crop it with padding,
and return the face encoding (128-d vector) for downstream similarity matching.

Dependencies: face_recognition (wraps dlib), Pillow
"""

import logging
import os
import uuid
from typing import Optional

import face_recognition
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Temp directory for cropped face images (gitignored)
_TMP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp_faces")


def detect_and_encode_face(image_path: str) -> dict:
    """
    Detect the primary face in *image_path*, crop it, and compute its encoding.

    Returns a dict with:
      success        (bool)
      cropped_path   (str)   — path to the saved cropped face image
      encoding       (list)  — 128-element face encoding (serialisable as JSON)
      face_location  (tuple) — (top, right, bottom, left) in pixels
      face_count     (int)   — total faces detected in image
      error          (str)   — populated only on failure
    """
    os.makedirs(_TMP_DIR, exist_ok=True)

    try:
        logger.info(f"Loading image: {image_path}")
        image = face_recognition.load_image_file(image_path)

        # HOG model is fast and works well for clean frontal photos
        face_locations = face_recognition.face_locations(image, model="hog")

        if not face_locations:
            return {
                "success": False,
                "error": "No face detected in the image. "
                         "Please upload a clear photo with a visible face.",
            }

        face_count = len(face_locations)
        if face_count > 1:
            logger.info(f"{face_count} faces found — using the largest one")
            # Pick largest face (highest pixel area)
            face_locations.sort(
                key=lambda loc: (loc[2] - loc[0]) * (loc[1] - loc[3]), reverse=True
            )

        face_location = face_locations[0]  # (top, right, bottom, left)

        encodings = face_recognition.face_encodings(image, [face_location])
        if not encodings:
            return {
                "success": False,
                "error": "Face detected but could not generate encoding. "
                         "Try a clearer, better-lit photo.",
            }

        encoding: np.ndarray = encodings[0]

        # Crop face with padding so the image is useful for reverse search
        top, right, bottom, left = face_location
        h, w = image.shape[:2]
        pad = max(30, int((bottom - top) * 0.3))
        top    = max(0, top - pad)
        left   = max(0, left - pad)
        bottom = min(h, bottom + pad)
        right  = min(w, right + pad)

        face_img = Image.fromarray(image[top:bottom, left:right])
        cropped_path = os.path.join(_TMP_DIR, f"face_{uuid.uuid4().hex[:8]}.jpg")
        face_img.save(cropped_path, "JPEG", quality=92)
        logger.info(f"Cropped face saved: {cropped_path}")

        return {
            "success":       True,
            "cropped_path":  cropped_path,
            "encoding":      encoding.tolist(),   # JSON-serialisable
            "face_location": face_location,
            "face_count":    face_count,
        }

    except Exception as exc:
        logger.exception("Unexpected error in face detection")
        return {"success": False, "error": str(exc)}
