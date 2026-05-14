from database import SessionLocal, Task
from uuid import uuid4
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class TaskService:
    @staticmethod
    def create_task(user_id: str, title: str, description: str = "", due_date=None, due_time: str = "", priority: str = "medium", tags: list = None):
        """Create a new task in database"""
        try:
            db = SessionLocal()
            task = Task(
                id=str(uuid4()),
                user_id=user_id,
                title=title,
                description=description,
                due_date=due_date,
                due_time=due_time,
                priority=priority,
                tags=json.dumps(tags or []),
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            db.close()
            logger.info(f"Task created: {task.id}")
            return task
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            raise
    
    @staticmethod
    def get_user_tasks(user_id: str):
        """Get all tasks for a user"""
        try:
            db = SessionLocal()
            tasks = db.query(Task).filter(Task.user_id == user_id).all()
            db.close()
            return [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "dueDate": t.due_date,
                    "dueTime": t.due_time,
                    "priority": t.priority,
                    "completed": t.completed,
                    "tags": json.loads(t.tags) if t.tags else [],
                }
                for t in tasks
            ]
        except Exception as e:
            logger.error(f"Error fetching tasks: {e}")
            return []
    
    @staticmethod
    def get_task(user_id: str, task_id: str):
        """Get a specific task"""
        try:
            db = SessionLocal()
            task = db.query(Task).filter(Task.id == task_id, Task.user_id == user_id).first()
            db.close()
            if task:
                return {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "dueDate": task.due_date,
                    "dueTime": task.due_time,
                    "priority": task.priority,
                    "completed": task.completed,
                    "tags": json.loads(task.tags) if task.tags else [],
                }
            return None
        except Exception as e:
            logger.error(f"Error fetching task: {e}")
            return None
    
    @staticmethod
    def update_task(user_id: str, task_id: str, updates: dict):
        """Update a task"""
        try:
            db = SessionLocal()
            task = db.query(Task).filter(Task.id == task_id, Task.user_id == user_id).first()
            if task:
                for key, value in updates.items():
                    if key == "tags" and isinstance(value, list):
                        setattr(task, key, json.dumps(value))
                    elif hasattr(task, key):
                        setattr(task, key, value)
                task.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(task)
                logger.info(f"Task updated: {task.id}")
                db.close()
                return task
            db.close()
            return None
        except Exception as e:
            logger.error(f"Error updating task: {e}")
            return None
    
    @staticmethod
    def delete_task(user_id: str, task_id: str):
        """Delete a task"""
        try:
            db = SessionLocal()
            task = db.query(Task).filter(Task.id == task_id, Task.user_id == user_id).first()
            if task:
                db.delete(task)
                db.commit()
                logger.info(f"Task deleted: {task_id}")
                db.close()
                return True
            db.close()
            return False
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            return False
    
    @staticmethod
    def complete_task(user_id: str, task_id: str):
        """Mark a task as complete"""
        try:
            db = SessionLocal()
            task = db.query(Task).filter(Task.id == task_id, Task.user_id == user_id).first()
            if task:
                task.completed = True
                task.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(task)
                logger.info(f"Task completed: {task.id}")
                db.close()
                return task
            db.close()
            return None
        except Exception as e:
            logger.error(f"Error completing task: {e}")
            return None
