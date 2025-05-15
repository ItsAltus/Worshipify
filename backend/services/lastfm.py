'''
lastfm genre/tag retrieving
'''

import os
import json
import re
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
BASE_URL = "http://ws.audioscrobbler.com/2.0/"
GENRES_FILE = os.path.abspath(os.path.join(__file__, "..", "..", "genres.txt"))

_nonword_re = re.compile(r"[^\w]+")
_word_re    = re.compile(r"\w+")

def _load_genre_filter():
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

ALLOWED_GENRES = _load_genre_filter()

def get_tags_for_song(song_name: str, artist_name: str, mbid: Optional[str] = None, limit: int = 5):
    def _call(**kwargs):
        params = {
            "method": "track.gettoptags",
            "api_key": LASTFM_API_KEY,
            "format": "json",
            "autocorrect": 1,
            **kwargs
        }
        results = requests.get(BASE_URL, params = params)
        results.raise_for_status()
        tags = results.json().get("toptags", {}).get("tag", [])
        return tags if isinstance(tags, list) else [tags]
    
    if mbid:
        raw_tags = _call(mbid = mbid)
    else:
        raw_tags = _call(artist = artist_name, track = song_name)
    
    filtered_tags = []
    for tag in raw_tags:
        name = tag.get("name", "").lower().strip()
        if name in ALLOWED_GENRES:
            filtered_tags.append({
                "name": name,
                "count": int(tag.get("count", 0)),
                "url": tag.get("url", "")
            })
        if len(filtered_tags) >= limit:
            break

    return filtered_tags
