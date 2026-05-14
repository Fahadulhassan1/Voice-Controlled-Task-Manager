import os
import re
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json
from uuid import uuid4
from datetime import datetime, date
from config import settings
from database import SessionLocal, User, ConversationContext
from services.ai_assistant import AIAssistant
from services.task_service import TaskService
import dateutil.parser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ai_assistant = None
websocket_manager = None

from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), ".env.local")
load_dotenv(env_path)

logger.info(f"[STARTUP] OLLAMA_URL configured: {settings.OLLAMA_URL}")

_AFFIRMATIVE = re.compile(
    r"^(yes|yeah|yep|yup|confirm)(\s|$|,|\.)|^\s*y\s*$",
    re.I,
)
_NEGATIVE = re.compile(
    r"^(no|nope|nah|n)\b|^\s*n\s*$|^(don\'t|dont|cancel|abort|stop)\b",
    re.I,
)


def _is_affirmative(text: str) -> bool:
    t = (text or "").strip().lower()
    return bool(_AFFIRMATIVE.search(t))


def _is_negative(text: str) -> bool:
    t = (text or "").strip().lower()
    return bool(_NEGATIVE.search(t))


def _task_label(tasks: list, task_id: str) -> str:
    for t in tasks:
        if t.get("id") == task_id:
            return t.get("title") or "that task"
    return "that task"


class WebSocketManager:
    def __init__(self):
        self.active_connections: dict = {}
        self.contexts: dict = {}

    def connect(self, connection_id: str, websocket: WebSocket):
        self.active_connections[connection_id] = websocket
        logger.info(f"Client added: {connection_id}")

    def disconnect(self, connection_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.contexts:
            del self.contexts[connection_id]
        logger.info(f"Client removed: {connection_id}")

    def get_context(self, connection_id: str, user_id: str):
        if connection_id not in self.contexts:
            self.contexts[connection_id] = {
                "userId": user_id,
                "connectionId": connection_id,
                "messages": [],
                "recentTasks": [],
                "lastAction": None,
                "confirmationPending": False,
            }
        return self.contexts[connection_id]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ai_assistant, websocket_manager
    ai_assistant = AIAssistant()
    websocket_manager = WebSocketManager()
    logger.info("AIAssistant initialized successfully with Ollama (mistral)")
    yield
    logger.info("Shutting down...")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CORS_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Voice Task Manager Backend"}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "voice-task-manager"}


@app.post("/init-demo")
async def init_demo():
    """Create a demo user and conversation context if they don't exist and return the user id."""
    db = None
    try:
        db = SessionLocal()
        demo = db.query(User).filter(User.email == "demo@example.com").first()
        if not demo:
            demo = User(
                id=str(uuid4()),
                username="demo",
                email="demo@example.com",
                password_hash="demo",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(demo)
            db.commit()

        ctx = db.query(ConversationContext).filter(ConversationContext.user_id == demo.id).first()
        if not ctx:
            ctx = ConversationContext(
                id=str(uuid4()),
                user_id=demo.id,
                connection_id="init-demo",
                messages="[]",
                recent_tasks="[]",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(ctx)
            db.commit()

        return {"userId": demo.id}
    except Exception as e:
        logger.error(f"Error initializing demo: {e}")
        return {"error": str(e)}
    finally:
        if db is not None:
            db.close()


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    connection_id = str(uuid4())[:8]
    await websocket.accept()

    websocket_manager.connect(connection_id, websocket)
    logger.info("New WebSocket connection established")

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)

            user_id = message_data.get("userId", f"user_{int(__import__('time').time() * 1000)}")
            user_message = message_data.get("message", "")
            client_says_confirm = message_data.get("isConfirmation", False)

            logger.info(f"Processing: {user_message} (user: {user_id})")

            context = websocket_manager.get_context(connection_id, user_id)

            try:
                user_tasks = TaskService.get_user_tasks(user_id)
                pending = context.get("confirmationPending")
                last = context.get("lastAction") or {}
                pending_kind = last.get("pendingKind")
                action_details: dict = {}
                action = "NONE"
                response_text = ""

                # --- Pending delete confirmation (voice yes/no; client flag optional) ---
                if pending and pending_kind == "DELETE":
                    if _is_negative(user_message):
                        response_text = "Okay, I won't delete anything."
                        action = "NONE"
                        context["confirmationPending"] = False
                        context["lastAction"] = None
                    elif client_says_confirm or _is_affirmative(user_message):
                        tid = (last.get("actionDetails") or {}).get("taskId")
                        if tid:
                            try:
                                TaskService.delete_task(user_id, tid)
                                label = _task_label(user_tasks, tid)
                                response_text = f"Done. I've removed {label}."
                                action = "DELETE_TASK"
                                logger.info(f"✓ Task deleted after confirmation: {tid}")
                            except Exception as e:
                                logger.error(f"Delete error: {e}")
                                response_text = "I couldn't delete that task. Please try again."
                                action = "NONE"
                        else:
                            response_text = "I still need to know which task to delete. Could you say the task name again?"
                            action = "CLARIFY"
                        context["confirmationPending"] = False
                        context["lastAction"] = None
                    else:
                        # New utterance while waiting — cancel delete wait and treat as a new command
                        context["confirmationPending"] = False
                        context["lastAction"] = None
                        result = ai_assistant.process_user_message(
                            user_message,
                            context["messages"],
                            user_tasks,
                        )
                        action = result.get("action", "NONE")
                        action_details = result.get("actionDetails", {}) or {}
                        response_text = result.get("response", "")
                        action, action_details, response_text = _apply_delete_safety_and_clarify(
                            action, action_details, response_text, user_tasks, context
                        )
                else:
                    result = ai_assistant.process_user_message(
                        user_message,
                        context["messages"],
                        user_tasks,
                    )
                    action = result.get("action", "NONE")
                    action_details = result.get("actionDetails", {}) or {}
                    response_text = result.get("response", "")
                    action, action_details, response_text = _apply_delete_safety_and_clarify(
                        action, action_details, response_text, user_tasks, context
                    )

                # --- Execute non-delete actions ---
                if action == "CREATE_TASK":
                    try:
                        title = action_details.get("title", "New Task")
                        due_time = action_details.get("dueTime", "")
                        due_date_val = None
                        if due_time:
                            try:
                                parsed = dateutil.parser.parse(due_time)
                                if parsed.year == 1900:
                                    today = datetime.now()
                                    parsed = parsed.replace(
                                        year=today.year, month=today.month, day=today.day
                                    )
                                due_date_val = parsed
                            except Exception:
                                due_date_val = datetime.combine(date.today(), datetime.min.time())

                        task = TaskService.create_task(
                            user_id=user_id,
                            title=title,
                            due_date=due_date_val,
                            due_time=due_time,
                            description=action_details.get("description", ""),
                            priority="medium",
                        )
                        logger.info(f"✓ Task created: {task.id}")
                    except Exception as e:
                        logger.error(f"Create error: {e}")
                        response_text = f"I couldn't create that task. {str(e)}"

                elif action == "CREATE_MULTIPLE_TASKS":
                    tasks_to_create = action_details.get("tasks", [])
                    try:
                        for task_info in tasks_to_create:
                            tt = task_info.get("dueTime", "")
                            due_date_val = None
                            if tt:
                                try:
                                    parsed = dateutil.parser.parse(tt)
                                    if parsed.year == 1900:
                                        today = datetime.now()
                                        parsed = parsed.replace(
                                            year=today.year, month=today.month, day=today.day
                                        )
                                    due_date_val = parsed
                                except Exception:
                                    due_date_val = datetime.combine(date.today(), datetime.min.time())

                            TaskService.create_task(
                                user_id=user_id,
                                title=task_info.get("title", "Task"),
                                due_date=due_date_val,
                                due_time=task_info.get("dueTime", ""),
                                description=task_info.get("description", ""),
                                priority="medium",
                            )
                        logger.info(f"✓ Created {len(tasks_to_create)} tasks")
                    except Exception as e:
                        logger.error(f"Create multiple error: {e}")

                elif action == "UPDATE_TASK":
                    task_id = action_details.get("taskId")
                    new_time = action_details.get("newTime")
                    if task_id and new_time:
                        try:
                            TaskService.update_task(user_id, task_id, {"due_time": new_time})
                            logger.info(f"✓ Task updated: {task_id}")
                        except Exception as e:
                            logger.error(f"Update error: {e}")

                elif action == "CLARIFY":
                    if action_details.get("requiresConfirmation") and action_details.get("taskId"):
                        context["confirmationPending"] = True
                        context["lastAction"] = {
                            "pendingKind": "DELETE",
                            "actionDetails": {
                                "taskId": action_details.get("taskId"),
                                "taskName": action_details.get("taskName", ""),
                            },
                        }
                    # else: non-delete clarification — do not hold confirmation state

                context["messages"].append({"role": "user", "content": user_message})
                context["messages"].append({"role": "assistant", "content": response_text})

                if len(context["messages"]) > 20:
                    context["messages"] = context["messages"][-20:]

                updated_tasks = TaskService.get_user_tasks(user_id)
                frontend_tasks = [
                    {
                        "id": t["id"],
                        "title": t["title"],
                        "description": t.get("description"),
                        "dueDate": str(t["dueDate"]) if t.get("dueDate") else None,
                        "dueTime": t.get("dueTime"),
                        "priority": t.get("priority"),
                        "completed": t.get("completed", False),
                        "tags": t.get("tags", []),
                        "createdAt": "",
                        "updatedAt": "",
                    }
                    for t in updated_tasks
                ]

                requires_confirmation = bool(
                    action == "CLARIFY"
                    and action_details.get("requiresConfirmation")
                    and action_details.get("taskId")
                )

                await websocket.send_json(
                    {
                        "success": True,
                        "response": response_text,
                        "action": action,
                        "message": response_text,
                        "tasks": frontend_tasks,
                        "requiresConfirmation": requires_confirmation,
                    }
                )

                try:
                    db = SessionLocal()
                    record = (
                        db.query(ConversationContext)
                        .filter(ConversationContext.connection_id == connection_id)
                        .first()
                    )
                    if not record:
                        record = (
                            db.query(ConversationContext)
                            .filter(ConversationContext.user_id == user_id)
                            .first()
                        )

                    if record:
                        record.messages = json.dumps(context.get("messages", []))
                        record.recent_tasks = json.dumps([t for t in frontend_tasks])
                        record.updated_at = datetime.utcnow()
                        db.add(record)
                        db.commit()
                    else:
                        new_ctx = ConversationContext(
                            id=str(uuid4()),
                            user_id=user_id,
                            connection_id=connection_id,
                            messages=json.dumps(context.get("messages", [])),
                            recent_tasks=json.dumps([t for t in frontend_tasks]),
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )
                        db.add(new_ctx)
                        db.commit()
                except Exception as e:
                    logger.error(f"Failed to persist conversation context: {e}")
                finally:
                    try:
                        db.close()
                    except Exception:
                        pass

            except Exception as e:
                logger.error(f"Error: {e}", exc_info=True)
                await websocket.send_json(
                    {
                        "success": False,
                        "error": str(e),
                        "message": "Something went wrong. Please try again.",
                    }
                )

    except WebSocketDisconnect:
        websocket_manager.disconnect(connection_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(connection_id)


def _apply_delete_safety_and_clarify(
    action: str,
    action_details: dict,
    response_text: str,
    user_tasks: list,
    context: dict,
) -> tuple:
    """
    Never execute DELETE from the model in one shot: require explicit user confirmation.
    """
    if action != "DELETE_TASK":
        return action, action_details, response_text

    tid = action_details.get("taskId")
    if not tid and action_details.get("taskName"):
        for t in user_tasks:
            if (t.get("title") or "").lower() == (action_details.get("taskName") or "").lower():
                tid = t.get("id")
                action_details["taskId"] = tid
                break

    if tid:
        label = _task_label(user_tasks, tid)
        ask = response_text.strip() if response_text else ""
        if not ask or "delete" not in ask.lower():
            ask = f"Should I delete {label}? Say yes to confirm."
        context["confirmationPending"] = True
        context["lastAction"] = {
            "pendingKind": "DELETE",
            "actionDetails": {"taskId": tid, "taskName": action_details.get("taskName", label)},
        }
        return (
            "CLARIFY",
            {"requiresConfirmation": True, "taskId": tid, "taskName": label},
            ask,
        )

    return (
        "CLARIFY",
        {"requiresConfirmation": False},
        response_text or "I couldn't find a matching task to delete. Can you describe it again?",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.BACKEND_PORT)
