"""Загрузка и валидация конфигурации."""

import os
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class TickerConfig(BaseModel):
    """Конфигурация тикера."""
    symbol: str
    market: str = "moex"


class WindowsConfig(BaseModel):
    """Настройки окон для индикаторов."""
    sma: List[int] = Field(default=[20, 50, 200])


class OutputConfig(BaseModel):
    """Настройки выходных файлов."""
    analysis_file: str = "data/analysis.json"
    reports_dir: str = "data/reports"
    raw_data_dir: str = "data/raw"


class ScheduleConfig(BaseModel):
    """Настройки планировщика."""
    daily_time: str = "19:10"
    tz: str = "Europe/Moscow"


class RateLimitConfig(BaseModel):
    """Настройки ограничения скорости."""
    per_symbol_sleep_sec: float = 0.4


class AppConfig(BaseModel):
    """Главная конфигурация приложения."""
    base_currency: str = "RUB"
    universe: List[TickerConfig]
    windows: WindowsConfig = Field(default_factory=WindowsConfig)
    dividend_target_pct: float = 8.0
    output: OutputConfig = Field(default_factory=OutputConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)

    @field_validator('universe')
    @classmethod
    def validate_universe(cls, v):
        """Проверка, что список тикеров не пустой."""
        if not v:
            raise ValueError("Universe cannot be empty")
        return v


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """
    Загрузить конфигурацию из YAML файла.
    
    Args:
        config_path: Путь к файлу конфигурации. Если не указан, используется app/config/config.yaml
        
    Returns:
        AppConfig: Загруженная и валидированная конфигурация
        
    Raises:
        FileNotFoundError: Если файл конфигурации не найден
        ValueError: Если конфигурация невалидна
    """
    if config_path is None:
        # Определяем путь относительно корня проекта
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "app" / "config" / "config.yaml"
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
    
    config = AppConfig(**config_data)
    
    # Создаём необходимые директории
    _ensure_directories(config)
    
    return config


def _ensure_directories(config: AppConfig) -> None:
    """Создать необходимые директории, если они не существуют."""
    project_root = Path(__file__).parent.parent.parent
    
    directories = [
        project_root / config.output.reports_dir,
        project_root / config.output.raw_data_dir,
        project_root / Path(config.output.analysis_file).parent,
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


# Глобальный экземпляр конфигурации (ленивая загрузка)
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """
    Получить глобальный экземпляр конфигурации.
    
    Returns:
        AppConfig: Конфигурация приложения
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config(config_path: Optional[str] = None) -> AppConfig:
    """
    Перезагрузить конфигурацию.
    
    Args:
        config_path: Путь к файлу конфигурации
        
    Returns:
        AppConfig: Обновлённая конфигурация
    """
    global _config
    _config = load_config(config_path)
    return _config

