"""Value Object для количества акций."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Quantity:
    """Value Object для количества акций/инструментов."""
    
    value: int
    
    def __post_init__(self):
        """Валидация при создании."""
        if self.value < 0:
            raise ValueError("Quantity cannot be negative")
    
    def __add__(self, other: "Quantity") -> "Quantity":
        """Сложение количеств."""
        if not isinstance(other, Quantity):
            return NotImplemented
        return Quantity(value=self.value + other.value)
    
    def __sub__(self, other: "Quantity") -> "Quantity":
        """Вычитание количеств."""
        if not isinstance(other, Quantity):
            return NotImplemented
        if self.value < other.value:
            raise ValueError("Cannot subtract: result would be negative")
        return Quantity(value=self.value - other.value)
    
    def __mul__(self, multiplier: float) -> "Quantity":
        """Умножение на число (для расчёта стоимости)."""
        if multiplier < 0:
            raise ValueError("Multiplier cannot be negative")
        return Quantity(value=int(self.value * multiplier))
    
    def __lt__(self, other: "Quantity") -> bool:
        """Сравнение количеств."""
        if not isinstance(other, Quantity):
            return NotImplemented
        return self.value < other.value
    
    def __le__(self, other: "Quantity") -> bool:
        """Сравнение количеств."""
        if not isinstance(other, Quantity):
            return NotImplemented
        return self.value <= other.value
    
    @classmethod
    def from_int(cls, value: Optional[int]) -> Optional["Quantity"]:
        """Создать Quantity из int или None."""
        if value is None:
            return None
        return cls(value=value)
    
    def to_int(self) -> int:
        """Преобразовать в int для совместимости."""
        return self.value
    
    def is_zero(self) -> bool:
        """Проверить, равно ли количество нулю."""
        return self.value == 0
    
    def __str__(self) -> str:
        """Строковое представление."""
        return str(self.value)
