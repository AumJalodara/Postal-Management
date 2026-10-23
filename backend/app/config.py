import os
from typing import List, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)


class Settings(BaseSettings):
    APPLICATION_ENV: str = "development"
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/smart_postal_db"
    JWT_SECRET: str = "super-secret-dev-key-change-in-production-min32chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440  # 24 hours
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    PROJECT_NAME: str = "Smart Postal Management System"
    API_V1_PREFIX: str = "/api/v1"

    # Frontend and CORS settings
    FRONTEND_URL: str = "http://localhost:5173"
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]

    # Module 3 Step 4 Dense & Hybrid Retrieval
    DENSE_MODEL_ID: str = "sentence-transformers/all-MiniLM-L6-v2"
    DENSE_EMBEDDING_DIR: str = os.path.join(PROJECT_ROOT, "data", "postal_documents", "embeddings")
    POSTAL_RETRIEVAL_DEFAULT_MODE: str = "hybrid"
    RRF_K: int = 60

    # Module 3 Step 6 RAG / LLM Provider
    LLM_PROVIDER: str = "groq"  # "groq" for demo, "mock" for offline tests, "gemini" for alternative real LLM
    GOOGLE_API_KEY: str = ""  # Set via environment variable only
    LLM_MODEL_NAME: str = "gemini-2.0-flash"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Module 4 Step 4 Intelligent Agent Assignment
    AGENT_DISTANCE_WEIGHT: float = 0.6
    AGENT_WORKLOAD_WEIGHT: float = 0.4

    # Module 4 Step 6 ETA Estimation
    ETA_AVERAGE_SPEED_KMPH: float = 30.0
    ETA_SERVICE_TIME_MINUTES_PER_STOP: float = 5.0
    ETA_BUFFER_MINUTES: float = 10.0

    # OTP Configuration
    OTP_VALIDITY_MINUTES: int = 15

    # Rate Limiting Configuration (OWASP API4:2023)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_STORAGE_URL: str = "memory://"
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_REGISTER: str = "5/minute"
    RATE_LIMIT_OTP: str = "10/minute"
    RATE_LIMIT_RAG: str = "10/minute"
    RATE_LIMIT_OPS_ASSISTANT: str = "10/minute"
    RATE_LIMIT_GENERAL: str = "100/minute"

    @property
    def is_production(self) -> bool:
        return self.APPLICATION_ENV.strip().lower() == "production"

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def canonicalize_sqlite_path(cls, v: str) -> str:
        """Ensure relative SQLite database URLs resolve to the canonical backend/smart_postal.db"""
        if v.startswith("sqlite:///") and not v.startswith("sqlite:////"):
            db_path = v[len("sqlite:///"):]
            if not os.path.isabs(db_path):
                # Clean prefix like ./
                clean_name = os.path.basename(db_path) if db_path.startswith("./") or db_path.startswith(".\\") else db_path
                abs_path = os.path.normpath(os.path.join(BACKEND_DIR, clean_name))
                return f"sqlite:///{abs_path}"
        return v

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        """
        Enforce cryptographic security policies.
        Prevents starting in production with missing, short, or default placeholder JWT secrets.
        """
        if self.is_production:
            secret = (self.JWT_SECRET or "").strip()
            if not secret:
                raise ValueError(
                    "CRITICAL CONFIGURATION ERROR: JWT_SECRET must be set in production environments."
                )
            if len(secret) < 32:
                raise ValueError(
                    f"CRITICAL CONFIGURATION ERROR: Production JWT_SECRET length ({len(secret)}) "
                    f"is below the minimum requirement of 32 characters (256-bit entropy)."
                )
            known_insecure_defaults = [
                "super-secret-dev-key-change-in-production-min32chars",
                "change-in-production",
                "secret-key",
                "default-secret",
            ]
            if any(placeholder in secret.lower() for placeholder in known_insecure_defaults):
                raise ValueError(
                    "CRITICAL CONFIGURATION ERROR: Known development placeholder detected in JWT_SECRET. "
                    "Production requires a cryptographically random secret key."
                )
        return self

    model_config = SettingsConfigDict(
        env_file=(
            os.path.join(BACKEND_DIR, ".env"),
            os.path.join(PROJECT_ROOT, ".env"),
            ".env"
        ),
        env_file_encoding="utf-8",
        extra="ignore"
    )



settings = Settings()
