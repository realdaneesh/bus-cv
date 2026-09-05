import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./bus_cv.db"
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    
    # Event Processor settings
    DETECTION_CONFIDENCE_THRESHOLD: float = 0.60
    EVENT_COOLDOWN_SECONDS: int = 30
    DUPLICATE_PROXIMITY_METERS: float = 35.0
    
    ACTIVE_BUS_CODE: str = "BUS_01"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
