"""Value Object для уверенности рекомендации."""

from enum import Enum
from dataclasses import dataclass


class ConfidenceLevel(str, Enum):
    """Уровни уверенности."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class Confidence:
    """Value Object для уверенности рекомендации."""
    
    level: ConfidenceLevel
    
    def is_high(self) -> bool:
        """Проверить, высокая ли уверенность."""
        return self.level == ConfidenceLevel.HIGH
    
    def is_medium(self) -> bool:
        """Проверить, средняя ли уверенность."""
        return self.level == ConfidenceLevel.MEDIUM
    
    def is_low(self) -> bool:
        """Проверить, низкая ли уверенность."""
        return self.level == ConfidenceLevel.LOW
    
    @classmethod
    def from_score(cls, confidence_score: float) -> "Confidence":
        """
        Создать Confidence на основе числового балла.
        
        Args:
            confidence_score: Балл уверенности (сумма факторов)
        """
        if confidence_score >= 3.0:
            return cls(level=ConfidenceLevel.HIGH)
        elif confidence_score >= 1.5:
            return cls(level=ConfidenceLevel.MEDIUM)
        else:
            return cls(level=ConfidenceLevel.LOW)
    
    @classmethod
    def from_string(cls, confidence_str: str) -> "Confidence":
        """Создать Confidence из строки."""
        try:
            level = ConfidenceLevel(confidence_str.upper())
            return cls(level=level)
        except ValueError:
            raise ValueError(f"Unknown confidence level: {confidence_str}")
    
    def to_string(self) -> str:
        """Преобразовать в строку."""
        return self.level.value
    
    def __str__(self) -> str:
        """Строковое представление."""
        return self.level.value
