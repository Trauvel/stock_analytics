"""
Генерация сигналов предсказания на основе анализа новостей.
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import logging
import json
from pathlib import Path

from .collector import NewsCollector
from .analyzer import NewsAnalyzer
from .llm_analyzer import LLMNewsAnalyzer
from .config import PredictorConfig

logger = logging.getLogger(__name__)


class EventSignalGenerator:
    """Генератор сигналов о возможных событиях."""
    
    def __init__(self, config: PredictorConfig):
        self.config = config
        self.collector = NewsCollector(
            sources=config.news_sources,
            cache_ttl=config.cache_ttl
        )
        self.analyzer = NewsAnalyzer(
            positive_keywords=config.positive_keywords,
            negative_keywords=config.negative_keywords
        )
        
        # LLM анализатор (если включен)
        self.llm_analyzer = None
        if config.llm_enabled:
            self.llm_analyzer = LLMNewsAnalyzer(
                use_llm_for=config.llm_use_for,
                confidence_threshold=config.llm_confidence_threshold,
                timeout=config.llm_timeout
            )
        
        self.history_file = Path(config.events_log_path)
        
    def _calculate_signal_level(self, stats: Dict) -> str:
        """
        Определение уровня сигнала на основе статистики.
        
        Args:
            stats: Статистика с категориями новостей
            
        Returns:
            Уровень сигнала: HIGH_PROBABILITY, MEDIUM_PROBABILITY или LOW
        """
        high_count = stats.get('HIGH_PROBABILITY', 0)
        medium_count = stats.get('MEDIUM_PROBABILITY', 0)
        negative_count = stats.get('NEGATIVE', 0)
        relevant_count = stats.get('relevant', 0)
        avg_score = stats.get('avg_score', 0.0)
        
        # Логика принятия решения
        if negative_count >= 3:
            return "NEGATIVE_SIGNAL"
        
        if high_count >= 2 and avg_score > 0.4:
            return "HIGH_PROBABILITY"
        
        if (high_count >= 1 and medium_count >= 2) or (medium_count >= 4 and avg_score > 0.3):
            return "MEDIUM_PROBABILITY"
        
        if relevant_count >= 5 and avg_score > 0.2:
            return "MEDIUM_PROBABILITY"
        
        return "LOW"
    
    def _save_to_history(self, signal_data: Dict):
        """Сохранение результата в историю."""
        try:
            # Создаём директорию если не существует
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Загружаем существующую историю
            history = []
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            
            # Добавляем новую запись
            history.append(signal_data)
            
            # Ограничиваем размер истории (последние 100 записей)
            history = history[-100:]
            
            # Сохраняем
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Сигнал сохранён в {self.history_file}")
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении истории: {e}")
    
    async def generate_signal(
        self, 
        target_companies: Optional[List[str]] = None,
        save_history: bool = True
    ) -> Dict:
        """
        Генерация сигнала предсказания событий.
        
        Args:
            target_companies: Список компаний для анализа (тикеры или названия)
            save_history: Сохранять ли результат в историю
            
        Returns:
            Словарь с уровнем сигнала и деталями
        """
        logger.info("Начинаем генерацию сигнала предсказания...")
        
        # Инициализируем LLM если включен
        if self.llm_analyzer:
            await self.llm_analyzer.initialize(warmup=self.config.llm_warmup)
            logger.info(f"LLM доступен: {self.llm_analyzer.is_available}")
        
        # Собираем данные
        vacancy_queries = None
        if target_companies and self.config.use_vacancies:
            vacancy_queries = target_companies
        
        items = await self.collector.collect_all(vacancy_queries)
        
        if not items:
            logger.warning("Не удалось собрать данные")
            return {
                'signal_level': 'LOW',
                'reason': 'Нет данных для анализа',
                'timestamp': datetime.now().isoformat(),
                'stats': {},
                'llm_used': False
            }
        
        # Анализируем данные (keyword analysis)
        keyword_analyzed = self.analyzer.analyze_batch(items, target_companies)
        
        # Дополнительный анализ через LLM (если включен)
        if self.llm_analyzer and self.llm_analyzer.is_available:
            logger.info("Запускаем LLM анализ...")
            analyzed = await self.llm_analyzer.analyze_batch(
                items, 
                keyword_analyzed,
                target_companies
            )
        else:
            analyzed = keyword_analyzed
        
        stats = self.analyzer.get_summary_stats(analyzed)
        
        # Определяем уровень сигнала
        signal_level = self._calculate_signal_level(stats)
        
        # Формируем обоснование
        reason = self._generate_reason(signal_level, stats, analyzed[:5])
        
        # Формируем результат
        result = {
            'signal_level': signal_level,
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
            'stats': stats,
            'top_items': analyzed[:5] if analyzed else [],
            'companies': target_companies or []
        }
        
        # Сохраняем в историю
        if save_history:
            self._save_to_history(result)
        
        logger.info(f"Сигнал сгенерирован: {signal_level}")
        return result
    
    def _generate_reason(self, signal_level: str, stats: Dict, top_items: List[Dict]) -> str:
        """Формирование текстового обоснования сигнала."""
        if signal_level == "HIGH_PROBABILITY":
            keywords = []
            for item in top_items:
                keywords.extend(item.get('matched_keywords', []))
            unique_keywords = list(set(keywords))[:5]
            
            return (
                f"Обнаружено {stats['HIGH_PROBABILITY']} сильно позитивных сигналов. "
                f"Средний балл: {stats['avg_score']:.2f}. "
                f"Ключевые слова: {', '.join(unique_keywords)}"
            )
        
        elif signal_level == "MEDIUM_PROBABILITY":
            return (
                f"Обнаружено умеренно позитивных сигналов: {stats['MEDIUM_PROBABILITY']}. "
                f"Релевантных новостей: {stats['relevant']}. "
                f"Средний балл: {stats['avg_score']:.2f}"
            )
        
        elif signal_level == "NEGATIVE_SIGNAL":
            return (
                f"Обнаружено {stats['NEGATIVE']} негативных сигналов. "
                f"Возможны риски."
            )
        
        else:
            return "Недостаточно данных для формирования значимого сигнала"


async def generate_event_signals(
    target_companies: Optional[List[str]] = None,
    config_path: Optional[str] = None
) -> Dict:
    """
    Основная функция для генерации сигналов.
    Может быть вызвана из других модулей.
    
    Args:
        target_companies: Список компаний для анализа
        config_path: Путь к файлу конфигурации (опционально)
        
    Returns:
        Словарь с результатами предсказания
    """
    # Загружаем конфигурацию
    config = PredictorConfig.load(config_path)
    
    # Создаём генератор и запускаем
    generator = EventSignalGenerator(config)
    result = await generator.generate_signal(target_companies)
    
    return result

