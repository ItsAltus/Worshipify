'''
song searching and audio feature retrieval
'''

import glob
import math
import os
import subprocess
import logging
from typing import List, Dict, Optional
import requests
import spotipy
import yt_dlp
from dotenv import load_dotenv
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyClientCredentials

logger = logging.getLogger(__name__)

load_dotenv()

sp = spotipy.Spotify(auth_manager = SpotifyClientCredentials(
    client_id = os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
))

TEMP_DIR = "temp"
RECCOBEATS_API = "https://api.reccobeats.com/v1/analysis/audio-features"

def search_song(song_name: Optional[str] = None, artist_name: Optional[str] = None, track_id: Optional[str] = None) -> Optional[Dict]:
    """Return metadata for the best matching Spotify track."""

    # If ISRC is provided, use the dedicated track endpoint
    if track_id:
        try:
            # Remove "spotify:track:" prefix if present
            track_id = track_id.replace("spotify:track:", "")
            track = sp.track(track_id)
            if not track:
                return {"error": "Track not found"}
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
        except SpotifyException as error:
            return {"error": f"Spotify track lookup failed: {error}"}
    
    # Otherwise, use search with song name and/or artist
    query = ""
    if song_name:
        query += f'track:"{song_name}"'
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

def validate_spotify_track(spotify_track_id: str) -> bool:
    """Check if a Spotify track ID is valid."""
    try:
        track = sp.track(spotify_track_id)
        return track is not None
    except SpotifyException:
        return False

def validate_spotify_album(spotify_album_id: str) -> bool:
    """Check if a Spotify album ID is valid."""
    try:
        album = sp.album(spotify_album_id)
        return album is not None
    except SpotifyException:
        return False

def validate_spotify_playlist(spotify_playlist_id: str) -> bool:
    """Check if a Spotify playlist ID is valid."""
    try:
        playlist = sp.playlist(spotify_playlist_id)
        return playlist is not None
    except SpotifyException:
        return False

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

def _get_duration(src: str) -> float:
    """Return duration of audio file in seconds using ffprobe."""
    out = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        src
    ])
    return float(out.strip())

def download_audio(youtube_url: str, base_path_no_ext: str) -> List[str]:
    """Download full audio from YouTube and split into 30s clips—dropping
    first/last if there are 4+ clips to save ffmpeg calls."""
    os.makedirs(TEMP_DIR, exist_ok=True)
    base = f"{base_path_no_ext}"
    outtmpl = base + ".%(ext)s"

    if not glob.glob(base + ".*"):
        yt_dlp.YoutubeDL(
            {
                "format": "bestaudio/best",
                "outtmpl": outtmpl,
                "nopart": True,
                "quiet": False,
            }
        ).download([youtube_url])

    matches = glob.glob(base + ".*")
    if not matches:
        raise FileNotFoundError("clip was not downloaded")
    raw = matches[0]

    total_secs = _get_duration(raw)
    num_clips  = int((total_secs + 29) // 30)

    if num_clips >= 4:
        clip_indices = range(1, num_clips-1)
    else:
        clip_indices = range(num_clips)

    out_paths: List[str] = []
    for idx in clip_indices:
        start = idx * 30
        duration = min(30, total_secs - start)
        mp3 = f"{base_path_no_ext}_clip{idx:02d}.mp3"
        if not os.path.exists(mp3):
            _ffmpeg_trim(raw, start, int(duration), mp3)
        out_paths.append(mp3)

    return out_paths

def extract_features(paths: List[str]):
    """Send audio clips to ReccoBeats and return the JSON responses."""
    features: List[Dict] = []
    EXPECTED_KEYS = {
        "acousticness","danceability","energy",
        "instrumentalness","speechiness","liveness",
        "loudness","tempo","valence"
    }

    for fp in paths:
        try:
            with open(fp, "rb") as f:
                r = requests.post(RECCOBEATS_API, files={"audioFile": f}, timeout=30)
            r.raise_for_status()
            data = r.json()

            if "audio_features" in data and isinstance(data["audio_features"], dict):
                data = data["audio_features"]

            if not EXPECTED_KEYS.issubset(data.keys()):
                raise ValueError(f"Missing keys: got {list(data.keys())}")

            features.append(data)

        except Exception as e:
            logger.warning(f"Skipping clip {fp!r}: {e}")

    if not features:
        raise RuntimeError("All ReccoBeats calls failed; no valid feature data")

    return features

def _normalise_bpm(bpm: float) -> float:
    """Normalize BPM into a human-friendly range."""
    if bpm == 0:
        return 0.0

    while bpm < 60:
        bpm *= 2
    while bpm > 200:
        bpm /= 2

    return round(bpm)

def _select_tempo(segments: List[Dict], threshold: float = 10.0, ref: float = 120.0) -> int:
    """
    Pick a tempo by taking the energy-weighted average of every segment's BPM.
    This ensures that high-energy, high-tempo slices pull the result upward,
    closely matching the track's actual tempo.
    """
    tempos = [_normalise_bpm(seg["tempo"]) for seg in segments]
    energies = [seg.get("energy", 0.5)    for seg in segments]

    total_energy = sum(energies) or 1e-6
    weighted_sum = sum(t * e for t, e in zip(tempos, energies))

    return round(weighted_sum / total_energy)

def merge_segments(segments: List[Dict]) -> dict:
    """
    Merge N feature-dicts into a single averaged dict.
        - First normalize BPM and clamp acousticness on each segment.
        - Then compute an energy-weighted average for every numeric feature.
        - Finally, pick a representative “tempo” via _select_tempo().
    """
    for seg in segments:
        seg["tempo"] = _normalise_bpm(seg["tempo"])
        if seg["energy"] > 0.5 and seg["instrumentalness"] < 0.1:
            seg["acousticness"] = min(seg["acousticness"], 0.3)

    energies = [seg["energy"] for seg in segments]
    total_energy = sum(energies) or 1e-6

    avg: Dict[str, float] = {}
    numeric_keys = [k for k, v in segments[0].items() if isinstance(v, (int, float))]

    for key in numeric_keys:
        weighted_sum = sum(seg[key] * seg["energy"] for seg in segments)
        avg[key] = round(weighted_sum / total_energy, 2)

    avg["tempo"] = _select_tempo(segments)

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
    }

def features_to_vector(features: Dict) -> List[float]:
    """Convert feature dict to a vector for inserting into the DB."""
    return [
        features["acousticness"],
        features["danceability"],
        features["energy"],
        features["valence"],
        features["instrumentalness"],
        features["speechiness"],
        features["liveness"],
        features["loudness"],
        features["tempo"],
    ]