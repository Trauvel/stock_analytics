"""Domain Events для Portfolio entity."""

from app.domain.shared.domain_event import DomainEvent


class PortfolioCreated(DomainEvent):
    """Событие: портфель создан."""
    
    def __init__(self, portfolio_name: str, currency: str, initial_cash: float):
        """
        Инициализация события.
        
        Args:
            portfolio_name: Название портфеля
            currency: Валюта портфеля
            initial_cash: Начальный кеш
        """
        super().__init__(aggregate_id=portfolio_name or "default")
        self.portfolio_name = portfolio_name
        self.currency = currency
        self.initial_cash = initial_cash
    
    def _get_event_data(self) -> dict:
        """Получить данные события."""
        return {
            "portfolio_name": self.portfolio_name,
            "currency": self.currency,
            "initial_cash": self.initial_cash
        }


class PositionAdded(DomainEvent):
    """Событие: позиция добавлена в портфель."""
    
    def __init__(self, symbol: str, quantity: int, avg_price: float):
        """
        Инициализация события.
        
        Args:
            symbol: Тикер позиции
            quantity: Количество
            avg_price: Средняя цена
        """
        super().__init__(aggregate_id=symbol)
        self.symbol = symbol
        self.quantity = quantity
        self.avg_price = avg_price
        self.total_cost = quantity * avg_price
    
    def _get_event_data(self) -> dict:
        """Получить данные события."""
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "avg_price": self.avg_price,
            "total_cost": self.total_cost
        }


class PositionRemoved(DomainEvent):
    """Событие: позиция удалена из портфеля."""
    
    def __init__(self, symbol: str):
        """
        Инициализация события.
        
        Args:
            symbol: Тикер позиции
        """
        super().__init__(aggregate_id=symbol)
        self.symbol = symbol
    
    def _get_event_data(self) -> dict:
        """Получить данные события."""
        return {
            "symbol": self.symbol
        }


class PortfolioValueChanged(DomainEvent):
    """Событие: стоимость портфеля изменилась."""
    
    def __init__(self, old_value: float, new_value: float, currency: str):
        """
        Инициализация события.
        
        Args:
            old_value: Старая стоимость
            new_value: Новая стоимость
            currency: Валюта
        """
        super().__init__(aggregate_id="portfolio")
        self.old_value = old_value
        self.new_value = new_value
        self.currency = currency
        self.change_pct = ((new_value - old_value) / old_value * 100) if old_value > 0 else 0.0
    
    def _get_event_data(self) -> dict:
        """Получить данные события."""
        return {
            "old_value": self.old_value,
            "new_value": self.new_value,
            "currency": self.currency,
            "change_pct": round(self.change_pct, 2)
        }
