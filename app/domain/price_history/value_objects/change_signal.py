"""Value object для сигнала об изменении цены."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class ChangeDirection(str, Enum):
    """Направление изменения цены."""
    UP = "UP"
    DOWN = "DOWN"
    STABLE = "STABLE"


class SignalPriority(str, Enum):
    """Приоритет сигнала."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class ChangeSignal:
    """
    Сигнал об изменении цены инструмента.
    
    Используется для генерации уведомлений в Telegram.
    """
    
    # Обязательные поля (без дефолтных значений)
    symbol: str
    """Тикер инструмента."""
    
    direction: ChangeDirection
    """Направление изменения (UP/DOWN/STABLE)."""
    
    price_change_pct: float
    """Изменение цены в процентах."""
    
    price_before: float
    """Цена до изменения."""
    
    price_after: float
    """Цена после изменения."""
    
    volume_spike: bool
    """Был ли всплеск объёма."""
    
    hours_ago: float
    """За сколько часов произошло изменение."""
    
    priority: SignalPriority
    """Приоритет сигнала."""
    
    recommendation: str
    """Рекомендация (например, "можно докупать", "можно продавать")."""
    
    timestamp: datetime
    """Время создания сигнала."""
    
    # Опциональные поля (с дефолтными значениями)
    volume_multiplier: Optional[float] = None
    """Во сколько раз объём превышает средний."""

    volume_before: Optional[float] = None
    """Объём в предыдущем снимке (если известен)."""

    volume_after: Optional[float] = None
    """Объём в текущем снимке (если известен)."""
    
    rsi: Optional[float] = None
    """RSI индикатор (если доступен)."""

    atr: Optional[float] = None
    """ATR (волатильность) из текущего снимка."""

    dy_pct: Optional[float] = None
    """DY% (дивиденды/купон) из текущего снимка."""

    sma_20: Optional[float] = None
    """SMA20 из текущего снимка."""

    sma_50: Optional[float] = None
    """SMA50 из текущего снимка."""

    sma_200: Optional[float] = None
    """SMA200 из текущего снимка."""

    price_vs_sma200_pct: Optional[float] = None
    """Отклонение цены от SMA200 в процентах (price_after vs sma_200)."""

    threshold_used_pct: Optional[float] = None
    """Порог срабатывания в процентах (адаптивный/базовый), который применили."""
    
    def to_dict(self) -> dict:
        """Преобразовать в словарь для сериализации."""
        return {
            'symbol': self.symbol,
            'direction': self.direction.value,
            'price_change_pct': self.price_change_pct,
            'price_before': self.price_before,
            'price_after': self.price_after,
            'volume_spike': self.volume_spike,
            'volume_multiplier': self.volume_multiplier,
            'volume_before': self.volume_before,
            'volume_after': self.volume_after,
            'hours_ago': self.hours_ago,
            'priority': self.priority.value,
            'rsi': self.rsi,
            'atr': self.atr,
            'dy_pct': self.dy_pct,
            'sma_20': self.sma_20,
            'sma_50': self.sma_50,
            'sma_200': self.sma_200,
            'price_vs_sma200_pct': self.price_vs_sma200_pct,
            'threshold_used_pct': self.threshold_used_pct,
            'recommendation': self.recommendation,
            'timestamp': self.timestamp.isoformat()
        }
