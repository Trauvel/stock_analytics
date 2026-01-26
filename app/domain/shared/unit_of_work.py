"""Unit of Work pattern для управления транзакциями."""

from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING
from loguru import logger

from app.domain.stock_analysis.repositories.stock_repository import StockRepository
from app.domain.portfolio.repositories.portfolio_repository import PortfolioRepository

if TYPE_CHECKING:
    from app.domain.portfolio.entities.portfolio import Portfolio


class UnitOfWork(ABC):
    """Абстрактный Unit of Work."""
    
    @abstractmethod
    def __enter__(self):
        """Вход в контекст транзакции."""
        pass
    
    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекста транзакции."""
        pass
    
    @abstractmethod
    def commit(self) -> None:
        """Зафиксировать изменения."""
        pass
    
    @abstractmethod
    def rollback(self) -> None:
        """Откатить изменения."""
        pass


class StockAnalysisUnitOfWork(UnitOfWork):
    """Unit of Work для Stock Analysis Context."""
    
    def __init__(self, stock_repository: StockRepository):
        """
        Инициализация Unit of Work.
        
        Args:
            stock_repository: Репозиторий для работы с акциями
        """
        self._stock_repository = stock_repository
        self._committed = False
    
    def __enter__(self):
        """Вход в контекст транзакции."""
        logger.debug("Starting Stock Analysis Unit of Work")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекста транзакции."""
        if exc_type is None and not self._committed:
            # Если не было ошибки и не был вызван commit, делаем автоматический commit
            self.commit()
        elif exc_type is not None:
            # Если была ошибка, делаем rollback
            self.rollback()
    
    def commit(self) -> None:
        """Зафиксировать изменения."""
        logger.debug("Committing Stock Analysis Unit of Work")
        # В текущей реализации репозиторий сохраняет сразу,
        # но здесь можно добавить кеширование и batch операции
        self._committed = True
    
    def rollback(self) -> None:
        """Откатить изменения."""
        logger.debug("Rolling back Stock Analysis Unit of Work")
        # В текущей реализации нет транзакций,
        # но здесь можно добавить откат изменений
        self._committed = False
    
    @property
    def stocks(self) -> StockRepository:
        """Получить репозиторий акций."""
        return self._stock_repository


class PortfolioUnitOfWork:
    """Unit of Work для Portfolio Management Context."""
    
    def __init__(self, portfolio_repository: PortfolioRepository):
        """
        Инициализация Unit of Work.
        
        Args:
            portfolio_repository: Репозиторий для работы с портфелем
        """
        self._portfolio_repository = portfolio_repository
        self._portfolio_cache: Optional["Portfolio"] = None
        self._committed = False
    
    async def __aenter__(self):
        """Вход в async контекст транзакции."""
        logger.debug("Starting Portfolio Unit of Work")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Выход из async контекста транзакции."""
        if exc_type is None and not self._committed:
            # Если не было ошибки и не был вызван commit, делаем автоматический commit
            await self.commit()
        elif exc_type is not None:
            # Если была ошибка, делаем rollback
            self.rollback()
    
    async def get_portfolio(self) -> Optional["Portfolio"]:
        """
        Получить портфель (с кешированием в рамках UoW).
        
        Returns:
            Portfolio или None
        """
        if self._portfolio_cache is None:
            self._portfolio_cache = await self._portfolio_repository.get()
        return self._portfolio_cache
    
    async def save_portfolio(self, portfolio: "Portfolio") -> None:
        """
        Сохранить портфель (в кеш, реальное сохранение при commit).
        
        Args:
            portfolio: Портфель для сохранения
        """
        self._portfolio_cache = portfolio
    
    async def commit(self) -> None:
        """Зафиксировать изменения."""
        logger.debug("Committing Portfolio Unit of Work")
        
        # Публикуем события перед сохранением
        if self._portfolio_cache:
            from app.domain.portfolio.entities.portfolio_helpers import publish_events
            publish_events(self._portfolio_cache)
            
            # Сохраняем портфель
            await self._portfolio_repository.save(self._portfolio_cache)
        
        self._committed = True
    
    async def rollback(self) -> None:
        """Откатить изменения."""
        logger.debug("Rolling back Portfolio Unit of Work")
        self._portfolio_cache = None
        self._committed = False
    
    @property
    def portfolio(self) -> PortfolioRepository:
        """Получить репозиторий портфеля."""
        return self._portfolio_repository
