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
    
    def calculate_rsi(self, candles: pd.DataFrame, period: int = 14) -> Optional[float]:
        """
        Рассчитать RSI (Relative Strength Index).
        
        Args:
            candles: DataFrame со свечами (должен содержать колонку 'close')
            period: Период для расчёта RSI (по умолчанию 14)
            
        Returns:
            Optional[float]: Значение RSI (0-100) или None если недостаточно данных
        """
        if candles.empty or 'close' not in candles.columns:
            logger.warning("Cannot calculate RSI: empty candles or missing 'close' column")
            return None
        
        if len(candles) < period + 1:
            logger.debug(f"Not enough data for RSI: have {len(candles)}, need {period + 1}")
            return None
        
        try:
            close_prices = candles['close']
            rsi_series = ta.rsi(close_prices, length=period)
            
            if rsi_series.empty:
                return None
            
            rsi_value = float(rsi_series.iloc[-1])
            return round(rsi_value, 2) if not pd.isna(rsi_value) else None
            
        except Exception as e:
            logger.warning(f"Error calculating RSI: {e}")
            return None
    
    def calculate_atr(self, candles: pd.DataFrame, period: int = 14) -> Optional[float]:
        """
        Рассчитать ATR (Average True Range) - индикатор волатильности.
        
        Args:
            candles: DataFrame со свечами (должен содержать high, low, close)
            period: Период для расчёта ATR (по умолчанию 14)
            
        Returns:
            Optional[float]: Значение ATR или None если недостаточно данных
        """
        if candles.empty or len(candles) < period + 1:
            return None
        
        required_columns = ['high', 'low', 'close']
        if not all(col in candles.columns for col in required_columns):
            return None
        
        try:
            atr_series = ta.atr(
                high=candles['high'],
                low=candles['low'],
                close=candles['close'],
                length=period
            )
            
            if atr_series.empty:
                return None
            
            atr_value = float(atr_series.iloc[-1])
            return round(atr_value, 2) if not pd.isna(atr_value) else None
            
        except Exception as e:
            logger.warning(f"Error calculating ATR: {e}")
            return None
    
    def calculate_volume_spike(self, candles: pd.DataFrame, threshold: float = 1.8) -> bool:
        """
        Определить всплеск объёма торгов.
        
        Args:
            candles: DataFrame со свечами
            threshold: Порог для определения всплеска (по умолчанию 1.8x от медианы)
            
        Returns:
            bool: True если есть всплеск объёма
        """
        if candles.empty or 'volume' not in candles.columns or len(candles) < 20:
            return False
        
        # Берём последние 20 дней
        recent_volumes = candles['volume'].tail(20)
        
        # Медиана объёма за последние 20 дней
        median_volume = recent_volumes.median()
        
        # Последний объём
        last_volume = candles['volume'].iloc[-1]
        
        # Проверяем всплеск (конвертируем в Python bool)
        return bool(last_volume > (median_volume * threshold)) if median_volume > 0 else False
    
    def calculate_all_metrics(
        self,
        candles: pd.DataFrame,
        current_price: float,
        div_ttm: float,
        symbol: Optional[str] = None
    ) -> dict:
        """
        Рассчитать все метрики для тикера (legacy совместимость).
        
        ⚠️ DEPRECATED: Используйте enrich_stock_with_metrics для DDD подхода.
        Этот метод оставлен для обратной совместимости.
        
        Args:
            candles: DataFrame со свечами
            current_price: Текущая цена (float)
            div_ttm: Дивиденды TTM (для акций) или купонная доходность в % (для облигаций)
            symbol: Тикер инструмента (для определения типа)
        
        Returns:
            Dict с всеми метриками и сигналами (legacy формат)
        """
        from ..value_objects.price import Price
        from ..value_objects.dividend_yield import DividendYield
        
        # Определяем, является ли это облигацией (по ISIN)
        is_bond = symbol is not None and len(symbol) == 12 and symbol[:2].isalpha()
        
        # Конвертируем в Value Objects для расчётов
        price_vo = Price.from_float(current_price)
        
        # Рассчитываем SMA (возвращает Price объекты)
        sma_data_vo = self.calculate_sma(candles)
        
        # Рассчитываем 52W диапазон
        range_52w_vo = self.calculate_52w_range(candles, price_vo)
        
        # Рассчитываем дивидендную доходность
        if is_bond:
            # Для облигаций div_ttm уже в процентах (купонная доходность)
            dy_pct = div_ttm
        else:
            # Для акций рассчитываем: (div_ttm / price) * 100
            if price_vo.value > 0:
                dy_pct = (div_ttm / price_vo.value) * 100
            else:
                dy_pct = None
        
        # Рассчитываем RSI и ATR
        rsi = self.calculate_rsi(candles)
        atr = self.calculate_atr(candles)
        
        # Конвертируем обратно в float для legacy формата
        sma_data = {
            'sma_20': sma_data_vo.get('sma_20').value if sma_data_vo.get('sma_20') else None,
            'sma_50': sma_data_vo.get('sma_50').value if sma_data_vo.get('sma_50') else None,
            'sma_200': sma_data_vo.get('sma_200').value if sma_data_vo.get('sma_200') else None,
        }
        
        range_52w = {
            'high_52w': range_52w_vo.get('high_52w').value if range_52w_vo.get('high_52w') else None,
            'low_52w': range_52w_vo.get('low_52w').value if range_52w_vo.get('low_52w') else None,
            'dist_52w_low_pct': None,  # Можно рассчитать если нужно
            'dist_52w_high_pct': None,  # Можно рассчитать если нужно
        }
        
        # Рассчитываем расстояния
        if range_52w['low_52w'] and current_price > 0:
            range_52w['dist_52w_low_pct'] = ((current_price / range_52w['low_52w']) - 1) * 100
        if range_52w['high_52w'] and current_price > 0:
            range_52w['dist_52w_high_pct'] = ((range_52w['high_52w'] / current_price) - 1) * 100
        
        # Генерируем сигналы (упрощённая версия для legacy)
        # Используем SignalType из value_objects (DDD версия)
        signals = []
        if sma_data['sma_200'] and current_price < sma_data['sma_200']:
            signals.append(SignalType.PRICE_BELOW_SMA200)
        if sma_data['sma_200'] and current_price > sma_data['sma_200']:
            signals.append(SignalType.PRICE_ABOVE_SMA200)
        if dy_pct and dy_pct >= self.dividend_target_pct:
            signals.append(SignalType.DY_GT_TARGET)
        if self.calculate_volume_spike(candles):
            signals.append(SignalType.VOL_SPIKE)
        if rsi is not None and rsi < 30:
            signals.append(SignalType.RSI_OVERSOLD)
        if rsi is not None and rsi > 70:
            signals.append(SignalType.RSI_OVERBOUGHT)
        
        # Конвертируем SignalType в строки для legacy формата (если нужно)
        # Но обычно SignalType уже совместим со строковым форматом
        
        # Собираем все метрики
        metrics = {
            **sma_data,
            **range_52w,
            'div_ttm': div_ttm,
            'dy_pct': dy_pct,
            'rsi': rsi,
            'atr': atr,
            'signals': signals
        }
        
        logger.debug(f"Calculated metrics (legacy format): SMA20={sma_data.get('sma_20')}, "
                    f"DY={dy_pct}%, RSI={rsi}, Signals={len(signals)}")
        
        return metrics
