"""Тесты для модуля метрик."""

import pytest
import pandas as pd
from datetime import datetime, timedelta

from app.process.metrics import MetricsCalculator
from app.models import SignalType


@pytest.fixture
def calculator():
    """Создать калькулятор метрик."""
    return MetricsCalculator()


@pytest.fixture
def sample_candles():
    """Создать тестовые свечи."""
    # Генерируем 300 свечей для тестирования
    dates = pd.date_range(end=datetime.now(), periods=300, freq='D')
    
    # Создаём тренд: сначала вниз, потом вверх
    prices = []
    base_price = 100.0
    
    for i in range(300):
        if i < 150:
            # Нисходящий тренд
            price = base_price - (i * 0.2)
        else:
            # Восходящий тренд
            price = base_price - 30 + ((i - 150) * 0.3)
        prices.append(price)
    
    df = pd.DataFrame({
        'open': [p * 0.99 for p in prices],
        'high': [p * 1.02 for p in prices],
        'low': [p * 0.98 for p in prices],
        'close': prices,
        'volume': [10000 + i * 100 for i in range(300)],
        'begin': dates,
        'end': dates
    })
    
    return df


def test_calculate_sma(calculator, sample_candles):
    """Тест расчёта SMA."""
    sma_data = calculator.calculate_sma(sample_candles)
    
    assert 'sma_20' in sma_data
    assert 'sma_50' in sma_data
    assert 'sma_200' in sma_data
    
    # Проверяем, что значения вычислены
    assert sma_data['sma_20'] is not None
    assert sma_data['sma_50'] is not None
    assert sma_data['sma_200'] is not None
    
    # SMA должны быть положительными числами
    assert sma_data['sma_20'] > 0
    assert sma_data['sma_50'] > 0
    assert sma_data['sma_200'] > 0


def test_calculate_sma_insufficient_data(calculator):
    """Тест расчёта SMA с недостаточными данными."""
    # Только 10 свечей
    df = pd.DataFrame({
        'close': [100 + i for i in range(10)]
    })
    
    sma_data = calculator.calculate_sma(df)
    
    # SMA20, 50, 200 не должны быть рассчитаны
    assert sma_data['sma_20'] is None
    assert sma_data['sma_50'] is None
    assert sma_data['sma_200'] is None


def test_calculate_52w_range(calculator, sample_candles):
    """Тест расчёта диапазона 52 недель."""
    current_price = sample_candles['close'].iloc[-1]
    range_data = calculator.calculate_52w_range(sample_candles, current_price)
    
    assert 'high_52w' in range_data
    assert 'low_52w' in range_data
    assert 'dist_52w_low_pct' in range_data
    assert 'dist_52w_high_pct' in range_data
    
    # Проверяем логику
    assert range_data['high_52w'] > range_data['low_52w']
    assert range_data['dist_52w_low_pct'] >= 0  # Должно быть положительным
    assert range_data['dist_52w_high_pct'] >= 0


def test_calculate_dividend_yield(calculator):
    """Тест расчёта дивидендной доходности."""
    # Цена 100, дивиденды 8 -> доходность 8%
    dy = calculator.calculate_dividend_yield(div_ttm=8.0, price=100.0)
    assert dy == 8.0
    
    # Цена 200, дивиденды 10 -> доходность 5%
    dy = calculator.calculate_dividend_yield(div_ttm=10.0, price=200.0)
    assert dy == 5.0
    
    # Нулевая цена
    dy = calculator.calculate_dividend_yield(div_ttm=10.0, price=0.0)
    assert dy is None


def test_calculate_volume_spike(calculator, sample_candles):
    """Тест определения всплеска объёма."""
    # Нормальный объём - нет всплеска
    has_spike = calculator.calculate_volume_spike(sample_candles, threshold=1.8)
    # Зависит от данных, но должен вернуть bool
    assert isinstance(has_spike, bool)
    
    # Создаём данные со всплеском
    df = sample_candles.copy()
    # Последний объём делаем в 3 раза больше медианы
    median_vol = df['volume'].tail(20).median()
    df.loc[df.index[-1], 'volume'] = median_vol * 3
    
    has_spike = calculator.calculate_volume_spike(df, threshold=1.8)
    assert has_spike is True


def test_generate_signals_price_below_sma200(calculator, sample_candles):
    """Тест генерации сигнала PRICE_BELOW_SMA200."""
    sma_data = calculator.calculate_sma(sample_candles)
    
    # Цена ниже SMA200
    low_price = sma_data['sma_200'] * 0.9
    signals = calculator.generate_signals(low_price, sma_data, None, sample_candles)
    
    assert SignalType.PRICE_BELOW_SMA200 in signals


def test_generate_signals_price_above_sma200(calculator, sample_candles):
    """Тест генерации сигнала PRICE_ABOVE_SMA200."""
    sma_data = calculator.calculate_sma(sample_candles)
    
    # Цена выше SMA200
    high_price = sma_data['sma_200'] * 1.1
    signals = calculator.generate_signals(high_price, sma_data, None, sample_candles)
    
    assert SignalType.PRICE_ABOVE_SMA200 in signals


def test_generate_signals_dy_gt_target(calculator, sample_candles):
    """Тест генерации сигнала DY_GT_TARGET."""
    sma_data = calculator.calculate_sma(sample_candles)
    
    # Дивидендная доходность выше целевой (8% по умолчанию)
    signals = calculator.generate_signals(100.0, sma_data, 10.0, sample_candles)
    
    assert SignalType.DY_GT_TARGET in signals


def test_calculate_all_metrics(calculator, sample_candles):
    """Тест расчёта всех метрик сразу."""
    current_price = sample_candles['close'].iloc[-1]
    div_ttm = 8.5
    
    metrics = calculator.calculate_all_metrics(sample_candles, current_price, div_ttm)
    
    # Проверяем наличие всех ключей
    assert 'sma_20' in metrics
    assert 'sma_50' in metrics
    assert 'sma_200' in metrics
    assert 'high_52w' in metrics
    assert 'low_52w' in metrics
    assert 'dist_52w_low_pct' in metrics
    assert 'dist_52w_high_pct' in metrics
    assert 'div_ttm' in metrics
    assert 'dy_pct' in metrics
    assert 'signals' in metrics
    
    # Проверяем типы
    assert isinstance(metrics['signals'], list)
    assert metrics['div_ttm'] == div_ttm


def test_empty_candles(calculator):
    """Тест с пустыми свечами."""
    empty_df = pd.DataFrame()
    
    sma_data = calculator.calculate_sma(empty_df)
    assert all(v is None for v in sma_data.values())
    
    range_data = calculator.calculate_52w_range(empty_df, 100.0)
    assert all(v is None for v in range_data.values())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

