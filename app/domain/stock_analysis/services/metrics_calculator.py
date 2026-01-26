"""Доменный сервис для расчёта метрик акций."""

from typing import List, Optional
import pandas as pd
import pandas_ta as ta
from loguru import logger

from ..entities.stock import Stock
from ..value_objects.price import Price
from ..value_objects.dividend_yield import DividendYield
from ..value_objects.signal import Signal, SignalType


class MetricsCalculator:
    """Доменный сервис для расчёта технических метрик."""
    
    def __init__(self, dividend_target_pct: float = 8.0):
        """
        Инициализация калькулятора.
        
        Args:
            dividend_target_pct: Целевая дивидендная доходность в процентах
        """
        self.dividend_target_pct = dividend_target_pct
    
    def calculate_sma(self, candles: pd.DataFrame) -> dict[str, Optional[Price]]:
        """
        Рассчитать простые скользящие средние (SMA).
        
        Args:
            candles: DataFrame со свечами (должен содержать колонку 'close')
            
        Returns:
            Dict с SMA как Price объекты
        """
        result = {}
        
        if candles.empty or 'close' not in candles.columns:
            logger.warning("Cannot calculate SMA: empty candles or missing 'close' column")
            return {'sma_20': None, 'sma_50': None, 'sma_200': None}
        
        close_prices = candles['close']
        windows = [20, 50, 200]
        
        for window in windows:
            if len(close_prices) >= window:
                sma_series = ta.sma(close_prices, length=window)
                sma_value = float(sma_series.iloc[-1]) if not sma_series.empty else None
                result[f'sma_{window}'] = Price.from_float(sma_value)
            else:
                logger.debug(f"Not enough data for SMA{window}: have {len(close_prices)}, need {window}")
                result[f'sma_{window}'] = None
        
        return result
    
    def calculate_52w_range(self, candles: pd.DataFrame, current_price: Price) -> dict[str, Optional[Price]]:
        """
        Рассчитать диапазон 52 недель.
        
        Args:
            candles: DataFrame со свечами
            current_price: Текущая цена
            
        Returns:
            Dict с high_52w и low_52w как Price объекты
        """
        result = {
            'high_52w': None,
            'low_52w': None
        }
        
        if candles.empty or 'high' not in candles.columns or 'low' not in candles.columns:
            logger.warning("Cannot calculate 52W range: empty candles or missing columns")
            return result
        
        # Берём данные за последние ~260 торговых дней (примерно 52 недели)
        recent_candles = candles.tail(260)
        
        if len(recent_candles) < 50:
            logger.debug(f"Not enough data for 52W range: have {len(recent_candles)} candles")
            return result
        
        high_52w = float(recent_candles['high'].max())
        low_52w = float(recent_candles['low'].min())
        
        result['high_52w'] = Price.from_float(high_52w, currency=current_price.currency)
        result['low_52w'] = Price.from_float(low_52w, currency=current_price.currency)
        
        return result
    
    def calculate_dividend_yield(self, div_ttm: float, price: Price) -> Optional[DividendYield]:
        """
        Рассчитать дивидендную доходность.
        
        Args:
            div_ttm: Дивиденды за последние 12 месяцев
            price: Текущая цена
            
        Returns:
            DividendYield или None
        """
        if price.value <= 0:
            return None
        
        dy_pct = (div_ttm / price.value) * 100
        return DividendYield(value=round(dy_pct, 2))
    
    def generate_signals(
        self,
        stock: Stock
    ) -> List[Signal]:
        """
        Генерировать торговые сигналы на основе метрик акции.
        
        Args:
            stock: Акция с рассчитанными метриками
            
        Returns:
            List[Signal]: Список сигналов
        """
        signals = []
        
        # Сигнал 1: Цена ниже SMA200
        if stock.is_undervalued():
            signals.append(Signal(
                signal_type=SignalType.PRICE_BELOW_SMA200,
                description="Цена ниже SMA200 - возможная недооценка"
            ))
        
        # Сигнал 2: Цена выше SMA200
        if stock.is_overvalued():
            signals.append(Signal(
                signal_type=SignalType.PRICE_ABOVE_SMA200,
                description="Цена выше SMA200 - возможная переоценка"
            ))
        
        # Сигнал 3: Золотой крест (SMA50 пересекла SMA200 снизу вверх)
        if self._check_golden_cross(stock):
            signals.append(Signal(
                signal_type=SignalType.SMA50_CROSS_UP_SMA200,
                description="Золотой крест - бычий сигнал"
            ))
        
        # Сигнал 4: Крест смерти (SMA50 пересекла SMA200 сверху вниз)
        if self._check_death_cross(stock):
            signals.append(Signal(
                signal_type=SignalType.SMA50_CROSS_DOWN_SMA200,
                description="Крест смерти - медвежий сигнал"
            ))
        
        # Сигнал 5: Дивидендная доходность выше целевой
        if stock.has_high_dividend_yield(self.dividend_target_pct):
            signals.append(Signal(
                signal_type=SignalType.DY_GT_TARGET,
                description=f"Дивидендная доходность {stock.dividend_yield.value:.1f}% ≥ {self.dividend_target_pct}%"
            ))
        
        # Сигнал 6: Цена в нижней трети 52W диапазона
        if stock.is_near_52w_low():
            signals.append(Signal(
                signal_type=SignalType.NEAR_52W_LOW,
                description="Цена в нижней трети 52W диапазона"
            ))
        
        # Сигнал 7: Цена у верхней границы 52W диапазона
        if stock.is_near_52w_high():
            signals.append(Signal(
                signal_type=SignalType.NEAR_52W_HIGH,
                description="Цена у верхней границы 52W диапазона"
            ))
        
        return signals
    
    def _check_golden_cross(self, stock: Stock) -> bool:
        """
        Проверить наличие золотого креста (SMA50 пересекла SMA200 снизу вверх).
        
        Примечание: Для точной проверки нужны исторические данные SMA.
        Здесь упрощённая версия - проверяем только текущее состояние.
        """
        if stock.sma_50 is None or stock.sma_200 is None:
            return False
        
        # Упрощённая проверка: SMA50 > SMA200 и цена выше SMA50
        return stock.sma_50 > stock.sma_200 and stock.price and stock.price > stock.sma_50
    
    def _check_death_cross(self, stock: Stock) -> bool:
        """
        Проверить наличие креста смерти (SMA50 пересекла SMA200 сверху вниз).
        
        Примечание: Для точной проверки нужны исторические данные SMA.
        """
        if stock.sma_50 is None or stock.sma_200 is None:
            return False
        
        # Упрощённая проверка: SMA50 < SMA200 и цена ниже SMA50
        return stock.sma_50 < stock.sma_200 and stock.price and stock.price < stock.sma_50
    
    def enrich_stock_with_metrics(
        self,
        stock: Stock,
        candles: pd.DataFrame
    ) -> Stock:
        """
        Обогатить акцию метриками на основе свечей.
        
        Args:
            stock: Базовая акция (с ценой и дивидендами)
            candles: DataFrame со свечами
            
        Returns:
            Обогащённая акция с метриками
        """
        if stock.price is None:
            return stock
        
        # Рассчитываем SMA
        sma_data = self.calculate_sma(candles)
        
        # Рассчитываем 52W диапазон
        range_52w = self.calculate_52w_range(candles, stock.price)
        
        # Генерируем сигналы (нужно обновить stock сначала)
        updated_stock = Stock(
            symbol=stock.symbol,
            price=stock.price,
            dividend_yield=stock.dividend_yield,
            sma_20=sma_data.get('sma_20'),
            sma_50=sma_data.get('sma_50'),
            sma_200=sma_data.get('sma_200'),
            high_52w=range_52w.get('high_52w'),
            low_52w=range_52w.get('low_52w'),
            signals=[],
            lot=stock.lot,
            div_ttm=stock.div_ttm,
            updated_at=stock.updated_at
        )
        
        # Генерируем сигналы
        signals = self.generate_signals(updated_stock)
        
        # Возвращаем финальную версию
        return Stock(
            symbol=updated_stock.symbol,
            price=updated_stock.price,
            dividend_yield=updated_stock.dividend_yield,
            sma_20=updated_stock.sma_20,
            sma_50=updated_stock.sma_50,
            sma_200=updated_stock.sma_200,
            high_52w=updated_stock.high_52w,
            low_52w=updated_stock.low_52w,
            signals=signals,
            lot=updated_stock.lot,
            div_ttm=updated_stock.div_ttm,
            updated_at=updated_stock.updated_at
        )
