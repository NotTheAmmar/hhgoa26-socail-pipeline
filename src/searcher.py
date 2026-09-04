import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
SOCIAL_DOMAINS = ["x.com", "twitter.com", "instagram.com", "linkedin.com", "reddit.com", "facebook.com"]

def reverse_image_search(image_path, mock=False, mock_file="mock_search.json"):
    """
    Perform a reverse image search using SerpApi Google Lens engine.
    Filters visual_matches to prioritize social media domains.
    """
    if mock:
        print(f"      -> [MOCK] Loading mock data from {mock_file}...")
        if os.path.exists(mock_file):
            with open(mock_file, 'r') as f:
                return json.load(f)
        else:
            # Create a default mock if it doesn't exist
            mock_data = {
                "source_platform": "X",
                "post_url": "https://x.com/example/status/123456789",
                "title": "Example Post about the OSINT investigation",
                "thumbnail_url": "https://example.com/mock_thumb.jpg",
                "timestamp": "2023-10-01"
            }
            with open(mock_file, 'w') as f:
                json.dump(mock_data, f, indent=4)
            return mock_data
            
    if not SERPAPI_KEY:
        raise ValueError("SERPAPI_KEY is not set in the environment.")

    # Upload local image to SerpApi (Google Lens hack via image parameter/url)
    print("      -> Uploading image to SerpApi...")
    with open(image_path, 'rb') as f:
        files = {'image': f}
        upload_resp = requests.post(f"https://serpapi.com/image?api_key={SERPAPI_KEY}", files=files)
    
    upload_resp.raise_for_status()
    image_id = upload_resp.json().get('image_id')
    if not image_id:
        raise ValueError("Failed to get image_id from SerpApi.")
        
    print(f"      -> Search query with image_id: {image_id}")
    params = {
        "engine": "google_lens",
        "image_id": image_id,
        "api_key": SERPAPI_KEY
    }
    
    search_resp = requests.get("https://serpapi.com/search", params=params)
    search_resp.raise_for_status()
    
    result = _filter_results(search_resp.json())
    if result:
        # Save real result as mock file if missing, for later use
        if not os.path.exists(mock_file):
            with open(mock_file, 'w') as f:
                json.dump(result, f, indent=4)
    return result

def _filter_results(data):
    visual_matches = data.get("visual_matches", [])
    if not visual_matches:
        return None
        
    # Prioritize social domains
    for match in visual_matches:
        link = match.get("link", "")
        if any(domain in link for domain in SOCIAL_DOMAINS):
            return {
                "source_platform": _extract_platform(link),
                "post_url": link,
                "title": match.get("title", "Unknown Title"),
                "thumbnail_url": match.get("thumbnail", ""),
                "timestamp": match.get("date", "Unknown") # Timestamp if available
            }
            
    # Fallback to top match
    top_match = visual_matches[0]
    return {
        "source_platform": _extract_platform(top_match.get("link", "")),
        "post_url": top_match.get("link", ""),
        "title": top_match.get("title", "Unknown Title"),
        "thumbnail_url": top_match.get("thumbnail", ""),
        "timestamp": top_match.get("date", "Unknown")
    }

def _extract_platform(url):
    for domain in SOCIAL_DOMAINS:
        if domain in url:
            return domain.split('.')[0].capitalize()
    if "://" in url:
        return url.split("://")[1].split("/")[0].capitalize()
    return "Unknown"
