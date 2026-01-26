"""Value Object для валюты."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Currency:
    """Value Object для валюты."""
    
    code: str  # RUB, USD, EUR и т.д.
    
    def __post_init__(self):
        """Валидация при создании."""
        if not self.code:
            raise ValueError("Currency code cannot be empty")
        if len(self.code) != 3:
            raise ValueError(f"Currency code must be 3 characters, got: {self.code}")
    
    @classmethod
    def rub(cls) -> "Currency":
        """Создать валюту RUB."""
        return cls(code="RUB")
    
    @classmethod
    def usd(cls) -> "Currency":
        """Создать валюту USD."""
        return cls(code="USD")
    
    @classmethod
    def from_string(cls, code: str) -> "Currency":
        """Создать Currency из строки."""
        return cls(code=code.upper())
    
    def __str__(self) -> str:
        """Строковое представление."""
        return self.code
