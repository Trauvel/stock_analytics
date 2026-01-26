"""Доменная сущность портфеля."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from ..value_objects.money import Money
from ..value_objects.currency import Currency
from .position import Position
from ..events.portfolio_events import (
    PortfolioCreated,
    PositionAdded,
    PositionRemoved,
    PortfolioValueChanged
)


@dataclass
class Portfolio:
    """Доменная сущность портфеля инвестора."""
    
    id: Optional[str] = None  # Уникальный идентификатор портфеля
    name: Optional[str] = None
    currency: Currency = None
    cash: Money = None
    positions: List[Position] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    _domain_events: List = field(default_factory=list, init=False, repr=False)
    
    def __post_init__(self):
        """Валидация при создании."""
        # Проверяем, что все позиции в той же валюте
        for position in self.positions:
            if position.avg_price and position.avg_price.currency.code != self.currency.code:
                raise ValueError(
                    f"Position {position.symbol} currency {position.avg_price.currency} "
                    f"does not match portfolio currency {self.currency}"
                )
    
    # === Бизнес-правила ===
    
    def total_positions_value(self) -> Money:
        """
        Рассчитать общую стоимость всех позиций.
        
        Returns:
            Money: Общая стоимость позиций
        """
        total = Money(amount=0.0, currency=self.currency)
        
        for position in self.positions:
            cost = position.calculate_cost()
            if cost:
                total = total + cost
        
        return total
    
    def total_value(self) -> Money:
        """
        Рассчитать общую стоимость портфеля (позиции + кеш).
        
        Returns:
            Money: Общая стоимость портфеля
        """
        positions_value = self.total_positions_value()
        return positions_value + self.cash
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """
        Получить позицию по тикеру.
        
        Args:
            symbol: Тикер инструмента
            
        Returns:
            Position или None если не найдена
        """
        for position in self.positions:
            if position.symbol == symbol:
                return position
        return None
    
    def has_position(self, symbol: str) -> bool:
        """Проверить, есть ли позиция по тикеру."""
        return self.get_position(symbol) is not None
    
    def add_position(self, position: Position) -> "Portfolio":
        """
        Добавить позицию в портфель.
        
        Args:
            position: Позиция для добавления
            
        Returns:
            Новый Portfolio с добавленной позицией
        """
        # Проверяем валюту
        if position.avg_price and position.avg_price.currency.code != self.currency.code:
            raise ValueError(f"Position currency must match portfolio currency: {self.currency}")
        
        # Запоминаем старую стоимость для события
        old_value = self.total_value().amount
        
        # Если позиция уже есть, объединяем
        existing = self.get_position(position.symbol)
        if existing:
            # Объединяем количества и пересчитываем среднюю цену
            total_quantity = existing.quantity.value + position.quantity.value
            existing_cost = existing.calculate_cost()
            new_cost = position.calculate_cost()
            
            if existing_cost and new_cost:
                total_cost = existing_cost.amount + new_cost.amount
                new_avg_price = Money(amount=total_cost / total_quantity, currency=self.currency)
                
                updated_position = Position(
                    symbol=position.symbol,
                    quantity=existing.quantity + position.quantity,
                    avg_price=new_avg_price,
                    position_type=position.position_type,
                    market=position.market,
                    notes=position.notes or existing.notes,
                    name=position.name or existing.name
                )
                
                new_positions = [p for p in self.positions if p.symbol != position.symbol]
                new_positions.append(updated_position)
            else:
                # Если нет цен, просто добавляем количество
                new_positions = [p for p in self.positions if p.symbol != position.symbol]
                new_positions.append(existing.add_quantity(position.quantity))
        else:
            # Новая позиция
            new_positions = self.positions + [position]
        
        new_portfolio = Portfolio(
            id=self.id,
            name=self.name,
            currency=self.currency,
            cash=self.cash,
            positions=new_positions,
            created_at=self.created_at,
            updated_at=datetime.now()
        )
        
        # Копируем события из текущего портфеля
        new_portfolio._domain_events = self._domain_events.copy()
        
        # Добавляем событие добавления позиции
        new_portfolio._domain_events.append(PositionAdded(
            symbol=position.symbol,
            quantity=position.quantity.value,
            avg_price=position.avg_price.amount if position.avg_price else 0.0
        ))
        
        # Добавляем событие изменения стоимости портфеля
        new_value = new_portfolio.total_value().amount
        if abs(new_value - old_value) > 0.01:  # Изменение больше 1 копейки
            new_portfolio._domain_events.append(PortfolioValueChanged(
                old_value=old_value,
                new_value=new_value,
                currency=self.currency.code
            ))
        
        return new_portfolio
    
    def remove_position(self, symbol: str) -> "Portfolio":
        """
        Удалить позицию из портфеля.
        
        Args:
            symbol: Тикер позиции для удаления
            
        Returns:
            Новый Portfolio без позиции
        """
        # Запоминаем старую стоимость для события
        old_value = self.total_value().amount
        
        new_positions = [p for p in self.positions if p.symbol != symbol]
        
        if len(new_positions) == len(self.positions):
            raise ValueError(f"Position {symbol} not found in portfolio")
        
        new_portfolio = Portfolio(
            name=self.name,
            currency=self.currency,
            cash=self.cash,
            positions=new_positions,
            created_at=self.created_at,
            updated_at=datetime.now()
        )
        
        # Копируем события из текущего портфеля
        new_portfolio._domain_events = self._domain_events.copy()
        
        # Добавляем событие удаления позиции
        new_portfolio._domain_events.append(PositionRemoved(symbol=symbol))
        
        # Добавляем событие изменения стоимости портфеля
        new_value = new_portfolio.total_value().amount
        if abs(new_value - old_value) > 0.01:
            new_portfolio._domain_events.append(PortfolioValueChanged(
                old_value=old_value,
                new_value=new_value,
                currency=self.currency.code
            ))
        
        return new_portfolio
    
    def update_cash(self, new_cash: Money) -> "Portfolio":
        """
        Обновить количество кеша.
        
        Args:
            new_cash: Новое количество кеша
            
        Returns:
            Новый Portfolio с обновлённым кешем
        """
        if new_cash.currency != self.currency:
            raise ValueError(f"Cash currency must match portfolio currency: {self.currency}")
        
        return Portfolio(
            id=self.id,
            name=self.name,
            currency=self.currency,
            cash=new_cash,
            positions=self.positions,
            created_at=self.created_at,
            updated_at=datetime.now()
        )
    
    def to_dict(self) -> dict:
        """Преобразовать в словарь для сериализации."""
        return {
            "id": self.id,
            "name": self.name,
            "currency": self.currency.code if self.currency else "RUB",
            "cash": self.cash.to_float() if self.cash else 0.0,
            "positions": [p.to_dict() for p in self.positions],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Portfolio":
        """Создать Portfolio из словаря."""
        currency = Currency.from_string(data.get("currency", "RUB"))
        cash = Money.from_float(data.get("cash", 0.0), currency.code)
        
        created_at = None
        if data.get("created_at"):
            if isinstance(data["created_at"], str):
                created_at = datetime.fromisoformat(data["created_at"])
            elif isinstance(data["created_at"], datetime):
                created_at = data["created_at"]
        
        updated_at = None
        if data.get("updated_at"):
            if isinstance(data["updated_at"], str):
                updated_at = datetime.fromisoformat(data["updated_at"])
            elif isinstance(data["updated_at"], datetime):
                updated_at = data["updated_at"]
        
        positions = [Position.from_dict(p) for p in data.get("positions", [])]
        
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            currency=currency,
            cash=cash,
            positions=positions,
            created_at=created_at,
            updated_at=updated_at
        )
