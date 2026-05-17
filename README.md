# BrandIntel

> AI-Powered Brand Threat Monitoring for the Agentic Era

BrandIntel is a multi-source threat monitoring engine that continuously scans external data sources for your brand mentions, then uses an LLM security analyst to classify real threats and alert you instantly via Slack.

---

## The Problem

AI coding agents push thousands of commits every minute. API keys slip into `.env` files, service account credentials land in public repos, and internal configs leak through commit messages — all at AI speed. Traditional keyword-only monitoring produces massive false positives and alert fatigue. Security teams miss real threats in the noise.

## How BrandIntel Solves It

```
Scan 4 sources → Detect with 5 strategies → Classify with AI → Alert via Slack
```

1. **Scans** GitHub, HackerNews, ransomware victim lists, and breach databases 24/7
2. **Detects** brand mentions using exact, fuzzy, regex, domain similarity, and email pattern matching
3. **Classifies** every hit through an LLM security analyst that determines if it's a real threat
4. **Alerts** instantly via Slack when the AI confirms a genuine threat — with severity, confidence, and AI reasoning

---

## Data Sources

| Source | What It Catches | API Key Required |
|--------|----------------|-----------------|
| **GitHub** | Leaked credentials in code, secrets in `.env` files, brand mentions in commits | GitHub PAT |
| **HackerNews** | Brand discussions, security incident mentions, public exposure threads | Free |
| **Ransomware.live** | Brand appearing as ransomware victim, leak site listings | Free |
| **XposedOrNot** | Domain/email in known data breach databases | Free |

## Detection Engine — 5 Matching Strategies

| Strategy | What It Detects | Confidence |
|----------|----------------|------------|
| **Exact** | Case-insensitive keyword/substring match | 1.0 |
| **Email Pattern** | Regex extraction of emails matching your domain | 1.0 |
| **Fuzzy** | Typosquat detection via Levenshtein distance (85% threshold) | ratio/100 |
| **Regex** | Custom regex rules per brand | 0.9 |
| **Domain Similarity** | Lookalike domains, homograph attacks (80% threshold) | similarity |

## AI Enrichment Pipeline

Every detected hit is sent to an LLM security analyst for classification:

```
Raw Hit → LLM Analyst → JSON Classification → Decision
```

The LLM returns:
- **is_threat**: true/false
- **severity**: CRITICAL / HIGH / MEDIUM / LOW
- **confidence**: 0.0–1.0
- **threat_types**: credential_leak, pii_exposure, api_key_leak, source_code_leak, database_dump, configuration_leak, internal_document
- **reasoning**: detailed analysis
- **recommended_action**: ALERT / SUPPRESS / ESCALATE_HUMAN

Decision thresholds:
- Confidence >= 0.85 + LLM says ALERT → **ALERT**
- Confidence >= 0.70 → **ALERT**
- Confidence >= 0.60 → **ESCALATE** (human review queue)
- Confidence < 0.60 → **SUPPRESS** (false positive)

Supports any OpenAI-compatible provider — GPT-4, Claude, Gemini, OpenRouter, or local Ollama.

---

## Architecture

```
Monitoring Daemon
├── GitHub Monitor        (code search, commit search, sensitive files)
├── HackerNews Monitor    (stories, comments)
├── Ransomware Monitor    (victim lists, leak sites)
├── XposedOrNot Monitor   (breach database, email checks)
│
├── Orchestrator          (parallel execution, semaphore-controlled concurrency)
├── KeywordMatcher        (5 matching strategies, confidence scoring)
├── Hit Storage           (SHA-256 content dedup, batch operations)
│
├── Enrichment Service    (LLM threat analysis, batch processing)
├── Alert Manager         (Slack webhook, deduplication, alert history)
│
├── Circuit Breaker       (OPEN/CLOSED/HALF_OPEN, auto-recovery)
├── Dead Letter Queue     (failed item retry, 3 attempts)
└── Health Check Server   (port 8001, DB ping, stats)
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB (local or remote)
- GitHub Personal Access Token (free tier works)
- LLM API key (OpenRouter free tier works)

### 1. Clone and Configure

```bash
git clone <repo-url>
cd brand-intel

# Create backend config
cp backend/.env.example backend/.env
# Edit backend/.env with your keys:
#   - MONGODB_URI
#   - LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
#   - GITHUB_TOKEN
```

### 2. Install Dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt
cd ..

# Frontend
cd frontend
npm install
cd ..
```

### 3. Start MongoDB

```bash
docker run -d --name brand-intel-mongo \
  -e MONGO_INITDB_ROOT_USERNAME=root \
  -e MONGO_INITDB_ROOT_PASSWORD=example \
  -p 27017:27017 \
  mongo:7
```

### 4. Start All Services

```bash
./start.sh
```

This launches:
- **FastAPI server** — http://localhost:8000
- **API docs** (Swagger) — http://localhost:8000/docs
- **React frontend** — http://localhost:3000

### 5. Start the Monitoring Daemon

```bash
cd backend
python daemon.py
```

The daemon runs continuously and:
- Scans all active brands every 15 minutes
- Processes pending hits through LLM enrichment every 5 minutes
- Retries DLQ items every 30 minutes
- Runs health checks every hour

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MONGODB_URI` | Yes | `mongodb://localhost:27017` | MongoDB connection string |
| `LLM_API_KEY` | Yes* | — | OpenAI-compatible API key |
| `LLM_BASE_URL` | Yes* | `https://api.openai.com/v1` | LLM endpoint URL |
| `LLM_MODEL` | Yes* | `gpt-4o` | Model name |
| `GITHUB_TOKEN` | Optional | — | GitHub PAT for code search |
| `SLACK_WEBHOOK_URL` | Optional | — | Slack webhook for alerts |
| `SCAN_INTERVAL_MINUTES` | No | 15 | Brand scan frequency |
| `ENRICHMENT_ENABLED` | No | true | Enable LLM enrichment |

*Required when `ENRICHMENT_ENABLED=true`

---

## API Endpoints (28 total)

### Brands
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/brands` | List all brands with stats |
| POST | `/api/v1/brands` | Create a brand |
| GET | `/api/v1/brands/{id}` | Get brand details |
| PUT | `/api/v1/brands/{id}` | Update brand |
| DELETE | `/api/v1/brands/{id}` | Delete brand |
| PATCH | `/api/v1/brands/{id}/toggle` | Toggle active/inactive |

### Monitors
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/monitors/status` | All monitors status + circuit breaker |
| POST | `/api/v1/monitors/trigger` | Trigger all monitors |
| GET | `/api/v1/monitors/runs` | Monitor run history |
| GET | `/api/v1/monitors/{type}/health` | Specific monitor health |

### Hits
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/hits` | List hits (paginated, filtered) |
| GET | `/api/v1/hits/{id}` | Hit details |
| PATCH | `/api/v1/hits/{id}/status` | Update hit status |
| GET | `/api/v1/hits/stats` | Statistics (source, status, timeline) |

### Enrichment
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/enrichment/config` | LLM config |
| PUT | `/api/v1/enrichment/config` | Update enrichment config |
| GET | `/api/v1/enrichment/stats` | Enrichment statistics |
| GET | `/api/v1/enrichment/llm-calls` | Recent LLM calls |
| GET | `/api/v1/enrichment/llm-calls/stats` | LLM call telemetry |
| POST | `/api/v1/enrichment/process/{hit_id}` | Manually process a hit |

### Health & Admin
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Basic health check |
| GET | `/api/v1/health/detailed` | Full system health |
| GET | `/api/v1/admin/dlq` | List dead letter queue items |
| POST | `/api/v1/admin/dlq/{id}/retry` | Retry DLQ item |
| POST | `/api/v1/admin/circuit-breaker/reset` | Reset circuit breaker |

---

## Dashboard Pages

| Page | Path | Description |
|------|------|-------------|
| **Dashboard** | `/` | Key metrics, 7-day timeline, source breakdown, top keywords |
| **Brands** | `/brands` | Brand CRUD, per-brand monitor toggles |
| **Monitors** | `/monitors` | Manual trigger, status cards, circuit breaker, run history |
| **Alerts** | `/alerts` | Hit viewer with filters, CSV export, status management |
| **Enrichment** | `/enrichment` | LLM config, decision pie chart, LLM call stats, manual processing |
| **Admin** | `/admin` | System health, DLQ management, cleanup |

---

## Resilience Features

- **Circuit Breaker** — Disables failing monitors after 5 consecutive errors, auto-retries after 5 minutes
- **Dead Letter Queue** — Stores failed operations for automatic retry (up to 3 attempts)
- **Content Deduplication** — SHA-256 hash prevents duplicate alerts per brand
- **Rate Limiting** — Token bucket pattern per data source to respect API limits
- **Exponential Backoff** — Retries with jitter on transient failures
- **Alert Deduplication** — Threat alerts deduplicated by hit_id within 24 hours

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API Server | FastAPI + Uvicorn |
| Backend | Python 3.11, async/await |
| Database | MongoDB (Motor async driver) |
| LLM | OpenAI-compatible (OpenRouter, Ollama, Gemini, Azure) + Anthropic |
| Matching | rapidfuzz, difflib |
| Scheduling | APScheduler |
| Frontend | React + TypeScript + Vite |
| Charts | Recharts |
| Testing | pytest + pytest-asyncio |

---

## Running Tests

```bash
cd backend
python -m pytest tests/test_monitors.py -v
```

---

## Project Structure

```
brand-intel/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routes, models, dependencies
│   │   ├── daemon/            # Scheduler, circuit breaker, alerting, DLQ
│   │   ├── enrichment/        # LLM providers, threat analysis service
│   │   ├── monitors/          # 4 data source monitors + matching engine
│   │   └── models/            # Pydantic/MongoDB schemas
│   ├── tests/
│   ├── .env.example
│   ├── requirements.txt
│   └── daemon.py              # Daemon entry point
├── frontend/
│   └── src/
│       ├── api/               # API client layer
│       ├── components/        # Reusable UI components
│       ├── pages/             # 6 dashboard pages
│       └── types/             # TypeScript interfaces
├── start.sh                   # Launch all services
├── start-daemon.sh            # Daemon only
├── start-api.sh               # FastAPI only
└── start-frontend.sh          # React frontend only
```
