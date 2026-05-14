from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Server
    BACKEND_PORT: int = 8888
    WEBSOCKET_PORT: int = 8888
    NODE_ENV: str = "development"
    
    # Database
    DATABASE_URL: str = "postgresql://taskuser:taskpass123@localhost:5432/voice_task_manager"
    
    # Ollama
    OLLAMA_URL: str = "http://localhost:11434"
    
    # JWT
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_EXPIRY: str = "7d"
    
    # CORS
    CORS_ORIGIN: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env.local"
        case_sensitive = True
        extra = "ignore"  # Ignore extra env vars

settings = Settings()
