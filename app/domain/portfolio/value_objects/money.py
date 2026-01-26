"""Value Object для денежной суммы."""

from dataclasses import dataclass
from typing import Optional

from .currency import Currency


@dataclass(frozen=True)
class Money:
    """Value Object для денежной суммы с валютой."""
    
    amount: float
    currency: Currency
    
    def __post_init__(self):
        """Валидация при создании."""
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")
    
    def __add__(self, other: "Money") -> "Money":
        """Сложение денежных сумм."""
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f"Cannot add money in different currencies: {self.currency} vs {other.currency}")
        return Money(amount=self.amount + other.amount, currency=self.currency)
    
    def __sub__(self, other: "Money") -> "Money":
        """Вычитание денежных сумм."""
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract money in different currencies: {self.currency} vs {other.currency}")
        if self.amount < other.amount:
            raise ValueError("Cannot subtract: result would be negative")
        return Money(amount=self.amount - other.amount, currency=self.currency)
    
    def __mul__(self, multiplier: float) -> "Money":
        """Умножение на число."""
        if multiplier < 0:
            raise ValueError("Multiplier cannot be negative")
        return Money(amount=self.amount * multiplier, currency=self.currency)
    
    def __lt__(self, other: "Money") -> bool:
        """Сравнение сумм."""
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare money in different currencies: {self.currency} vs {other.currency}")
        return self.amount < other.amount
    
    def __le__(self, other: "Money") -> bool:
        """Сравнение сумм."""
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare money in different currencies: {self.currency} vs {other.currency}")
        return self.amount <= other.amount
    
    @classmethod
    def from_float(cls, amount: Optional[float], currency_code: str = "RUB") -> Optional["Money"]:
        """Создать Money из float или None."""
        if amount is None:
            return None
        return cls(amount=amount, currency=Currency.from_string(currency_code))
    
    def to_float(self) -> float:
        """Преобразовать в float для совместимости."""
        return self.amount
    
    def __str__(self) -> str:
        """Строковое представление."""
        return f"{self.amount:.2f} {self.currency}"
