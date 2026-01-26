"""Базовый класс для доменных сущностей с поддержкой Domain Events."""

from abc import ABC
from typing import List

from .domain_event import DomainEvent, get_event_publisher


class Entity(ABC):
    """Базовый класс для доменных сущностей."""
    
    def __init__(self):
        """Инициализация сущности."""
        self._domain_events: List[DomainEvent] = []
    
    def add_domain_event(self, event: DomainEvent) -> None:
        """
        Добавить доменное событие.
        
        Args:
            event: Событие для добавления
        """
        self._domain_events.append(event)
    
    def get_domain_events(self) -> List[DomainEvent]:
        """
        Получить все доменные события.
        
        Returns:
            List[DomainEvent]: Список событий
        """
        return self._domain_events.copy()
    
    def clear_domain_events(self) -> None:
        """Очистить список доменных событий."""
        self._domain_events.clear()
    
    def publish_events(self) -> None:
        """Опубликовать все накопленные события."""
        publisher = get_event_publisher()
        events = self.get_domain_events()
        
        for event in events:
            publisher.publish(event)
        
        self.clear_domain_events()
