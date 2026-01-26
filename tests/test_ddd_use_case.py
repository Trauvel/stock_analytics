"""Тесты для Use Case генерации отчёта."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.application.stock_analysis.generate_report_use_case import GenerateReportUseCase
from app.domain.stock_analysis.entities.stock import Stock
from app.domain.stock_analysis.value_objects import Price, DividendYield, Signal, SignalType
from app.domain.stock_analysis.services.metrics_calculator import MetricsCalculator
import pandas as pd


class TestGenerateReportUseCase:
    """Тесты для Use Case генерации отчёта."""
    
    @pytest.fixture
    def mock_stock_repository(self):
        """Создать мок репозитория."""
        repo = Mock()
        repo.get_all = AsyncMock()
        return repo
    
    @pytest.fixture
    def mock_metrics_calculator(self):
        """Создать мок калькулятора метрик."""
        return Mock(spec=MetricsCalculator)
    
    @pytest.fixture
    def mock_moex_client(self):
        """Создать мок MOEX клиента."""
        client = Mock()
        return client
    
    @pytest.fixture
    def sample_stock(self):
        """Создать пример акции."""
        return Stock(
            symbol="SBER",
            price=Price(value=250.0),
            dividend_yield=DividendYield(value=8.5),
            sma_200=Price(value=280.0),
            signals=[],
            updated_at=datetime.now()
        )
    
    @pytest.fixture
    def sample_candles(self):
        """Создать пример свечей."""
        # Создаём DataFrame с минимальными данными
        dates = pd.date_range(start='2024-01-01', periods=300, freq='D')
        return pd.DataFrame({
            'begin': dates,
            'end': dates,
            'open': [250.0] * 300,
            'high': [260.0] * 300,
            'low': [240.0] * 300,
            'close': [250.0] * 300,
            'volume': [1000000] * 300
        })
    
    @pytest.mark.asyncio
    async def test_execute_success(
        self,
        mock_stock_repository,
        mock_metrics_calculator,
        mock_moex_client,
        sample_stock,
        sample_candles
    ):
        """Тест успешного выполнения use case."""
        # Настраиваем моки
        mock_stock_repository.get_all.return_value = [sample_stock]
        mock_moex_client.get_candles.return_value = sample_candles
        
        # Настраиваем калькулятор метрик
        enriched_stock = Stock(
            symbol=sample_stock.symbol,
            price=sample_stock.price,
            dividend_yield=sample_stock.dividend_yield,
            sma_20=Price(value=245.0),
            sma_50=Price(value=248.0),
            sma_200=Price(value=280.0),
            high_52w=Price(value=300.0),
            low_52w=Price(value=200.0),
            signals=[Signal(signal_type=SignalType.PRICE_BELOW_SMA200)],
            lot=sample_stock.lot,
            div_ttm=sample_stock.div_ttm,
            updated_at=sample_stock.updated_at
        )
        mock_metrics_calculator.enrich_stock_with_metrics.return_value = enriched_stock
        
        # Создаём use case
        use_case = GenerateReportUseCase(
            stock_repository=mock_stock_repository,
            metrics_calculator=mock_metrics_calculator,
            moex_client=mock_moex_client,
            dividend_target_pct=8.0
        )
        
        # Выполняем
        report = await use_case.execute(symbols=["SBER"])
        
        # Проверяем результат
        assert report is not None
        assert "generated_at" in report
        assert "universe" in report
        assert "by_symbol" in report
        assert len(report["universe"]) == 1
        assert "SBER" in report["by_symbol"]
        
        # Проверяем данные по тикеру
        sber_data = report["by_symbol"]["SBER"]
        assert sber_data["price"] == 250.0
        assert sber_data["dy_pct"] == 8.5
        assert len(sber_data["signals"]) == 1
    
    @pytest.mark.asyncio
    async def test_execute_empty_symbols(
        self,
        mock_stock_repository,
        mock_metrics_calculator,
        mock_moex_client
    ):
        """Тест выполнения с пустым списком тикеров."""
        mock_stock_repository.get_all.return_value = []
        
        use_case = GenerateReportUseCase(
            stock_repository=mock_stock_repository,
            metrics_calculator=mock_metrics_calculator,
            moex_client=mock_moex_client
        )
        
        report = await use_case.execute(symbols=[])
        
        assert report is not None
        assert len(report["universe"]) == 0
        assert len(report["by_symbol"]) == 0
    
    @pytest.mark.asyncio
    async def test_execute_multiple_symbols(
        self,
        mock_stock_repository,
        mock_metrics_calculator,
        mock_moex_client,
        sample_stock,
        sample_candles
    ):
        """Тест выполнения для нескольких тикеров."""
        # Создаём несколько акций
        stock1 = sample_stock
        stock2 = Stock(
            symbol="VTBR",
            price=Price(value=100.0),
            dividend_yield=DividendYield(value=10.0),
            sma_200=None,
            signals=[],
            updated_at=datetime.now()
        )
        
        mock_stock_repository.get_all.return_value = [stock1, stock2]
        mock_moex_client.get_candles.return_value = sample_candles
        
        # Настраиваем калькулятор
        enriched_stock1 = Stock(
            symbol=stock1.symbol,
            price=stock1.price,
            dividend_yield=stock1.dividend_yield,
            sma_20=None,
            sma_50=None,
            sma_200=Price(value=280.0),
            high_52w=None,
            low_52w=None,
            signals=[],
            lot=stock1.lot,
            div_ttm=stock1.div_ttm,
            updated_at=stock1.updated_at
        )
        enriched_stock2 = Stock(
            symbol=stock2.symbol,
            price=stock2.price,
            dividend_yield=stock2.dividend_yield,
            sma_20=None,
            sma_50=None,
            sma_200=None,
            high_52w=None,
            low_52w=None,
            signals=[],
            lot=None,
            div_ttm=None,
            updated_at=stock2.updated_at
        )
        
        def enrich_side_effect(stock, candles):
            if stock.symbol == "SBER":
                return enriched_stock1
            return enriched_stock2
        
        mock_metrics_calculator.enrich_stock_with_metrics.side_effect = enrich_side_effect
        
        use_case = GenerateReportUseCase(
            stock_repository=mock_stock_repository,
            metrics_calculator=mock_metrics_calculator,
            moex_client=mock_moex_client
        )
        
        report = await use_case.execute(symbols=["SBER", "VTBR"])
        
        assert len(report["universe"]) == 2
        assert "SBER" in report["by_symbol"]
        assert "VTBR" in report["by_symbol"]
    
    @pytest.mark.asyncio
    async def test_execute_error_handling(
        self,
        mock_stock_repository,
        mock_metrics_calculator,
        mock_moex_client,
        sample_stock
    ):
        """Тест обработки ошибок."""
        # Репозиторий возвращает акцию
        mock_stock_repository.get_all.return_value = [sample_stock]
        
        # Но MOEX клиент выбрасывает ошибку
        mock_moex_client.get_candles.side_effect = Exception("MOEX API error")
        
        use_case = GenerateReportUseCase(
            stock_repository=mock_stock_repository,
            metrics_calculator=mock_metrics_calculator,
            moex_client=mock_moex_client
        )
        
        # Use case должен обработать ошибку и вернуть stock без метрик
        report = await use_case.execute(symbols=["SBER"])
        
        assert report is not None
        assert "SBER" in report["by_symbol"]
        # Stock должен быть в отчёте, но без обогащённых метрик
