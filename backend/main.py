'''
FastAPI Entry Point
Contains FastAPI methods and references to external functions
'''

from fastapi import FastAPI
from typing import Optional
from services.spotify import *

TEMP_DIR = "temp"
TEMP_BASE_FILENAME = "audio"

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Worshipify Backend is Running!"}

@app.get("/search") # Visit http://127.0.0.1:8000/search?song_name=your_secular_song_name&artist_name=songs_artist_name (artist optional)
def search(song: str, artist: Optional[str] = None):
    """Search for a secular song and return its details."""
    secular_song_details = search_song(song, artist)
    base_no_ext = os.path.join(TEMP_DIR, TEMP_BASE_FILENAME)

    try:
        mp3_path = download_audio(secular_song_details["yt_url"], base_no_ext)
        status, features = extract_features(mp3_path)
        features["original_tempo"] = features["tempo"]
        features["tempo"] = adjust_bpm(
            features["tempo"],
            energy=features["energy"],
            danceability=features["danceability"]
        )
        print(f"✅ Status code: {status}")
    except Exception as error:
        print("❌ Error:", error)
        return
    finally:
        for file_name in os.listdir(TEMP_DIR) if os.path.isdir(TEMP_DIR) else []:
            try:
                os.remove(os.path.join(TEMP_DIR, file_name))
            except:
                pass
        try:
            os.rmdir(TEMP_DIR)
        except:
            pass

    return features

@app.get("/help")
def docs():
    return {"message": "Visit /docs for API documentation."}
