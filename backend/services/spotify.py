'''
song searching and audio feature retrieval
'''

import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

# Load API keys from .env file
load_dotenv()

# Authenticate with Spotify
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
))

def search_song(song_name: str):
    results = sp.search(q=song_name, type="track", limit=1)

    if results["tracks"]["items"]:
        track = results["tracks"]["items"][0]
        return{
            "title": track["name"],
            "artist": track["artists"][0]["name"],
            "spotify_url": track["external_urls"]["spotify"],
            "preview_url": track["preview_url"],
            "album_art": track["album"]["images"][0]["url"] if track["album"]["images"] else None
        }
    return {"error": "Song not found"}
