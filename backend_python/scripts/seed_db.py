#!/usr/bin/env python3
from uuid import uuid4
from datetime import datetime
import json
from database import SessionLocal, Base, engine, User, ConversationContext

# Ensure tables exist
Base.metadata.create_all(bind=engine)

def seed():
    db = SessionLocal()
    try:
        # Create user
        user_id = str(uuid4())
        user = User(
            id=user_id,
            username='demo',
            email='demo@example.com',
            password_hash='demo',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(user)

        # Create conversation context
        context = ConversationContext(
            id=str(uuid4()),
            user_id=user_id,
            connection_id='seed-conn',
            messages=json.dumps([]),
            recent_tasks=json.dumps([]),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(context)

        db.commit()
        print('Seed successful')
        print(f'User id: {user_id}')
    except Exception as e:
        db.rollback()
        print('Seed failed:', e)
    finally:
        db.close()

if __name__ == '__main__':
    seed()
