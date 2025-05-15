'''
song searching and audio feature retrieval
'''

import os
import requests
import math
import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.exceptions import SpotifyException
from dotenv import load_dotenv

# Load API keys from .env file
load_dotenv()

# Authenticate with Spotify
sp = spotipy.Spotify(auth_manager = SpotifyClientCredentials(
    client_id = os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
))

TEMP_DIR = "temp"
TEMP_BASE_FILENAME = "audio"
RECCOBEATS_API = "https://api.reccobeats.com/v1/analysis/audio-features"

def search_song(song_name: str, artist_name: str):
    query = f'track:"{song_name}"'
    if artist_name:
        query += f' artist:"{artist_name}"'

    try:
        results = sp.search(q = query, type = "track", limit = 1)
    except SpotifyException as error:
        return {"error": f"Spotify search failed: {error}"}

    if results["tracks"]["items"]:
        track = results["tracks"]["items"][0]
        return{
            "title": track["name"],
            "artist": track["artists"][0]["name"],
            "spotify_url": track["external_urls"]["spotify"],
            "preview_url": track["preview_url"],
            "album_art": track["album"]["images"][0]["url"] if track["album"]["images"] else None,
            "track_id": track["id"],
            "isrc": track["external_ids"]["isrc"],
            "yt_url": f"ytsearch1:{track['name']} {track['artists'][0]['name']} official audio"
        }
    return {"error": "Song not found"}

def download_audio(youtube_url: str, base_path_no_ext):
    os.makedirs(TEMP_DIR, exist_ok = True)
    output_template = base_path_no_ext
    ydl_options = {
        "format": 'bestaudio/best',
        "outtmpl": output_template,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "postprocessor_args": ["-ss", str(30), "-t", str(60)],
        "quiet": False,
    }
    
    with yt_dlp.YoutubeDL(ydl_options) as ydl:
        ydl.download([youtube_url])
    
    final_path = base_path_no_ext + ".mp3"
    if not os.path.exists(final_path):
        raise FileNotFoundError(f"Expected output file not found: {final_path}")

    return final_path

def extract_features(file_path):
    with open(file_path, "rb") as file:
        files = {"audioFile": file}
        result = requests.post(RECCOBEATS_API, files=files)
    return result.status_code, result.json()

def adjust_bpm(bpm, energy, danceability):
    if bpm < 100 and energy > 0.5 and danceability > 0.5:
        return round(bpm * 2, 2)
    return round(bpm, 2)

def normalize_features(f):
    return {
        "acousticness": round(f["acousticness"], 2),
        "danceability": round(f["danceability"], 2),
        "energy": round(f["energy"], 2),
        "valence": round(f["valence"], 2),
        "instrumentalness": math.floor(f["instrumentalness"] * 100) / 100,
        "speechiness": math.floor(f["speechiness"] * 100) / 100,
        "liveness": round(f["liveness"], 2),
        "loudness": round(f["loudness"], 1),
        "tempo": round(f["tempo"]),
        "original_tempo":   round(f.get("original_tempo", f["tempo"]))
    }
