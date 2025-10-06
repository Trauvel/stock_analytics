"""Тесты для MOEX клиента."""

import pytest
from datetime import datetime
import pandas as pd

from app.ingest.moex_client import MOEXClient, MOEXClientError


# Пропускаем тесты если нет подключения к интернету
pytestmark = pytest.mark.skip(reason="Requires internet connection, run manually")


def test_get_quote():
    """Тест получения котировки."""
    client = MOEXClient(rate_limit_sleep=0.5)
    
    # Тестируем на надёжном тикере
    result = client.get_quote("SBER")
    
    assert 'price' in result
    assert 'lot' in result
    assert 'board' in result
    
    assert result['price'] > 0
    assert result['lot'] > 0
    assert isinstance(result['board'], str)
    
    print(f"\nSBER quote: {result}")


def test_get_dividends():
    """Тест получения дивидендов."""
    client = MOEXClient(rate_limit_sleep=0.5)
    
    # SBER обычно платит дивиденды
    divs = client.get_dividends("SBER")
    
    assert isinstance(divs, float)
    assert divs >= 0
    
    print(f"\nSBER dividends TTM: {divs}")


def test_get_candles():
    """Тест получения свечей."""
    client = MOEXClient(rate_limit_sleep=0.5)
    
    candles = client.get_candles("SBER", days=100)
    
    assert isinstance(candles, pd.DataFrame)
    assert len(candles) > 0
    
    # Проверка колонок
    required_cols = ['open', 'high', 'low', 'close', 'volume', 'begin', 'end']
    for col in required_cols:
        assert col in candles.columns
    
    # Проверка типов
    assert candles['open'].dtype == float
    assert candles['high'].dtype == float
    assert candles['low'].dtype == float
    assert candles['close'].dtype == float
    assert candles['volume'].dtype == int
    
    # Проверка валидности данных
    assert (candles['high'] >= candles['low']).all()
    assert (candles['volume'] >= 0).all()
    
    print(f"\nSBER candles count: {len(candles)}")
    print(f"Latest candle:\n{candles.iloc[-1]}")


def test_get_all_data():
    """Тест получения всех данных."""
    client = MOEXClient(rate_limit_sleep=0.5)
    
    result = client.get_all_data("GAZP")
    
    assert 'quote' in result
    assert 'dividends' in result
    assert 'candles' in result
    assert 'error' in result
    
    if result['error'] is None:
        assert result['quote'] is not None
        assert isinstance(result['dividends'], float)
        assert isinstance(result['candles'], pd.DataFrame)
    
    print(f"\nGAZP all data: quote={result['quote']}, divs={result['dividends']}, candles={len(result['candles']) if result['candles'] is not None else 0}")


def test_multiple_tickers():
    """Тест на нескольких тикерах."""
    client = MOEXClient(rate_limit_sleep=0.5)
    
    tickers = ["SBER", "GAZP", "LKOH"]
    
    for ticker in tickers:
        print(f"\n--- Testing {ticker} ---")
        
        try:
            quote = client.get_quote(ticker)
            print(f"Quote: {quote}")
            
            divs = client.get_dividends(ticker)
            print(f"Dividends: {divs}")
            
            candles = client.get_candles(ticker, days=30)
            print(f"Candles: {len(candles)} rows")
            
            assert quote['price'] > 0
            assert divs >= 0
            assert len(candles) > 0
            
        except MOEXClientError as e:
            print(f"Error for {ticker}: {e}")
            # Не фейлим тест, если какой-то тикер не доступен
            continue


if __name__ == "__main__":
    # Для ручного запуска без pytest.mark.skip
    print("Running manual tests...")
    
    test_get_quote()
    test_get_dividends()
    test_get_candles()
    test_get_all_data()
    test_multiple_tickers()
    
    print("\n✓ All manual tests passed!")

