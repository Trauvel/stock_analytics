"""
Анализ тональности и релевантности собранных данных.
Использует keyword matching и sentiment analysis для русского языка.
"""
import re
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class NewsAnalyzer:
    """Анализатор новостей с поддержкой русского языка."""
    
    def __init__(self, positive_keywords: List[str], negative_keywords: List[str]):
        self.positive_keywords = [kw.lower() for kw in positive_keywords]
        self.negative_keywords = [kw.lower() for kw in negative_keywords]
        
        # Усилители для более точной оценки
        self.strong_positive = [
            'запуск', 'запущен', 'открыт', 'открытие',
            'новый продукт', 'расширение', 'рост', 'прибыль',
            'успешно', 'лидер', 'инновация'
        ]
        
        self.strong_negative = [
            'санкции', 'убытки', 'падение', 'кризис',
            'расследование', 'приостановка', 'закрыт', 'банкротство',
            'штраф', 'скандал'
        ]
    
    def _calculate_keyword_score(self, text: str) -> Tuple[float, List[str]]:
        """
        Подсчёт балла на основе ключевых слов.
        
        Returns:
            (score, matched_keywords): Балл от -1 до 1 и список найденных ключевых слов
        """
        text_lower = text.lower()
        score = 0.0
        matched = []
        
        # Проверяем позитивные ключевые слова
        for keyword in self.positive_keywords:
            if keyword in text_lower:
                weight = 2.0 if keyword in self.strong_positive else 1.0
                score += weight
                matched.append(f"+{keyword}")
        
        # Проверяем негативные ключевые слова
        for keyword in self.negative_keywords:
            if keyword in text_lower:
                weight = 2.0 if keyword in self.strong_negative else 1.0
                score -= weight
                matched.append(f"-{keyword}")
        
        # Нормализуем в диапазон [-1, 1]
        if score > 0:
            score = min(1.0, score / 5.0)
        elif score < 0:
            score = max(-1.0, score / 5.0)
        
        return score, matched
    
    def _detect_company_mentions(self, text: str, companies: List[str]) -> List[str]:
        """Определение упоминаний компаний в тексте."""
        text_lower = text.lower()
        mentioned = []
        
        for company in companies:
            company_lower = company.lower()
            # Проверяем точное совпадение или с частицами
            if re.search(rf'\b{re.escape(company_lower)}\b', text_lower):
                mentioned.append(company)
        
        return mentioned
    
    def analyze_item(self, item: Dict, target_companies: List[str] = None) -> Dict:
        """
        Анализ отдельного элемента новостей/вакансий.
        
        Args:
            item: Словарь с полями title, description
            target_companies: Список компаний для отслеживания
            
        Returns:
            Обогащённый словарь с результатами анализа
        """
        text = f"{item.get('title', '')} {item.get('description', '')}"
        
        # Подсчёт балла
        score, keywords = self._calculate_keyword_score(text)
        
        # Определение категории
        if score >= 0.6:
            category = "HIGH_PROBABILITY"
        elif score >= 0.2:
            category = "MEDIUM_PROBABILITY"
        elif score <= -0.4:
            category = "NEGATIVE"
        else:
            category = "NEUTRAL"
        
        # Поиск упоминаний компаний
        mentioned_companies = []
        if target_companies:
            mentioned_companies = self._detect_company_mentions(text, target_companies)
        
        return {
            **item,
            'score': score,
            'category': category,
            'matched_keywords': keywords,
            'mentioned_companies': mentioned_companies,
            'is_relevant': len(mentioned_companies) > 0 or len(keywords) > 0
        }
    
    def analyze_batch(self, items: List[Dict], target_companies: List[str] = None) -> List[Dict]:
        """
        Анализ пакета новостей/вакансий.
        
        Returns:
            Список обогащённых словарей с результатами анализа
        """
        analyzed = []
        
        for item in items:
            try:
                result = self.analyze_item(item, target_companies)
                analyzed.append(result)
            except Exception as e:
                logger.error(f"Ошибка при анализе элемента: {e}")
                continue
        
        # Сортируем по релевантности и баллу
        analyzed.sort(key=lambda x: (x['is_relevant'], x['score']), reverse=True)
        
        logger.info(f"Проанализировано {len(analyzed)} элементов")
        return analyzed
    
    def get_summary_stats(self, analyzed_items: List[Dict]) -> Dict:
        """
        Получение статистики по проанализированным данным.
        
        Returns:
            Словарь со статистикой
        """
        stats = {
            'total': len(analyzed_items),
            'HIGH_PROBABILITY': 0,
            'MEDIUM_PROBABILITY': 0,
            'NEGATIVE': 0,
            'NEUTRAL': 0,
            'relevant': 0,
            'avg_score': 0.0
        }
        
        if not analyzed_items:
            return stats
        
        total_score = 0.0
        for item in analyzed_items:
            category = item.get('category', 'NEUTRAL')
            stats[category] = stats.get(category, 0) + 1
            
            if item.get('is_relevant'):
                stats['relevant'] += 1
            
            total_score += item.get('score', 0.0)
        
        stats['avg_score'] = total_score / len(analyzed_items)
        
        return stats

