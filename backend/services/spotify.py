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

def christian_song_same_genre(secular_song_name: str):
    secular_result = sp.search(q=secular_song_name, type="track", limit=1)

    if not secular_result["tracks"]["items"]:
        return {"error": "Secular song not found"}
    
    secular_track = secular_result["tracks"]["items"][0]
    secular_artist_id = secular_track["artists"][0]["id"]

    artist_details = sp.artist(secular_artist_id)
    secular_genres = artist_details.get("genres", [])
    print(secular_genres)

    if not secular_genres:
        return {"error": f"no genre data available for artist {secular_track["artists"][0]["name"]}"}
    
    christian_genres = [f"christian {genre}" for genre in secular_genres]
    print(christian_genres)

    for genre in christian_genres:
        christian_result = sp.search(q=f"genre:{genre}", type="track", limit=1)

        if christian_result["tracks"]["items"]:
            christian_track = christian_result["tracks"]["items"][0]
            christian_artist_id = christian_track["artists"][0]["id"]
            christian_artist_details = sp.artist(christian_artist_id)
            christian_genres_list = christian_artist_details.get("genres", [])

            print(christian_genres_list)
            print(f"Matched genre: {genre}")

            return{
                "title": christian_track["name"],
                "artist": christian_track["artists"][0]["name"],
                "spotify_url": christian_track["external_urls"]["spotify"],
                "preview_url": christian_track["preview_url"],
                "album_art": christian_track["album"]["images"][0]["url"] if christian_track["album"]["images"] else None
            }
    return {"error": "No christian songs of same genre found"}

# Fetch a track by The Weeknd
track_result = sp.search(q="Blinding Lights", type="track", limit=1)

if track_result["tracks"]["items"]:
    artist_id = track_result["tracks"]["items"][0]["artists"][0]["id"]
    artist_details = sp.artist(artist_id)
    print(f"Genres from track lookup: {artist_details.get('genres', [])}")
