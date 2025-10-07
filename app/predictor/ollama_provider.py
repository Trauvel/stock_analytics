"""
Провайдер для работы с Ollama (локальные LLM модели).
"""
import asyncio
from typing import Optional
import logging

from .llm_provider import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Провайдер для Ollama."""
    
    def __init__(
        self, 
        model_name: str = "mistral", 
        base_url: str = "http://localhost:11434"
    ):
        super().__init__(model_name, base_url)
        self.client = None
        
    async def check_availability(self) -> bool:
        """Проверка доступности Ollama."""
        try:
            import ollama
            
            # Проверяем что Ollama запущен
            try:
                client = ollama.Client(host=self.base_url)
                models_response = client.list()
                
                # Проверяем что нужная модель установлена
                models_list = models_response.get('models', [])
                if not models_list:
                    logger.warning("Ollama запущен, но нет установленных моделей")
                    self.is_available = False
                    return False
                
                available_models = [m.get('name', m.get('model', '')) for m in models_list]
                
                # Ollama возвращает модели с тегом :latest
                model_variants = [
                    self.model_name,
                    f"{self.model_name}:latest",
                    self.model_name.split(':')[0]  # без тега
                ]
                
                self.is_available = any(
                    any(variant in str(model) for variant in model_variants)
                    for model in available_models
                )
                
                if self.is_available:
                    logger.info(f"Ollama доступен, модель {self.model_name} найдена")
                else:
                    logger.warning(
                        f"Ollama запущен, но модель {self.model_name} не найдена. "
                        f"Доступные модели: {available_models}"
                    )
                
                return self.is_available
                
            except Exception as e:
                logger.warning(f"Ollama недоступен: {e}")
                self.is_available = False
                return False
                
        except ImportError:
            logger.warning("Библиотека ollama не установлена. Установите: pip install ollama")
            self.is_available = False
            return False
    
    async def analyze_sentiment(
        self, 
        text: str, 
        company: Optional[str] = None,
        timeout: int = 10
    ) -> LLMResponse:
        """Анализ тональности через Ollama."""
        if not self.is_available:
            await self.check_availability()
            
            if not self.is_available:
                return LLMResponse(
                    sentiment='neutral',
                    score=0.0,
                    confidence='low',
                    reasoning='Ollama недоступен',
                    success=False,
                    error='Ollama is not available'
                )
        
        try:
            import ollama
            
            prompt = self._build_sentiment_prompt(text, company)
            
            # Запускаем в отдельном потоке с таймаутом
            client = ollama.Client(host=self.base_url)
            
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.generate,
                    model=self.model_name,
                    prompt=prompt,
                    options={
                        'temperature': 0.3,  # Низкая температура для стабильности
                        'num_predict': 200,  # Ограничиваем длину ответа
                    }
                ),
                timeout=timeout
            )
            
            response_text = response.get('response', '')
            
            logger.debug(f"Ollama response: {response_text[:200]}...")
            
            return self._parse_llm_response(response_text)
            
        except asyncio.TimeoutError:
            logger.warning(f"Таймаут при запросе к Ollama (>{timeout}s)")
            return LLMResponse(
                sentiment='neutral',
                score=0.0,
                confidence='low',
                reasoning='Таймаут запроса',
                success=False,
                error='Timeout'
            )
            
        except Exception as e:
            logger.error(f"Ошибка при запросе к Ollama: {e}")
            return LLMResponse(
                sentiment='neutral',
                score=0.0,
                confidence='low',
                reasoning='Ошибка запроса',
                success=False,
                error=str(e)
            )

