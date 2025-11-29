"""
Script to populate the database
"""

import os
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import time
from db_helpers import *
from services.lastfm import is_song_christian
from services.spotify import features_to_vector
from main import process_single
from typing import Optional
from sqlalchemy import text

TEMP_DIR = "temp"
TEMP_BASE_FILENAME = "audio"

def _fail_job(db, job_id: int, error_message: str):
    """
    Mark a job as failed in the populate_queue table.
    """
    db.execute(text("""
        UPDATE populate_queue
        SET status = 'failed',
            last_error = :error,
            last_attempt_at = NOW(),
            attempt_count = attempt_count + 1
        WHERE id = :id
    """), {"id": job_id, "error": error_message})

def fetch_next_job(db) -> Optional[dict]:
    """
    Fetch the next job from the populate_queue table.
    Locks the row to prevent other workers from processing it.
    Returns a dictionary with job details or None if no pending jobs.
    If the worker is interrupted, the transaction is rolled back.
    """
    row = db.execute(text("""
        SELECT id,
               spotify_track_id,
               source,
               enqueued_at,
               status
        FROM populate_queue
        WHERE status = 'pending'
        ORDER BY enqueued_at
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    """)).fetchone()

    if row is None:
        return None
    
    return {
        "id": row.id,
        "spotify_track_id": row.spotify_track_id,
        "source": row.source,
        "enqueued_at": row.enqueued_at,
        "status": row.status
    }

def process_next_job(db):
    """
    Process the next job in the populate_queue table.
    Processes one job at a time, then moves onto the next.
    Sleeps if no jobs are available, and retries.
    """
    job = fetch_next_job(db)

    if job is None:
        return False  # No job found
    
    print(f"[worker] Got job {job['id']} for track {job['spotify_track_id']} from source {job['source']}")

    # Mark job as in progress
    db.execute(text("""
        UPDATE populate_queue
        SET status = 'processing',
            last_error = NULL
        WHERE id = :id
    """), {"id": job["id"]})

    try:
        print(f"[worker] Processing track {job['spotify_track_id']}...")

        # Check if the song is actually Christian
        result = is_song_christian(job["spotify_track_id"])
        is_christian, tags, method, isrc, song_info = result
        
        # If not Christian, mark job as failed
        if not is_christian:
            print(f"[worker] Track {job['spotify_track_id']} determined to be non-Christian. Marking job as failed.")
            _fail_job(db, job["id"], "Track determined to be non-Christian")
            return True
        
        # If song_info could not be retrieved, mark job as failed
        if song_info is None:
            print(f"[worker] Failed to retrieve song info for track {job['spotify_track_id']}. Marking job as failed.")
            _fail_job(db, job["id"], "Failed to retrieve song info from Spotify")
            return True

        # If song already exists in DB, mark job as failed
        existing_song = db.execute(text("""
            SELECT isrc
            FROM christian_songs
            WHERE isrc = :isrc
        """), {"isrc": isrc}).fetchone()

        if existing_song is not None:
            print(f"[worker] Track {job['spotify_track_id']} already exists in the database with ISRC {existing_song.isrc}. Skipping job.")
            _fail_job(db, job["id"], "Track already exists in the database")
            return True
        
        # Insert the new Christian song into the database
        try:
            song_data = process_single(song_info["title"], song_info["artist"], idx=job["id"])
        except Exception as err:
            _fail_job(db, job["id"], str(err))
            return True
        finally:
            try:
                for fn in os.listdir(TEMP_DIR):
                    os.remove(os.path.join(TEMP_DIR, fn))
                os.rmdir(TEMP_DIR)
            except Exception:
                pass
        
        audio_features = song_data["audio_features"]["average"]
        weighted_features = weight_features(audio_features)

        db.execute(text("""
            INSERT INTO christian_songs (
                track_id,
                isrc,
                title,
                artist,
                album,
                tag_count,
                tags_method,
                audio_features,
                weighted_features,
                num_indexes,
                last_indexed
            ) VALUES (
                :track_id,
                :isrc,
                :title,
                :artist,
                :album,
                :tag_count,
                :tags_method,
                :audio_features,
                :weighted_features,
                :num_indexes,
                :last_indexed
            )
        """), {
            "track_id": song_info["track_id"],
            "isrc": isrc,
            "title": song_info["title"],
            "artist": song_info["artist"],  
            "album": song_info.get("album"),
            "tag_count": len(tags) if tags else 0,
            "tags_method": method,
            "audio_features": features_to_vector(audio_features),
            "weighted_features": weighted_features,
            "num_indexes": 0,
            "last_indexed": None
        })

        # Insert the tags into the song_tags table
        if tags:
            tag_rows = [
                {
                    "track_id": song_info["track_id"],
                    "tag": tag["name"].strip().lower(),
                    "count": tag["count"],
                }
                for tag in tags
            ]

            for tag_row in tag_rows:
                db.execute(text("""
                    INSERT INTO song_tags (track_id, tag, count)
                    VALUES (:track_id, :tag, :count)
                    ON CONFLICT (track_id, tag) DO NOTHING
                """), tag_row)

        # On success, mark job as completed
        db.execute(text("""
            UPDATE populate_queue
            SET status = 'done'
            WHERE id = :id
        """), {"id": job["id"]})

        print(f"[worker] Job {job['id']} done")
        return True

    except Exception as error:
        _fail_job(db, job["id"], str(error))
        print(f"[worker] Job {job['id']} failed: {error}")
        return True

def main():
    """
    Main worker loop to continuously process jobs.
    Sleeps when no jobs are available.
    Exits by keyboard interrupt.
    """
    # Create DB engine
    engine = connect_to_db()

    # Test DB connection
    test_db_connection(engine)

    try:
        while True:
            with engine.begin() as db:
                has_job = process_next_job(db)

            if not has_job:
                print("[worker] No jobs found, sleeping for 3 seconds...")
                time.sleep(3)

    except KeyboardInterrupt:
        print("\n[worker] Interrupted by user. Worker shutting down. Database rolled back.")
        time.sleep(3)

if __name__ == "__main__":
    main()
