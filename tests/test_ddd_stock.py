"""Тесты для доменной сущности Stock."""

import pytest
from datetime import datetime
from app.domain.stock_analysis.entities.stock import Stock
from app.domain.stock_analysis.value_objects import Price, DividendYield, Signal, SignalType


class TestStock:
    """Тесты для доменной сущности Stock."""
    
    def test_create_stock(self):
        """Тест создания акции."""
        stock = Stock(
            symbol="SBER",
            price=Price(value=250.0),
            dividend_yield=DividendYield(value=8.5),
            sma_20=None,
            sma_50=None,
            sma_200=Price(value=280.0),
            high_52w=None,
            low_52w=None,
            signals=[]
        )
        
        assert stock.symbol == "SBER"
        assert stock.price.value == 250.0
        assert stock.dividend_yield.value == 8.5
    
    def test_stock_validation_empty_symbol(self):
        """Тест валидации пустого символа."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Stock(
                symbol="",
                price=Price(value=250.0),
                dividend_yield=None,
                sma_20=None,
                sma_50=None,
                sma_200=None,
                high_52w=None,
                low_52w=None,
                signals=[]
            )
    
    def test_stock_is_undervalued(self):
        """Тест проверки недооценки."""
        stock = Stock(
            symbol="SBER",
            price=Price(value=250.0),
            dividend_yield=None,
            sma_20=None,
            sma_50=None,
            sma_200=Price(value=280.0),
            high_52w=None,
            low_52w=None,
            signals=[]
        )
        
        assert stock.is_undervalued() == True
        assert stock.is_overvalued() == False
    
    def test_stock_is_overvalued(self):
        """Тест проверки переоценки."""
        stock = Stock(
            symbol="SBER",
            price=Price(value=300.0),
            dividend_yield=None,
            sma_20=None,
            sma_50=None,
            sma_200=Price(value=280.0),
            high_52w=None,
            low_52w=None,
            signals=[]
        )
        
        assert stock.is_overvalued() == True
        assert stock.is_undervalued() == False
    
    def test_stock_has_high_dividend_yield(self):
        """Тест проверки высокой дивидендной доходности."""
        stock = Stock(
            symbol="SBER",
            price=Price(value=250.0),
            dividend_yield=DividendYield(value=10.0),
            sma_20=None,
            sma_50=None,
            sma_200=None,
            high_52w=None,
            low_52w=None,
            signals=[]
        )
        
        assert stock.has_high_dividend_yield(threshold=8.0) == True
        assert stock.has_high_dividend_yield(threshold=12.0) == False
    
    def test_stock_discount_to_sma200(self):
        """Тест расчёта дисконта к SMA200."""
        stock = Stock(
            symbol="SBER",
            price=Price(value=250.0),
            dividend_yield=None,
            sma_20=None,
            sma_50=None,
            sma_200=Price(value=280.0),
            high_52w=None,
            low_52w=None,
            signals=[]
        )
        
        discount = stock.discount_to_sma200()
        assert discount is not None
        assert discount < 0  # Отрицательное значение = дисконт
        assert abs(discount - (-10.714285714285714)) < 0.01
    
    def test_stock_position_in_52w_range(self):
        """Тест расчёта позиции в 52W диапазоне."""
        stock = Stock(
            symbol="SBER",
            price=Price(value=250.0),
            dividend_yield=None,
            sma_20=None,
            sma_50=None,
            sma_200=None,
            high_52w=Price(value=300.0),
            low_52w=Price(value=200.0),
            signals=[]
        )
        
        position = stock.position_in_52w_range()
        assert position is not None
        assert 0.0 <= position <= 1.0
        # (250 - 200) / (300 - 200) = 0.5
        assert abs(position - 0.5) < 0.01
    
    def test_stock_is_near_52w_low(self):
        """Тест проверки близости к минимуму 52W."""
        stock = Stock(
            symbol="SBER",
            price=Price(value=210.0),
            dividend_yield=None,
            sma_20=None,
            sma_50=None,
            sma_200=None,
            high_52w=Price(value=300.0),
            low_52w=Price(value=200.0),
            signals=[]
        )
        
        # Позиция: (210-200)/(300-200) = 0.1 < 0.3
        assert stock.is_near_52w_low(threshold=0.3) == True
    
    def test_stock_is_near_52w_high(self):
        """Тест проверки близости к максимуму 52W."""
        stock = Stock(
            symbol="SBER",
            price=Price(value=290.0),
            dividend_yield=None,
            sma_20=None,
            sma_50=None,
            sma_200=None,
            high_52w=Price(value=300.0),
            low_52w=Price(value=200.0),
            signals=[]
        )
        
        # Позиция: (290-200)/(300-200) = 0.9 > 0.85
        assert stock.is_near_52w_high(threshold=0.85) == True
        # При пороге 0.9 позиция 0.9 не проходит (строгое >)
        assert stock.is_near_52w_high(threshold=0.9) == False
    
    def test_stock_has_signal(self):
        """Тест проверки наличия сигнала."""
        signal = Signal(signal_type=SignalType.PRICE_BELOW_SMA200)
        stock = Stock(
            symbol="SBER",
            price=Price(value=250.0),
            dividend_yield=None,
            sma_20=None,
            sma_50=None,
            sma_200=None,
            high_52w=None,
            low_52w=None,
            signals=[signal]
        )
        
        assert stock.has_signal(SignalType.PRICE_BELOW_SMA200) == True
        assert stock.has_signal(SignalType.DY_GT_TARGET) == False
    
    def test_stock_bullish_bearish_signals_count(self):
        """Тест подсчёта бычьих и медвежьих сигналов."""
        signals = [
            Signal(signal_type=SignalType.PRICE_BELOW_SMA200),  # бычий
            Signal(signal_type=SignalType.DY_GT_TARGET),  # бычий
            Signal(signal_type=SignalType.PRICE_ABOVE_SMA200),  # медвежий
        ]
        
        stock = Stock(
            symbol="SBER",
            price=Price(value=250.0),
            dividend_yield=None,
            sma_20=None,
            sma_50=None,
            sma_200=None,
            high_52w=None,
            low_52w=None,
            signals=signals
        )
        
        assert stock.bullish_signals_count() == 2
        assert stock.bearish_signals_count() == 1
    
    def test_stock_to_dict(self):
        """Тест преобразования в словарь."""
        stock = Stock(
            symbol="SBER",
            price=Price(value=250.0),
            dividend_yield=DividendYield(value=8.5),
            sma_20=None,
            sma_50=None,
            sma_200=Price(value=280.0),
            high_52w=None,
            low_52w=None,
            signals=[Signal(signal_type=SignalType.PRICE_BELOW_SMA200)],
            lot=10,
            div_ttm=25.0,
            updated_at=datetime.now()
        )
        
        data = stock.to_dict()
        
        assert data["symbol"] == "SBER"
        assert data["price"] == 250.0
        assert data["dy_pct"] == 8.5
        assert data["sma_200"] == 280.0
        assert len(data["signals"]) == 1
        assert data["signals"][0] == "PRICE_BELOW_SMA200"
    
    def test_stock_from_dict(self):
        """Тест создания из словаря."""
        data = {
            "symbol": "SBER",
            "price": 250.0,
            "dy_pct": 8.5,
            "sma_200": 280.0,
            "signals": ["PRICE_BELOW_SMA200"],
            "lot": 10,
            "div_ttm": 25.0
        }
        
        stock = Stock.from_dict(data)
        
        assert stock.symbol == "SBER"
        assert stock.price.value == 250.0
        assert stock.dividend_yield.value == 8.5
        assert stock.sma_200.value == 280.0
        assert len(stock.signals) == 1
        assert stock.signals[0].signal_type == SignalType.PRICE_BELOW_SMA200
