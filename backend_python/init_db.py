#!/usr/bin/env python3
"""Initialize database tables from SQLAlchemy models"""

from database import Base, engine, SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """Create all tables in database"""
    try:
        logger.info("Dropping existing database tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("✓ Existing tables dropped")
        
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Database tables created successfully!")
        
        # Test connection
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("✓ Database connection verified!")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

if __name__ == "__main__":
    init_db()
