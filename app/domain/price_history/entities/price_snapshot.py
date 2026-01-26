"""Доменная сущность снимка цены инструмента."""

from datetime import datetime
from typing import Optional
from dataclasses import dataclass


@dataclass
class PriceSnapshot:
    """
    Снимок цены и метрик инструмента в определённый момент времени.
    
    Используется для отслеживания изменений и генерации уведомлений.
    """
    
    symbol: str
    """Тикер инструмента или ISIN код облигации."""
    
    timestamp: datetime
    """Время создания снимка."""
    
    price: float
    """Текущая цена инструмента."""
    
    volume: Optional[float] = None
    """Объём торгов за последний период."""
    
    sma_20: Optional[float] = None
    """SMA за 20 дней."""
    
    sma_50: Optional[float] = None
    """SMA за 50 дней."""
    
    sma_200: Optional[float] = None
    """SMA за 200 дней."""
    
    dy_pct: Optional[float] = None
    """Дивидендная доходность (для акций) или купонная доходность (для облигаций) в процентах."""
    
    rsi: Optional[float] = None
    """RSI индикатор (если рассчитан)."""
    
    atr: Optional[float] = None
    """ATR индикатор (Average True Range) для измерения волатильности."""
    
    def to_dict(self) -> dict:
        """Преобразовать в словарь для сериализации."""
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'price': self.price,
            'volume': self.volume,
            'sma_20': self.sma_20,
            'sma_50': self.sma_50,
            'sma_200': self.sma_200,
            'dy_pct': self.dy_pct,
            'rsi': self.rsi,
            'atr': self.atr
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PriceSnapshot':
        """Создать из словаря."""
        return cls(
            symbol=data['symbol'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            price=data['price'],
            volume=data.get('volume'),
            sma_20=data.get('sma_20'),
            sma_50=data.get('sma_50'),
            sma_200=data.get('sma_200'),
            dy_pct=data.get('dy_pct'),
            rsi=data.get('rsi'),
            atr=data.get('atr')
        )
