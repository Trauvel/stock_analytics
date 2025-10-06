"""Тесты для Pydantic моделей."""

import pytest
import json
from datetime import datetime
from pathlib import Path

from app.models import (
    AnalysisReport,
    SymbolData,
    Portfolio,
    Position,
    Candle,
    SignalType,
    PositionType
)


def test_symbol_data_creation():
    """Тест создания данных по тикеру."""
    data = SymbolData(
        price=285.50,
        lot=10,
        div_ttm=25.20,
        dy_pct=8.83,
        signals=[SignalType.PRICE_ABOVE_SMA200, SignalType.DY_GT_TARGET]
    )
    
    assert data.price == 285.50
    assert data.lot == 10
    assert len(data.signals) == 2
    assert SignalType.DY_GT_TARGET in data.signals


def test_analysis_report_from_example():
    """Тест загрузки отчёта из примера."""
    example_path = Path(__file__).parent.parent / "docs" / "examples" / "analysis.json"
    
    with open(example_path, encoding='utf-8') as f:
        data = json.load(f)
    
    report = AnalysisReport(**data)
    
    assert report.universe == ["SBER", "GAZP", "LKOH"]
    assert "SBER" in report.by_symbol
    assert report.by_symbol["SBER"].price == 285.50
    assert report.by_symbol["LKOH"].meta.error is not None


def test_portfolio_from_example():
    """Тест загрузки портфеля из примера."""
    example_path = Path(__file__).parent.parent / "docs" / "examples" / "portfolio.json"
    
    with open(example_path, encoding='utf-8') as f:
        data = json.load(f)
    
    portfolio = Portfolio(**data)
    
    assert portfolio.name == "Основной портфель"
    assert portfolio.currency == "RUB"
    assert portfolio.cash == 50000.00
    assert len(portfolio.positions) == 4


def test_position_creation():
    """Тест создания позиции."""
    position = Position(
        symbol="SBER",
        quantity=100,
        avg_price=265.30,
        type=PositionType.STOCK
    )
    
    assert position.symbol == "SBER"
    assert position.quantity == 100
    assert position.market == "moex"


def test_candle_validation():
    """Тест валидации свечи."""
    candle = Candle(
        open=283.50,
        high=287.20,
        low=282.10,
        close=285.50,
        volume=125430000,
        begin=datetime.now(),
        end=datetime.now()
    )
    
    assert candle.high >= candle.low
    assert candle.volume >= 0


def test_candle_invalid_high_low():
    """Тест невалидной свечи (high < low)."""
    with pytest.raises(ValueError):
        Candle(
            open=283.50,
            high=280.00,  # Меньше low
            low=282.10,
            close=285.50,
            volume=125430000,
            begin=datetime.now(),
            end=datetime.now()
        )


def test_empty_universe_validation():
    """Тест валидации пустого universe."""
    with pytest.raises(ValueError, match="Universe cannot be empty"):
        AnalysisReport(
            generated_at=datetime.now(),
            universe=[],
            by_symbol={}
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

