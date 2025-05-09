'''
FastAPI Entry Point
Contains FastAPI methods and references to external functions
'''

from fastapi import FastAPI
from services.spotify import search_song #, christian_song_same_genre
from backend.services.lastfm import get_tags_for_song

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Worshipify Backend is Running!"}

@app.get("/search") # Visit http://127.0.0.1:8000/search?secular_song=your_song_name
def search(secular_song: str):
    """Search for a secular song and return its details."""
    secular_song_details = search_song(secular_song)
    secular_song_genres = get_tags_for_song(secular_song_details["artist"], secular_song_details["title"])
    #christian_song_details = christian_song_same_genre(secular_song)
    return{
        "secular_song_info": secular_song_details,
        "secular_song_genres": secular_song_genres
        #"christian_song_same_genre": christian_song_details
    }

@app.get("/help")
def docs():
    return {"message": "Visit /docs for API documentation."}
