"""Доменная сущность акции."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from ..value_objects.price import Price
from ..value_objects.dividend_yield import DividendYield
from ..value_objects.signal import Signal, SignalType


@dataclass
class Stock:
    """Доменная сущность акции с бизнес-логикой."""
    
    symbol: str
    price: Optional[Price]
    dividend_yield: Optional[DividendYield]
    sma_20: Optional[Price]
    sma_50: Optional[Price]
    sma_200: Optional[Price]
    high_52w: Optional[Price]
    low_52w: Optional[Price]
    signals: List[Signal]
    lot: Optional[int] = None
    div_ttm: Optional[float] = None  # Дивиденды TTM в рублях
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Валидация и инициализация."""
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if self.signals is None:
            self.signals = []
    
    # === Бизнес-правила ===
    
    def is_undervalued(self) -> bool:
        """
        Проверить, недооценена ли акция.
        
        Акция считается недооцененной, если цена ниже SMA200.
        """
        if self.price is None or self.sma_200 is None:
            return False
        return self.price < self.sma_200
    
    def is_overvalued(self) -> bool:
        """
        Проверить, переоценена ли акция.
        
        Акция считается переоцененной, если цена выше SMA200.
        """
        if self.price is None or self.sma_200 is None:
            return False
        return self.price > self.sma_200
    
    def has_high_dividend_yield(self, threshold: float = 8.0) -> bool:
        """
        Проверить, имеет ли акция высокую дивидендную доходность.
        
        Args:
            threshold: Порог доходности в процентах (по умолчанию 8%)
        """
        if self.dividend_yield is None:
            return False
        return self.dividend_yield.is_high(threshold)
    
    def discount_to_sma200(self) -> Optional[float]:
        """
        Вычислить дисконт к SMA200 в процентах.
        
        Returns:
            Процентная разница (отрицательная = дисконт, положительная = премия)
        """
        if self.price is None or self.sma_200 is None:
            return None
        return self.price.percentage_diff(self.sma_200)
    
    def position_in_52w_range(self) -> Optional[float]:
        """
        Вычислить позицию в 52-недельном диапазоне (0.0 = минимум, 1.0 = максимум).
        
        Returns:
            Позиция от 0.0 до 1.0 или None если данных недостаточно
        """
        if self.price is None or self.high_52w is None or self.low_52w is None:
            return None
        
        range_size = self.high_52w.value - self.low_52w.value
        if range_size == 0:
            return 0.5  # Если диапазон нулевой, считаем серединой
        
        position = (self.price.value - self.low_52w.value) / range_size
        return max(0.0, min(1.0, position))  # Ограничиваем [0, 1]
    
    def is_near_52w_low(self, threshold: float = 0.3) -> bool:
        """
        Проверить, находится ли цена в нижней трети 52W диапазона.
        
        Args:
            threshold: Порог (0.3 = нижняя треть)
        """
        position = self.position_in_52w_range()
        if position is None:
            return False
        return position < threshold
    
    def is_near_52w_high(self, threshold: float = 0.9) -> bool:
        """
        Проверить, находится ли цена у верхней границы 52W диапазона.
        
        Args:
            threshold: Порог (0.9 = верхние 10%)
        """
        position = self.position_in_52w_range()
        if position is None:
            return False
        return position > threshold
    
    def has_signal(self, signal_type: SignalType) -> bool:
        """Проверить, есть ли у акции конкретный сигнал."""
        return any(s.signal_type == signal_type for s in self.signals)
    
    def bullish_signals_count(self) -> int:
        """Подсчитать количество бычьих сигналов."""
        return sum(1 for s in self.signals if s.is_bullish())
    
    def bearish_signals_count(self) -> int:
        """Подсчитать количество медвежьих сигналов."""
        return sum(1 for s in self.signals if s.is_bearish())
    
    # === Методы для совместимости со старым кодом ===
    
    def to_dict(self) -> dict:
        """Преобразовать в словарь для сериализации."""
        return {
            "symbol": self.symbol,
            "price": self.price.to_float() if self.price else None,
            "lot": self.lot,
            "div_ttm": self.div_ttm,
            "dy_pct": self.dividend_yield.to_float() if self.dividend_yield else None,
            "sma_20": self.sma_20.to_float() if self.sma_20 else None,
            "sma_50": self.sma_50.to_float() if self.sma_50 else None,
            "sma_200": self.sma_200.to_float() if self.sma_200 else None,
            "high_52w": self.high_52w.to_float() if self.high_52w else None,
            "low_52w": self.low_52w.to_float() if self.low_52w else None,
            "dist_52w_low_pct": self.position_in_52w_range() * 100 if self.position_in_52w_range() is not None else None,
            "dist_52w_high_pct": (1 - self.position_in_52w_range()) * 100 if self.position_in_52w_range() is not None else None,
            "signals": [s.to_string() for s in self.signals],
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Stock":
        """Создать Stock из словаря (для совместимости)."""
        from ..value_objects.price import Price
        from ..value_objects.dividend_yield import DividendYield
        from ..value_objects.signal import Signal
        
        updated_at = None
        if data.get("updated_at"):
            if isinstance(data["updated_at"], str):
                updated_at = datetime.fromisoformat(data["updated_at"])
            elif isinstance(data["updated_at"], datetime):
                updated_at = data["updated_at"]
        
        return cls(
            symbol=data["symbol"],
            price=Price.from_float(data.get("price")),
            dividend_yield=DividendYield.from_float(data.get("dy_pct")),
            sma_20=Price.from_float(data.get("sma_20")),
            sma_50=Price.from_float(data.get("sma_50")),
            sma_200=Price.from_float(data.get("sma_200")),
            high_52w=Price.from_float(data.get("high_52w")),
            low_52w=Price.from_float(data.get("low_52w")),
            signals=Signal.from_list(data.get("signals", [])) if data.get("signals") else [],
            lot=data.get("lot"),
            div_ttm=data.get("div_ttm"),
            updated_at=updated_at
        )
