# SalesBattle

React dashboard and FastAPI service for reviewing CRM conversations and generating evidence-based deal health scores (0-10).

## Start on Windows

From the project root, run this in your own PowerShell terminal:

```powershell
.\Start-SalesBattle.ps1
```

Keep the terminal open, then visit http://localhost:8000. The launcher builds the frontend and starts the backend on loopback only. Stop an older backend with Ctrl+C before restarting. Use `-SkipBuild` only when the frontend build is already current.

First-time installation, if dependencies are missing:

```powershell
python -m venv backend\venv
backend\venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
cd frontend
npm.cmd ci
cd ..
```

Copy `backend/.env.example` to `backend/.env` only if you do not already have a configured file. Set your MySQL credentials, schema mappings, and `OPENAI_API_KEY` there. Never put the key in frontend code. Tested locally with Python 3.14 and Node 24.

For frontend development, run `npm.cmd run dev` inside `frontend` in a second terminal. Vite proxies `/api` to the backend on port 8000.

## Dashboard behavior

- The app selects an actual lead from MySQL or a `?lead=...` link. It displays connection errors and empty states instead of example customers.
- Opening a lead reads its profile, timeline and a valid saved score. GET requests do not call OpenAI. Choose **Generate score** or **Sync Battlecard** to generate a new score; this can incur API usage.
- Saved scores are checked against a fingerprint of the current profile, all configured interaction sources, and configured model. Changed evidence requires a new analysis. Existing older caches will also require one new analysis.
- Editing a lead persists through `PATCH /api/leads/{id}`. Failed saves keep the dialog open. Switching leads aborts obsolete frontend requests.
- Proposals are editable drafts with unconfirmed terms clearly marked. Account views use recorded fields only. Reports download actual lead/timeline/analysis data as JSON. Live notifications and external CRM deep links are not integrated.
- Scores estimate readiness, not calibrated win probability. Validate against labeled won/lost outcomes before operational use.

## Conversation sources

`INTERACTION_SOURCES` lists the enabled sources. The default reads `whats_app`, `ticket_email`, `pm1call_log`, `pm1cti_event`, `customer_thread`, and `rep_thread`. Their columns are defined in `backend/app/repositories/mysql_repo.py`.

Use `generic` to read `TABLE_INTERACTIONS` with the `COL_INT_*` mapping instead, or alongside native sources when the data does not overlap. An enabled source that fails stops analysis; a source excluded from configuration is intentionally not included. Do not enable both representations of the same conversation, or duplicate evidence may be analyzed.

Undated interactions remain undated. Naive database timestamps are interpreted as UTC; convert source timestamps to UTC before importing if your CRM stores local time. A source query order is stabilized by date, channel and ID for reproducible sentiment indices and cache fingerprints.

Long histories are compressed in lossless Unicode-safe input chunks of at most 12,000 UTF-8 bytes, into a rolling structured memory capped at 450 words and 6,000 serialized bytes. Summary processing can add API calls. `MAX_EVIDENCE_BYTES` limits the complete scoring input (default 240,000 bytes); oversize histories fail rather than being silently truncated. Byte limits are not measured token counts. Evidence quotes are checked against source text; this does not guarantee perfect speaker attribution or model accuracy.

## Authentication and hosting

Development without credentials is restricted to loopback requests. To host the app:

1. Set `APP_ENV=production`, `DEBUG=false`, `AUTH_USERNAME`, and a strong unique `AUTH_PASSWORD` of at least 16 characters in the backend environment.
2. Serve behind HTTPS. The browser prompts for HTTP Basic credentials. Those credentials protect the dashboard, API and documentation; never send them over public plain HTTP.
3. Configure explicit `ALLOWED_ORIGINS` only when needed. Keep the backend private to the HTTPS proxy. Do not expose a Vite development server.
4. Use a dedicated database account with only the required lead update, source read and cache privileges. The cache table is initialized on demand, so CREATE privileges are currently required for caching.
5. Run a single application worker for the included in-process duplicate-analysis guard. Multiple workers need a shared job lock and a production rate limiter.

This is a **single-operator, single-CRM database** access model: the authenticated operator can access every lead in that configured database. It is not a multi-tenant service or a role-based CRM authorization integration. Add organization/user ownership rules and SSO before sharing one instance across separate customer organizations. Use infrastructure rate limits for internet-facing deployments.

`ENABLE_TEST_ANALYZE=false` disables the synthetic analysis endpoint by default. Enabling it allows authenticated or local development users to submit synthetic conversation evidence and incur API usage.

## Troubleshooting scores

- **Cannot reach backend:** start the backend in your own terminal and check http://localhost:8000/api/health.
- **Database unavailable/source failure:** verify database credentials and the configured tables/columns. The app does not substitute an empty successful response for a database failure.
- **No current score saved:** use Generate score or Sync Battlecard.
- **Cannot connect to OpenAI:** check connectivity from the backend process. A restricted agent session may block outgoing sockets (Windows error 10013); run the launcher from your own PowerShell. A connection failure does not establish whether the key or quota is valid.
- **Credentials rejected/quota exhausted:** update API credentials or address API project billing as indicated by the specific error.
- **Already running:** wait for the current analysis to finish before retrying. API calls have timeouts; long histories may require multiple calls.
- **Score not saved:** the analysis succeeded, but cache persistence failed. Check MySQL permissions before generating the same score again.

## API

| Method | Endpoint | Behavior |
| --- | --- | --- |
| GET | `/api/health` | Database connectivity; no OpenAI request |
| GET | `/api/leads?offset=0&limit=200` | Paginated leads with string IDs |
| GET | `/api/leads/{id}/timeline` | Profile and configured interaction history |
| GET | `/api/leads/{id}/battlecard` | Current cached score; 409 if generation is needed |
| POST | `/api/leads/{id}/sync` | Generate and cache a score |
| PATCH | `/api/leads/{id}` | Persist validated lead profile changes |
| POST | `/api/leads/test-analyze` | Synthetic analysis, only when explicitly enabled |

Profile updates accept `name`, `company`, `status`, `stage`, and `assigned_to`. Omit unchanged fields. Explicit null/blank changes and unknown fields are rejected.

## Tests

```powershell
cd backend
.\venv\Scripts\python.exe -m unittest discover -s tests -v
cd ..\frontend
npm.cmd test
npm.cmd run lint
npm.cmd run build
```

Backend tests cover database updates, validation, source failures, authentication, cache invalidation, safe errors, and evidence summarization without paid API calls. Frontend tests cover request cancellation, pagination, error handling, rendered zero-score and error states, empty evidence panels, modal initialization and numeric-ID search.

`backend/tests/browser_fixture.py` and `browser_smoke.py` provide optional synthetic browser QA. They never access CRM data or OpenAI. Start the fixture with `python -m uvicorn tests.browser_fixture:app --host 127.0.0.1 --port 18001` from backend. Start a dedicated headless Chrome/Edge profile with remote debugging on port 19229, then run `python tests/browser_smoke.py`. The runner checks editing/reload, failure states, lead switching, search, zero scores, and mobile overflow. Restricted Windows sessions may prevent the browser GPU subprocess from starting; unit tests/build success do not establish that browser QA passed.

## Optional demo database

```powershell
cd backend
.\venv\Scripts\python.exe scripts\init_mock_db.py --database salesbattle_demo
```

The demo script uses your configured MySQL connection credentials but requires a separate database name ending in `_demo`. It does not replace existing lead 123 records. Point `DB_NAME` at that database only when you intentionally want synthetic CRM data. Starting the app never seeds or replaces CRM records.
