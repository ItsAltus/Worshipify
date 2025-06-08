'''
song searching and audio feature retrieval
'''

import glob
import math
import os
import subprocess
from typing import List
import requests
import spotipy
import yt_dlp
from dotenv import load_dotenv
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyClientCredentials

load_dotenv()

sp = spotipy.Spotify(auth_manager = SpotifyClientCredentials(
    client_id = os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
))

TEMP_DIR = "temp"
RECCOBEATS_API = "https://api.reccobeats.com/v1/analysis/audio-features"

def search_song(song_name: str, artist_name: str):
    """Return metadata for the best matching Spotify track."""
    query = f'track:"{song_name}"'
    if artist_name:
        query += f' artist:"{artist_name}"'

    try:
        results = sp.search(q = query, type = "track", limit = 1)
    except SpotifyException as error:
        return {"error": f"Spotify search failed: {error}"}

    if results and results.get("tracks") and results["tracks"].get("items"):
        track = results["tracks"]["items"][0]
        return{
            "title": track["name"],
            "artist": track["artists"][0]["name"],
            "album": track["album"]["name"],
            "spotify_url": track["external_urls"]["spotify"],
            "preview_url": track["preview_url"],
            "album_art": track["album"]["images"][0]["url"] if track["album"]["images"] else None,
            "track_id": track["id"],
            "isrc": track["external_ids"]["isrc"],
            "yt_url": f"ytsearch1:{track['name']} {track['artists'][0]['name']} official audio"
        }
    return {"error": "Song not found"}

def _ffmpeg_trim(src: str, start: int, dur: int, dst: str) -> None:
    """Trim ``dur`` seconds from ``src`` starting at ``start`` using ffmpeg."""
    subprocess.run(
        [
            "ffmpeg",
            "-y", "-loglevel", "quiet",
            "-ss", str(start), "-t", str(dur),
            "-i", src,
            "-acodec", "libmp3lame", "-b:a", "192k",
            dst,
        ],
        check=True,
    )

def download_audio(youtube_url: str, base_path_no_ext: str) -> List[str]:
    """Download a 60s preview from YouTube and split it into two clips."""
    os.makedirs(TEMP_DIR, exist_ok=True)

    base60 = f"{base_path_no_ext}_60s"
    outtmpl = base60 + ".%(ext)s"

    if not glob.glob(base60 + ".*"):
        yt_dlp.YoutubeDL(
            {
                "format": "bestaudio/best",
                "outtmpl": outtmpl,
                "download_sections": ["*00:00:00-00:01:00"],
                "nopart": True,
                "quiet": False,
            }
        ).download([youtube_url])

    matches = glob.glob(base60 + ".*")
    if not matches:
        raise FileNotFoundError("60-second clip was not downloaded")
    raw60 = matches[0]

    out_paths: List[str] = []
    for start in (0, 30):
        mp3 = f"{base_path_no_ext}_from{start}s.mp3"
        if not os.path.exists(mp3):
            _ffmpeg_trim(raw60, start, 30, mp3)
        out_paths.append(mp3)

    return out_paths

def extract_features(paths: List[str]):
    """Send audio clips to ReccoBeats and return the JSON responses."""
    results = []
    for fp in paths:
        with open(fp, "rb") as f:
            r = requests.post(RECCOBEATS_API, files={"audioFile": f})
            results.append((fp, r.status_code, r.json()))
    return results

def _normalise_bpm(bpm: float) -> float:
    """Normalize BPM into a human-friendly range."""
    if bpm == 0:
        return 0.0

    while bpm < 60:
        bpm *= 2
    while bpm > 200:
        bpm /= 2

    return round(bpm)

def _select_tempo(s1: dict, s2: dict) -> int:
    """Pick a sensible tempo from two feature dictionaries."""
    t1, t2 = s1["tempo"], s2["tempo"]
    e1, e2 = s1.get("energy", 0.5), s2.get("energy", 0.5)

    # If the tempos are similar, return an energy weighted average
    if abs(t1 - t2) <= 10:
        weighted = (t1 * e1 + t2 * e2) / (e1 + e2 or 1e-6)
        return round(weighted)

    # Otherwise pick the tempo closest to a common reference (120 BPM)
    ref = 120
    d1, d2 = abs(t1 - ref), abs(t2 - ref)
    if d1 == d2:
        # tie-breaker based on higher energy
        return round(t1 if e1 >= e2 else t2)
    return round(t1 if d1 < d2 else t2)

def merge_segments(s1: dict, s2: dict) -> dict:
    """Weighted merge of two feature dictionaries."""
    for seg in (s1, s2):
        seg["tempo"] = _normalise_bpm(seg["tempo"])
        if seg["energy"] > 0.5 and seg["instrumentalness"] < 0.1:
            seg["acousticness"] = min(seg["acousticness"], 0.3)

    w1, w2 = s1["energy"], s2["energy"]
    total = w1 + w2 or 1e-6
    avg = {k: round((s1[k]*w1 + s2[k]*w2)/total, 2)
           for k in s1 if isinstance(s1[k], (int, float))}

    bpm = _select_tempo(s1, s2)
    avg["tempo"] = bpm
    return avg

def normalize_features(f):
    """Round and clean up raw feature data returned by ReccoBeats."""
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
        "original_tempo": f["tempo"]
    }