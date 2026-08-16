"""
Configuration Management System for JARVIS OS.
Uses Pydantic BaseSettings to load and validate environment and configuration parameters.
"""

import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings container loaded from environment variables or defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core Application Metadata
    APP_NAME: str = "JARVIS OS"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = True

    # FastAPI Server Options
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    SECRET_KEY: str = "default-jarvis-secret-key-change-me-in-production"

    # Security & Encryption Policies
    VAULT_MASTER_KEY: str = "jarvis-default-master-key-32-chars-long!"
    SENSITIVE_ACTION_CONFIRMATION_REQUIRED: bool = True
    MAX_BULK_DELETE_THRESHOLD: int = 5

    # Storage Databases
    DATABASE_URL: str = "sqlite:///./jarvis_data.db"
    CHROMADB_PATH: str = "./chroma_db"

    # AI Model Providers & Keys
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    DEFAULT_LLM_PROVIDER: str = "gemini"
    DEFAULT_MODEL: str = "gemini-2.0-flash"

    # Voice Assistant Parameters
    STT_MODEL: str = "whisper-base"
    TTS_ENGINE: str = "edge-tts"
    WAKE_WORD: str = "Hey Jarvis"

    # Automation Guardrails
    MAX_STEP_RETRIES: int = 3
    STEP_TIMEOUT_SECONDS: int = 30


# Global settings singleton
settings = Settings()
