# Voice Controlled Task Manager

Web app for managing tasks by voice: browser speech recognition, spoken replies, a FastAPI WebSocket backend, **PostgreSQL** storage, and **Ollama** (e.g. Mistral) for intent and conversation.

## Repository layout

```
urban_ground_task/
├── frontend/          # Next.js (App Router), voice UI
├── backend_python/    # FastAPI, WebSocket `/ws/chat`, SQLAlchemy + Postgres
└── README.md
```

## Prerequisites

- Node.js 18+
- Python 3.10+ (3.9 may work)
- PostgreSQL
- [Ollama](https://ollama.com/) with the `mistral` model: `ollama pull mistral`

## Backend

```bash
cd backend_python
pip install -r requirements.txt
# Copy and edit: DATABASE_URL, OLLAMA_URL, CORS_ORIGIN
python init_db.py   # if you use the project’s DB bootstrap script
uvicorn main:app --reload --host 0.0.0.0 --port 8888
```

See `backend_python/README.md` for details.

## Frontend

```bash
cd frontend
npm install
# Optional .env.local:
# NEXT_PUBLIC_API_URL=http://localhost:8888
# NEXT_PUBLIC_WS_URL=ws://localhost:8888/ws/chat
npm run dev
```

Open `http://localhost:3000`, use **Initialize Demo Data** if you want the shared demo user, then speak using the microphone control.

## Run both services (from repo root)

```bash
npm install
npm run setup
npm run backend:install   # once: Python deps for FastAPI
npm run dev               # backend :8888 + frontend :3000
```

## How it works

- **STT / TTS**: Web Speech API in the browser (no typed task commands in the main flow).
- **CRUD**: Messages go over the WebSocket; the model returns structured actions; the server updates Postgres. Deletes require an explicit **yes** after the assistant asks to confirm.
- **Reconnect**: The WebSocket client reconnects automatically after a drop.
