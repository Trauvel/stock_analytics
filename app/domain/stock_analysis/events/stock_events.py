"""Domain Events для Stock entity."""

from app.domain.shared.domain_event import DomainEvent


class StockAnalyzed(DomainEvent):
    """Событие: акция проанализирована."""
    
    def __init__(self, symbol: str, price: float, signals_count: int):
        """
        Инициализация события.
        
        Args:
            symbol: Тикер акции
            price: Цена акции
            signals_count: Количество сигналов
        """
        super().__init__(aggregate_id=symbol)
        self.symbol = symbol
        self.price = price
        self.signals_count = signals_count
    
    def _get_event_data(self) -> dict:
        """Получить данные события."""
        return {
            "symbol": self.symbol,
            "price": self.price,
            "signals_count": self.signals_count
        }


class StockPriceChanged(DomainEvent):
    """Событие: цена акции изменилась."""
    
    def __init__(self, symbol: str, old_price: float, new_price: float):
        """
        Инициализация события.
        
        Args:
            symbol: Тикер акции
            old_price: Старая цена
            new_price: Новая цена
        """
        super().__init__(aggregate_id=symbol)
        self.symbol = symbol
        self.old_price = old_price
        self.new_price = new_price
        self.change_pct = ((new_price - old_price) / old_price * 100) if old_price > 0 else 0.0
    
    def _get_event_data(self) -> dict:
        """Получить данные события."""
        return {
            "symbol": self.symbol,
            "old_price": self.old_price,
            "new_price": self.new_price,
            "change_pct": round(self.change_pct, 2)
        }
