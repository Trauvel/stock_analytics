"""Вспомогательные методы для Portfolio (Domain Events)."""

from app.domain.portfolio.entities.portfolio import Portfolio
from app.domain.shared.domain_event import DomainEvent, get_event_publisher


def add_domain_event(portfolio: Portfolio, event: DomainEvent) -> None:
    """Добавить доменное событие в портфель."""
    portfolio._domain_events.append(event)


def get_domain_events(portfolio: Portfolio) -> list:
    """Получить все доменные события портфеля."""
    return portfolio._domain_events.copy()


def clear_domain_events(portfolio: Portfolio) -> None:
    """Очистить список доменных событий."""
    portfolio._domain_events.clear()


def publish_events(portfolio: Portfolio) -> None:
    """Опубликовать все накопленные события портфеля."""
    publisher = get_event_publisher()
    events = get_domain_events(portfolio)
    
    for event in events:
        publisher.publish(event)
    
    clear_domain_events(portfolio)
