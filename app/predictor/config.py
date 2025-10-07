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
    
    # === LLM настройки ===
    llm_enabled: bool = False
    llm_provider: str = "ollama"  # ollama, openai, localai
    llm_model: str = "mistral"
    llm_base_url: str = "http://localhost:11434"
    llm_use_for: str = "relevant_only"  # all, relevant_only, uncertain
    llm_timeout: int = 30
    llm_confidence_threshold: float = 0.3
    llm_warmup: bool = True
    
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
            
            # Обрабатываем вложенный llm блок
            llm_config = data.get('llm', {})
            
            # Создаём экземпляр с данными из файла
            config = cls()
            
            # Обновляем базовые настройки
            config.news_sources = data.get('news_sources', config.news_sources)
            config.use_vacancies = data.get('use_vacancies', config.use_vacancies)
            config.positive_keywords = data.get('positive_keywords', config.positive_keywords)
            config.negative_keywords = data.get('negative_keywords', config.negative_keywords)
            config.cache_ttl = data.get('cache_ttl', config.cache_ttl)
            config.events_log_path = data.get('events_log_path', config.events_log_path)
            config.log_level = data.get('log_level', config.log_level)
            config.log_file = data.get('log_file', config.log_file)
            config.requests_per_minute = data.get('requests_per_minute', config.requests_per_minute)
            
            # Обновляем LLM настройки
            config.llm_enabled = llm_config.get('enabled', config.llm_enabled)
            config.llm_provider = llm_config.get('provider', config.llm_provider)
            config.llm_model = llm_config.get('model', config.llm_model)
            config.llm_base_url = llm_config.get('base_url', config.llm_base_url)
            config.llm_use_for = llm_config.get('use_for', config.llm_use_for)
            config.llm_timeout = llm_config.get('timeout', config.llm_timeout)
            config.llm_confidence_threshold = llm_config.get('confidence_threshold', config.llm_confidence_threshold)
            config.llm_warmup = llm_config.get('warmup', config.llm_warmup)
            
            return config
            
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

