"""Use case для удаления позиции из портфеля."""

from loguru import logger

from app.domain.portfolio.entities.portfolio import Portfolio
from app.domain.portfolio.repositories.portfolio_repository import PortfolioRepository


class RemovePositionUseCase:
    """Use case для удаления позиции из портфеля."""
    
    def __init__(self, portfolio_repository: PortfolioRepository):
        """
        Инициализация use case.
        
        Args:
            portfolio_repository: Репозиторий для работы с портфелем
        """
        self._portfolio_repo = portfolio_repository
    
    async def execute(self, symbol: str) -> Portfolio:
        """
        Выполнить use case - удалить позицию из портфеля.
        
        Args:
            symbol: Тикер позиции для удаления
            
        Returns:
            Обновлённый портфель
        """
        logger.info(f"Removing position: {symbol}")
        
        # Получаем текущий портфель
        portfolio = await self._portfolio_repo.get()
        
        if portfolio is None:
            raise ValueError("Portfolio not found")
        
        # Удаляем позицию
        updated_portfolio = portfolio.remove_position(symbol)
        
        # Сохраняем
        await self._portfolio_repo.save(updated_portfolio)
        
        logger.info(f"Position removed: {symbol}, "
                   f"remaining positions: {len(updated_portfolio.positions)}")
        
        return updated_portfolio
