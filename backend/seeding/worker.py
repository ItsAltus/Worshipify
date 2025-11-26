"""
Script to populate the database
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

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

# Test connection
with engine.connect() as test_connection:
    result = test_connection.execute(text("SELECT version()"))
    version = result.scalar()
print(f"Connected to Worshipify database with version: {version}")

def process_one_job(db):
    #TODO: Implement job processing logic here
    print("Processing one job...")

def main():
    with engine.begin() as db:
        while True:
            process_one_job(db)
            break

if __name__ == "__main__":
    main()
