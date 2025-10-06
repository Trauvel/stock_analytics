"""Тесты для модуля хранилища."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
import pandas as pd

from app.store.io import (
    save_json,
    load_json,
    save_table_parquet,
    load_table_parquet,
    save_candles,
    load_candles,
    save_analysis_report,
    save_daily_report,
    load_analysis_report,
    save_portfolio,
    load_portfolio,
    StorageError
)


def test_save_load_json(tmp_path):
    """Тест сохранения и загрузки JSON."""
    test_data = {
        "symbol": "SBER",
        "price": 290.5,
        "metrics": {
            "sma_20": 285.3,
            "sma_50": 280.1
        }
    }
    
    file_path = tmp_path / "test.json"
    
    # Сохраняем
    save_json(file_path, test_data)
    assert file_path.exists()
    
    # Загружаем
    loaded_data = load_json(file_path)
    assert loaded_data == test_data


def test_save_load_parquet(tmp_path):
    """Тест сохранения и загрузки Parquet."""
    # Создаём тестовый DataFrame
    df = pd.DataFrame({
        'open': [100.0, 101.0, 102.0],
        'high': [105.0, 106.0, 107.0],
        'low': [99.0, 100.0, 101.0],
        'close': [104.0, 105.0, 106.0],
        'volume': [1000, 1100, 1200]
    })
    
    file_path = tmp_path / "test.parquet"
    
    # Сохраняем
    save_table_parquet(file_path, df)
    assert file_path.exists()
    
    # Загружаем
    loaded_df = load_table_parquet(file_path)
    pd.testing.assert_frame_equal(df, loaded_df)


def test_save_load_candles(tmp_path):
    """Тест сохранения и загрузки свечей."""
    df = pd.DataFrame({
        'open': [290.0, 291.0],
        'high': [295.0, 296.0],
        'low': [289.0, 290.0],
        'close': [294.0, 295.0],
        'volume': [10000, 11000],
        'begin': pd.to_datetime(['2025-10-05', '2025-10-06']),
        'end': pd.to_datetime(['2025-10-05', '2025-10-06'])
    })
    
    # Сохраняем
    symbol = "SBER"
    file_path = save_candles(symbol, df, base_dir=tmp_path)
    
    assert file_path.exists()
    assert file_path == tmp_path / symbol / "candles.parquet"
    
    # Загружаем
    loaded_df = load_candles(symbol, base_dir=tmp_path)
    assert loaded_df is not None
    assert len(loaded_df) == len(df)


def test_load_nonexistent_candles(tmp_path):
    """Тест загрузки несуществующих свечей."""
    result = load_candles("NONEXISTENT", base_dir=tmp_path)
    assert result is None


def test_save_analysis_report(tmp_path):
    """Тест сохранения отчёта анализа."""
    report_data = {
        "generated_at": "2025-10-06T19:10:00+03:00",
        "universe": ["SBER", "GAZP"],
        "by_symbol": {
            "SBER": {
                "price": 290.5,
                "dy_pct": 11.98
            }
        }
    }
    
    file_path = tmp_path / "analysis.json"
    save_analysis_report(report_data, file_path)
    
    assert file_path.exists()
    loaded = load_analysis_report(file_path)
    assert loaded == report_data


def test_save_daily_report(tmp_path):
    """Тест сохранения ежедневного отчёта."""
    report_data = {
        "generated_at": "2025-10-06T19:10:00+03:00",
        "universe": ["SBER"]
    }
    
    test_date = datetime(2025, 10, 6)
    file_path = save_daily_report(report_data, date=test_date, reports_dir=tmp_path)
    
    assert file_path.exists()
    assert file_path.name == "2025-10-06.json"
    
    loaded = load_json(file_path)
    assert loaded == report_data


def test_save_load_portfolio(tmp_path):
    """Тест сохранения и загрузки портфеля."""
    portfolio_data = {
        "name": "Тестовый портфель",
        "currency": "RUB",
        "cash": 100000.0,
        "positions": [
            {"symbol": "SBER", "quantity": 100}
        ]
    }
    
    file_path = tmp_path / "portfolio.json"
    save_portfolio(portfolio_data, file_path)
    
    assert file_path.exists()
    
    loaded = load_portfolio(file_path)
    assert loaded == portfolio_data


def test_load_nonexistent_portfolio(tmp_path):
    """Тест загрузки несуществующего портфеля."""
    file_path = tmp_path / "nonexistent.json"
    result = load_portfolio(file_path)
    assert result is None


def test_auto_directory_creation(tmp_path):
    """Тест автоматического создания директорий."""
    # Создаём путь с несуществующими вложенными директориями
    deep_path = tmp_path / "level1" / "level2" / "level3" / "test.json"
    
    test_data = {"test": "data"}
    save_json(deep_path, test_data)
    
    assert deep_path.exists()
    assert deep_path.parent.exists()


def test_json_with_datetime():
    """Тест сохранения JSON с datetime (должен сериализоваться)."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_data = {
            "timestamp": datetime.now().isoformat(),
            "data": "test"
        }
        
        file_path = Path(tmp_dir) / "test.json"
        save_json(file_path, test_data)
        
        loaded = load_json(file_path)
        assert loaded["data"] == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

