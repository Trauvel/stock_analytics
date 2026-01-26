"""Доменная сущность позиции в портфеле."""

from dataclasses import dataclass
from typing import Optional
from enum import Enum

from ..value_objects.quantity import Quantity
from ..value_objects.money import Money, Currency
from ..value_objects.currency import Currency as CurrencyVO


class PositionType(str, Enum):
    """Типы инструментов."""
    STOCK = "stock"
    BOND = "bond"
    ETF = "etf"
    FUND = "fund"
    CURRENCY = "currency"


@dataclass
class Position:
    """Доменная сущность позиции в портфеле."""
    
    symbol: str
    quantity: Quantity
    avg_price: Optional[Money]
    position_type: PositionType = PositionType.STOCK
    market: str = "moex"
    notes: Optional[str] = None
    name: Optional[str] = None
    current_value: Optional[Money] = None
    
    def __post_init__(self):
        """Валидация при создании."""
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if self.quantity.is_zero():
            raise ValueError("Position quantity cannot be zero")
    
    def calculate_cost(self) -> Optional[Money]:
        """
        Рассчитать стоимость позиции (количество × средняя цена).
        
        Returns:
            Money или None если нет средней цены
        """
        if self.avg_price is None:
            return None
        
        # Умножаем количество на цену
        total_amount = self.quantity.value * self.avg_price.amount
        return Money(amount=total_amount, currency=self.avg_price.currency)
    
    def calculate_pnl(self, current_price: Optional[Money]) -> Optional[Money]:
        """
        Рассчитать прибыль/убыток (P&L).
        
        Args:
            current_price: Текущая цена
            
        Returns:
            Money или None если нет данных
        """
        if current_price is None or self.avg_price is None:
            return None
        
        if current_price.currency != self.avg_price.currency:
            raise ValueError(f"Price currencies must match: {current_price.currency} vs {self.avg_price.currency}")
        
        # P&L = (текущая_цена - средняя_цена) × количество
        price_diff = current_price.amount - self.avg_price.amount
        pnl_amount = price_diff * self.quantity.value
        
        return Money(amount=pnl_amount, currency=current_price.currency)
    
    def calculate_pnl_percent(self, current_price: Optional[Money]) -> Optional[float]:
        """
        Рассчитать прибыль/убыток в процентах.
        
        Args:
            current_price: Текущая цена
            
        Returns:
            float или None если нет данных
        """
        if current_price is None or self.avg_price is None:
            return None
        
        if self.avg_price.amount == 0:
            return None
        
        pnl_pct = ((current_price.amount - self.avg_price.amount) / self.avg_price.amount) * 100.0
        return round(pnl_pct, 2)
    
    def add_quantity(self, additional: Quantity) -> "Position":
        """Добавить количество к позиции."""
        new_quantity = self.quantity + additional
        return Position(
            symbol=self.symbol,
            quantity=new_quantity,
            avg_price=self.avg_price,
            position_type=self.position_type,
            market=self.market,
            notes=self.notes,
            name=self.name,
            current_value=self.current_value
        )
    
    def remove_quantity(self, to_remove: Quantity) -> "Position":
        """Удалить количество из позиции."""
        if to_remove.value > self.quantity.value:
            raise ValueError(f"Cannot remove {to_remove.value} from position with {self.quantity.value}")
        
        new_quantity = self.quantity - to_remove
        return Position(
            symbol=self.symbol,
            quantity=new_quantity,
            avg_price=self.avg_price,
            position_type=self.position_type,
            market=self.market,
            notes=self.notes,
            name=self.name,
            current_value=self.current_value
        )
    
    def to_dict(self) -> dict:
        """Преобразовать в словарь для сериализации."""
        return {
            "symbol": self.symbol,
            "quantity": self.quantity.to_int(),
            "qty": self.quantity.to_int(),  # Для совместимости
            "avg_price": self.avg_price.to_float() if self.avg_price else None,
            "market": self.market,
            "type": self.position_type.value,
            "notes": self.notes,
            "name": self.name,
            "current_value": self.current_value.to_float() if self.current_value else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Position":
        """Создать Position из словаря."""
        quantity_value = data.get("quantity") or data.get("qty") or 0
        currency_code = data.get("currency", "RUB")
        
        return cls(
            symbol=data["symbol"],
            quantity=Quantity.from_int(quantity_value),
            avg_price=Money.from_float(data.get("avg_price"), currency_code),
            position_type=PositionType(data.get("type", "stock")),
            market=data.get("market", "moex"),
            notes=data.get("notes"),
            name=data.get("name"),
            current_value=Money.from_float(data.get("current_value"), currency_code)
        )
