'''
Helper functions for database operations
'''

import os
from pathlib import Path
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
