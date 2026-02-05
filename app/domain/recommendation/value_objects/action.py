"""Value Object для действия рекомендации."""

from enum import Enum
from dataclasses import dataclass


class ActionType(str, Enum):
    """Типы действий рекомендации (в т.ч. HOLD_STRONG / HOLD_NEUTRAL для UX)."""
    BUY = "BUY"
    ACCUMULATE = "ACCUMULATE"
    HOLD_STRONG = "HOLD_STRONG"   # держать, можно докупать при просадках
    HOLD_NEUTRAL = "HOLD_NEUTRAL"  # ничего не делаем
    REDUCE = "REDUCE"
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
        """Проверить, является ли действие удержанием (любой HOLD)."""
        return self.action_type in (ActionType.HOLD_STRONG, ActionType.HOLD_NEUTRAL)

    def is_hold_strong(self) -> bool:
        return self.action_type == ActionType.HOLD_STRONG

    def is_hold_neutral(self) -> bool:
        return self.action_type == ActionType.HOLD_NEUTRAL

    def is_accumulate(self) -> bool:
        """Проверить, является ли действие докупкой понемногу."""
        return self.action_type == ActionType.ACCUMULATE

    def is_reduce(self) -> bool:
        """Проверить, является ли действие «не докупать / сократить» (REDUCE)."""
        return self.action_type == ActionType.REDUCE

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
