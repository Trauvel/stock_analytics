"""
Абстрактный интерфейс для LLM провайдеров.
Позволяет легко переключаться между Ollama, OpenAI, LocalAI и др.
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Ответ от LLM модели."""
    sentiment: str  # positive, neutral, negative
    score: float  # от -1 до 1
    confidence: str  # high, medium, low
    reasoning: str  # обоснование
    success: bool = True
    error: Optional[str] = None


class LLMProvider(ABC):
    """Базовый класс для LLM провайдеров."""
    
    def __init__(self, model_name: str, base_url: Optional[str] = None):
        self.model_name = model_name
        self.base_url = base_url
        self.is_available = False
        
    @abstractmethod
    async def analyze_sentiment(
        self, 
        text: str, 
        company: Optional[str] = None,
        timeout: int = 10
    ) -> LLMResponse:
        """
        Анализ тональности текста.
        
        Args:
            text: Текст для анализа
            company: Название компании (опционально)
            timeout: Таймаут в секундах
            
        Returns:
            LLMResponse с результатами анализа
        """
        pass
    
    @abstractmethod
    async def check_availability(self) -> bool:
        """
        Проверка доступности модели.
        
        Returns:
            True если модель доступна
        """
        pass
    
    def _build_sentiment_prompt(self, text: str, company: Optional[str] = None) -> str:
        """Построение промпта для анализа тональности."""
        company_context = f" о компании '{company}'" if company else ""
        
        return f"""Проанализируй тональность финансовой новости{company_context}.

Новость: "{text}"

Определи:
1. Тональность: positive/neutral/negative
2. Уверенность: high/medium/low
3. Балл от -1.0 (крайне негативно) до +1.0 (крайне позитивно)
4. Краткое обоснование (1 предложение)

Учитывай:
- Завуалированные формулировки (например, "пересматривает стратегию" = проблемы)
- Контекст для финансовых рынков
- Возможное влияние на цену акций

Ответь СТРОГО в формате JSON:
{{
  "sentiment": "positive",
  "confidence": "high",
  "score": 0.7,
  "reasoning": "Запуск нового продукта - позитивный сигнал для роста"
}}

JSON:"""

    def _parse_llm_response(self, response_text: str) -> LLMResponse:
        """Парсинг ответа от LLM."""
        try:
            import json
            
            # Ищем JSON в ответе
            response_text = response_text.strip()
            
            # Пытаемся найти JSON блок
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            
            # Находим { и } для извлечения JSON
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("JSON not found in response")
            
            json_str = response_text[start_idx:end_idx]
            data = json.loads(json_str)
            
            return LLMResponse(
                sentiment=data.get('sentiment', 'neutral'),
                score=float(data.get('score', 0.0)),
                confidence=data.get('confidence', 'medium'),
                reasoning=data.get('reasoning', ''),
                success=True
            )
            
        except Exception as e:
            logger.error(f"Ошибка парсинга ответа LLM: {e}")
            logger.debug(f"Response text: {response_text}")
            
            return LLMResponse(
                sentiment='neutral',
                score=0.0,
                confidence='low',
                reasoning='Ошибка парсинга ответа',
                success=False,
                error=str(e)
            )

