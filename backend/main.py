from fastapi import FastAPI
from services.spotify import search_song, christian_song_same_genre

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Worshipify Backend is Running!"}

@app.get("/search")
def search(secular_song: str):
    """Search for a secular song and return its details."""
    secular_song_details = search_song(secular_song)
    christian_song_details = christian_song_same_genre(secular_song)
    return{
        "secular_song": secular_song_details,
        "christian_song_same_genre": christian_song_details
    }