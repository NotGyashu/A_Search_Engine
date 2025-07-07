# Environment Configuration
import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 1
    
    # Database Configuration
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "search_engine"
    POSTGRES_USER: str = "search_user"
    POSTGRES_PASSWORD: str = "search_password"
    
    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # AI/ML Configuration
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    HF_TOKEN: Optional[str] = None  # Hugging Face token
    
    # Search Configuration
    MAX_SEARCH_RESULTS: int = 10
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    LLM_MODEL: str = "gpt-3.5-turbo"
    
    # Data Paths
    DATA_RAW_PATH: str = "../data/raw"
    DATA_PROCESSED_PATH: str = "../data/processed"
    DATA_EMBEDDINGS_PATH: str = "../data/embeddings"
    
    # Performance
    BATCH_SIZE: int = 100
    MAX_CONTENT_LENGTH: int = 10000  # Max chars for LLM context
    
    class Config:
        env_file = ".env"

settings = Settings()

# Database URL
DATABASE_URL = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
