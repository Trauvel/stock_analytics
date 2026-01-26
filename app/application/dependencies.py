"""Dependency Injection контейнер для приложения."""

from dependency_injector import containers, providers

from app.domain.stock_analysis.services.metrics_calculator import MetricsCalculator
from app.domain.stock_analysis.repositories.stock_repository import StockRepository
from app.infrastructure.persistence.repositories.stock_repository_impl import StockRepositoryImpl
from app.ingest.moex_client import MOEXClient
from app.config.loader import get_config
from app.application.stock_analysis.generate_report_use_case import GenerateReportUseCase
from app.domain.recommendation.services.recommendation_engine import (
    RecommendationEngine,
    RecommendationConfig
)
from app.application.recommendation.generate_recommendations_use_case import GenerateRecommendationsUseCase
from app.domain.portfolio.repositories.portfolio_repository import PortfolioRepository
from app.infrastructure.persistence.repositories.portfolio_repository_impl import PortfolioRepositoryImpl
from app.application.portfolio.get_portfolio_use_case import GetPortfolioUseCase
from app.application.portfolio.save_portfolio_use_case import SavePortfolioUseCase
from app.application.portfolio.add_position_use_case import AddPositionUseCase
from app.application.portfolio.remove_position_use_case import RemovePositionUseCase
from app.application.portfolio.import_sber_html_use_case import ImportSberHTMLUseCase
from app.application.portfolio.list_portfolios_use_case import ListPortfoliosUseCase
from app.application.portfolio.create_portfolio_use_case import CreatePortfolioUseCase
from app.application.portfolio.delete_portfolio_use_case import DeletePortfolioUseCase


class ApplicationContainer(containers.DeclarativeContainer):
    """Контейнер зависимостей приложения."""
    
    # Конфигурация
    config = providers.Configuration()
    
    # Infrastructure
    moex_client = providers.Singleton(
        MOEXClient
    )
    
    # Repositories
    stock_repository = providers.Factory(
        StockRepositoryImpl,
        moex_client=moex_client
    )
    
    # Domain Services
    metrics_calculator = providers.Factory(
        MetricsCalculator,
        dividend_target_pct=providers.Callable(
            lambda: get_config().dividend_target_pct
        )
    )
    
    # Domain Services - Recommendation
    def _load_reco_config() -> RecommendationConfig:
        """Загрузить конфигурацию рекомендаций."""
        try:
            from app.reco.config import get_reco_config
            old_config = get_reco_config()
            return RecommendationConfig(
                dy_buy_min=old_config.dy_buy_min,
                dy_very_high=old_config.dy_very_high,
                max_discount_vs_sma200=old_config.max_discount_vs_sma200,
                min_premium_vs_sma200=old_config.min_premium_vs_sma200,
                trend_up_min=old_config.trend_up_min,
                trend_down_max=old_config.trend_down_max,
                buy_score_cutoff=old_config.buy_score_cutoff,
                sell_score_cutoff=old_config.sell_score_cutoff,
                near_52w_low_threshold=old_config.near_52w_low_threshold,
                near_52w_high_threshold=old_config.near_52w_high_threshold,
                event_predictor_enabled=old_config.event_predictor_enabled,
                event_predictor_weights=old_config.event_predictor_weights
            )
        except Exception:
            # Fallback на дефолтную конфигурацию
            return RecommendationConfig()
    
    recommendation_config = providers.Factory(
        _load_reco_config
    )
    
    recommendation_engine = providers.Factory(
        RecommendationEngine,
        config=recommendation_config
    )
    
    # Use Cases
    generate_report_use_case = providers.Factory(
        GenerateReportUseCase,
        stock_repository=stock_repository,
        metrics_calculator=metrics_calculator,
        moex_client=moex_client,
        dividend_target_pct=providers.Callable(
            lambda: get_config().dividend_target_pct
        )
    )
    
    generate_recommendations_use_case = providers.Factory(
        GenerateRecommendationsUseCase,
        stock_repository=stock_repository,
        recommendation_engine=recommendation_engine
    )
    
    # Repositories - Portfolio
    portfolio_repository = providers.Factory(
        PortfolioRepositoryImpl
    )
    
    # Use Cases - Portfolio
    get_portfolio_use_case = providers.Factory(
        GetPortfolioUseCase,
        portfolio_repository=portfolio_repository
    )
    
    save_portfolio_use_case = providers.Factory(
        SavePortfolioUseCase,
        portfolio_repository=portfolio_repository
    )
    
    add_position_use_case = providers.Factory(
        AddPositionUseCase,
        portfolio_repository=portfolio_repository
    )
    
    remove_position_use_case = providers.Factory(
        RemovePositionUseCase,
        portfolio_repository=portfolio_repository
    )
    
    import_sber_html_use_case = providers.Factory(
        ImportSberHTMLUseCase,
        portfolio_repository=portfolio_repository
    )
    
    list_portfolios_use_case = providers.Factory(
        ListPortfoliosUseCase,
        portfolio_repository=portfolio_repository
    )
    
    create_portfolio_use_case = providers.Factory(
        CreatePortfolioUseCase,
        portfolio_repository=portfolio_repository
    )
    
    delete_portfolio_use_case = providers.Factory(
        DeletePortfolioUseCase,
        portfolio_repository=portfolio_repository
    )


# Глобальный контейнер (можно сделать синглтоном)
container = ApplicationContainer()

# Регистрируем обработчики событий при инициализации
try:
    from app.infrastructure.events.event_handlers import register_event_handlers
    register_event_handlers()
except Exception as e:
    # Если не удалось зарегистрировать обработчики, это не критично
    from loguru import logger
    logger.warning(f"Could not register event handlers: {e}")
