# Backend Module Overview

This document provides a brief description of the modules found within the `backend` directory.

## main.py
Entry point for the FastAPI application. Defines routes and orchestrates the calls to service modules.

## services/spotify.py
Contains helpers for searching Spotify, downloading audio previews via YouTube, interacting with ReccoBeats and normalising audio features.

## services/lastfm.py
Retrieves and filters genre tags from Last.fm using several fallback queries.

## services/matcher.py
Placeholder for the audio similarity and song matching logic.

## services/mapping.py
Placeholder for future utilities to build Christian music metadata.

## tests/
Includes small unit tests such as `test_dependencies.py` which validates that packages from `requirements.txt` are installed.
