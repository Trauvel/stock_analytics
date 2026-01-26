"""Базовые классы для Domain Events."""

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4


@dataclass
class DomainEvent(ABC):
    """Базовый класс для всех доменных событий."""
    
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=datetime.now)
    aggregate_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать событие в словарь для сериализации."""
        return {
            "event_id": self.event_id,
            "event_type": self.__class__.__name__,
            "occurred_at": self.occurred_at.isoformat(),
            "aggregate_id": self.aggregate_id,
            **self._get_event_data()
        }
    
    def _get_event_data(self) -> Dict[str, Any]:
        """
        Получить данные события для сериализации.
        
        Переопределяется в подклассах.
        """
        return {}


class DomainEventPublisher:
    """Публикатор доменных событий."""
    
    def __init__(self):
        """Инициализация публикатора."""
        self._handlers: Dict[type, list] = {}
    
    def subscribe(self, event_type: type, handler):
        """
        Подписаться на события определённого типа.
        
        Args:
            event_type: Тип события
            handler: Обработчик события (callable)
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def publish(self, event: DomainEvent) -> None:
        """
        Опубликовать событие.
        
        Args:
            event: Событие для публикации
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                # Логируем ошибку, но не прерываем выполнение
                from loguru import logger
                logger.error(f"Error handling event {event_type.__name__}: {e}")


# Глобальный экземпляр публикатора
_event_publisher = DomainEventPublisher()


def get_event_publisher() -> DomainEventPublisher:
    """Получить глобальный экземпляр публикатора событий."""
    return _event_publisher
