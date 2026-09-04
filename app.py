"""
app.py — Flask web application for the Face ID & Blockchain Verification Pipeline
"""

import logging
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

from pipeline.orchestrator import run_pipeline

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB upload limit

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "bmp"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    return render_template("index.html")


@app.post("/run")
def run():
    """
    Accept an image upload, run the full pipeline, return JSON results.
    """
    if "image" not in request.files:
        return jsonify({"success": False, "error": "No image file provided"}), 400

    file = request.files["image"]
    if not file.filename or not _allowed(file.filename):
        return jsonify({
            "success": False,
            "error": "Invalid file type. Please upload a JPG, PNG, or WebP image.",
        }), 400

    ext = file.filename.rsplit(".", 1)[1].lower()
    saved_path = UPLOAD_DIR / f"{uuid.uuid4().hex}.{ext}"
    file.save(saved_path)
    logger.info(f"Saved upload: {saved_path}")

    try:
        result = run_pipeline(str(saved_path))
    except Exception as exc:
        logger.exception("Pipeline crashed unexpectedly")
        result = {"success": False, "error": str(exc), "steps": {}}
    finally:
        # Clean up the original upload (cropped face is in tmp_faces/)
        try:
            saved_path.unlink(missing_ok=True)
        except Exception:
            pass

    return jsonify(result)


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=5000, debug=debug)
