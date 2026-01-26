"""Value Object для торгового сигнала."""

from dataclasses import dataclass
from enum import Enum
from typing import List


class SignalType(str, Enum):
    """Типы торговых сигналов."""
    PRICE_BELOW_SMA200 = "PRICE_BELOW_SMA200"
    PRICE_ABOVE_SMA200 = "PRICE_ABOVE_SMA200"
    SMA50_CROSS_UP_SMA200 = "SMA50_CROSS_UP_SMA200"
    SMA50_CROSS_DOWN_SMA200 = "SMA50_CROSS_DOWN_SMA200"
    DY_GT_TARGET = "DY_GT_TARGET"
    VOL_SPIKE = "VOL_SPIKE"
    NEAR_52W_LOW = "NEAR_52W_LOW"
    NEAR_52W_HIGH = "NEAR_52W_HIGH"


@dataclass(frozen=True)
class Signal:
    """Value Object для торгового сигнала."""
    
    signal_type: SignalType
    description: str = ""
    
    def is_bullish(self) -> bool:
        """Проверить, является ли сигнал бычьим (покупка)."""
        bullish_signals = [
            SignalType.PRICE_BELOW_SMA200,
            SignalType.SMA50_CROSS_UP_SMA200,
            SignalType.DY_GT_TARGET,
            SignalType.NEAR_52W_LOW
        ]
        return self.signal_type in bullish_signals
    
    def is_bearish(self) -> bool:
        """Проверить, является ли сигнал медвежьим (продажа)."""
        bearish_signals = [
            SignalType.PRICE_ABOVE_SMA200,
            SignalType.SMA50_CROSS_DOWN_SMA200,
            SignalType.NEAR_52W_HIGH
        ]
        return self.signal_type in bearish_signals
    
    @classmethod
    def from_string(cls, signal_str: str) -> "Signal":
        """Создать Signal из строки."""
        try:
            signal_type = SignalType(signal_str)
            return cls(signal_type=signal_type)
        except ValueError:
            raise ValueError(f"Unknown signal type: {signal_str}")
    
    @classmethod
    def from_list(cls, signals: List) -> List["Signal"]:
        """
        Создать список Signal из списка строк или SignalType.
        
        Args:
            signals: Список строк, SignalType или Signal объектов
        """
        result = []
        for s in signals:
            if isinstance(s, Signal):
                result.append(s)
            elif isinstance(s, SignalType):
                result.append(cls(signal_type=s))
            elif isinstance(s, str):
                result.append(cls.from_string(s))
            else:
                raise ValueError(f"Cannot create Signal from {type(s)}: {s}")
        return result
    
    def to_string(self) -> str:
        """Преобразовать в строку для совместимости."""
        return self.signal_type.value
    
    def __str__(self) -> str:
        """Строковое представление."""
        return self.signal_type.value
