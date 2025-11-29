'''
Helper functions for database operations
'''

import os
import math
from pathlib import Path
from pyexpat import features
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

def connect_to_db():
    # Load environment variables from ../.env
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(env_path)

    # Get DB URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is missing or .env failed to load")

    # Create normal SQLAlchemy engine (sync)
    engine = create_engine(
        db_url,
        echo = False, # Print SQL queries
        pool_pre_ping = True # Avoid stale connections
    )

    return engine

def test_db_connection(engine):
    """
    Test the database connection on startup.
    Exits the program if connection fails.
    """
    try:
        with engine.connect() as test_connection:
            result = test_connection.execute(text("SELECT version()"))
            version = result.scalar()
        print(f"Connected to Worshipify database with version: {version}")

    except Exception as error:
        print(f"Failed to connect to the database: {error}")
        exit(1) # Don't proceed if DB connection fails

def weight_features(features: dict) -> list:
    """
    Apply weights to audio features following the similarity algorithm.
    """
    
    # Extract raw values
    f1 = features.get("acousticness", 0.0)
    f2 = features.get("danceability", 0.0)
    f3 = features.get("energy", 0.0)
    f4 = features.get("valence", 0.0)
    f5 = features.get("instrumentalness", 0.0)
    f6 = features.get("speechiness", 0.0)
    f7 = features.get("liveness", 0.0)
    loud = features.get("loudness", -7.0)
    bpm = max(40.0, min(features.get("tempo", 120.0), 240.0)) # Guard against nonsense BPM
    
    # Tempo normalization constants
    ln80 = math.log(80.0)
    ln200 = math.log(200.0)

    # Apply weights matching the SQL algorithm
    weighted = [
        f1 * 1.0,                                           # acousticness
        f2 * 1.9,                                           # danceability
        f3 * 2.1,                                           # energy
        f4 * 2.5,                                           # valence
        f5 * 1.5,                                           # instrumentalness
        f6 * 0.8,                                           # speechiness
        f7 * 0.3,                                           # liveness
        ((loud + 16) / 12.0) * 0.2,                        # loudness (normalized)
        ((math.log(bpm) - ln80) / (ln200 - ln80)) * 3.2    # tempo (log-normalized)
    ]

    return weighted