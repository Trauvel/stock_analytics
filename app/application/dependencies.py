"""Dependency Injection контейнер для приложения."""

from dependency_injector import containers, providers

from app.domain.stock_analysis.services.metrics_calculator import MetricsCalculator
from app.domain.stock_analysis.repositories.stock_repository import StockRepository
from app.infrastructure.persistence.repositories.stock_repository_impl import StockRepositoryImpl
from app.ingest.moex_client import MOEXClient
from app.config.loader import get_config
from app.application.stock_analysis.generate_report_use_case import GenerateReportUseCase
from app.application.stock_analysis.get_universe_use_case import GetUniverseUseCase
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
from app.domain.price_history.repositories.price_history_repository import PriceHistoryRepository
from app.infrastructure.persistence.repositories.price_history_repository_impl import PriceHistoryRepositoryImpl
from app.application.price_history.save_snapshot_use_case import SaveSnapshotUseCase


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
    
    # Use Cases - Stock Analysis
    get_universe_use_case = providers.Factory(
        GetUniverseUseCase
    )
    
    # Domain Services - Recommendation
    def _load_reco_config() -> RecommendationConfig:
        """Загрузить конфигурацию рекомендаций."""
        try:
            from app.reco.config import get_reco_config
            from app.config.loader import get_config
            old_config = get_reco_config()
            app_cfg = get_config()
            return RecommendationConfig(
                # Минимальная DY для BUY синхронизируется с глобальной целевой DY
                dy_buy_min=getattr(app_cfg, "dividend_target_pct", old_config.dy_buy_min),
                dy_very_high=old_config.dy_very_high,
                dy_score_cap=getattr(old_config, 'dy_score_cap', 12.0),
                max_discount_vs_sma200=old_config.max_discount_vs_sma200,
                min_premium_vs_sma200=old_config.min_premium_vs_sma200,
                buy_score_if_below_sma200=getattr(old_config, 'buy_score_if_below_sma200', 3.2),
                trend_up_min=old_config.trend_up_min,
                trend_down_max=old_config.trend_down_max,
                buy_score_cutoff=old_config.buy_score_cutoff,
                accumulate_score_min=getattr(old_config, 'accumulate_score_min', 0.5),
                avoid_score_max=getattr(old_config, 'avoid_score_max', -1.0),
                sell_score_cutoff=old_config.sell_score_cutoff,
                max_buy_count=getattr(old_config, 'max_buy_count', 4),
                commodity_tickers=getattr(old_config, 'commodity_tickers', None) or ['TGLD'],
                fund_tickers=getattr(old_config, 'fund_tickers', None) or [],
                market_regime=getattr(old_config, 'market_regime', 'sideways') or 'sideways',
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
    
    # Repositories - Price History
    price_history_repository = providers.Singleton(
        PriceHistoryRepositoryImpl
    )
    
    # Use Cases - Price History
    save_snapshot_use_case = providers.Factory(
        SaveSnapshotUseCase,
        price_history_repository=price_history_repository
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
