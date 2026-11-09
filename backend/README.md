# SalesBattle Backend Service

FastAPI-powered semantic intelligence engine and deal health prediction service for Paramantra CRM.

---

## Architecture Overview

```
backend/
├── app/
│   ├── api/
│   │   └── routes.py             # REST API endpoints & SSE streaming handlers
│   ├── core/
│   │   ├── config.py             # Pydantic Settings & environment variables
│   │   ├── database.py           # SQLAlchemy database connection pool
│   │   └── security.py           # Local/remote authentication middleware
│   ├── repositories/
│   │   ├── base.py               # Abstract repository contracts
│   │   └── mysql_repo.py         # MySQL queries across Paramantra CRM tables
│   ├── schemas/
│   │   ├── battlecard.py         # Pydantic schemas for Battlecard & Metrics
│   │   └── lead.py               # Lead profile and interaction schemas
│   └── services/
│       ├── analyzer.py           # OpenAI structured output analyzer
│       ├── battlecard_service.py # Orchestrator & caching service
│       ├── evidence_agent.py     # Rolling evidence summarizer & memory agent
│       ├── summary.py            # Chunker & compressor
│       └── providers/            # Multi-provider LLM routing layer
│           ├── base.py           # Abstract BaseLLMProvider & ProviderError
│           ├── router.py         # Failover router (OpenAI -> Gemini -> Heuristic)
│           ├── openai_provider.py# OpenAI GPT-4o-mini implementation
│           ├── gemini_provider.py# Google Gemini 1.5 Flash implementation
│           └── offline_provider.py# Deterministic offline heuristic engine
├── scripts/
│   ├── init_mock_db.py           # Database table initialization
│   ├── seed_pipeline_leads.py    # Seed realistic multi-channel opportunities
│   └── check_openai.py           # OpenAI connection diagnostics
└── tests/                        # 54+ unit tests covering all components
```

---

## Environment Variables (`backend/.env`)

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `DB_HOST` | `127.0.0.1` | MySQL Host |
| `DB_PORT` | `3306` | MySQL Port |
| `DB_USER` | `root` | MySQL Username |
| `DB_PASSWORD` | - | MySQL Password |
| `DB_NAME` | `paramantra_salesbattle` | MySQL Database Name |
| `OPENAI_API_KEY` | - | Optional OpenAI API Key |
| `OPENAI_MODEL` | `gpt-4o-mini` | Primary OpenAI Model |
| `GEMINI_API_KEY` | - | Optional Google Gemini API Key |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Secondary Gemini Model |
| `LLM_PROVIDER` | `auto` | `auto`, `openai`, `gemini`, or `offline` |
| `ALLOW_OFFLINE_FALLBACK` | `True` | Fallback to heuristic engine on auth/quota errors |

---

## Development Setup

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

# Run Unit Tests
python -m unittest discover -s tests -v

# Start Local Dev Server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

