'''
lastfm genre/tag retrieving
'''

import os
import json
import re
import requests
from services.spotify import *
from dotenv import load_dotenv

load_dotenv()
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
BASE_URL = "http://ws.audioscrobbler.com/2.0/"
GENRES_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "genres.txt")

_nonword_re = re.compile(r"[^\w]+")
_word_re    = re.compile(r"\w+")

def _load_genre_filter():
    """Load allowed genre keywords from ``genres.txt``."""
    genre_filters = set()
    with open(GENRES_FILE, "r", encoding = "utf-8") as txt:
        for line in txt:
            line = line.strip()
            if not line:
                continue
            try:
                line_contents = json.loads(line)
                name = line_contents.get("name", "").lower()
            except json.JSONDecodeError:
                continue
            name = name.strip()
            if not name:
                continue

            genre_filters.add(name)

            bare = _nonword_re.sub("", name)
            if bare:
                genre_filters.add(bare)
            
            for word in _word_re.findall(name):
                genre_filters.add(word)

    return genre_filters

def _normalize_genre(name: str):
    """Normalize a genre string for comparison."""
    return _nonword_re.sub("", name.lower().strip())

ALLOWED_GENRES = _load_genre_filter()

def get_tags_for_song(song_name: str, artist_name: str, limit: int = 5):
    """Return a filtered list of tags from Last.fm for a given song."""
    def _call(method, **kwargs):
        params = {
            "method": method,
            "api_key": LASTFM_API_KEY,
            "format": "json",
            "autocorrect": 1,
            **kwargs
        }
        results = requests.get(BASE_URL, params = params)
        results.raise_for_status()
        tags = results.json().get("toptags", {}).get("tag", [])
        return tags if isinstance(tags, list) else [tags]
    
    attempts = [
        ("track.gettoptags", {"artist": artist_name, "track": song_name}),
        ("track.getTags", {"artist": artist_name, "track": song_name}),
        ("album.gettoptags", {"artist": artist_name, "album": song_name}),
        ("artist.gettoptags", {"artist": artist_name}),
    ]

    seen = set()
    filtered_tags = []
    raw_tags = []
    DISSALLOWED_TAGS = {"usa", "american", "seen live", "french", "german", artist_name.lower()}
    sources = []

    for method, kwargs in attempts:
        try:
            raw_tags = _call(method, **kwargs)

            if len(raw_tags) < 5:
                sources.append(f"Method {method} returned {len(raw_tags)} raw tags, therefore not used")
                continue

            for tag in raw_tags:
                name = tag.get("name", "").lower().strip()
                norm = _normalize_genre(name)

                if (norm in seen or name in DISSALLOWED_TAGS or artist_name.lower() in name):
                    continue

                if (name in ALLOWED_GENRES or norm in ALLOWED_GENRES or any(word in ALLOWED_GENRES for word in _word_re.findall(name))):
                    filtered_tags.append({
                        "name": name,
                        "count": int(tag.get("count", 0)),
                        "url": tag.get("url", "")
                    })
                    seen.add(norm)

                if len(filtered_tags) >= limit:
                    break

            if filtered_tags:
                sources.append(f"Method {method} returned {len(raw_tags)} raw tags, therefore was used")
                break

        except Exception:
            continue

    return filtered_tags, sources
