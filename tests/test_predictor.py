"""
Тесты для модуля предсказаний новостных всплесков.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.predictor.collector import NewsCollector
from app.predictor.analyzer import NewsAnalyzer
from app.predictor.signals import EventSignalGenerator, generate_event_signals
from app.predictor.config import PredictorConfig


class TestNewsCollector:
    """Тесты для сборщика новостей."""
    
    @pytest.mark.asyncio
    async def test_fetch_rss_success(self):
        """Тест успешного получения RSS."""
        collector = NewsCollector(sources=["https://test.com/rss"])
        
        # Мокаем ответ
        mock_xml = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Тестовая новость</title>
                    <description>Описание новости</description>
                    <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>
        """
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=mock_xml)
            mock_get.return_value.__aenter__.return_value = mock_response
            
            items = await collector.collect_all()
            
            assert len(items) == 1
            assert items[0]['title'] == 'Тестовая новость'
    
    @pytest.mark.asyncio
    async def test_cache_mechanism(self):
        """Тест механизма кэширования."""
        collector = NewsCollector(sources=["https://test.com/rss"], cache_ttl=3600)
        
        mock_xml = """<?xml version="1.0"?>
        <rss><channel><item><title>Test</title></item></channel></rss>
        """
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=mock_xml)
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Первый вызов - должен обратиться к API
            items1 = await collector.collect_all()
            assert mock_get.call_count == 1
            
            # Второй вызов - должен использовать кэш
            items2 = await collector.collect_all()
            assert mock_get.call_count == 1  # Не увеличилось
            assert items1 == items2
    
    @pytest.mark.asyncio
    async def test_hh_vacancies(self):
        """Тест получения вакансий с hh.ru."""
        collector = NewsCollector(sources=[])
        
        mock_json = {
            'items': [
                {
                    'name': 'Python Developer',
                    'snippet': {'requirement': 'Опыт работы с Python'},
                    'employer': {'name': 'Tech Company'},
                    'published_at': '2024-01-01T00:00:00'
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_json)
            mock_get.return_value.__aenter__.return_value = mock_response
            
            items = await collector.collect_all(vacancy_queries=['Python'])
            
            assert len(items) == 1
            assert items[0]['title'] == 'Python Developer'


class TestNewsAnalyzer:
    """Тесты для анализатора новостей."""
    
    def test_positive_keywords_detection(self):
        """Тест определения позитивных ключевых слов."""
        analyzer = NewsAnalyzer(
            positive_keywords=['запуск', 'фьючерс'],
            negative_keywords=['санкции']
        )
        
        item = {
            'title': 'Запуск нового фьючерса на бирже',
            'description': 'Компания объявила о запуске'
        }
        
        result = analyzer.analyze_item(item)
        
        assert result['score'] > 0
        assert result['category'] in ['HIGH_PROBABILITY', 'MEDIUM_PROBABILITY']
        assert len(result['matched_keywords']) > 0
    
    def test_negative_keywords_detection(self):
        """Тест определения негативных ключевых слов."""
        analyzer = NewsAnalyzer(
            positive_keywords=['запуск'],
            negative_keywords=['санкции', 'убытки']
        )
        
        item = {
            'title': 'Компания столкнулась с санкциями',
            'description': 'Убытки выросли'
        }
        
        result = analyzer.analyze_item(item)
        
        assert result['score'] < 0
        assert result['category'] == 'NEGATIVE'
    
    def test_company_mentions(self):
        """Тест определения упоминаний компаний."""
        analyzer = NewsAnalyzer(
            positive_keywords=['запуск'],
            negative_keywords=[]
        )
        
        item = {
            'title': 'Сбербанк запустил новый продукт',
            'description': 'Газпром тоже участвует'
        }
        
        result = analyzer.analyze_item(item, target_companies=['SBER', 'Сбербанк', 'Газпром'])
        
        assert 'Сбербанк' in result['mentioned_companies']
        assert 'Газпром' in result['mentioned_companies']
        assert result['is_relevant'] is True
    
    def test_summary_stats(self):
        """Тест получения статистики."""
        analyzer = NewsAnalyzer(
            positive_keywords=['запуск', 'рост'],
            negative_keywords=['падение']
        )
        
        items = [
            {'title': 'Запуск нового продукта', 'description': ''},
            {'title': 'Рост прибыли', 'description': ''},
            {'title': 'Падение акций', 'description': ''},
            {'title': 'Обычная новость', 'description': ''},
        ]
        
        analyzed = analyzer.analyze_batch(items)
        stats = analyzer.get_summary_stats(analyzed)
        
        assert stats['total'] == 4
        assert stats['HIGH_PROBABILITY'] + stats['MEDIUM_PROBABILITY'] >= 2
        assert stats['NEGATIVE'] >= 1


class TestEventSignalGenerator:
    """Тесты для генератора сигналов."""
    
    @pytest.mark.asyncio
    async def test_high_probability_signal(self):
        """Тест генерации HIGH_PROBABILITY сигнала."""
        config = PredictorConfig(
            news_sources=[],
            use_vacancies=False
        )
        
        generator = EventSignalGenerator(config)
        
        # Мокаем collector
        mock_items = [
            {'title': 'Запуск фьючерсов', 'description': 'Новый продукт'},
            {'title': 'Расширение торгов', 'description': 'API готово'},
            {'title': 'Лицензия получена', 'description': 'Успешно'},
        ]
        
        with patch.object(generator.collector, 'collect_all', return_value=mock_items):
            signal = await generator.generate_signal(['SPBE'])
            
            assert signal['signal_level'] in ['HIGH_PROBABILITY', 'MEDIUM_PROBABILITY']
            assert 'reason' in signal
            assert 'stats' in signal
    
    @pytest.mark.asyncio
    async def test_negative_signal(self):
        """Тест генерации NEGATIVE_SIGNAL."""
        config = PredictorConfig(
            news_sources=[],
            use_vacancies=False
        )
        
        generator = EventSignalGenerator(config)
        
        mock_items = [
            {'title': 'Санкции против компании', 'description': ''},
            {'title': 'Убытки выросли', 'description': 'Кризис'},
            {'title': 'Приостановка торгов', 'description': 'Штраф'},
        ]
        
        with patch.object(generator.collector, 'collect_all', return_value=mock_items):
            signal = await generator.generate_signal(['TEST'])
            
            assert signal['signal_level'] == 'NEGATIVE_SIGNAL'
    
    @pytest.mark.asyncio
    async def test_low_signal_no_data(self):
        """Тест генерации LOW сигнала при отсутствии данных."""
        config = PredictorConfig(
            news_sources=[],
            use_vacancies=False
        )
        
        generator = EventSignalGenerator(config)
        
        with patch.object(generator.collector, 'collect_all', return_value=[]):
            signal = await generator.generate_signal(['TEST'])
            
            assert signal['signal_level'] == 'LOW'
            assert 'Нет данных' in signal['reason']


class TestPredictorConfig:
    """Тесты для конфигурации."""
    
    def test_default_config(self):
        """Тест дефолтной конфигурации."""
        config = PredictorConfig()
        
        assert config.cache_ttl == 3600
        assert config.use_vacancies is True
        assert len(config.positive_keywords) > 0
        assert len(config.negative_keywords) > 0
    
    def test_config_load_nonexistent(self):
        """Тест загрузки несуществующего файла."""
        config = PredictorConfig.load("nonexistent.yaml")
        
        # Должна вернуться дефолтная конфигурация
        assert config.cache_ttl == 3600
    
    def test_config_save_and_load(self, tmp_path):
        """Тест сохранения и загрузки конфигурации."""
        config_file = tmp_path / "test_predictor.yaml"
        
        config1 = PredictorConfig(cache_ttl=7200, use_vacancies=False)
        config1.save(str(config_file))
        
        config2 = PredictorConfig.load(str(config_file))
        
        assert config2.cache_ttl == 7200
        assert config2.use_vacancies is False


@pytest.mark.asyncio
async def test_generate_event_signals_integration():
    """Интеграционный тест главной функции."""
    with patch('app.predictor.signals.PredictorConfig.load') as mock_load:
        mock_config = PredictorConfig(news_sources=[], use_vacancies=False)
        mock_load.return_value = mock_config
        
        with patch('app.predictor.collector.NewsCollector.collect_all') as mock_collect:
            mock_collect.return_value = [
                {'title': 'Позитивная новость', 'description': 'Запуск продукта'}
            ]
            
            result = await generate_event_signals(['TEST'])
            
            assert 'signal_level' in result
            assert 'reason' in result
            assert 'timestamp' in result

