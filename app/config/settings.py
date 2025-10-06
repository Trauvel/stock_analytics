"""Настройки приложения из переменных окружения."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Загружаем .env файл
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


class Settings:
    """Настройки приложения из переменных окружения."""
    
    # Логирование
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "data/logs/app.log")
    LOG_ROTATION: str = os.getenv("LOG_ROTATION", "10 MB")
    LOG_RETENTION: str = os.getenv("LOG_RETENTION", "30 days")
    LOG_JSON_FILE: str = os.getenv("LOG_JSON_FILE", "data/logs/app.json.log")
    LOG_FORMAT_JSON: bool = os.getenv("LOG_FORMAT_JSON", "false").lower() == "true"
    
    # Временная зона
    TZ: str = os.getenv("TZ", "Europe/Moscow")
    
    # API настройки
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_RELOAD: bool = os.getenv("API_RELOAD", "false").lower() == "true"
    
    # Планировщик
    DAILY_RUN_TIME: Optional[str] = os.getenv("DAILY_RUN_TIME")  # Переопределяет config.yaml
    SCHEDULER_ENABLED: bool = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
    
    # MOEX API
    MOEX_RATE_LIMIT: Optional[float] = (
        float(os.getenv("MOEX_RATE_LIMIT")) 
        if os.getenv("MOEX_RATE_LIMIT") 
        else None
    )
    
    # Debug режим
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    @classmethod
    def get_effective_log_level(cls) -> str:
        """Получить эффективный уровень логирования."""
        if cls.DEBUG:
            return "DEBUG"
        return cls.LOG_LEVEL
    
    @classmethod
    def display(cls):
        """Вывести все настройки (для отладки)."""
        print("=" * 80)
        print("APPLICATION SETTINGS")
        print("=" * 80)
        print(f"LOG_LEVEL:         {cls.LOG_LEVEL}")
        print(f"LOG_FILE:          {cls.LOG_FILE}")
        print(f"LOG_JSON_FILE:     {cls.LOG_JSON_FILE}")
        print(f"LOG_FORMAT_JSON:   {cls.LOG_FORMAT_JSON}")
        print(f"TZ:                {cls.TZ}")
        print(f"API_HOST:          {cls.API_HOST}")
        print(f"API_PORT:          {cls.API_PORT}")
        print(f"SCHEDULER_ENABLED: {cls.SCHEDULER_ENABLED}")
        print(f"DEBUG:             {cls.DEBUG}")
        print("=" * 80)


# Глобальный экземпляр настроек
settings = Settings()

