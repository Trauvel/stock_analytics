"""Тесты для модуля конфигурации."""

import pytest
from pathlib import Path

from app.config.loader import load_config, AppConfig


def test_load_config():
    """Тест загрузки конфигурации."""
    config = load_config()
    
    # Проверка базовых настроек
    assert config.base_currency == "RUB"
    assert config.dividend_target_pct == 8.0
    
    # Проверка universe
    assert len(config.universe) > 0
    assert all(ticker.market == "moex" for ticker in config.universe)
    
    # Проверка наличия основных тикеров
    symbols = [ticker.symbol for ticker in config.universe]
    assert "SBER" in symbols
    assert "GAZP" in symbols
    assert "LKOH" in symbols
    
    # Проверка окон SMA
    assert config.windows.sma == [20, 50, 200]
    
    # Проверка выходных настроек
    assert config.output.analysis_file == "data/analysis.json"
    assert config.output.reports_dir == "data/reports"
    
    # Проверка расписания
    assert config.schedule.daily_time == "19:10"
    assert config.schedule.tz == "Europe/Moscow"
    
    # Проверка rate limit
    assert config.rate_limit.per_symbol_sleep_sec == 0.4


def test_config_directories_created():
    """Тест создания необходимых директорий."""
    config = load_config()
    
    project_root = Path(__file__).parent.parent
    
    # Проверка существования директорий
    assert (project_root / config.output.reports_dir).exists()
    assert (project_root / config.output.raw_data_dir).exists()


def test_ticker_config():
    """Тест конфигурации тикеров."""
    config = load_config()
    
    for ticker in config.universe:
        assert ticker.symbol  # Не пустой
        assert ticker.market == "moex"
        assert ticker.symbol.isupper()  # Тикеры в верхнем регистре


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

