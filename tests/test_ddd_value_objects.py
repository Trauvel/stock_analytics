"""Тесты для Value Objects."""

import pytest
from app.domain.stock_analysis.value_objects import Price, DividendYield, Signal, SignalType


class TestPrice:
    """Тесты для Value Object Price."""
    
    def test_create_price(self):
        """Тест создания цены."""
        price = Price(value=100.0, currency="RUB")
        assert price.value == 100.0
        assert price.currency == "RUB"
    
    def test_price_validation_negative(self):
        """Тест валидации отрицательной цены."""
        with pytest.raises(ValueError, match="cannot be negative"):
            Price(value=-10.0)
    
    def test_price_comparison(self):
        """Тест сравнения цен."""
        price1 = Price(value=100.0)
        price2 = Price(value=200.0)
        
        assert price1 < price2
        assert price2 > price1
        assert price1 <= price2
        assert price2 >= price1
    
    def test_price_comparison_different_currency(self):
        """Тест сравнения цен в разных валютах."""
        price1 = Price(value=100.0, currency="RUB")
        price2 = Price(value=200.0, currency="USD")
        
        with pytest.raises(ValueError, match="different currencies"):
            _ = price1 < price2
    
    def test_price_percentage_diff(self):
        """Тест расчёта процентной разницы."""
        price1 = Price(value=100.0)
        price2 = Price(value=150.0)
        
        diff = price1.percentage_diff(price2)
        # Используем приблизительное сравнение из-за точности float
        assert abs(diff - (-33.333333333333336)) < 0.0001  # (100-150)/150 * 100
    
    def test_price_from_float(self):
        """Тест создания цены из float."""
        price = Price.from_float(100.5)
        assert price.value == 100.5
        assert price.currency == "RUB"
        
        # None должен вернуть None
        assert Price.from_float(None) is None
    
    def test_price_arithmetic(self):
        """Тест арифметических операций."""
        price1 = Price(value=100.0)
        price2 = Price(value=50.0)
        
        sum_price = price1 + price2
        assert sum_price.value == 150.0
        
        diff_price = price1 - price2
        assert diff_price.value == 50.0


class TestDividendYield:
    """Тесты для Value Object DividendYield."""
    
    def test_create_dividend_yield(self):
        """Тест создания дивидендной доходности."""
        dy = DividendYield(value=8.5)
        assert dy.value == 8.5
    
    def test_dividend_yield_validation_negative(self):
        """Тест валидации отрицательной доходности."""
        with pytest.raises(ValueError, match="cannot be negative"):
            DividendYield(value=-5.0)
    
    def test_dividend_yield_is_high(self):
        """Тест проверки высокой доходности."""
        dy = DividendYield(value=10.0)
        assert dy.is_high(threshold=8.0) == True
        assert dy.is_high(threshold=12.0) == False
    
    def test_dividend_yield_is_very_high(self):
        """Тест проверки очень высокой доходности."""
        dy = DividendYield(value=18.0)
        assert dy.is_very_high(threshold=15.0) == True
        assert dy.is_very_high(threshold=20.0) == False
    
    def test_dividend_yield_from_float(self):
        """Тест создания из float."""
        dy = DividendYield.from_float(8.5)
        assert dy.value == 8.5
        
        assert DividendYield.from_float(None) is None


class TestSignal:
    """Тесты для Value Object Signal."""
    
    def test_create_signal(self):
        """Тест создания сигнала."""
        signal = Signal(signal_type=SignalType.PRICE_BELOW_SMA200)
        assert signal.signal_type == SignalType.PRICE_BELOW_SMA200
    
    def test_signal_is_bullish(self):
        """Тест проверки бычьего сигнала."""
        signal = Signal(signal_type=SignalType.PRICE_BELOW_SMA200)
        assert signal.is_bullish() == True
        
        signal2 = Signal(signal_type=SignalType.DY_GT_TARGET)
        assert signal2.is_bullish() == True
    
    def test_signal_is_bearish(self):
        """Тест проверки медвежьего сигнала."""
        signal = Signal(signal_type=SignalType.PRICE_ABOVE_SMA200)
        assert signal.is_bearish() == True
        
        signal2 = Signal(signal_type=SignalType.SMA50_CROSS_DOWN_SMA200)
        assert signal2.is_bearish() == True
    
    def test_signal_from_string(self):
        """Тест создания сигнала из строки."""
        signal = Signal.from_string("PRICE_BELOW_SMA200")
        assert signal.signal_type == SignalType.PRICE_BELOW_SMA200
    
    def test_signal_from_string_invalid(self):
        """Тест создания сигнала из невалидной строки."""
        with pytest.raises(ValueError, match="Unknown signal type"):
            Signal.from_string("INVALID_SIGNAL")
    
    def test_signal_from_list(self):
        """Тест создания списка сигналов."""
        signals = Signal.from_list(["PRICE_BELOW_SMA200", "DY_GT_TARGET"])
        assert len(signals) == 2
        assert signals[0].signal_type == SignalType.PRICE_BELOW_SMA200
        assert signals[1].signal_type == SignalType.DY_GT_TARGET
    
    def test_signal_from_list_mixed(self):
        """Тест создания списка из разных типов."""
        signals = Signal.from_list([
            "PRICE_BELOW_SMA200",
            SignalType.DY_GT_TARGET,
            Signal(signal_type=SignalType.VOL_SPIKE)
        ])
        assert len(signals) == 3
        assert all(isinstance(s, Signal) for s in signals)
