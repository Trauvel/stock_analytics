"""Use case для сохранения портфеля."""

from datetime import datetime
from loguru import logger

from app.domain.portfolio.entities.portfolio import Portfolio
from app.domain.portfolio.repositories.portfolio_repository import PortfolioRepository
from app.domain.shared.unit_of_work import PortfolioUnitOfWork


class SavePortfolioUseCase:
    """Use case для сохранения портфеля."""
    
    def __init__(self, portfolio_repository: PortfolioRepository):
        """
        Инициализация use case.
        
        Args:
            portfolio_repository: Репозиторий для работы с портфелем
        """
        self._portfolio_repo = portfolio_repository
    
    async def execute(self, portfolio: Portfolio) -> Portfolio:
        """
        Выполнить use case - сохранить портфель (с использованием Unit of Work).
        
        Args:
            portfolio: Портфель для сохранения
            
        Returns:
            Сохранённый портфель с обновлёнными временными метками
        """
        logger.info(f"Saving portfolio: {len(portfolio.positions)} positions")
        
        # Обновляем временные метки
        now = datetime.now()
        updated_portfolio = Portfolio(
            id=portfolio.id,
            name=portfolio.name,
            currency=portfolio.currency,
            cash=portfolio.cash,
            positions=portfolio.positions,
            created_at=portfolio.created_at or now,
            updated_at=now
        )
        
        # Копируем события из исходного портфеля
        updated_portfolio._domain_events = portfolio._domain_events.copy()
        
        # Используем Unit of Work для транзакционности
        uow = PortfolioUnitOfWork(self._portfolio_repo)
        
        async with uow:
            # Сохраняем в кеш UoW
            await uow.save_portfolio(updated_portfolio)
            
            # Явно вызываем commit (или будет автоматически при выходе из with)
            await uow.commit()
        
        logger.info(f"Portfolio saved successfully: total value = {updated_portfolio.total_value()}")
        
        return updated_portfolio
