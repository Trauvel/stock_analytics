"""Use case для получения портфеля."""

from typing import Optional
from loguru import logger

from app.domain.portfolio.entities.portfolio import Portfolio
from app.domain.portfolio.repositories.portfolio_repository import PortfolioRepository


class GetPortfolioUseCase:
    """Use case для получения портфеля."""
    
    def __init__(self, portfolio_repository: PortfolioRepository):
        """
        Инициализация use case.
        
        Args:
            portfolio_repository: Репозиторий для работы с портфелем
        """
        self._portfolio_repo = portfolio_repository
    
    async def execute(self, portfolio_id: Optional[str] = None) -> Optional[Portfolio]:
        """
        Выполнить use case - получить портфель.
        
        Args:
            portfolio_id: ID портфеля (если None, возвращает дефолтный)
        
        Returns:
            Portfolio или None если не найден
        """
        logger.info(f"Getting portfolio: {portfolio_id or 'default'}")
        
        portfolio = await self._portfolio_repo.get(portfolio_id)
        
        if portfolio:
            logger.info(f"Portfolio found: {len(portfolio.positions)} positions, "
                       f"total value: {portfolio.total_value()}")
        else:
            logger.info("Portfolio not found")
        
        return portfolio
