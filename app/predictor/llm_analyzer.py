"""
LLM-based анализатор для глубокого понимания тональности новостей.
"""
import asyncio
from typing import List, Dict, Optional
import logging

from .llm_provider import LLMProvider, LLMResponse
from .ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)


class LLMNewsAnalyzer:
    """Анализатор новостей с использованием LLM."""
    
    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        use_llm_for: str = "relevant_only",  # all, relevant_only, uncertain
        confidence_threshold: float = 0.3,
        timeout: int = 10
    ):
        """
        Args:
            provider: LLM провайдер (по умолчанию Ollama)
            use_llm_for: Когда использовать LLM
                - "all": для всех новостей
                - "relevant_only": только для релевантных
                - "uncertain": только для неоднозначных
            confidence_threshold: Порог уверенности для keyword анализа
            timeout: Таймаут для каждого запроса к LLM
        """
        self.provider = provider or OllamaProvider()
        self.use_llm_for = use_llm_for
        self.confidence_threshold = confidence_threshold
        self.timeout = timeout
        self.is_available = False
        
    async def initialize(self, warmup: bool = True) -> bool:
        """
        Инициализация и проверка доступности LLM.
        
        Args:
            warmup: Прогреть модель (первый запрос медленный)
        """
        self.is_available = await self.provider.check_availability()
        
        if self.is_available and warmup:
            logger.info("Прогрев LLM модели (первый запрос)...")
            try:
                # Простой тестовый запрос для загрузки модели в память
                await self.provider.analyze_sentiment(
                    text="Тестовая новость для прогрева модели",
                    timeout=self.timeout
                )
                logger.info("LLM модель прогрета и готова к работе")
            except Exception as e:
                logger.warning(f"Не удалось прогреть модель: {e}")
        
        return self.is_available
    
    def should_use_llm(
        self, 
        item: Dict,
        keyword_score: float,
        is_relevant: bool
    ) -> bool:
        """
        Определяет нужно ли использовать LLM для этой новости.
        
        Args:
            item: Новость
            keyword_score: Балл от keyword анализа
            is_relevant: Релевантна ли новость
            
        Returns:
            True если нужно использовать LLM
        """
        if not self.is_available:
            return False
        
        if self.use_llm_for == "all":
            return True
        
        if self.use_llm_for == "relevant_only":
            return is_relevant
        
        if self.use_llm_for == "uncertain":
            # Используем LLM для неоднозначных случаев
            return abs(keyword_score) < self.confidence_threshold
        
        return False
    
    async def analyze_item(
        self,
        item: Dict,
        keyword_analysis: Dict,
        company: Optional[str] = None
    ) -> Dict:
        """
        Анализ новости с помощью LLM.
        
        Args:
            item: Исходная новость
            keyword_analysis: Результат keyword анализа
            company: Название компании
            
        Returns:
            Обогащённый результат с LLM анализом
        """
        keyword_score = keyword_analysis.get('score', 0.0)
        is_relevant = keyword_analysis.get('is_relevant', False)
        
        # Проверяем нужно ли использовать LLM
        if not self.should_use_llm(item, keyword_score, is_relevant):
            # Возвращаем только keyword анализ
            return {
                **keyword_analysis,
                'llm_used': False
            }
        
        # Формируем текст для анализа
        text = f"{item.get('title', '')}. {item.get('description', '')}"
        text = text.strip()
        
        if not text:
            return {
                **keyword_analysis,
                'llm_used': False
            }
        
        try:
            # Запрашиваем анализ у LLM
            llm_response: LLMResponse = await self.provider.analyze_sentiment(
                text=text,
                company=company,
                timeout=self.timeout
            )
            
            if not llm_response.success:
                logger.warning(f"LLM анализ не удался: {llm_response.error}")
                return {
                    **keyword_analysis,
                    'llm_used': False,
                    'llm_error': llm_response.error
                }
            
            # Комбинируем keyword и LLM результаты
            # Вес: keyword 30%, LLM 70%
            combined_score = keyword_score * 0.3 + llm_response.score * 0.7
            
            # Определяем категорию на основе комбинированного score
            if combined_score >= 0.6:
                category = "HIGH_PROBABILITY"
            elif combined_score >= 0.2:
                category = "MEDIUM_PROBABILITY"
            elif combined_score <= -0.4:
                category = "NEGATIVE"
            else:
                category = "NEUTRAL"
            
            return {
                **keyword_analysis,
                'llm_used': True,
                'llm_score': llm_response.score,
                'llm_sentiment': llm_response.sentiment,
                'llm_confidence': llm_response.confidence,
                'llm_reasoning': llm_response.reasoning,
                'score': combined_score,  # Обновляем финальный score
                'category': category,  # Обновляем категорию
                'analysis_method': 'hybrid'  # keyword + LLM
            }
            
        except Exception as e:
            logger.error(f"Ошибка LLM анализа: {e}")
            return {
                **keyword_analysis,
                'llm_used': False,
                'llm_error': str(e)
            }
    
    async def analyze_batch(
        self,
        items: List[Dict],
        keyword_analyses: List[Dict],
        companies: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Пакетный анализ новостей.
        
        Args:
            items: Список новостей
            keyword_analyses: Результаты keyword анализа
            companies: Список компаний для контекста
            
        Returns:
            Список обогащённых результатов
        """
        if not self.is_available:
            logger.info("LLM недоступен, используем только keyword анализ")
            return [
                {**analysis, 'llm_used': False}
                for analysis in keyword_analyses
            ]
        
        # Определяем компанию для контекста
        company = companies[0] if companies else None
        
        # Анализируем каждую новость
        tasks = [
            self.analyze_item(item, analysis, company)
            for item, analysis in zip(items, keyword_analyses)
        ]
        
        # Выполняем параллельно с ограничением
        # Чтобы не перегрузить LLM, обрабатываем по 3 новости одновременно
        results = []
        batch_size = 3
        
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Ошибка в batch анализе: {result}")
                    # Используем keyword результат при ошибке
                    idx = len(results)
                    if idx < len(keyword_analyses):
                        results.append({
                            **keyword_analyses[idx],
                            'llm_used': False,
                            'llm_error': str(result)
                        })
                else:
                    results.append(result)
        
        # Подсчитываем статистику использования LLM
        llm_used_count = sum(1 for r in results if r.get('llm_used'))
        logger.info(
            f"LLM анализ: использован для {llm_used_count}/{len(results)} новостей"
        )
        
        return results
    
    def get_provider_info(self) -> Dict:
        """Информация о текущем провайдере."""
        return {
            'provider': self.provider.__class__.__name__,
            'model': self.provider.model_name,
            'available': self.is_available,
            'use_for': self.use_llm_for
        }

