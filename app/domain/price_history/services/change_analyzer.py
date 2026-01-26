"""Сервис для анализа изменений цен."""

from datetime import datetime, timedelta, time
from typing import List, Optional
from loguru import logger

from app.domain.price_history.entities.price_snapshot import PriceSnapshot
from app.domain.price_history.repositories.price_history_repository import PriceHistoryRepository
from app.domain.price_history.value_objects.change_signal import (
    ChangeSignal,
    ChangeDirection,
    SignalPriority
)


class ChangeAnalyzer:
    """Сервис для анализа изменений цен и генерации сигналов."""
    
    def __init__(
        self,
        price_history_repository: PriceHistoryRepository,
        price_change_threshold_pct: float = 3.0,
        volume_spike_threshold: float = 2.0,
        use_adaptive_thresholds: bool = True
    ):
        """
        Инициализация анализатора.
        
        Args:
            price_history_repository: Репозиторий для работы с историей
            price_change_threshold_pct: Базовое минимальное изменение цены для уведомления (%)
            volume_spike_threshold: Порог всплеска объёма (во сколько раз больше среднего)
            use_adaptive_thresholds: Использовать ли адаптивные пороги на основе волатильности
        """
        self.price_history_repo = price_history_repository
        self.base_price_change_threshold_pct = price_change_threshold_pct
        self.volume_spike_threshold = volume_spike_threshold
        self.use_adaptive_thresholds = use_adaptive_thresholds
    
    def _get_adaptive_threshold(
        self,
        symbol: str,
        current_price: float,
        atr: Optional[float] = None
    ) -> float:
        """
        Получить адаптивный порог изменения цены на основе волатильности инструмента.
        
        Args:
            symbol: Тикер инструмента
            current_price: Текущая цена
            atr: ATR индикатор (если доступен)
            
        Returns:
            float: Адаптивный порог в процентах
        """
        if not self.use_adaptive_thresholds:
            return self.base_price_change_threshold_pct
        
        # Определяем тип инструмента
        is_bond = len(symbol) == 12 and symbol[:2].isalpha()
        
        # Для облигаций используем меньший порог (они менее волатильны)
        if is_bond:
            base_threshold = 1.5  # 1.5% для облигаций
        else:
            base_threshold = self.base_price_change_threshold_pct
        
        # Если есть ATR, корректируем порог
        if atr and current_price > 0:
            # ATR в процентах от цены
            atr_pct = (atr / current_price) * 100
            
            # Если волатильность высокая (ATR > 3%), увеличиваем порог
            # Если волатильность низкая (ATR < 1%), уменьшаем порог
            if atr_pct > 3.0:
                # Высокая волатильность → порог выше
                adaptive_threshold = base_threshold * 1.5
            elif atr_pct < 1.0:
                # Низкая волатильность → порог ниже
                adaptive_threshold = base_threshold * 0.7
            else:
                adaptive_threshold = base_threshold
            
            return max(1.0, min(adaptive_threshold, 10.0))  # Ограничиваем диапазон 1-10%
        
        return base_threshold
    
    def compare_with_previous(
        self,
        symbol: str,
        current_snapshot: PriceSnapshot,
        hours_ago: float = 3.0
    ) -> Optional[ChangeSignal]:
        """
        Сравнить текущий снимок с предыдущим (N часов назад).
        
        Args:
            symbol: Тикер инструмента
            current_snapshot: Текущий снимок
            hours_ago: За сколько часов сравнивать
            
        Returns:
            ChangeSignal или None если изменение незначимо
        """
        try:
            # Получаем предыдущий снимок
            previous_snapshot = self.price_history_repo.get_before_time(
                symbol=symbol,
                timestamp=current_snapshot.timestamp,
                hours_ago=hours_ago
            )
            
            if not previous_snapshot:
                logger.debug(f"No previous snapshot found for {symbol} {hours_ago} hours ago")
                return None
            
            # Рассчитываем изменение цены
            price_change_pct = ((current_snapshot.price - previous_snapshot.price) / previous_snapshot.price) * 100
            
            # Определяем направление
            if abs(price_change_pct) < 0.01:  # Меньше 0.01% - стабильно
                direction = ChangeDirection.STABLE
            elif price_change_pct > 0:
                direction = ChangeDirection.UP
            else:
                direction = ChangeDirection.DOWN
            
            # Получаем адаптивный порог
            adaptive_threshold = self._get_adaptive_threshold(
                symbol=symbol,
                current_price=current_snapshot.price,
                atr=current_snapshot.atr
            )
            
            # Проверяем, значимо ли изменение
            if abs(price_change_pct) < adaptive_threshold:
                logger.debug(f"Change for {symbol} is below threshold: {price_change_pct:.2f}% < {adaptive_threshold:.2f}%")
                return None
            
            # Анализируем объём
            volume_spike = False
            volume_multiplier = None
            if current_snapshot.volume and previous_snapshot.volume:
                if previous_snapshot.volume > 0:
                    volume_multiplier = current_snapshot.volume / previous_snapshot.volume
                    volume_spike = volume_multiplier >= self.volume_spike_threshold
            
            # Определяем приоритет
            priority = self._determine_priority(
                price_change_pct=abs(price_change_pct),
                volume_spike=volume_spike
            )
            
            # Генерируем рекомендацию
            recommendation = self._generate_recommendation(
                direction=direction,
                price_change_pct=abs(price_change_pct),
                volume_spike=volume_spike,
                rsi=current_snapshot.rsi
            )
            
            signal = ChangeSignal(
                symbol=symbol,
                direction=direction,
                price_change_pct=price_change_pct,
                price_before=previous_snapshot.price,
                price_after=current_snapshot.price,
                volume_spike=volume_spike,
                hours_ago=hours_ago,
                priority=priority,
                recommendation=recommendation,
                timestamp=current_snapshot.timestamp,
                volume_multiplier=volume_multiplier,
                rsi=current_snapshot.rsi
            )
            
            logger.info(f"Generated change signal for {symbol}: {direction.value} {price_change_pct:.2f}% "
                       f"(priority: {priority.value}, volume_spike: {volume_spike})")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error comparing snapshots for {symbol}: {e}")
            return None
    
    def _is_trading_hours(self, timestamp: datetime) -> bool:
        """
        Проверить, находится ли время в торговых часах МосБиржи.
        
        Args:
            timestamp: Время для проверки
            
        Returns:
            bool: True если время в торговых часах (10:00-18:45 МСК)
        """
        # Торговые часы МосБиржи: 10:00 - 18:45 МСК
        trading_start = time(10, 0)
        trading_end = time(18, 45)
        
        current_time = timestamp.time()
        return trading_start <= current_time <= trading_end
    
    def detect_significant_changes(
        self,
        symbols: List[str],
        compare_periods: List[float] = None,
        filter_trading_hours: bool = True
    ) -> List[ChangeSignal]:
        """
        Обнаружить значимые изменения для списка инструментов.
        
        Args:
            symbols: Список тикеров для проверки
            compare_periods: Список периодов для сравнения в часах (по умолчанию [3, 24])
            filter_trading_hours: Фильтровать ли изменения вне торговых часов
            
        Returns:
            List[ChangeSignal]: Список сигналов об изменениях
        """
        if compare_periods is None:
            compare_periods = [3.0, 24.0]
        
        signals = []
        
        for symbol in symbols:
            # Получаем последний снимок
            latest_snapshot = self.price_history_repo.get_latest(symbol)
            
            if not latest_snapshot:
                logger.debug(f"No snapshot found for {symbol}, skipping")
                continue
            
            # Фильтр по времени торгов (игнорируем изменения вне торговых часов)
            if filter_trading_hours and not self._is_trading_hours(latest_snapshot.timestamp):
                logger.debug(f"Snapshot for {symbol} is outside trading hours, skipping")
                continue
            
            # Сравниваем с разными периодами
            for hours_ago in compare_periods:
                signal = self.compare_with_previous(
                    symbol=symbol,
                    current_snapshot=latest_snapshot,
                    hours_ago=hours_ago
                )
                
                if signal:
                    signals.append(signal)
                    # Для каждого инструмента берём только один сигнал (самый значимый)
                    break
        
        # Сортируем по приоритету
        priority_order = {SignalPriority.HIGH: 3, SignalPriority.MEDIUM: 2, SignalPriority.LOW: 1}
        signals.sort(key=lambda s: priority_order[s.priority], reverse=True)
        
        return signals
    
    def _determine_priority(
        self,
        price_change_pct: float,
        volume_spike: bool
    ) -> SignalPriority:
        """
        Определить приоритет сигнала на основе изменения цены и объёма.
        
        Args:
            price_change_pct: Изменение цены в процентах (абсолютное значение)
            volume_spike: Был ли всплеск объёма
            
        Returns:
            SignalPriority: Приоритет сигнала
        """
        if price_change_pct >= 5.0 and volume_spike:
            return SignalPriority.HIGH
        elif price_change_pct >= 3.0 and volume_spike:
            return SignalPriority.MEDIUM
        elif price_change_pct >= 5.0:
            return SignalPriority.MEDIUM
        elif price_change_pct >= 3.0:
            return SignalPriority.LOW
        else:
            return SignalPriority.LOW
    
    def _generate_recommendation(
        self,
        direction: ChangeDirection,
        price_change_pct: float,
        volume_spike: bool,
        rsi: Optional[float] = None
    ) -> str:
        """
        Сгенерировать текстовую рекомендацию на основе изменения.
        
        Args:
            direction: Направление изменения
            price_change_pct: Изменение цены в процентах (абсолютное значение)
            volume_spike: Был ли всплеск объёма
            rsi: RSI индикатор
            
        Returns:
            str: Текстовая рекомендация
        """
        if direction == ChangeDirection.DOWN:
            if rsi is not None and rsi < 30:
                return "Сильный сигнал на покупку (перепроданность + падение цены)"
            elif volume_spike:
                return "Можно докупать (падение цены + высокий объём)"
            else:
                return "Возможность докупить (падение цены)"
        
        elif direction == ChangeDirection.UP:
            if rsi is not None and rsi > 70:
                return "Сильный сигнал на продажу (перекупленность + рост цены)"
            elif volume_spike:
                return "Можно продавать (рост цены + высокий объём)"
            else:
                return "Возможность продать (рост цены)"
        
        else:
            return "Цена стабильна"
