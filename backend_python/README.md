# Voice Task Manager — Backend (Python)

FastAPI service: **WebSocket** `/ws/chat` for voice-driven task CRUD, **PostgreSQL** via SQLAlchemy, and **Ollama** (Mistral) for intent and replies.

## Prerequisites

- Python **3.10+** (3.9 often works)
- **PostgreSQL** reachable from this machine
- **[Ollama](https://ollama.com/)** with the **mistral** model: `ollama pull mistral`

## Environment variables (`.env.local`)

Configuration uses **Pydantic Settings** (`config.py`). It loads from:

1. **Process environment** (shell exports, Docker `env`, platform env)
2. File **`.env.local`** in this directory: **`backend_python/.env.local`**

Create `backend_python/.env.local` next to `main.py`. **Do not commit** real secrets; the file should be gitignored.

Restart the server after editing env vars.

### Variables

| Variable | Required | Default (if unset) | Description |
|----------|----------|--------------------|-------------|
| `DATABASE_URL` | No* | `postgresql://taskuser:taskpass123@localhost:5432/voice_task_manager` | SQLAlchemy Postgres URL |
| `OLLAMA_URL` | No | `http://localhost:11434` | Ollama HTTP API base |
| `BACKEND_PORT` | No | `8888` | Port for `python main.py` / Uvicorn |
| `WEBSOCKET_PORT` | No | `8888` | Documented for symmetry; HTTP and WS share the same server port |
| `CORS_ORIGIN` | No | `http://localhost:3000` | Allowed browser origin for the Next.js app |
| `JWT_SECRET` | No | (dev placeholder) | Reserved for future auth — change in production |
| `JWT_EXPIRY` | No | `7d` | Reserved for future auth |
| `NODE_ENV` | No | `development` | Optional label; not used by Node here |

\*Required in practice: Postgres must exist and match this URL (or your override).

### Example `backend_python/.env.local`

```bash
# Database (match your Postgres / docker-compose)
DATABASE_URL=postgresql://taskuser:taskpass123@localhost:5432/voice_task_manager

# Ollama
OLLAMA_URL=http://localhost:11434

# Server
BACKEND_PORT=8888

# Frontend origin (CORS)
CORS_ORIGIN=http://localhost:3000

# Future auth — set strong values if you add login
JWT_SECRET=change-me-in-production
JWT_EXPIRY=7d
```

`main.py` also calls `load_dotenv(".env.local")` so the same file is available to any code using `os.environ` early in startup.

## Setup

### 1. Virtual environment (recommended)

```bash
cd backend_python
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Database

With Postgres running and `DATABASE_URL` correct, create tables **once** (dev only — drops existing tables):

```bash
python init_db.py
```

Docker Postgres from **repository root** (credentials match the default `DATABASE_URL` above):

```bash
cd ..
docker compose up -d postgres
cd backend_python
```

### 4. Ollama

Ensure the Ollama daemon is running. Optional: keep the model loaded:

```bash
ollama run mistral
```

## Run the server

From **`backend_python/`** with the venv activated.

### Option A — `python main.py`

```bash
python main.py
```

Listens on `0.0.0.0` and **`BACKEND_PORT`** (default **8888**). No `--reload`.

### Option B — Uvicorn with reload (development)

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8888
```

Adjust the port if it differs from `BACKEND_PORT`.

### Option C — `run.sh`

Runs `pip install` then Uvicorn with reload:

```bash
bash run.sh
```

## Quick checks

| URL / action | Purpose |
|--------------|---------|
| `GET http://localhost:8888/` | API root |
| `GET http://localhost:8888/health` | Health |
| `POST http://localhost:8888/init-demo` | Ensure demo user (optional) |
| `WebSocket ws://localhost:8888/ws/chat` | Voice session |

## Architecture

- **FastAPI** — HTTP + WebSocket on one process
- **SQLAlchemy** — PostgreSQL
- **Ollama** — `mistral` (see `services/ai_assistant.py`)
- **WebSocket `/ws/chat`** — task CRUD for the voice app (no separate REST task API)

## Related docs

- **Frontend env & run:** `../frontend/README.md`
- **Monorepo overview:** `../README.md`
