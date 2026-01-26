"""Value Object для цены акции."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Price:
    """Value Object для цены. Неизменяемый объект."""
    
    value: float
    currency: str = "RUB"
    
    def __post_init__(self):
        """Валидация при создании."""
        if self.value < 0:
            raise ValueError("Price cannot be negative")
        if not self.currency:
            raise ValueError("Currency cannot be empty")
    
    def __lt__(self, other: "Price") -> bool:
        """Сравнение цен."""
        if not isinstance(other, Price):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare prices in different currencies: {self.currency} vs {other.currency}")
        return self.value < other.value
    
    def __le__(self, other: "Price") -> bool:
        """Сравнение цен."""
        if not isinstance(other, Price):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare prices in different currencies: {self.currency} vs {other.currency}")
        return self.value <= other.value
    
    def __gt__(self, other: "Price") -> bool:
        """Сравнение цен."""
        if not isinstance(other, Price):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare prices in different currencies: {self.currency} vs {other.currency}")
        return self.value > other.value
    
    def __ge__(self, other: "Price") -> bool:
        """Сравнение цен."""
        if not isinstance(other, Price):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare prices in different currencies: {self.currency} vs {other.currency}")
        return self.value >= other.value
    
    def __add__(self, other: "Price") -> "Price":
        """Сложение цен."""
        if not isinstance(other, Price):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f"Cannot add prices in different currencies: {self.currency} vs {other.currency}")
        return Price(self.value + other.value, self.currency)
    
    def __sub__(self, other: "Price") -> "Price":
        """Вычитание цен."""
        if not isinstance(other, Price):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract prices in different currencies: {self.currency} vs {other.currency}")
        return Price(self.value - other.value, self.currency)
    
    def percentage_diff(self, other: "Price") -> float:
        """Вычислить процентную разницу между ценами."""
        if not isinstance(other, Price):
            raise ValueError("Can only compare with Price")
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare prices in different currencies: {self.currency} vs {other.currency}")
        if other.value == 0:
            return 0.0
        return ((self.value - other.value) / other.value) * 100.0
    
    @classmethod
    def from_float(cls, value: Optional[float], currency: str = "RUB") -> Optional["Price"]:
        """Создать Price из float или None."""
        if value is None:
            return None
        return cls(value=value, currency=currency)
    
    def to_float(self) -> float:
        """Преобразовать в float для совместимости."""
        return self.value
    
    def __str__(self) -> str:
        """Строковое представление."""
        return f"{self.value:.2f} {self.currency}"
