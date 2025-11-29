'''
lastfm genre/tag retrieving
'''

import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

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

def _apply_christian_tag_filter(tags: list):
    """Filter tags to only include Christian-related ones."""
    christian_keywords = {"christian", "ccm", "worship", "gospel", "chh", "jesus", "bible", "christ"}
    filtered = []
    for tag in tags:
        name = tag.get("name", "").lower().strip()
        # Check if any Christian keyword is contained in the tag name
        if any(keyword in name for keyword in christian_keywords):
            filtered.append(tag)
    return filtered

ALLOWED_GENRES = _load_genre_filter()

def get_tags_for_song(song_name: str, artist_name: str, limit: int = 5):
    """Return a filtered list of tags from Last.fm for a given song."""
    def _get_spotify_artist_genres(artist_name: str):
        # Use Spotify artist genres as tags
        artist_info = search_song(artist_name = artist_name)
        if not artist_info:
            return []
        track_id = artist_info.get("track_id")
        if not track_id:
            return []
        try:
            track = sp.track(track_id)
            if not track or not track.get("artists"):
                return []
            artist_id = track["artists"][0]["id"]
            artist = sp.artist(artist_id)
            if not artist:
                return []
            genres = artist.get("genres", [])
            tags = [{"name": genre, "count": 0, "url": ""} for genre in genres]
            return tags
        except SpotifyException:
            return []

    def _call(method, **kwargs):
        if method != "spotify":
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
    method = None

    for method, kwargs in attempts:
        try:
            raw_tags = _call(method, **kwargs)

            if not raw_tags or (len(raw_tags) < 5 and method != "artist.gettoptags"):
                sources.append(f"Method {method} returned {len(raw_tags) if raw_tags else 0} raw tags, therefore not used")
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

    if method == "artist.gettoptags":
        spotify_tags = _get_spotify_artist_genres(artist_name)
        filtered_tags.extend(spotify_tags)

    return filtered_tags, sources

def is_song_christian(song_id: str):
    """Determine if a song is Christian based on its Last.fm tags."""
    song_info = search_song(track_id = song_id)
    if not song_info:
        return False, None, None, None, None

    song_name = song_info.get("title")
    artist_name = song_info.get("artist")
    if not song_name or not artist_name:
        return False, None, None, None, None

    tags, methods = get_tags_for_song(song_name, artist_name, limit = 10)
    if not tags:
        return False, None, None, None, None
    
    christian_tags = _apply_christian_tag_filter(tags)
    is_christian = len(christian_tags) > 0

    if is_christian:
        isrc = song_info.get("isrc")
    else:
        isrc = None

    return is_christian, tags, methods, isrc, song_info
