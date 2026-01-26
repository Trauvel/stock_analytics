"""Интерфейс репозитория для работы с акциями."""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.stock import Stock


class StockRepository(ABC):
    """Абстрактный репозиторий для работы с акциями."""
    
    @abstractmethod
    async def get_by_symbol(self, symbol: str) -> Optional[Stock]:
        """
        Получить акцию по тикеру.
        
        Args:
            symbol: Тикер акции
            
        Returns:
            Stock или None если не найдена
        """
        pass
    
    @abstractmethod
    async def get_all(self, symbols: List[str]) -> List[Stock]:
        """
        Получить список акций по тикерам.
        
        Args:
            symbols: Список тикеров
            
        Returns:
            Список акций (может быть короче symbols, если некоторые не найдены)
        """
        pass
    
    @abstractmethod
    async def save(self, stock: Stock) -> None:
        """
        Сохранить акцию.
        
        Args:
            stock: Акция для сохранения
        """
        pass
