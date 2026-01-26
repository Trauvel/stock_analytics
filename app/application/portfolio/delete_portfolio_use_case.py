"""Use case для удаления портфеля."""

from loguru import logger

from app.domain.portfolio.repositories.portfolio_repository import PortfolioRepository


class DeletePortfolioUseCase:
    """Use case для удаления портфеля."""
    
    def __init__(self, portfolio_repository: PortfolioRepository):
        """
        Инициализация use case.
        
        Args:
            portfolio_repository: Репозиторий для работы с портфелями
        """
        self._portfolio_repo = portfolio_repository
    
    async def execute(self, portfolio_id: str) -> None:
        """
        Выполнить use case - удалить портфель.
        
        Args:
            portfolio_id: ID портфеля для удаления
        """
        logger.info(f"Deleting portfolio: {portfolio_id}")
        
        await self._portfolio_repo.delete_by_id(portfolio_id)
        
        logger.info(f"Deleted portfolio: {portfolio_id}")
