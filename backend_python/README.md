# Python Backend for Voice Task Manager

## Setup

### 1. Install Python Dependencies

```bash
cd backend_python
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env.local`:
- `OLLAMA_URL`: Should point to your Ollama instance (default: http://localhost:11434)
- `DATABASE_URL`: PostgreSQL connection string (default: postgresql://taskuser:taskpass123@localhost:5432/voice_task_manager)

### 3. Ensure Ollama is Running

In another terminal:
```bash
ollama run mistral
```

### 4. Start Backend

```bash
bash run.sh
```

Or directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8888
```

## HTTP / WebSocket

- `GET /` — API root
- `GET /health` — Health check
- `POST /init-demo` — Ensures demo user + context (optional for local testing)
- `WebSocket /ws/chat` — Voice conversation and task actions (CRUD is driven here only)

## Architecture

- **FastAPI**: Modern async web framework
- **SQLAlchemy**: ORM for PostgreSQL
- **Ollama**: Local LLM integration
- **WebSocket**: Real-time chat
