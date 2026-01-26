"""Use case для получения списка всех портфелей."""

from typing import List
from loguru import logger

from app.domain.portfolio.entities.portfolio import Portfolio
from app.domain.portfolio.repositories.portfolio_repository import PortfolioRepository


class ListPortfoliosUseCase:
    """Use case для получения списка всех портфелей."""
    
    def __init__(self, portfolio_repository: PortfolioRepository):
        """
        Инициализация use case.
        
        Args:
            portfolio_repository: Репозиторий для работы с портфелями
        """
        self._portfolio_repo = portfolio_repository
    
    async def execute(self) -> List[Portfolio]:
        """
        Выполнить use case - получить список всех портфелей.
        
        Returns:
            List[Portfolio]: Список всех портфелей
        """
        logger.info("Listing all portfolios")
        
        portfolios = await self._portfolio_repo.list_all()
        
        logger.info(f"Found {len(portfolios)} portfolios")
        return portfolios
