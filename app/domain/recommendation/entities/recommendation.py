"""Доменная сущность рекомендации."""

from dataclasses import dataclass
from typing import List, Optional

from ..value_objects.action import Action, ActionType
from ..value_objects.confidence import Confidence


@dataclass
class Recommendation:
    """Доменная сущность рекомендации по акции."""
    
    symbol: str
    action: Action
    score: float
    reasons: List[str]
    confidence: Confidence
    sizing_hint: Optional[str] = None
    price: Optional[float] = None  # Цена для отображения
    dy_pct: Optional[float] = None  # Дивидендная доходность для отображения
    
    def __post_init__(self):
        """Валидация при создании."""
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if not self.reasons:
            self.reasons = []
    
    def is_buy_recommendation(self) -> bool:
        """Проверить, является ли рекомендация покупкой."""
        return self.action.is_buy()
    
    def is_sell_recommendation(self) -> bool:
        """Проверить, является ли рекомендация продажей."""
        return self.action.is_sell()
    
    def is_hold_recommendation(self) -> bool:
        """Проверить, является ли рекомендация удержанием."""
        return self.action.is_hold()
    
    def has_high_confidence(self) -> bool:
        """Проверить, высокая ли уверенность."""
        return self.confidence.is_high()
    
    def is_strong_signal(self) -> bool:
        """Проверить, является ли сигнал сильным (высокий score и уверенность)."""
        return abs(self.score) >= 3.0 and self.confidence.is_high()
    
    def to_dict(self) -> dict:
        """Преобразовать в словарь для сериализации."""
        return {
            "symbol": self.symbol,
            "action": self.action.to_string(),
            "score": round(self.score, 2),
            "reasons": self.reasons,
            "confidence": self.confidence.to_string(),
            "sizing_hint": self.sizing_hint,
            "price": self.price,
            "dy_pct": self.dy_pct
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Recommendation":
        """Создать Recommendation из словаря."""
        return cls(
            symbol=data["symbol"],
            action=Action.from_string(data["action"]),
            score=data["score"],
            reasons=data.get("reasons", []),
            confidence=Confidence.from_string(data.get("confidence", "MEDIUM")),
            sizing_hint=data.get("sizing_hint")
        )
