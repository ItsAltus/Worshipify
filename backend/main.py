'''
FastAPI Entry Point
Contains FastAPI methods and references to external functions
'''

import os
from fastapi import FastAPI
from typing import Optional, Dict
from services.spotify import *
from services.lastfm import *

TEMP_DIR = "temp"
TEMP_BASE_FILENAME = "audio"

app = FastAPI()

@app.get("/")
def home():
    """Health check endpoint returning a basic running message."""
    return {"message": "Worshipify Backend is Running!"}

def _process_single(song: str, artist: str, idx: int) -> Dict:
    """Process a single song through search, download and tagging pipeline."""
    details = search_song(song, artist)
    base_no_ext = os.path.join(TEMP_DIR, f"{TEMP_BASE_FILENAME}_{idx}")

    paths = download_audio(details["yt_url"], base_no_ext)

    raw_feature_dicts = extract_features(paths)
    segments = [normalize_features(feats) for feats in raw_feature_dicts]
    avg = merge_segments(segments)

    tags = get_tags_for_song(details["title"], details["artist"])

    return {
        "secular_song_info": details,
        "audio_features": {"average": avg, "segments": segments},
        "tags": tags,
    }

@app.get("/search") # Visit http://127.0.0.1:8000/search?song_name=your_secular_song_name&artist_name=songs_artist_name (artist optional)
def search(song: str, artist: Optional[str] = None):
    """Public endpoint for analysing a song and returning metadata."""
    os.makedirs(TEMP_DIR, exist_ok=True)

    try:
        result = _process_single(song, artist or "", idx=0)
    except Exception as err:
        print("❌ Error:", err)
        return {"error": str(err)}
    finally:
        try:
            for fn in os.listdir(TEMP_DIR):
                os.remove(os.path.join(TEMP_DIR, fn))
            os.rmdir(TEMP_DIR)
        except Exception:
            pass

    return result

@app.get("/help")
def docs():
    """Simple helper pointing users to the automatic API docs."""
    return {"message": "Visit /docs for API documentation."}
