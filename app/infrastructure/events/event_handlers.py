"""Обработчики доменных событий."""

from loguru import logger
from app.domain.shared.domain_event import DomainEvent
from app.domain.stock_analysis.events.stock_events import StockAnalyzed, StockPriceChanged
from app.domain.portfolio.events.portfolio_events import (
    PortfolioCreated,
    PositionAdded,
    PositionRemoved,
    PortfolioValueChanged
)


def handle_stock_analyzed(event: StockAnalyzed) -> None:
    """Обработчик события анализа акции."""
    logger.info(
        f"📊 Stock analyzed: {event.symbol} "
        f"price={event.price:.2f} "
        f"signals={event.signals_count}"
    )


def handle_stock_price_changed(event: StockPriceChanged) -> None:
    """Обработчик события изменения цены."""
    change_sign = "+" if event.change_pct >= 0 else ""
    logger.info(
        f"💰 Price changed: {event.symbol} "
        f"{event.old_price:.2f} → {event.new_price:.2f} "
        f"({change_sign}{event.change_pct:.2f}%)"
    )


def handle_portfolio_created(event: PortfolioCreated) -> None:
    """Обработчик события создания портфеля."""
    logger.info(
        f"💼 Portfolio created: {event.portfolio_name} "
        f"currency={event.currency} "
        f"cash={event.initial_cash:.2f}"
    )


def handle_position_added(event: PositionAdded) -> None:
    """Обработчик события добавления позиции."""
    logger.info(
        f"➕ Position added: {event.symbol} "
        f"qty={event.quantity} "
        f"avg_price={event.avg_price:.2f} "
        f"total={event.total_cost:.2f}"
    )


def handle_position_removed(event: PositionRemoved) -> None:
    """Обработчик события удаления позиции."""
    logger.info(f"➖ Position removed: {event.symbol}")


def handle_portfolio_value_changed(event: PortfolioValueChanged) -> None:
    """Обработчик события изменения стоимости портфеля."""
    change_sign = "+" if event.change_pct >= 0 else ""
    logger.info(
        f"📈 Portfolio value changed: "
        f"{event.old_value:.2f} → {event.new_value:.2f} {event.currency} "
        f"({change_sign}{event.change_pct:.2f}%)"
    )


def register_event_handlers() -> None:
    """Зарегистрировать все обработчики событий."""
    from app.domain.shared.domain_event import get_event_publisher
    
    publisher = get_event_publisher()
    
    # Stock Analysis events
    publisher.subscribe(StockAnalyzed, handle_stock_analyzed)
    publisher.subscribe(StockPriceChanged, handle_stock_price_changed)
    
    # Portfolio events
    publisher.subscribe(PortfolioCreated, handle_portfolio_created)
    publisher.subscribe(PositionAdded, handle_position_added)
    publisher.subscribe(PositionRemoved, handle_position_removed)
    publisher.subscribe(PortfolioValueChanged, handle_portfolio_value_changed)
    
    logger.info("Event handlers registered")
