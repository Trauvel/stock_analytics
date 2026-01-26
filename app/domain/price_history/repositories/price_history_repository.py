"""Интерфейс репозитория для работы с историей цен."""

from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime, timedelta

from ..entities.price_snapshot import PriceSnapshot


class PriceHistoryRepository(ABC):
    """Абстрактный репозиторий для работы с историей цен."""
    
    @abstractmethod
    def save(self, snapshot: PriceSnapshot) -> None:
        """
        Сохранить снимок цены.
        
        Args:
            snapshot: Снимок для сохранения
        """
        pass
    
    @abstractmethod
    def get_latest(self, symbol: str) -> Optional[PriceSnapshot]:
        """
        Получить последний снимок для инструмента.
        
        Args:
            symbol: Тикер инструмента
            
        Returns:
            Последний снимок или None если не найден
        """
        pass
    
    @abstractmethod
    def get_at_time(
        self, 
        symbol: str, 
        timestamp: datetime
    ) -> Optional[PriceSnapshot]:
        """
        Получить снимок для инструмента на определённое время.
        
        Args:
            symbol: Тикер инструмента
            timestamp: Время снимка
            
        Returns:
            Снимок или None если не найден
        """
        pass
    
    @abstractmethod
    def get_in_range(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[PriceSnapshot]:
        """
        Получить все снимки для инструмента в диапазоне времени.
        
        Args:
            symbol: Тикер инструмента
            start_time: Начало диапазона
            end_time: Конец диапазона
            
        Returns:
            Список снимков, отсортированных по времени
        """
        pass
    
    @abstractmethod
    def get_before_time(
        self,
        symbol: str,
        timestamp: datetime,
        hours_ago: float
    ) -> Optional[PriceSnapshot]:
        """
        Получить снимок, который был создан примерно N часов назад.
        
        Args:
            symbol: Тикер инструмента
            timestamp: Текущее время (для расчёта)
            hours_ago: Сколько часов назад
            
        Returns:
            Ближайший снимок или None
        """
        pass
    
    @abstractmethod
    def cleanup_old(self, days_to_keep: int = 30) -> int:
        """
        Удалить старые снимки, оставив только последние N дней.
        
        Args:
            days_to_keep: Сколько дней хранить
            
        Returns:
            Количество удалённых записей
        """
        pass
