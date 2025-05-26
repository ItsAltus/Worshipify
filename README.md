# Worshipify
![CI](https://github.com/ItsAltus/Worshipify/actions/workflows/test.yml/badge.svg?branch=main)<br>
![Project Status: In Progress](https://img.shields.io/badge/status-in--progress-yellow)<br>
[![wakatime](https://wakatime.com/badge/user/eea1cec5-46f2-49ac-bf45-3167a116bf92/project/c1ab9930-d8f3-4b90-a752-e481f2be6999.svg)](https://wakatime.com/badge/user/eea1cec5-46f2-49ac-bf45-3167a116bf92/project/c1ab9930-d8f3-4b90-a752-e481f2be6999)

## ⚠️ Work in Progress
This repository is under active development and is **not yet production-ready**. Expect frequent changes, unfinished features, and evolving recommendation logic.

---

## About Worshipify

**Worshipify** is a music recommendation web app that helps Christians discover worship-based alternatives to secular songs.  

---

## Key Functionality

Due to recent changes to the [Spotify Web API (Nov 2024)](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api), Worshipify reduces dependency on Spotify and instead uses a multi-layered backend with custom logic and external APIs:

### ✅ Spotify
Used only for:
- Initial track search (`track:"..." artist:"..."`)
- Metadata for generating a YouTube query string

### ✅ Last.fm
Used to:
- Retrieve rich user-generated tags via fallback queries
- Filter out irrelevant or non-worship genres using a curated whitelist
- Normalize tags through regex-based processing

### ✅ Custom Genre Filtering
- A large genre database contained within `genres.txt` is parsed and compiled into a flexible filter set (handling word stems, special characters, etc.)
- Only tags passing multiple heuristic checks are returned

### ✅ yt_dlp + ffmpeg (YouTube Preview Pipeline)
- Downloads a 60-second preview of the song using `yt_dlp`
- Slices it into two 30s segments using `ffmpeg`
- Sends each to ReccoBeats for detailed feature extraction

### ✅ ReccoBeats
- Receives raw audio segments and returns detailed stats:
  - Energy, acousticness, valence, etc.
- This data is then passed through a strict and intricate custom algorithm to adjust audio features to ensure accuracy

---

## Planned Features

- **Secular-to-Worship Matching**  
  Recommend spiritually aligned tracks based on musical similarity.

- **Advanced Genre Filtering**  
  Fine-tune results by focusing on worship, gospel, CCM, and excluding secular overlap.

- **Interactive Previews**  
  Provide playable audio via YouTube, especially for non-Spotify users.

- **Track Logging & Feedback**  
  Build a user-driven system for improving match quality over time.

---

## Tech Stack

**Backend:**  
`Python`, `FastAPI`, `Spotipy`, `yt_dlp`, `ReccoBeats API`, `Last.fm API`

**Frontend:**  
`React`, `Next.js`, `Tailwind CSS`

**Deployment:**  
`Railway` (backend), `Vercel` (frontend)

---

> This is an active portfolio project exploring intelligent audio-based recommendation systems.  

---
