'''
lastfm genre/tag retrieving
'''

import os
import requests
from dotenv import load_dotenv

load_dotenv()
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
LASTFM_API_SECRET = os.getenv("LASTFM_API_SECRET")

BASE_URL = "http://ws.audioscrobbler.com/2.0/"
CHRISTIAN_KEYWORKS = ["christian", "worship", "gospel", "ccm"]
DEFAULT_GENRE_MAP = {
    "pop": "christian pop",
    "rock": "christian rock",
    "hip hop": "gospel rap",
    "edm": "christian edm",
    "folk": "ccm",
    "r-n-b": "gospel",
    "indie": "christian alternative",
}

def get_tags_for_song(artist: str, track: str):
    params = {
        "method": "track.getTopTags",
        "artist": artist,
        "track": track,
        "api_key": LASTFM_API_KEY,
        "format": "json"
    }
    res = requests.get(BASE_URL, params=params).json()
    return [tag["name"].lower() for tag in res.get("toptags", {}).get("tag", [])]
