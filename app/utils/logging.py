"""Настройка логирования."""

import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger


def json_formatter(record: Dict[str, Any]) -> str:
    """
    Форматировать запись лога в JSON.
    
    Args:
        record: Запись лога от loguru
        
    Returns:
        str: JSON строка
    """
    log_entry = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
        "message": record["message"],
    }
    
    # Добавляем дополнительный контекст если есть
    if record.get("extra"):
        log_entry["extra"] = record["extra"]
    
    return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(
    level: str = "INFO",
    log_file: str = "data/logs/app.log",
    json_log_file: Optional[str] = None,
    rotation: str = "10 MB",
    retention: str = "30 days",
    enable_json: bool = False
):
    """
    Настроить логирование приложения.
    
    Args:
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
        log_file: Путь к обычному файлу логов
        json_log_file: Путь к JSON файлу логов (если None, не создаётся)
        rotation: Ротация файлов (размер или время)
        retention: Время хранения логов
        enable_json: Включить JSON формат для основного файла
    """
    # Удаляем дефолтный handler
    logger.remove()
    
    # Консольный вывод с цветами
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
        colorize=True,
        enqueue=True  # Thread-safe
    )
    
    # Создаём директорию для логов
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Основной файл логов
    if enable_json:
        # JSON формат
        logger.add(
            log_file,
            format=json_formatter,
            level=level,
            rotation=rotation,
            retention=retention,
            compression="zip",
            serialize=True,
            enqueue=True
        )
    else:
        # Текстовый формат
        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            level=level,
            rotation=rotation,
            retention=retention,
            compression="zip",
            enqueue=True
        )
    
    # Отдельный JSON файл логов (если указан)
    if json_log_file:
        json_path = Path(json_log_file)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            json_log_file,
            format=json_formatter,
            level=level,
            rotation=rotation,
            retention=retention,
            compression="zip",
            serialize=True,
            enqueue=True
        )
    
    logger.info(f"Logging initialized at level {level}")
    logger.debug(f"Log file: {log_file}")
    if json_log_file:
        logger.debug(f"JSON log file: {json_log_file}")


def get_logger():
    """Получить настроенный логгер."""
    return logger


def add_context(**kwargs):
    """
    Добавить контекст к логам.
    
    Usage:
        with add_context(ticker="SBER", operation="fetch"):
            logger.info("Processing...")
    """
    return logger.contextualize(**kwargs)


# Инициализация при импорте
from app.config.settings import settings

setup_logging(
    level=settings.get_effective_log_level(),
    log_file=settings.LOG_FILE,
    json_log_file=settings.LOG_JSON_FILE if settings.LOG_FORMAT_JSON else None,
    rotation=settings.LOG_ROTATION,
    retention=settings.LOG_RETENTION,
    enable_json=settings.LOG_FORMAT_JSON
)

