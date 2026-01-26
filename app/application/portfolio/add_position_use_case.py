"""Use case для добавления позиции в портфель."""

from loguru import logger

from app.domain.portfolio.entities.portfolio import Portfolio
from app.domain.portfolio.entities.position import Position
from app.domain.portfolio.repositories.portfolio_repository import PortfolioRepository


class AddPositionUseCase:
    """Use case для добавления позиции в портфель."""
    
    def __init__(self, portfolio_repository: PortfolioRepository):
        """
        Инициализация use case.
        
        Args:
            portfolio_repository: Репозиторий для работы с портфелем
        """
        self._portfolio_repo = portfolio_repository
    
    async def execute(self, position: Position) -> Portfolio:
        """
        Выполнить use case - добавить позицию в портфель.
        
        Args:
            position: Позиция для добавления
            
        Returns:
            Обновлённый портфель
        """
        logger.info(f"Adding position: {position.symbol} x {position.quantity}")
        
        # Получаем текущий портфель
        portfolio = await self._portfolio_repo.get()
        
        if portfolio is None:
            # Создаём новый портфель
            from app.domain.portfolio.value_objects.currency import Currency
            from app.domain.portfolio.value_objects.money import Money
            
            currency = position.avg_price.currency if position.avg_price else Currency.rub()
            portfolio = Portfolio(
                name="Мой портфель",
                currency=currency,
                cash=Money(amount=0.0, currency=currency),
                positions=[]
            )
            logger.info("Created new portfolio")
        
        # Добавляем позицию
        updated_portfolio = portfolio.add_position(position)
        
        # Сохраняем
        await self._portfolio_repo.save(updated_portfolio)
        
        logger.info(f"Position added: {position.symbol}, "
                   f"total positions: {len(updated_portfolio.positions)}")
        
        return updated_portfolio
