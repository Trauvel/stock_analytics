"""Модуль для расчёта метрик и генерации торговых сигналов."""

from typing import List, Dict, Any, Optional
import pandas as pd
import pandas_ta as ta
from loguru import logger

from app.models import SignalType
from app.config.loader import get_config


class MetricsCalculator:
    """Калькулятор метрик для анализа акций."""
    
    def __init__(self):
        """Инициализация калькулятора."""
        self.config = get_config()
    
    def calculate_sma(self, candles: pd.DataFrame) -> Dict[str, Optional[float]]:
        """
        Рассчитать простые скользящие средние (SMA).
        
        Args:
            candles: DataFrame со свечами (должен содержать колонку 'close')
            
        Returns:
            Dict[str, Optional[float]]: Словарь с SMA {sma_20: value, sma_50: value, sma_200: value}
        """
        result = {}
        
        if candles.empty or 'close' not in candles.columns:
            logger.warning("Cannot calculate SMA: empty candles or missing 'close' column")
            return {f'sma_{w}': None for w in self.config.windows.sma}
        
        close_prices = candles['close']
        
        for window in self.config.windows.sma:
            if len(close_prices) >= window:
                # Используем pandas-ta для расчёта SMA
                sma_series = ta.sma(close_prices, length=window)
                # Берём последнее значение (текущее SMA)
                sma_value = float(sma_series.iloc[-1]) if not sma_series.empty else None
                result[f'sma_{window}'] = sma_value
            else:
                logger.debug(f"Not enough data for SMA{window}: have {len(close_prices)}, need {window}")
                result[f'sma_{window}'] = None
        
        return result
    
    def calculate_52w_range(self, candles: pd.DataFrame, current_price: float) -> Dict[str, Optional[float]]:
        """
        Рассчитать диапазон 52 недель и расстояния от текущей цены.
        
        Args:
            candles: DataFrame со свечами
            current_price: Текущая цена
            
        Returns:
            Dict с high_52w, low_52w, dist_52w_low_pct, dist_52w_high_pct
        """
        result = {
            'high_52w': None,
            'low_52w': None,
            'dist_52w_low_pct': None,
            'dist_52w_high_pct': None
        }
        
        if candles.empty or 'high' not in candles.columns or 'low' not in candles.columns:
            logger.warning("Cannot calculate 52W range: empty candles or missing columns")
            return result
        
        # Берём данные за последние ~260 торговых дней (примерно 52 недели)
        recent_candles = candles.tail(260)
        
        if len(recent_candles) < 50:  # Минимум 50 свечей для валидного расчёта
            logger.debug(f"Not enough data for 52W range: have {len(recent_candles)} candles")
            return result
        
        high_52w = float(recent_candles['high'].max())
        low_52w = float(recent_candles['low'].min())
        
        # Расстояние от минимума: (price / low52 - 1) * 100
        dist_from_low = ((current_price / low_52w) - 1) * 100 if low_52w > 0 else None
        
        # Расстояние до максимума: (high52 / price - 1) * 100
        dist_to_high = ((high_52w / current_price) - 1) * 100 if current_price > 0 else None
        
        result.update({
            'high_52w': high_52w,
            'low_52w': low_52w,
            'dist_52w_low_pct': dist_from_low,
            'dist_52w_high_pct': dist_to_high
        })
        
        return result
    
    def calculate_dividend_yield(self, div_ttm: float, price: float) -> Optional[float]:
        """
        Рассчитать дивидендную доходность.
        
        Args:
            div_ttm: Дивиденды за последние 12 месяцев
            price: Текущая цена
            
        Returns:
            Optional[float]: Дивидендная доходность в процентах
        """
        if price <= 0:
            return None
        
        dy_pct = (div_ttm / price) * 100
        return round(dy_pct, 2)
    
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
    
    def generate_signals(
        self,
        price: float,
        sma_data: Dict[str, Optional[float]],
        dy_pct: Optional[float],
        candles: pd.DataFrame
    ) -> List[SignalType]:
        """
        Генерировать торговые сигналы на основе метрик.
        
        Args:
            price: Текущая цена
            sma_data: Данные SMA
            dy_pct: Дивидендная доходность
            candles: DataFrame со свечами для дополнительных проверок
            
        Returns:
            List[SignalType]: Список сигналов
        """
        signals = []
        
        # Сигнал 1: Цена ниже SMA200
        if sma_data.get('sma_200') and price < sma_data['sma_200']:
            signals.append(SignalType.PRICE_BELOW_SMA200)
        
        # Сигнал 2: Цена выше SMA200
        if sma_data.get('sma_200') and price > sma_data['sma_200']:
            signals.append(SignalType.PRICE_ABOVE_SMA200)
        
        # Сигнал 3: Золотой крест (SMA50 пересекла SMA200 снизу вверх)
        if self._check_golden_cross(candles, sma_data):
            signals.append(SignalType.SMA50_CROSS_UP_SMA200)
        
        # Сигнал 4: Крест смерти (SMA50 пересекла SMA200 сверху вниз)
        if self._check_death_cross(candles, sma_data):
            signals.append(SignalType.SMA50_CROSS_DOWN_SMA200)
        
        # Сигнал 5: Дивидендная доходность выше целевой
        if dy_pct and dy_pct >= self.config.dividend_target_pct:
            signals.append(SignalType.DY_GT_TARGET)
        
        # Сигнал 6: Всплеск объёма (опционально)
        if self.calculate_volume_spike(candles):
            signals.append(SignalType.VOL_SPIKE)
        
        return signals
    
    def _check_golden_cross(self, candles: pd.DataFrame, sma_data: Dict[str, Optional[float]]) -> bool:
        """
        Проверить наличие золотого креста (SMA50 пересекла SMA200 снизу вверх).
        
        Проверяем по последним двум точкам:
        - Предыдущая точка: SMA50 < SMA200
        - Текущая точка: SMA50 > SMA200
        """
        if len(candles) < 200:  # Нужно достаточно данных
            return False
        
        if not sma_data.get('sma_50') or not sma_data.get('sma_200'):
            return False
        
        close_prices = candles['close']
        
        # Рассчитываем SMA для предыдущей точки
        sma50_series = ta.sma(close_prices, length=50)
        sma200_series = ta.sma(close_prices, length=200)
        
        if len(sma50_series) < 2 or len(sma200_series) < 2:
            return False
        
        # Предыдущие значения
        prev_sma50 = sma50_series.iloc[-2]
        prev_sma200 = sma200_series.iloc[-2]
        
        # Текущие значения
        curr_sma50 = sma_data['sma_50']
        curr_sma200 = sma_data['sma_200']
        
        # Проверяем пересечение снизу вверх
        return prev_sma50 < prev_sma200 and curr_sma50 > curr_sma200
    
    def _check_death_cross(self, candles: pd.DataFrame, sma_data: Dict[str, Optional[float]]) -> bool:
        """
        Проверить наличие креста смерти (SMA50 пересекла SMA200 сверху вниз).
        """
        if len(candles) < 200:
            return False
        
        if not sma_data.get('sma_50') or not sma_data.get('sma_200'):
            return False
        
        close_prices = candles['close']
        
        sma50_series = ta.sma(close_prices, length=50)
        sma200_series = ta.sma(close_prices, length=200)
        
        if len(sma50_series) < 2 or len(sma200_series) < 2:
            return False
        
        prev_sma50 = sma50_series.iloc[-2]
        prev_sma200 = sma200_series.iloc[-2]
        
        curr_sma50 = sma_data['sma_50']
        curr_sma200 = sma_data['sma_200']
        
        # Проверяем пересечение сверху вниз
        return prev_sma50 > prev_sma200 and curr_sma50 < curr_sma200
    
    def calculate_all_metrics(
        self,
        candles: pd.DataFrame,
        current_price: float,
        div_ttm: float
    ) -> Dict[str, Any]:
        """
        Рассчитать все метрики для тикера.
        
        Args:
            candles: DataFrame со свечами
            current_price: Текущая цена
            div_ttm: Дивиденды TTM
            
        Returns:
            Dict с всеми метриками и сигналами
        """
        # Рассчитываем SMA
        sma_data = self.calculate_sma(candles)
        
        # Рассчитываем 52W диапазон
        range_52w = self.calculate_52w_range(candles, current_price)
        
        # Рассчитываем дивидендную доходность
        dy_pct = self.calculate_dividend_yield(div_ttm, current_price)
        
        # Генерируем сигналы
        signals = self.generate_signals(current_price, sma_data, dy_pct, candles)
        
        # Собираем все метрики
        metrics = {
            **sma_data,
            **range_52w,
            'div_ttm': div_ttm,
            'dy_pct': dy_pct,
            'signals': signals
        }
        
        logger.debug(f"Calculated metrics: SMA20={sma_data.get('sma_20')}, "
                    f"DY={dy_pct}%, Signals={len(signals)}")
        
        return metrics

