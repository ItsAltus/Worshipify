from fastapi import FastAPI
from services.spotify import search_song

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Worshipify Backend is Running!"}

@app.get("/search")
def search(secular_song: str):
    """Search for a secular song and return its details."""
    return search_song(secular_song)
