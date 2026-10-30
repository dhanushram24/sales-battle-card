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

Calls currently supply `pm1call_log.call_remarks`, not audio recordings. Full call transcripts must be stored in that text field or mapped through the generic interaction source to be analyzed. Telephony duration/disposition alone is not buyer speech. No speech-to-text integration is included.

Undated interactions remain undated. Naive database timestamps are interpreted as UTC; convert source timestamps to UTC before importing if your CRM stores local time. A source query order is stabilized by date, channel and ID for reproducible sentiment indices and cache fingerprints.

## Summary agent and token usage

Long histories use two stages: `EvidencePreparationAgent` produces compact buying evidence, then `OpenAILeadAnalyzer` scores that evidence. The configured scoring model is unchanged. `OPENAI_SUMMARY_MODEL` optionally selects a separate summarization model; blank uses `OPENAI_MODEL`.

- Histories of at most 12,000 UTF-8 bytes go straight to scoring, avoiding an unnecessary summary call.
- Longer histories are read in Unicode-safe chunks and condensed to at most **300 words and 4,000 serialized UTF-8 bytes**, preserving needs, budget, authority, timing, conditional commitments, rejections, objections, competitors, contradictions, unknowns and attributed quotes.
- A completed summary is saved in the separate `lead_evidence_memory` MySQL table before scoring. If scoring fails, its retry can reuse that summary.
- Unchanged conversation history reuses the saved summary with **zero new summarization calls**. Sync still makes a scoring call; simply opening a valid cached battlecard makes no AI calls.
- When conversations are appended, only the appended source plus the saved memory goes to summarization. Original interaction numbering is preserved.
- Editing, deleting, reordering or backfilling earlier conversations invalidates the snapshot and rebuilds it. Model/prompt/budget changes also invalidate summaries. Profile edits can reuse conversation memory because the scorer receives the current profile separately.
- Long-call continuations carry the source header, explicit speaker label and up to 600 preceding characters of context. Repeated context is not counted as new engagement. Scoring prompt/schema changes invalidate saved battlecards.
- Numeric score bands determine the displayed classification. Insufficient evidence is labeled explicitly with low confidence. Replies should acknowledge the actual objection, use verified facts and suggest a concrete next step; explicit requests to stop contact must be respected.
- An incomplete or oversized summary is never saved. Failure to save a completed summary is reported, so repeated processing is not hidden. The original CRM history is never truncated or replaced by the memory.

Expand **Analysis usage** beneath the score to inspect summary mode, reused interaction count, source/scoring byte sizes and provider-reported input/output tokens for the last score generation. Summary and scoring usage are tracked separately. If usage is missing, it displays ?not reported,? not an invented estimate. Completed-call usage is not an invoice reconciliation of failed requests or transport retries.

The first summary must still read the history and can increase total usage compared with one full-history scoring call. Savings are expected from smaller scoring context and reusing memory on later runs; there is no fixed savings percentage. Byte sizes are not token counts and exclude system/schema overhead. Runtime metadata is added in Python rather than generated by the scoring model.

`MAX_EVIDENCE_BYTES` still limits the full source history (default 240,000 bytes). Oversize histories fail instead of being silently truncated. A 300-word memory cannot guarantee perfect semantic fidelity; confidence is not a calibrated probability, and all changes need evaluation against labeled deals.

### Compare semantic accuracy and usage

Nine synthetic long-history cases cover rejection, conditional purchase, approved commitment, later cancellation, rep enthusiasm versus customer intent, multilingual rejection, outbound call attribution, system-only events and instructions embedded in WhatsApp messages. Their score ranges are illustrative review expectations, not production calibration.

Validate fixtures without API calls:

```powershell
cd backend
.\venv\Scripts\python.exe scripts\evaluate_analysis.py
```

To make a paid comparison from a terminal with OpenAI access:

```powershell
.\venv\Scripts\python.exe scripts\evaluate_analysis.py --run-api --output eval-results.json
```

The comparison runs full-history scoring, first-time compact scoring and repeated compact scoring for each case. Review the scores, outlooks, reasoning, retained facts and token usage together. Matching the baseline alone does not prove correctness. Add domain-reviewed real won/lost deals before claiming an accuracy improvement. `--case explicit_rejection` limits the run to one case. No CRM data is sent by this evaluation script.

## Authentication and hosting

Development without credentials is restricted to loopback requests. To host the app:

1. Set `APP_ENV=production`, `DEBUG=false`, `AUTH_USERNAME`, and a strong unique `AUTH_PASSWORD` of at least 16 characters in the backend environment.
2. Serve behind HTTPS. The browser prompts for HTTP Basic credentials. Those credentials protect the dashboard, API and documentation; never send them over public plain HTTP.
3. Configure explicit `ALLOWED_ORIGINS` only when needed. Keep the backend private to the HTTPS proxy. Do not expose a Vite development server.
4. Use a dedicated database account with only the required lead update, source read and cache privileges. The battlecard and evidence-memory tables are initialized on demand, so CREATE privileges are currently required for caching.
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

Backend tests cover database updates, validation, source failures, authentication, cache invalidation, safe errors, evidence summarization, incremental append-only memory, changed-history rebuilds and measured usage without paid API calls. Frontend tests cover request cancellation, pagination, error handling, rendered zero-score and error states, empty evidence panels, modal initialization and numeric-ID search.

`backend/tests/browser_fixture.py` and `browser_smoke.py` provide optional synthetic browser QA. They never access CRM data or OpenAI. Start the fixture with `python -m uvicorn tests.browser_fixture:app --host 127.0.0.1 --port 18001` from backend. Start a dedicated headless Chrome/Edge profile with remote debugging on port 19229, then run `python tests/browser_smoke.py`. The runner checks editing/reload, failure states, lead switching, search, zero scores, and mobile overflow. Restricted Windows sessions may prevent the browser GPU subprocess from starting; unit tests/build success do not establish that browser QA passed.

## Optional demo database

```powershell
cd backend
.\venv\Scripts\python.exe scripts\init_mock_db.py --database salesbattle_demo
```

The demo script uses your configured MySQL connection credentials but requires a separate database name ending in `_demo`. It does not replace existing lead 123 records. Point `DB_NAME` at that database only when you intentionally want synthetic CRM data. Starting the app never seeds or replaces CRM records.
