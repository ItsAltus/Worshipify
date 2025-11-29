'''
Manager for the script to populate the database
'''

import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import time
from db_helpers import connect_to_db, test_db_connection
from services.spotify import validate_spotify_track
from typing import Optional
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

add_song_inputs = ["1", "1.", "add", "add song", "add song to queue", "a"]
view_queue_inputs = ["2", "2.", "view", "view queue", "v"]
exit_inputs = ["3", "3.", "exit", "e"]

def command_line_interface():
    """
    Command line interface for the manager.
    """
    print("[manager] Options:")
    print("   1. Add song to queue")
    print("   2. View queue")
    print("   3. Exit\n")
    choice = input("[manager] Enter your choice: ")
    return choice

def add_song_to_queue(engine, spotify_track_id: str):
    """
    Adds a song to the population queue.
    """
    try:
        with engine.begin() as db:
            db.execute(text("""
                INSERT INTO populate_queue (spotify_track_id, source)
                VALUES (:spotify_track_id, 'manual')
            """), {"spotify_track_id": spotify_track_id})
        print(f"[manager] Added track {spotify_track_id} to the queue.\n")
    except IntegrityError:
        print(f"[manager] Failed to add track to the queue: Track already exists in the queue.\n")
    except Exception as error:
        print(f"[manager] Failed to add track to the queue: {error}\n")

def view_queue(engine):
    """
    Displays the current population queue.
    """
    with engine.connect() as db:
        result = db.execute(text("""
            SELECT id, spotify_track_id, source, enqueued_at, status, attempt_count, last_attempt_at, last_error
            FROM populate_queue
            ORDER BY enqueued_at ASC
        """))

        rows = result.mappings().all()
        if len(rows) == 0:
            print("[manager] Population queue is empty.\n")

        print("[manager] Choose a status to filter by:")
        print("   1. pending")
        print("   2. in_progress")
        print("   3. completed")
        print("   4. failed")
        print("   5. all records\n")

        status_choice = input("[manager] Enter your choice (or press Enter for all): ")
        print("")

        if status_choice == "1":
            rows = [row for row in rows if row["status"] == "pending"]
        elif status_choice == "2":
            rows = [row for row in rows if row["status"] == "in_progress"]
        elif status_choice == "3":
            rows = [row for row in rows if row["status"] == "completed"]
        elif status_choice == "4":
            rows = [row for row in rows if row["status"] == "failed"]
        elif status_choice == "5" or status_choice == "":
            pass
        else:
            print("[manager] Invalid choice, showing all records.\n")
    
        print("[manager] Current Population Queue:")
        print("-----------------------------------")
        for row in rows:
            print(f"  ID: {row['id']}, Track ID: {row['spotify_track_id']}, Status: {row['status']}, Source: {row['source']}, Enqueued At: {row['enqueued_at']}, Attempts: {row['attempt_count']}, Last Attempt At: {row['last_attempt_at']}, Last Error: {row['last_error']}")
        print("")

def main():
    """
    Main function to run the manager for the database population worker.
    """
    # Create DB engine
    engine = connect_to_db()

    # Test DB connection
    test_db_connection(engine)

    # Command line interface loop, shows options to the user.
    print("\n[manager] Welcome to the Seeding Manager!\n")
    while True:
        choice = command_line_interface()
        print("")

        if choice.lower() in add_song_inputs:
            spotify_track_id = input("[manager] Enter Spotify Track ID: ")
            print("")
            if validate_spotify_track(spotify_track_id):
                add_song_to_queue(engine, spotify_track_id)
            else:
                print(f"[manager] Invalid Spotify Track ID: {spotify_track_id}\n")
        
        elif choice.lower() in view_queue_inputs:
            view_queue(engine)
        
        elif choice.lower() in exit_inputs:
            print("[manager] Exiting...")
            time.sleep(3)
            break

        else:
            print("[manager] Invalid choice, please try again.\n")

if __name__ == "__main__":
    main()