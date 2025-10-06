"""Тесты для системы логирования."""

import pytest
import tempfile
from pathlib import Path
import json

from app.utils.logging import setup_logging, json_formatter
from app.utils.context_logger import log_operation, get_ticker_logger
from app.config.settings import Settings
from loguru import logger


def test_settings_load():
    """Тест загрузки настроек из окружения."""
    assert Settings.LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR"]
    assert Settings.API_PORT > 0
    assert Settings.TZ is not None


def test_logging_initialization():
    """Тест инициализации логирования."""
    # Логгер должен быть настроен при импорте
    assert logger is not None


def test_ticker_logger():
    """Тест логгера с контекстом тикера."""
    ticker_logger = get_ticker_logger("SBER")
    
    assert ticker_logger.ticker == "SBER"
    
    # Должны работать без ошибок
    ticker_logger.info("Test message")
    ticker_logger.debug("Debug message")
    ticker_logger.warning("Warning message")


def test_log_operation_success():
    """Тест успешной операции с логированием."""
    with log_operation("test_operation", ticker="SBER"):
        # Операция выполняется
        result = 1 + 1
    
    assert result == 2


def test_log_operation_with_error():
    """Тест операции с ошибкой."""
    with pytest.raises(ValueError):
        with log_operation("test_operation", ticker="GAZP"):
            raise ValueError("Test error")


def test_json_formatter():
    """Тест JSON форматтера."""
    # Создаём фейковую запись лога
    from datetime import datetime
    
    record = {
        "time": datetime.now(),
        "level": type('Level', (), {'name': 'INFO'}),
        "name": "test_module",
        "function": "test_function",
        "line": 42,
        "message": "Test message",
        "extra": {}
    }
    
    result = json_formatter(record)
    
    # Проверяем что это валидный JSON
    parsed = json.loads(result)
    
    assert parsed["level"] == "INFO"
    assert parsed["module"] == "test_module"
    assert parsed["message"] == "Test message"
    assert "timestamp" in parsed


def test_context_logging():
    """Тест контекстного логирования."""
    # Используем контекст
    with logger.contextualize(ticker="LKOH", operation="test"):
        logger.info("Message with context")
    
    # Без контекста
    logger.info("Message without context")


def test_setup_logging_custom():
    """Тест настройки логирования с кастомными параметрами."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        log_file = Path(tmp_dir) / "test.log"
        
        # Настраиваем отдельный логгер для теста
        from loguru import logger as test_logger
        test_logger.remove()
        
        handler_id = test_logger.add(
            log_file,
            format="{time} | {level} | {message}",
            level="DEBUG"
        )
        
        test_logger.info("Test message")
        
        # Проверяем что файл создан
        assert log_file.exists()
        
        # Удаляем handler перед очисткой директории
        test_logger.remove(handler_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

