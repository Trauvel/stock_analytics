"""Тесты для проверки соответствия отчётов JSON схемам."""

import pytest
import json
from pathlib import Path
from datetime import datetime

from app.models import AnalysisReport, Portfolio, Candle


def test_analysis_example_validates():
    """Тест валидации примера analysis.json по схеме."""
    example_path = Path(__file__).parent.parent / "docs" / "examples" / "analysis.json"
    
    with open(example_path, encoding='utf-8') as f:
        data = json.load(f)
    
    # Валидация через Pydantic модель
    report = AnalysisReport(**data)
    
    # Проверки структуры
    assert report.universe
    assert len(report.universe) > 0
    assert report.by_symbol
    
    # Проверка всех тикеров из universe присутствуют в by_symbol
    for ticker in report.universe:
        assert ticker in report.by_symbol


def test_portfolio_example_validates():
    """Тест валидации примера portfolio.json по схеме."""
    example_path = Path(__file__).parent.parent / "docs" / "examples" / "portfolio.json"
    
    with open(example_path, encoding='utf-8') as f:
        data = json.load(f)
    
    # Валидация через Pydantic модель
    portfolio = Portfolio(**data)
    
    # Проверки
    assert portfolio.currency
    assert portfolio.positions
    assert len(portfolio.positions) > 0
    
    # Все позиции должны иметь валидные символы
    for pos in portfolio.positions:
        assert pos.symbol
        assert pos.quantity >= 0


def test_candles_example_validates():
    """Тест валидации примера candles.json по схеме."""
    example_path = Path(__file__).parent.parent / "docs" / "examples" / "candles.json"
    
    with open(example_path, encoding='utf-8') as f:
        data = json.load(f)
    
    # Валидация каждой свечи
    for candle_data in data:
        candle = Candle(**candle_data)
        
        # Проверки
        assert candle.open >= 0
        assert candle.high >= candle.low
        assert candle.close >= 0
        assert candle.volume >= 0


def test_generated_report_validates():
    """Тест валидации сгенерированного отчёта."""
    report_path = Path(__file__).parent.parent / "data" / "analysis.json"
    
    if not report_path.exists():
        pytest.skip("No generated report found, run: python run_job_once.py")
    
    with open(report_path, encoding='utf-8') as f:
        data = json.load(f)
    
    # Валидация через Pydantic
    report = AnalysisReport(**data)
    
    # Проверки
    assert report.generated_at
    assert len(report.universe) > 0
    assert len(report.by_symbol) == len(report.universe)
    
    # Проверяем структуру каждого тикера
    for symbol, symbol_data in report.by_symbol.items():
        assert symbol in report.universe
        
        # Если нет ошибки, должны быть данные
        if symbol_data.meta.error is None:
            assert symbol_data.price is not None
            assert symbol_data.lot is not None
            # signals может быть пустым списком
            assert symbol_data.signals is not None


def test_all_reports_in_archive_validate():
    """Тест валидации всех отчётов в архиве."""
    reports_dir = Path(__file__).parent.parent / "data" / "reports"
    
    if not reports_dir.exists():
        pytest.skip("No reports directory")
    
    report_files = list(reports_dir.glob("*.json"))
    
    if not report_files:
        pytest.skip("No reports in archive")
    
    valid_count = 0
    
    for report_file in report_files:
        with open(report_file, encoding='utf-8') as f:
            data = json.load(f)
        
        # Валидация
        try:
            report = AnalysisReport(**data)
            valid_count += 1
        except Exception as e:
            pytest.fail(f"Report {report_file} failed validation: {e}")
    
    assert valid_count == len(report_files)
    print(f"\nValidated {valid_count} reports from archive")


def test_schema_consistency():
    """Тест согласованности между примерами и схемами."""
    # Все примеры должны соответствовать моделям
    examples_dir = Path(__file__).parent.parent / "docs" / "examples"
    
    # Analysis
    with open(examples_dir / "analysis.json", encoding='utf-8') as f:
        AnalysisReport(**json.load(f))
    
    # Portfolio
    with open(examples_dir / "portfolio.json", encoding='utf-8') as f:
        Portfolio(**json.load(f))
    
    # Candles
    with open(examples_dir / "candles.json", encoding='utf-8') as f:
        candles_data = json.load(f)
        for candle_data in candles_data:
            Candle(**candle_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

