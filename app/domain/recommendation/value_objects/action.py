"""Value Object для действия рекомендации."""

from enum import Enum
from dataclasses import dataclass


class ActionType(str, Enum):
    """Типы действий рекомендации (4 уровня по отзыву)."""
    BUY = "BUY"
    ACCUMULATE = "ACCUMULATE"
    HOLD = "HOLD"
    AVOID = "AVOID"
    SELL = "SELL"


@dataclass(frozen=True)
class Action:
    """Value Object для действия рекомендации."""
    
    action_type: ActionType
    
    def is_buy(self) -> bool:
        """Проверить, является ли действие покупкой."""
        return self.action_type == ActionType.BUY
    
    def is_sell(self) -> bool:
        """Проверить, является ли действие продажей."""
        return self.action_type == ActionType.SELL
    
    def is_hold(self) -> bool:
        """Проверить, является ли действие удержанием."""
        return self.action_type == ActionType.HOLD

    def is_accumulate(self) -> bool:
        """Проверить, является ли действие докупкой понемногу."""
        return self.action_type == ActionType.ACCUMULATE

    def is_avoid(self) -> bool:
        """Проверить, является ли действие «не докупать / сократить»."""
        return self.action_type == ActionType.AVOID

    @classmethod
    def from_string(cls, action_str: str) -> "Action":
        """Создать Action из строки."""
        try:
            action_type = ActionType(action_str.upper())
            return cls(action_type=action_type)
        except ValueError:
            raise ValueError(f"Unknown action type: {action_str}")
    
    def to_string(self) -> str:
        """Преобразовать в строку."""
        return self.action_type.value
    
    def __str__(self) -> str:
        """Строковое представление."""
        return self.action_type.value
