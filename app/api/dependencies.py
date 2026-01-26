"""Dependencies для FastAPI routes."""

from fastapi import Depends
from app.application.dependencies import container
from app.application.stock_analysis.generate_report_use_case import GenerateReportUseCase
from app.application.recommendation.generate_recommendations_use_case import GenerateRecommendationsUseCase
from app.application.portfolio.get_portfolio_use_case import GetPortfolioUseCase
from app.application.portfolio.save_portfolio_use_case import SavePortfolioUseCase
from app.application.portfolio.add_position_use_case import AddPositionUseCase
from app.application.portfolio.remove_position_use_case import RemovePositionUseCase
from app.application.portfolio.import_sber_html_use_case import ImportSberHTMLUseCase
from app.application.portfolio.list_portfolios_use_case import ListPortfoliosUseCase
from app.application.portfolio.create_portfolio_use_case import CreatePortfolioUseCase
from app.application.portfolio.delete_portfolio_use_case import DeletePortfolioUseCase


def get_generate_report_use_case() -> GenerateReportUseCase:
    """Получить use case для генерации отчёта."""
    return container.generate_report_use_case()


def get_generate_recommendations_use_case() -> GenerateRecommendationsUseCase:
    """Получить use case для генерации рекомендаций."""
    return container.generate_recommendations_use_case()


def get_portfolio_use_case() -> GetPortfolioUseCase:
    """Получить use case для получения портфеля."""
    return container.get_portfolio_use_case()


def get_save_portfolio_use_case() -> SavePortfolioUseCase:
    """Получить use case для сохранения портфеля."""
    return container.save_portfolio_use_case()


def get_add_position_use_case() -> AddPositionUseCase:
    """Получить use case для добавления позиции."""
    return container.add_position_use_case()


def get_remove_position_use_case() -> RemovePositionUseCase:
    """Получить use case для удаления позиции."""
    return container.remove_position_use_case()


def get_import_sber_html_use_case() -> ImportSberHTMLUseCase:
    """Получить use case для импорта из HTML Сбера."""
    return container.import_sber_html_use_case()


def get_list_portfolios_use_case() -> ListPortfoliosUseCase:
    """Получить use case для получения списка портфелей."""
    return container.list_portfolios_use_case()


def get_create_portfolio_use_case() -> CreatePortfolioUseCase:
    """Получить use case для создания портфеля."""
    return container.create_portfolio_use_case()


def get_delete_portfolio_use_case() -> DeletePortfolioUseCase:
    """Получить use case для удаления портфеля."""
    return container.delete_portfolio_use_case()
