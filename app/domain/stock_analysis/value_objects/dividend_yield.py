"""Value Object для дивидендной доходности."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DividendYield:
    """Value Object для дивидендной доходности (в процентах)."""
    
    value: float  # В процентах (например, 8.5 для 8.5%)
    
    def __post_init__(self):
        """Валидация при создании."""
        if self.value < 0:
            raise ValueError("Dividend yield cannot be negative")
        # Реалистичный максимум - 100%
        if self.value > 100:
            raise ValueError(f"Dividend yield {self.value}% seems unrealistic")
    
    def is_high(self, threshold: float = 8.0) -> bool:
        """Проверить, является ли доходность высокой."""
        return self.value >= threshold
    
    def is_very_high(self, threshold: float = 15.0) -> bool:
        """Проверить, является ли доходность очень высокой."""
        return self.value >= threshold
    
    @classmethod
    def from_float(cls, value: Optional[float]) -> Optional["DividendYield"]:
        """Создать DividendYield из float или None."""
        if value is None:
            return None
        return cls(value=value)
    
    def to_float(self) -> float:
        """Преобразовать в float для совместимости."""
        return self.value
    
    def __str__(self) -> str:
        """Строковое представление."""
        return f"{self.value:.2f}%"
