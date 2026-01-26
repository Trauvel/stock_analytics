"""Интерфейс репозитория для работы с портфелем."""

from abc import ABC, abstractmethod
from typing import Optional, List

from ..entities.portfolio import Portfolio


class PortfolioRepository(ABC):
    """Абстрактный репозиторий для работы с портфелем."""
    
    @abstractmethod
    async def get(self, portfolio_id: Optional[str] = None) -> Optional[Portfolio]:
        """
        Получить портфель по ID (или дефолтный, если ID не указан).
        
        Args:
            portfolio_id: ID портфеля (если None, возвращает дефолтный)
        
        Returns:
            Portfolio или None если не найден
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, portfolio_id: str) -> Optional[Portfolio]:
        """
        Получить портфель по ID.
        
        Args:
            portfolio_id: ID портфеля
        
        Returns:
            Portfolio или None если не найден
        """
        pass
    
    @abstractmethod
    async def list_all(self) -> List[Portfolio]:
        """
        Получить список всех портфелей.
        
        Returns:
            List[Portfolio]: Список всех портфелей
        """
        pass
    
    @abstractmethod
    async def save(self, portfolio: Portfolio) -> Portfolio:
        """
        Сохранить портфель.
        
        Args:
            portfolio: Портфель для сохранения
            
        Returns:
            Сохранённый портфель с обновлённым ID (если был создан новый)
        """
        pass
    
    @abstractmethod
    async def delete(self, portfolio_id: Optional[str] = None) -> None:
        """
        Удалить портфель.
        
        Args:
            portfolio_id: ID портфеля (если None, удаляет дефолтный)
        """
        pass
    
    @abstractmethod
    async def delete_by_id(self, portfolio_id: str) -> None:
        """
        Удалить портфель по ID.
        
        Args:
            portfolio_id: ID портфеля
        """
        pass
