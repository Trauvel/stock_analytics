"""Тесты для генератора отчётов."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
import pandas as pd

from app.process.report import ReportGenerator
from app.models import SymbolData, SymbolMeta


@pytest.fixture
def mock_config():
    """Мок конфигурации."""
    config = Mock()
    config.universe = [
        Mock(symbol='SBER'),
        Mock(symbol='GAZP')
    ]
    config.dividend_target_pct = 8.0
    config.output.analysis_file = 'data/test_analysis.json'
    config.output.reports_dir = 'data/test_reports'
    return config


@pytest.fixture
def mock_candles():
    """Мок данных свечей."""
    dates = pd.date_range(end=datetime.now(), periods=300, freq='D')
    return pd.DataFrame({
        'open': [100.0] * 300,
        'high': [105.0] * 300,
        'low': [95.0] * 300,
        'close': [102.0] * 300,
        'volume': [10000] * 300,
        'begin': dates,
        'end': dates
    })


@patch('app.process.report.get_config')
@patch('app.process.report.MOEXClient')
def test_report_generator_init(mock_client, mock_get_config, mock_config):
    """Тест инициализации генератора."""
    mock_get_config.return_value = mock_config
    
    generator = ReportGenerator()
    
    assert generator.config == mock_config
    assert generator.client is not None
    assert generator.calculator is not None


@patch('app.process.report.get_config')
@patch('app.process.report.MOEXClient')
def test_process_symbol_success(mock_client_class, mock_get_config, mock_config, mock_candles):
    """Тест успешной обработки тикера."""
    mock_get_config.return_value = mock_config
    
    # Настраиваем моки
    mock_client = Mock()
    mock_client.get_quote.return_value = {
        'price': 290.5,
        'lot': 10,
        'board': 'TQBR'
    }
    mock_client.get_dividends.return_value = 25.0
    mock_client.get_candles.return_value = mock_candles
    
    mock_client_class.return_value = mock_client
    
    generator = ReportGenerator()
    result = generator._process_symbol('SBER')
    
    assert isinstance(result, SymbolData)
    assert result.price == 290.5
    assert result.lot == 10
    assert result.div_ttm == 25.0
    assert result.meta.error is None


@patch('app.process.report.get_config')
@patch('app.process.report.MOEXClient')
def test_process_symbol_error(mock_client_class, mock_get_config, mock_config):
    """Тест обработки ошибки при получении данных."""
    mock_get_config.return_value = mock_config
    
    # Настраиваем мок для выброса ошибки
    mock_client = Mock()
    mock_client.get_quote.side_effect = Exception("Connection error")
    
    mock_client_class.return_value = mock_client
    
    generator = ReportGenerator()
    result = generator._process_symbol('INVALID')
    
    assert isinstance(result, SymbolData)
    assert result.price is None
    assert result.meta.error is not None
    assert "Connection error" in result.meta.error


@patch('app.process.report.get_config')
@patch('app.process.report.MOEXClient')
@patch('app.process.report.save_analysis_report')
@patch('app.process.report.save_daily_report')
def test_generate_and_save(mock_save_daily, mock_save_analysis, 
                          mock_client_class, mock_get_config, 
                          mock_config, mock_candles):
    """Тест генерации и сохранения отчёта."""
    mock_get_config.return_value = mock_config
    
    # Настраиваем моки
    mock_client = Mock()
    mock_client.get_quote.return_value = {
        'price': 290.5,
        'lot': 10,
        'board': 'TQBR'
    }
    mock_client.get_dividends.return_value = 25.0
    mock_client.get_candles.return_value = mock_candles
    
    mock_client_class.return_value = mock_client
    
    generator = ReportGenerator()
    report_dict = generator.generate_and_save(save_daily=True)
    
    # Проверяем структуру отчёта
    assert 'generated_at' in report_dict
    assert 'universe' in report_dict
    assert 'by_symbol' in report_dict
    
    # Проверяем, что функции сохранения были вызваны
    assert mock_save_analysis.called
    assert mock_save_daily.called


@patch('app.process.report.get_config')
def test_get_summary(mock_get_config, mock_config):
    """Тест получения сводки по отчёту."""
    mock_get_config.return_value = mock_config
    
    from app.models import AnalysisReport
    
    # Создаём тестовый отчёт
    report = AnalysisReport(
        generated_at=datetime.now(),
        universe=['SBER', 'GAZP'],
        by_symbol={
            'SBER': SymbolData(
                price=290.5,
                lot=10,
                dy_pct=10.0,
                sma_200=280.0,
                meta=SymbolMeta(error=None)
            ),
            'GAZP': SymbolData(
                price=120.0,
                lot=10,
                dy_pct=5.0,
                sma_200=125.0,
                meta=SymbolMeta(error=None)
            )
        }
    )
    
    generator = ReportGenerator()
    summary = generator.get_summary(report)
    
    assert summary['total_symbols'] == 2
    assert summary['successful'] == 2
    assert summary['failed'] == 0
    assert 'SBER' in summary['high_dividend']  # DY > 8%
    assert 'SBER' in summary['above_sma200']  # Цена > SMA200
    assert 'GAZP' in summary['below_sma200']  # Цена < SMA200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

