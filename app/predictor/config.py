"""
Конфигурация модуля предсказаний.
"""
from dataclasses import dataclass, field
from typing import List, Optional
import yaml
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class PredictorConfig:
    """Конфигурация модуля предсказаний новостных всплесков."""
    
    # Источники новостей (RSS)
    news_sources: List[str] = field(default_factory=lambda: [
        "https://www.interfax.ru/rss.asp",
        "https://www.rbc.ru/rss/",
    ])
    
    # Использовать ли API вакансий
    use_vacancies: bool = True
    
    # Ключевые слова для анализа
    positive_keywords: List[str] = field(default_factory=lambda: [
        "запуск", "запущен", "фьючерс", "опцион",
        "новая секция", "развитие продукта", "тестирование",
        "лицензия", "расширение торгов", "API",
        "инновация", "партнёрство", "открытие",
        "прибыль", "рост", "успешно", "одобрен"
    ])
    
    negative_keywords: List[str] = field(default_factory=lambda: [
        "расследование", "приостановка", "санкции",
        "убытки", "падение", "кризис", "банкротство",
        "штраф", "скандал", "закрыт", "отменён"
    ])
    
    # Настройки кэша
    cache_ttl: int = 3600  # секунды
    
    # Путь к файлу истории событий
    events_log_path: str = "data/events_history.json"
    
    # Настройки логирования
    log_level: str = "INFO"
    log_file: str = "data/logs/predictor.log"
    
    # Rate limiting для API
    requests_per_minute: int = 10
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> 'PredictorConfig':
        """
        Загрузка конфигурации из YAML файла.
        
        Args:
            config_path: Путь к файлу конфигурации
            
        Returns:
            Экземпляр PredictorConfig
        """
        if config_path is None:
            config_path = "config/predictor.yaml"
        
        config_file = Path(config_path)
        
        # Если файл не существует, создаём с дефолтными значениями
        if not config_file.exists():
            logger.warning(
                f"Файл конфигурации {config_path} не найден. "
                "Используем дефолтные настройки."
            )
            return cls()
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                logger.warning("Пустой файл конфигурации. Используем дефолтные настройки.")
                return cls()
            
            # Создаём экземпляр с данными из файла
            return cls(
                news_sources=data.get('news_sources', cls.news_sources),
                use_vacancies=data.get('use_vacancies', cls.use_vacancies),
                positive_keywords=data.get('positive_keywords', cls.positive_keywords),
                negative_keywords=data.get('negative_keywords', cls.negative_keywords),
                cache_ttl=data.get('cache_ttl', cls.cache_ttl),
                events_log_path=data.get('events_log_path', cls.events_log_path),
                log_level=data.get('log_level', cls.log_level),
                log_file=data.get('log_file', cls.log_file),
                requests_per_minute=data.get('requests_per_minute', cls.requests_per_minute),
            )
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке конфигурации: {e}")
            logger.warning("Используем дефолтные настройки.")
            return cls()
    
    def save(self, config_path: Optional[str] = None):
        """
        Сохранение конфигурации в YAML файл.
        
        Args:
            config_path: Путь к файлу конфигурации
        """
        if config_path is None:
            config_path = "config/predictor.yaml"
        
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'news_sources': self.news_sources,
            'use_vacancies': self.use_vacancies,
            'positive_keywords': self.positive_keywords,
            'negative_keywords': self.negative_keywords,
            'cache_ttl': self.cache_ttl,
            'events_log_path': self.events_log_path,
            'log_level': self.log_level,
            'log_file': self.log_file,
            'requests_per_minute': self.requests_per_minute,
        }
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
            
            logger.info(f"Конфигурация сохранена в {config_path}")
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении конфигурации: {e}")

