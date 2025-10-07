"""
Сбор данных из различных источников:
- RSS новостей
- API вакансий
- Публичные API бирж
"""
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


class NewsCollector:
    """Асинхронный сборщик новостей из различных источников."""
    
    def __init__(self, sources: List[str], cache_ttl: int = 3600):
        self.sources = sources
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, tuple[datetime, List[Dict]]] = {}
        self.timeout = aiohttp.ClientTimeout(total=10)
        
    async def _fetch_rss(self, session: aiohttp.ClientSession, url: str) -> List[Dict]:
        """Получение новостей из RSS-ленты."""
        try:
            async with session.get(url, timeout=self.timeout) as response:
                if response.status != 200:
                    logger.warning(f"RSS {url} вернул статус {response.status}")
                    return []
                
                text = await response.text()
                root = ET.fromstring(text)
                
                items = []
                for item in root.findall('.//item'):
                    title_elem = item.find('title')
                    pubdate_elem = item.find('pubDate')
                    description_elem = item.find('description')
                    
                    if title_elem is not None:
                        items.append({
                            'title': title_elem.text or '',
                            'description': description_elem.text if description_elem is not None else '',
                            'pubdate': pubdate_elem.text if pubdate_elem is not None else '',
                            'source': url
                        })
                
                logger.info(f"Собрано {len(items)} новостей из {url}")
                return items
                
        except asyncio.TimeoutError:
            logger.error(f"Таймаут при запросе к {url}")
            return []
        except Exception as e:
            logger.error(f"Ошибка при парсинге RSS {url}: {e}")
            return []
    
    async def _fetch_hh_vacancies(self, session: aiohttp.ClientSession, search_text: str) -> List[Dict]:
        """Получение вакансий с hh.ru API."""
        url = "https://api.hh.ru/vacancies"
        params = {
            'text': search_text,
            'per_page': 20,
            'period': 7  # за последнюю неделю
        }
        
        try:
            async with session.get(url, params=params, timeout=self.timeout) as response:
                if response.status != 200:
                    logger.warning(f"hh.ru API вернул статус {response.status}")
                    return []
                
                data = await response.json()
                items = []
                
                for vacancy in data.get('items', []):
                    items.append({
                        'title': vacancy.get('name', ''),
                        'description': vacancy.get('snippet', {}).get('requirement', ''),
                        'employer': vacancy.get('employer', {}).get('name', ''),
                        'pubdate': vacancy.get('published_at', ''),
                        'source': 'hh.ru'
                    })
                
                logger.info(f"Собрано {len(items)} вакансий по запросу '{search_text}'")
                return items
                
        except Exception as e:
            logger.error(f"Ошибка при запросе к hh.ru: {e}")
            return []
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Проверка актуальности кэша."""
        if cache_key not in self._cache:
            return False
        
        cached_time, _ = self._cache[cache_key]
        return (datetime.now() - cached_time).total_seconds() < self.cache_ttl
    
    async def collect_all(self, vacancy_queries: Optional[List[str]] = None) -> List[Dict]:
        """
        Собрать все данные из настроенных источников.
        
        Args:
            vacancy_queries: Список поисковых запросов для вакансий
            
        Returns:
            Список словарей с собранными данными
        """
        cache_key = "all_news"
        
        # Проверяем кэш
        if self._is_cache_valid(cache_key):
            logger.info("Используем закэшированные данные")
            _, cached_data = self._cache[cache_key]
            return cached_data
        
        all_items = []
        
        async with aiohttp.ClientSession() as session:
            # Собираем RSS новости
            tasks = [self._fetch_rss(session, url) for url in self.sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_items.extend(result)
                else:
                    logger.error(f"Ошибка при сборе новостей: {result}")
            
            # Собираем вакансии
            if vacancy_queries:
                vacancy_tasks = [
                    self._fetch_hh_vacancies(session, query) 
                    for query in vacancy_queries
                ]
                vacancy_results = await asyncio.gather(*vacancy_tasks, return_exceptions=True)
                
                for result in vacancy_results:
                    if isinstance(result, list):
                        all_items.extend(result)
        
        # Кэшируем результат
        self._cache[cache_key] = (datetime.now(), all_items)
        
        logger.info(f"Всего собрано {len(all_items)} элементов")
        return all_items

