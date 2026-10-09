import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

_BASE_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BASE_DIR / ".env"
if _ENV_FILE.exists():
    load_dotenv(dotenv_path=_ENV_FILE)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="allow")

    APP_NAME: str = "CareerPulse AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # SerpApi
    SERPAPI_API_KEY: str = os.getenv("SERPAPI_API_KEY", "")
    SERPAPI_CACHE_ENABLED: bool = bool(int(os.getenv("SERPAPI_CACHE_ENABLED", "1")))
    
    # Base paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    CACHE_DIR: Path = BASE_DIR / "cache"
    SAMPLE_DATA_DIR: Path = BASE_DIR / "sample_data"
    
    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "mock")  # "mock", "gemini", "openai"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

settings = Settings()
settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
