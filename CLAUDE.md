# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Bellie is a RAG API over a personal journal: journal text is parsed into dated entries, embedded with OpenAI, stored in Postgres/pgvector, and queried through a FastAPI `/ask` endpoint that retrieves the nearest entries and has Claude answer from them.

## Commands

```bash
source .venv/bin/activate
pip install -r requirements.txt          # pytest is not listed; install it separately

uvicorn main:app --reload                # dev server; Swagger UI at /docs (use the Authorize button for x-api-key)
pytest                                   # run tests
pytest tests/test_rate_limit.py::test_ask_returns_429_after_limit_exceeded   # single test

# Ingest a journal into a database (table must already exist, see README.md for schema)
DB_NAME=bellie_demo JOURNAL_FILE=synthetic_journal.txt python ingest.py

# Manual smoke tests (hit real OpenAI/Anthropic/Postgres)
python retrieve.py
python generate.py
```

Deployment uses the `Procfile` (`uvicorn main:app --host 0.0.0.0 --port $PORT`).

## Architecture

Pipeline: `parser.py` → `ingest.py` (offline, writes to DB) and `retrieve.py` → `generate.py` (online, called from `main.py`).

- **parser.py**: splits raw text on date header lines matching `M/D Weekday` (e.g. `9/26 Saturday`). Entries carry no year in the source, so `parse_journal(raw, year=...)` assigns one (defaults to the current year; `ingest.py` does not override it).
- **ingest.py**: embeds each entry and inserts into `entries(entry_date, content, embedding vector(1536))`. Refuses to run if the table already has rows; `TRUNCATE TABLE entries;` to re-ingest.
- **retrieve.py**: embeds the question and orders by pgvector `<=>` distance, with optional `start_date`/`end_date` filter (applied only when both are given). Returns `(entry_date, content, distance)` tuples, which `generate.py` unpacks positionally.
- **generate.py**: wraps entries in `[Entry: date]` blocks inside a prompt that instructs Claude to treat them as data only and answer solely from them.
- **main.py**: `/ask` requires the `x-api-key` header (compared to `BELLIE_API_KEY` via `secrets.compare_digest`), is rate-limited to 10/min per IP by slowapi (in-memory), and a catch-all exception handler returns a generic 500 instead of leaking details. `/health` is unauthenticated and unlimited.

## Gotchas

- All config comes from `.env`: `BELLIE_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DB_NAME`, `JOURNAL_FILE`, `EMBEDDING_MODEL`, `CLAUDE_MODEL`, `MAX_TOKENS`.
- `ingest.py` hardcodes `text-embedding-3-small`, while `retrieve.py` uses `EMBEDDING_MODEL`. These must be the same model (and 1536 dims) or similarity search is meaningless.
- `retrieve.py` and `generate.py` construct API clients at import time, so tests set dummy keys in `tests/conftest.py` before importing `main`, and monkeypatch `main.retrieve` / `main.generate`. Call `main.limiter.reset()` between tests since rate-limit counts persist in memory.
- `journal.txt` is the real personal journal; `synthetic_journal.txt` is fake data for demos/testing (typically ingested into a separate `bellie_demo` DB).
