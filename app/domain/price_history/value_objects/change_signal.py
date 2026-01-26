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
    
    rsi: Optional[float] = None
    """RSI индикатор (если доступен)."""
    
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
            'hours_ago': self.hours_ago,
            'priority': self.priority.value,
            'rsi': self.rsi,
            'recommendation': self.recommendation,
            'timestamp': self.timestamp.isoformat()
        }
