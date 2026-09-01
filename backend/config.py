from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "kinnect_user"
    DB_PASSWORD: str = "kdbR85"
    DB_NAME: str = "kinnect_db"

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    VAULT_STORAGE_PATH: str = "./vault_storage"
    VAULT_TOKEN_EXPIRE_MINUTES: int = 10

    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    HF_API_TOKEN: str = ""
    HF_MODEL_ID: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    GROQ_API_KEY: str = ""
    GROQ_MODEL_ID: str = "llama3-8b-8192"
    YOLO_MODEL: str = "yolov8n.pt"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings():
    return Settings()

settings = get_settings()
