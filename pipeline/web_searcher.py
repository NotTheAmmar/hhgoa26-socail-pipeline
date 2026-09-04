"""
web_searcher.py
===============
Step 2 of the pipeline:
  a) Upload the cropped face to imgbb (free temp public URL)
  b) Query SerpAPI Google Lens for visual matches across the web / social media
  c) For each result thumbnail, attempt to detect a face and compute
     cosine similarity to the original encoding — "face match confidence"

Dependencies: serpapi (google-search-results), requests, face_recognition, Pillow
"""

import io
import logging
import os
from typing import Optional

import face_recognition
import numpy as np
import requests
from serpapi import GoogleSearch

logger = logging.getLogger(__name__)

_IMGBB_UPLOAD_URL = "https://api.imgbb.com/1/upload"
_LENS_MATCH_LIMIT = 10   # max results to attempt face-similarity on
_REQUEST_TIMEOUT  = 8    # seconds for thumbnail downloads


# ---------------------------------------------------------------------------
# Image hosting
# ---------------------------------------------------------------------------

def _upload_to_imgbb(image_path: str) -> str:
    """Upload a local image to imgbb; return the public URL."""
    api_key = os.environ.get("IMGBB_API_KEY", "")
    if not api_key:
        raise EnvironmentError("IMGBB_API_KEY is not set in .env")

    with open(image_path, "rb") as fh:
        resp = requests.post(
            _IMGBB_UPLOAD_URL,
            params={"key": api_key},
            files={"image": fh},
            timeout=20,
        )
    resp.raise_for_status()
    data = resp.json()
    url = data["data"]["url"]
    logger.info(f"Image hosted at: {url}")
    return url


# ---------------------------------------------------------------------------
# Face similarity helper
# ---------------------------------------------------------------------------

def _face_similarity(image_url: str, reference_encoding: np.ndarray) -> Optional[float]:
    """
    Download *image_url*, detect the first face, compute Euclidean distance to
    *reference_encoding*, and convert to a 0-100 similarity score.
    Returns None if no face is found or download fails.
    """
    try:
        resp = requests.get(image_url, timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
        img = face_recognition.load_image_file(io.BytesIO(resp.content))
        encodings = face_recognition.face_encodings(img)
        if not encodings:
            return None
        distance = face_recognition.face_distance([reference_encoding], encodings[0])[0]
        # face_recognition uses Euclidean distance; 0.6 is the typical match threshold.
        # We map [0, 1] distance → [100, 0] similarity, clamp to [0, 100].
        similarity = max(0.0, (1.0 - distance)) * 100.0
        return round(similarity, 1)
    except Exception as exc:
        logger.debug(f"Similarity check skipped for {image_url}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Main search function
# ---------------------------------------------------------------------------

def search_face_on_web(image_path: str, face_encoding: list) -> dict:
    """
    Perform a Google Lens reverse-image search for the face in *image_path*.

    Parameters
    ----------
    image_path    : path to the cropped face JPEG
    face_encoding : 128-element list (from face_detector, JSON-serialisable)

    Returns
    -------
    dict with keys:
      success        (bool)
      hosted_url     (str)   — public URL used for the Lens query
      matches        (list)  — list of result dicts (sorted by face similarity)
      best_match     (dict)  — highest-confidence result
      total_matches  (int)
      error          (str)   — only on failure
    """
    # -- 1. Upload to temporary public host ----------------------------------
    logger.info("Uploading face image to imgbb...")
    try:
        hosted_url = _upload_to_imgbb(image_path)
    except Exception as exc:
        return {"success": False, "error": f"Image upload failed: {exc}"}

    # -- 2. Google Lens reverse-image search ----------------------------------
    serpapi_key = os.environ.get("SERPAPI_KEY", "")
    if not serpapi_key:
        return {"success": False, "error": "SERPAPI_KEY is not set in .env"}

    logger.info("Querying Google Lens via SerpAPI...")
    try:
        search = GoogleSearch({
            "engine":  "google_lens",
            "url":     hosted_url,
            "api_key": serpapi_key,
        })
        raw = search.get_dict()
    except Exception as exc:
        return {"success": False, "error": f"SerpAPI request failed: {exc}"}

    visual_matches = raw.get("visual_matches", [])
    if not visual_matches:
        return {
            "success":    False,
            "hosted_url": hosted_url,
            "error":      "Google Lens returned no visual matches. "
                          "Try a clearer, higher-resolution photo.",
        }

    # -- 3. Pre-sort all visual matches to prioritize social media --------------
    # We want to pull actual social media posts from ANYWHERE in the 60+ results to the top
    # BEFORE we limit to the first 10 for expensive face similarity computation.
    SOCIAL_DOMAINS = [
        "instagram.com", "x.com", "twitter.com", "facebook.com",
        "tiktok.com", "linkedin.com", "reddit.com", "threads.net",
        "pinterest.com", "youtube.com"
    ]

    def _is_social_post(url: str) -> bool:
        url_lower = url.lower()
        if not any(domain in url_lower for domain in SOCIAL_DOMAINS):
            return False
        
        # Filter out generic subreddits, profiles, and channels
        if "reddit.com" in url_lower and "/comments/" not in url_lower:
            return False
        if "youtube.com" in url_lower and "/watch" not in url_lower and "/shorts" not in url_lower:
            return False
        if "instagram.com" in url_lower and "/p/" not in url_lower and "/reel/" not in url_lower:
            return False
        if ("x.com" in url_lower or "twitter.com" in url_lower) and "/status/" not in url_lower:
            return False
            
        return True

    # Sort all raw matches: True (social post) comes before False (web/generic)
    visual_matches.sort(key=lambda m: _is_social_post(m.get("link", "")), reverse=True)

    # -- 4. Compute face-similarity for the top results -----------------------
    ref_encoding = np.array(face_encoding)
    matches = []

    for item in visual_matches[:_LENS_MATCH_LIMIT]:
        # Lens provides a small cropped face thumbnail (fast for similarity)
        lens_thumb = item.get("thumbnail", "")
        # But we want to display the actual post image in the UI if available
        post_img = item.get("image") or lens_thumb
        
        similarity = _face_similarity(lens_thumb, ref_encoding) if lens_thumb else None

        matches.append({
            "title":      item.get("title", "Unknown"),
            "link":       item.get("link", ""),
            "source":     item.get("source", ""),
            "thumbnail":  post_img,     # <--- Use the real image for UI
            "similarity": similarity,   # 0-100 or None
        })

    # -- 5. Final Rank and Sort for the processed matches ---------------------
    # Within the processed top 10, ensure social is first, then rank by similarity
    def sort_key(m):
        is_soc = _is_social_post(m["link"])
        sim = m["similarity"] or 0
        return (is_soc, sim)

    matches.sort(key=sort_key, reverse=True)

    # Append any remaining results (beyond LIMIT) without similarity
    for item in visual_matches[_LENS_MATCH_LIMIT:]:
        matches.append({
            "title":      item.get("title", "Unknown"),
            "link":       item.get("link", ""),
            "source":     item.get("source", ""),
            "thumbnail":  item.get("image") or item.get("thumbnail", ""),
            "similarity": None,
        })

    return {
        "success":       True,
        "hosted_url":    hosted_url,
        "matches":       matches,
        "best_match":    matches[0] if matches else None,
        "total_matches": len(visual_matches),
    }
