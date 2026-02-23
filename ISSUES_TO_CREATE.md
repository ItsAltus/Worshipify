# Issue Drafts: TODOs, Upgrades, and Optimizations

Use the following drafts to create GitHub issues in this repository.

## 1) Upgrade vulnerable frontend dependencies

**Title:** Upgrade Next.js and lint toolchain to patched versions  
**Labels:** `dependencies`, `security`, `frontend`

**Problem**
- `npm audit` currently reports 18 vulnerabilities (including 1 critical) in the frontend dependency tree.
- `next@15.3.1` is flagged by multiple advisories and should be upgraded to a patched 15.x release.

**Scope**
- Upgrade `next`, `eslint`, and related lint dependencies to patched, compatible versions.
- Regenerate lockfile and verify `npm run lint` and `npm run build`.

**Acceptance Criteria**
- `npm audit` reports no critical vulnerabilities.
- Frontend lint/build still pass after dependency upgrades.

---

## 2) Clean up backend Python dependencies

**Title:** Remove deprecated/duplicate packages from `backend/requirements.txt`  
**Labels:** `dependencies`, `backend`, `maintenance`

**Problem**
- `backend/requirements.txt` includes both `dotenv` and `python-dotenv`.
- `dotenv==0.9.9` is legacy/unmaintained and duplicates purpose.
- Both `psycopg2` and `psycopg2-binary` are pinned at the same time.

**Scope**
- Remove redundant/deprecated entries.
- Keep one PostgreSQL driver strategy and document rationale.
- Re-run dependency validation test.

**Acceptance Criteria**
- `backend/requirements.txt` no longer includes `dotenv==0.9.9`.
- Only one of `psycopg2` / `psycopg2-binary` remains (or documented exception exists).
- `python backend/tests/test_dependencies.py` passes in CI environment.

---

## 3) Replace scaffolded frontend placeholders with project-specific content

**Title:** Replace default Next.js starter page/metadata with Worshipify branding  
**Labels:** `frontend`, `enhancement`, `product`

**Problem**
- Frontend still contains mostly default `create-next-app` UI and metadata (`Create Next App`).
- `frontend/README.md` is also default scaffold text.

**Scope**
- Update app metadata and homepage content to reflect Worshipify.
- Update `frontend/README.md` with project-relevant setup and architecture notes.

**Acceptance Criteria**
- No remaining “Create Next App” placeholder metadata.
- Homepage reflects Worshipify use case instead of starter template.
- Frontend README documents actual local development workflow for this repo.

---

## 4) Implement matching logic module currently stubbed

**Title:** Implement `backend/services/matcher.py` song matching logic  
**Labels:** `backend`, `feature`, `algorithm`

**Problem**
- `backend/services/matcher.py` is currently a stub with only a module docstring.

**Scope**
- Implement matching functions used to compare candidate worship songs against extracted features/tags.
- Add unit tests for matching behavior and ranking edge cases.

**Acceptance Criteria**
- `matcher.py` exposes concrete, documented functions.
- Tests cover deterministic ranking and tie/empty-result behavior.

---

## 5) Implement mapping helper module currently stubbed

**Title:** Implement `backend/services/mapping.py` tag/genre mapping utilities  
**Labels:** `backend`, `feature`, `data`

**Problem**
- `backend/services/mapping.py` is currently a stub with only a module docstring.

**Scope**
- Add normalization/mapping helpers for tag canonicalization used by recommendation pipeline.
- Add tests for normalization and alias handling.

**Acceptance Criteria**
- `mapping.py` contains concrete mapping utilities with docstrings.
- Tests validate expected mappings for representative genre/tag inputs.

---

## 6) Improve frontend build reliability in restricted-network CI/dev environments

**Title:** Avoid build-time dependency on Google Fonts network fetch  
**Labels:** `frontend`, `ci`, `reliability`

**Problem**
- `npm run build` can fail in restricted environments due to `next/font/google` fetch errors (`fonts.googleapis.com` DNS/network unavailable).

**Scope**
- Replace remote font dependency with local/self-hosted font strategy or robust fallback.
- Ensure production build does not hard-fail when external font endpoints are unreachable.

**Acceptance Criteria**
- Frontend build succeeds in environments without outbound access to Google Fonts.
- Visual regression is acceptable and documented.
