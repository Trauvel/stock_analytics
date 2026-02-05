"""Use case для генерации рекомендаций."""

from typing import List, Optional
from loguru import logger

from app.domain.stock_analysis.repositories.stock_repository import StockRepository
from app.domain.recommendation.services.recommendation_engine import (
    RecommendationEngine,
    RecommendationConfig
)
from app.domain.recommendation.entities.recommendation import Recommendation


class GenerateRecommendationsUseCase:
    """Use case для генерации рекомендаций по акциям."""
    
    def __init__(
        self,
        stock_repository: StockRepository,
        recommendation_engine: RecommendationEngine
    ):
        """
        Инициализация use case.
        
        Args:
            stock_repository: Репозиторий для получения акций
            recommendation_engine: Движок для генерации рекомендаций
        """
        self._stock_repo = stock_repository
        self._recommendation_engine = recommendation_engine
    
    async def execute(
        self,
        symbols: Optional[List[str]] = None,
        only: Optional[List[str]] = None,
        min_score: Optional[float] = None
    ) -> List[Recommendation]:
        """
        Выполнить use case - сгенерировать рекомендации.
        
        Args:
            symbols: Список тикеров (если None, берутся из репозитория)
            only: Фильтр по действиям (BUY, HOLD, SELL)
            min_score: Минимальный score для включения
            
        Returns:
            List[Recommendation]: Список рекомендаций
        """
        logger.info(f"Generating recommendations for {len(symbols) if symbols else 'all'} symbols")
        
        # Получаем акции через репозиторий
        if symbols:
            stocks = await self._stock_repo.get_all(symbols)
        else:
            # Если symbols не указаны, нужно получить из конфига
            # Пока возвращаем пустой список
            logger.warning("No symbols provided, returning empty list")
            return []
        
        recommendations = []
        
        for stock in stocks:
            try:
                # Получаем сигнал от модуля предсказаний (опционально)
                event_signal = await self._get_event_signal(stock.symbol)
                
                # Генерируем рекомендацию
                recommendation = self._recommendation_engine.generate(
                    stock=stock,
                    event_signal=event_signal
                )
                
                # Применяем фильтры
                if only and recommendation.action.to_string() not in only:
                    continue
                
                if min_score is not None and abs(recommendation.score) < abs(min_score):
                    continue
                
                recommendations.append(recommendation)
                
            except Exception as e:
                logger.error(f"Error generating recommendation for {stock.symbol}: {e}")
                continue
        
        # Сортировка: BUY → ACCUMULATE → HOLD_STRONG → HOLD_NEUTRAL → REDUCE → SELL
        def _action_order(r):
            if r.action.is_buy(): return 0
            if r.action.is_accumulate(): return 1
            if r.action.is_hold_strong(): return 2
            if r.action.is_hold_neutral(): return 3
            if r.action.is_reduce(): return 4
            return 5  # SELL
        recommendations.sort(key=lambda r: (
            _action_order(r),
            -r.score if r.action.is_buy() or r.action.is_accumulate() or r.action.is_hold() or r.action.is_reduce() else r.score
        ))
        
        logger.info(f"Generated {len(recommendations)} recommendations")
        return recommendations
    
    async def _get_event_signal(self, symbol: str) -> Optional[dict]:
        """Получить сигнал от модуля предсказаний."""
        try:
            from app.predictor import generate_event_signals
            signal = await generate_event_signals(target_companies=[symbol])
            return signal
        except Exception as e:
            logger.debug(f"Could not get event signal for {symbol}: {e}")
            return None
