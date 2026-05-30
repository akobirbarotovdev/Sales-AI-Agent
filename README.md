# Sales Agent — Multi-Agent AI Lead Generation Pipeline

A production-oriented **multi-agent AI system** that runs a full B2B sales-lead
pipeline end to end: it finds companies, researches decision-makers, scores
each lead, validates contact data, and drafts personalized outreach — all
orchestrated as a stateful agent graph.

Built with **LangGraph**, **Anthropic Claude**, and **FastAPI**, with a live
dashboard for reviewing, editing, and sending.

> Note: This repo includes a **simulation mode** so the entire pipeline and
> dashboard run with zero API keys — useful for demos and local development.

---

## Why this is interesting (engineering highlights)

- **Supervisor-routed agent graph** — a `StateGraph` with a supervisor node that
  decides the next phase; specialized agents return to the supervisor after each
  step, giving a clean, inspectable control flow with checkpointing.
- **Five specialized agents**, each with its own model/timeout budget
  (cost-aware: Haiku for high-volume steps, Sonnet for reasoning-heavy scoring):
  - `lead_generation` — multi-source sourcing (async scrapers + Tavily + LLM)
  - `research` — decision-maker, activity, pain-point enrichment
  - `qualification` — 7-criteria weighted scoring (0–100)
  - `validator` — contact-quality guardrails
  - `email_draft` — personalized, research-grounded outreach
- **Deliverability guardrail** — only contacts whose email was actually *scraped
  from the company site* pass validation into outreach; AI-guessed addresses are
  never emailed (protects sender-domain reputation).
- **Robust LLM JSON parsing** — tolerant extraction from fenced/prose-wrapped
  model output, so real-world responses don't silently fall back to defaults.
- **Async I/O throughout** — concurrent scraping (`asyncio.gather`), background
  pipeline execution so the API never blocks.
- **Full stack** — FastAPI REST API + vanilla-JS dashboard + SQLite (WAL),
  Excel export, SMTP sending.

## Architecture

```
                ┌─────────────┐
        ┌──────▶│  Supervisor │──────┐  (routes to next phase, checkpointed)
        │       └─────────────┘      │
        │                            ▼
        │   lead_generation → research → qualification → validation → email_draft
        │                            │
        └────────────────────────────┘
                                     ▼
                                  finish → results persisted
```

State is a typed `PipelineState` (TypedDict); each agent node updates it and
returns control to the supervisor until all phases complete.

## Tech stack

`Python` · `LangGraph` · `LangChain` · `Anthropic Claude (Sonnet / Haiku)` ·
`FastAPI` · `httpx` / `BeautifulSoup` / `Playwright` (scraping) · `SQLite` ·
`openpyxl` (Excel) · `Tavily` (web search)

## Quick start

```bash
git clone https://github.com/akobirbaratov1/sales-agent.git
cd sales-agent
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # add ANTHROPIC_API_KEY for real mode (optional)
./run.sh                    # → http://localhost:8000
```

Without an API key the system runs in **simulation mode** (mock data) so you can
explore the dashboard and pipeline immediately.

## Project layout

```
agents/      # supervisor + 5 specialized agents (base + per-role prompts)
pipeline/    # LangGraph state machine + typed state
scraping/    # async http + Playwright scrapers, Tavily client
api/         # FastAPI routes + schemas
dashboard/   # single-page review/send UI
database.py  # SQLite layer (pipelines, leads, agent logs)
```

## License

MIT — use it, learn from it, build on it.
