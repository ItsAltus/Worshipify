"""
Script to populate the database
"""

import os
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import time
from db_helpers import connect_to_db, test_db_connection, weight_features
from services.lastfm import is_song_christian, get_similar_tracks_by_id
from services.spotify import features_to_vector
from main import process_single
from typing import Optional
from sqlalchemy import text
TEMP_DIR = "temp"
TEMP_BASE_FILENAME = "audio"

def cleanup_temp_dir():
    """Removes all files in the temp directory and then removes the directory itself."""
    try:
        if os.path.exists(TEMP_DIR):
            for fn in os.listdir(TEMP_DIR):
                file_path = os.path.join(TEMP_DIR, fn)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            os.rmdir(TEMP_DIR)
    except Exception as e:
        print(f"[worker] Temp cleanup failed: {e}")

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
               status,
               seed_depth,
               seed_parent_spotify_id,
               seed_batch_id
        FROM populate_queue
        WHERE status = 'pending'
        ORDER BY enqueued_at ASC
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
        "status": row.status,
        "seed_depth": row.seed_depth if hasattr(row, 'seed_depth') else 0,
        "seed_parent_spotify_id": row.seed_parent_spotify_id if hasattr(row, 'seed_parent_spotify_id') else None,
        "seed_batch_id": row.seed_batch_id if hasattr(row, 'seed_batch_id') else None
    }

def check_song_exists(db, isrc: str) -> bool:
    """
    Check if a song with the given ISRC already exists in the christian_songs table.
    """
    existing_song = db.execute(text("""
        SELECT isrc
        FROM christian_songs
        WHERE isrc = :isrc
    """), {"isrc": isrc}).fetchone()

    return existing_song is not None

def validate_track_info(db, job: dict):
    """
    Validate and retrieve track information
    Raises ValueError if validation fails
    """
    # Retrieve necessary info from Last.fm and Spotify
    result = is_song_christian(job["spotify_track_id"])
    is_christian, tags, method, isrc, song_info = result

    validations = [
        (not is_christian, "Track determined to be non-Christian"),
        (song_info is None, "Failed to retrieve song info from Spotify"),
        (isrc is None, "Failed to retrieve ISRC"),
        (tags is None, "Failed to retrieve tags"),
        (method is None, "Failed to retrieve method"),
        (isrc and check_song_exists(db, isrc), "Track already exists in the database")
    ]

    for condition, message in validations:
        if condition:
            raise ValueError(message)
    
    # Type narrowing: assert that all values are non-None after validation
    assert song_info is not None
    assert isrc is not None
    assert tags is not None
    assert method is not None
    
    return song_info, isrc, tags, method

def insert_christian_song(db, song_info: dict, job: dict, isrc: str, tags: list, method: list):
    """
    Insert a new Christian song into the christian_songs table.
    """
    try:
        song_data = process_single(song_info["title"], song_info["artist"], idx=job["id"])
    except Exception as err:
        raise ValueError(f"Error processing song audio: {err}")
    finally:
        cleanup_temp_dir()
    
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

    # Insert the tags into the normalized tags and song_tags tables
    if tags:
        # 1. Ensure all tags exist in the tags table
        db.execute(text("""
            INSERT INTO tags (name)
            VALUES (:name)
            ON CONFLICT (name) DO NOTHING
        """), [{"name": tag["name"].strip().lower()} for tag in tags])

        # 2. Get the IDs of those tags
        tag_names = tuple(tag["name"].strip().lower() for tag in tags)
        tag_records = db.execute(text("""
            SELECT id, name FROM tags WHERE name IN :names
        """), {"names": tag_names}).fetchall()
        
        tag_id_map = {row.name: row.id for row in tag_records}

        # 3. Insert into the join table
        join_rows = [
            {
                "track_id": song_info["track_id"],
                "tag_id": tag_id_map[tag["name"].strip().lower()],
                "count": tag["count"],
            }
            for tag in tags
        ]

        db.execute(
            text("""
                INSERT INTO song_tags (track_id, tag_id, count)
                VALUES (:track_id, :tag_id, :count)
                ON CONFLICT (track_id, tag_id) DO NOTHING
            """),
            join_rows,
        )

def enqueue_similar_tracks(db, job: dict):
    """
    Fetch similar tracks from Spotify and enqueue them safely in the populate_queue.
    Implements depth-based expansion, filtering, and queue backpressure.
    """
    try:
        # Generate batch ID for debugging
        import uuid
        batch_id = str(uuid.uuid4())

        # 1. Uncapped Gating (Fetch up to 5 tracks recursively every time)
        current_depth = job.get('seed_depth', 0)
        target_adds = 5
        fetch_limit = 50
            
        # Get recommendations
        recommended_tracks = get_similar_tracks_by_id(job["spotify_track_id"], limit=fetch_limit)
        if not recommended_tracks:
            return

        added = 0
        skipped_missing_info = 0
        skipped_in_db = 0
        skipped_in_queue = 0

        for track in recommended_tracks:
            if added >= target_adds:
                break
                
            title = track.get("title", "")
            artist = track.get("artist", "")
            track_id = track.get("track_id")
            
            # Pre-enqueue filtering
            if not track_id or not title or not artist:
                skipped_missing_info += 1
                continue

            # Check if track is already in christian_songs
            isrc = track.get("isrc")
            if isrc and check_song_exists(db, isrc):
                skipped_in_db += 1
                continue
                
            # Check if track is already in populate_queue
            in_queue = db.execute(text("""
                SELECT 1 FROM populate_queue WHERE spotify_track_id = :spotify_track_id
            """), {"spotify_track_id": track_id}).scalar()
            if in_queue:
                skipped_in_queue += 1
                continue
                
            # Resolve specific source API
            source_api = track.get("source_api", "unknown")
            source_str = f'auto_seeded_{source_api}'
            
            # Attempt insertion with ON CONFLICT DO NOTHING to avoid IntegrityErrors poisoning the transaction
            result = db.execute(text("""
                INSERT INTO populate_queue (
                    spotify_track_id, source, seed_depth, seed_parent_spotify_id, seed_batch_id
                ) VALUES (
                    :spotify_track_id, :source, :seed_depth, :seed_parent_spotify_id, :seed_batch_id
                ) ON CONFLICT (spotify_track_id) DO NOTHING
            """), {
                "spotify_track_id": track_id,
                "source": source_str,
                "seed_depth": current_depth + 1,
                "seed_parent_spotify_id": job["spotify_track_id"],
                "seed_batch_id": batch_id
            })
            if result.rowcount > 0:
                added += 1

        print(f"[worker] Auto-seeded {added} similar tracks at depth {current_depth + 1}. Skipped {skipped_in_db} (in DB), {skipped_in_queue} (in queue), {skipped_missing_info} (missing info).")
    except Exception as error:
        print(f"[worker] Non-fatal error in enqueue_similar_tracks: {error}")

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

    try:
        # Use a savepoint so that if an SQL error occurs, it doesn't abort the entire transaction.
        # This allows us to safely call _fail_job(db) if needed, without encountering InFailedSqlTransaction.
        with db.begin_nested():
            # Validate and retrieve track info
            song_info, isrc, tags, method = validate_track_info(db, job)

            # Mark job as in progress
            db.execute(text("""
                UPDATE populate_queue
                SET status = 'processing',
                    last_error = NULL
                WHERE id = :id
            """), {"id": job["id"]})

            print(f"[worker] Processing track {job['spotify_track_id']}...")

            # Insert the Christian song into the christian_songs table
            insert_christian_song(db, song_info, job, isrc, tags, method)

            # Enqueue similar tracks based on recommendation API (Recursive Seeding)
            enqueue_similar_tracks(db, job)

            # Mark as completed
            db.execute(text("""
                UPDATE populate_queue
                SET status = 'done'
                WHERE id = :id
            """), {"id": job["id"]})

        print(f"[worker] Job {job['id']} completed successfully.")
        return True

    except Exception as error:
        try:
            _fail_job(db, job["id"], str(error))
        except Exception as fail_error:
            print(f"[worker] Could not mark job as failed (connection may be dead): {fail_error}")
            
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
            try:
                with engine.begin() as db:
                    has_job = process_next_job(db)

                if not has_job:
                    print("[worker] No jobs found, sleeping for 3 seconds...")
                    time.sleep(3)
            except Exception as e:
                print(f"[worker] Database transaction error (connection drop?): {e}")
                print("[worker] Reconnecting in 5 seconds...")
                time.sleep(5)

    except KeyboardInterrupt:
        print("\n[worker] Interrupted by user. Worker shutting down. Database rolled back.")
        cleanup_temp_dir()
        time.sleep(1)

if __name__ == "__main__":
    main()
