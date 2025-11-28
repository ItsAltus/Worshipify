"""
Script to populate the database
"""

import time
from db_helpers import connect_to_db, test_db_connection
from typing import Optional
from sqlalchemy import text

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
        #
        ##
        ###
        #TODO: Add actual processing logic here
        ###
        ##
        #

        print(f"[worker] Processing track {job['spotify_track_id']}...")

        time.sleep(3)

        # On success, mark job as completed
        db.execute(text("""
            UPDATE populate_queue
            SET status = 'done'
            WHERE id = :id
        """), {"id": job["id"]})

        print(f"[worker] Job {job['id']} done")
        return True

    except Exception as error:
        db.execute(text("""
            UPDATE populate_queue
            SET status = 'failed',
                last_error = :error,
                last_attempt_at = NOW(),
                attempt_count = attempt_count + 1
            WHERE id = :id
        """), {"id": job["id"], "error": str(error)})

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
