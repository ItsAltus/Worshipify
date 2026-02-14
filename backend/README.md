# Worshipify Backend Onboarding

## Purpose
Worshipify backend ingests secular tracks, enriches them with metadata and audio features, and builds a curated Christian-song dataset used for future matching and recommendations.

Current maturity: active work in progress, not production-ready.

## What The Backend Does Today
1. Searches Spotify for track metadata.
2. Builds a YouTube query and downloads audio with `yt-dlp`.
3. Splits audio clips with `ffmpeg`.
4. Sends clips to ReccoBeats for audio features.
5. Pulls and filters tags from Last.fm.
6. Queues and stores Christian tracks in Postgres via seeding tools.

## High-Level Architecture
- API entrypoint: `backend/main.py`
- External integrations and audio processing: `backend/services/spotify.py`
- Last.fm tag retrieval and Christian classification: `backend/services/lastfm.py`
- DB connection + weighted feature math: `backend/seeding/db_helpers.py`
- Queue manager CLI: `backend/seeding/manager.py`
- Queue worker CLI: `backend/seeding/worker.py`
- Dependency smoke test: `backend/tests/test_dependencies.py`
- CI workflow: `.github/workflows/test.yml`

## What Is Not Finished Yet
- `backend/services/matcher.py` is a placeholder.
- `backend/services/mapping.py` is a placeholder.
- No committed DB schema/migration files for required tables.
- CI only runs dependency checks; there are no true unit/integration tests yet.

## Prerequisites
Install and configure before running backend code:

1. Python 3.13.x
2. `ffmpeg` and `ffprobe` on PATH
3. API credentials:
   - Spotify client ID and secret
   - Last.fm API key
4. Postgres database URL for seeding workflows

## Environment Variables
Create `backend/.env` with:

```env
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
LASTFM_API_KEY=...
DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname
```

Notes:
- API endpoints need Spotify and Last.fm variables.
- Seeding manager/worker also need `DATABASE_URL`.

## Local Setup
From repo root:

```powershell
python -m venv backend\venv
backend\venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
```

Run dependency test:

```powershell
$env:PYTHONUTF8='1'
python backend\tests\test_dependencies.py
```

Why `PYTHONUTF8=1`: the test script prints Unicode checkmarks that can fail in some Windows cp1252 terminals.

## Run The API
From repo root with venv active:

```powershell
uvicorn backend.main:app --reload
```

Endpoints:
- `GET /` health
- `GET /search?song=<name>&artist=<optional>`
- `GET /help` pointer to `/docs`

## Seeding Workflow (Queue + Worker)
The seeding system assumes existing DB tables:
- `populate_queue`
- `christian_songs`
- `song_tags`

### Start manager
```powershell
python backend\seeding\manager.py
```

Use manager to:
1. Add single track ID
2. Add album tracks
3. Add playlist tracks
4. Inspect queue status

### Start worker
```powershell
python backend\seeding\worker.py
```

Worker loop behavior:
1. Pull next pending queue job with row locking.
2. Validate Christian status and metadata.
3. Process audio and compute features.
4. Insert song and tags into DB.
5. Mark queue record done or failed.

## Known Risks And Footguns
1. Temp directory cleanup is global (`temp/`) and can conflict under concurrency.
2. Queue status labels are inconsistent between worker and manager wording.
3. `search_song` returns error dicts; callers do not always handle this explicitly.
4. Heuristic-heavy logic means results can drift by API changes or noisy metadata.
5. Missing migrations make environment bootstrapping fragile for new members.

## First-Day Checklist
- [ ] Clone repo and open project in IDE
- [ ] Create and activate Python 3.13 virtual environment
- [ ] Install dependencies from `backend/requirements.txt`
- [ ] Add `backend/.env` with required keys
- [ ] Verify `ffmpeg` and `ffprobe` are accessible
- [ ] Run dependency script successfully
- [ ] Run FastAPI app and confirm `/` and `/docs` work
- [ ] Execute one `/search` request end-to-end

## First-Week Checklist
- [ ] Confirm DB connectivity with `DATABASE_URL`
- [ ] Run manager and enqueue one known Spotify track
- [ ] Run worker and verify DB inserts in all three tables
- [ ] Read and trace `process_single` execution path
- [ ] Review Christian tag filtering logic and allowed genre file
- [ ] Identify one bug or hardening improvement and ship a PR
- [ ] Add at least one test beyond dependency smoke testing

## Suggested Next Engineering Priorities
1. Add Alembic migrations for all referenced tables and constraints.
2. Implement matcher/mapping modules and define recommendation API contract.
3. Replace broad dict/error handling with typed models and explicit exceptions.
4. Make temp-file handling request-scoped for safe parallelism.
5. Build real test coverage for services, API behavior, and worker lifecycle.

## Quick Code Pointers
- API orchestration: `backend/main.py` (`process_single`, `/search`)
- Audio feature pipeline: `backend/services/spotify.py`
- Tag and Christian classification logic: `backend/services/lastfm.py`
- Feature weighting for DB similarity vectors: `backend/seeding/db_helpers.py`
- Queue enqueue UX: `backend/seeding/manager.py`
- Queue processing lifecycle: `backend/seeding/worker.py`

## Definition Of Done For "Backend Is Ready For Wider Contribution"
- [ ] Migrations committed and reproducible DB bootstrap docs added
- [ ] CI runs unit and integration tests, not only dependency checks
- [ ] Clear error model and logging strategy documented
- [ ] Matcher endpoint implemented behind stable contract
- [ ] Concurrency-safe temp and job-processing behavior validated
