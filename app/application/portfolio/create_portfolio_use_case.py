"""Use case для создания нового портфеля."""

from datetime import datetime
from loguru import logger

from app.domain.portfolio.entities.portfolio import Portfolio
from app.domain.portfolio.repositories.portfolio_repository import PortfolioRepository
from app.domain.portfolio.value_objects.currency import Currency
from app.domain.portfolio.value_objects.money import Money


class CreatePortfolioUseCase:
    """Use case для создания нового портфеля."""
    
    def __init__(self, portfolio_repository: PortfolioRepository):
        """
        Инициализация use case.
        
        Args:
            portfolio_repository: Репозиторий для работы с портфелями
        """
        self._portfolio_repo = portfolio_repository
    
    async def execute(
        self,
        name: str,
        currency: str = "RUB",
        cash: float = 0.0
    ) -> Portfolio:
        """
        Выполнить use case - создать новый портфель.
        
        Args:
            name: Название портфеля
            currency: Валюта портфеля (по умолчанию RUB)
            cash: Начальный кеш (по умолчанию 0.0)
            
        Returns:
            Созданный портфель
        """
        logger.info(f"Creating new portfolio: {name}")
        
        now = datetime.now()
        
        portfolio = Portfolio(
            id=None,  # ID будет сгенерирован в репозитории
            name=name,
            currency=Currency.from_string(currency),
            cash=Money.from_float(cash, currency),
            positions=[],
            created_at=now,
            updated_at=now
        )
        
        # Сохраняем портфель (репозиторий сгенерирует ID)
        saved_portfolio = await self._portfolio_repo.save(portfolio)
        
        logger.info(f"Created portfolio {saved_portfolio.id}: {name}")
        
        return saved_portfolio
