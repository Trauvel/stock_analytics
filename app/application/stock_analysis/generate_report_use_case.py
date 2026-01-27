"""Use case для генерации отчёта анализа акций."""

from datetime import datetime
from typing import List
from loguru import logger

from app.domain.stock_analysis.entities.stock import Stock
from app.domain.stock_analysis.repositories.stock_repository import StockRepository
from app.domain.stock_analysis.services.metrics_calculator import MetricsCalculator
from app.ingest.moex_client import MOEXClient
from app.config.monitoring_loader import load_monitoring_config


class GenerateReportUseCase:
    """Use case для генерации отчёта анализа акций."""
    
    def __init__(
        self,
        stock_repository: StockRepository,
        metrics_calculator: MetricsCalculator,
        moex_client: MOEXClient,  # Временно для получения свечей
        dividend_target_pct: float = 8.0
    ):
        """
        Инициализация use case.
        
        Args:
            stock_repository: Репозиторий для получения акций
            metrics_calculator: Калькулятор метрик
            moex_client: Клиент MOEX (временно, пока не вынесен в репозиторий)
            dividend_target_pct: Целевая дивидендная доходность
        """
        self._stock_repo = stock_repository
        self._metrics_calc = metrics_calculator
        self._moex_client = moex_client
        self._dividend_target_pct = dividend_target_pct

        cfg = load_monitoring_config()
        mon = (cfg or {}).get("monitoring", {}) or {}
        self._candles_cache_enabled = bool(mon.get("candles_cache_enabled", True))
        self._candles_cache_refresh_days = int(mon.get("candles_cache_refresh_days", 7))
        self._candles_period_minutes = int(mon.get("candles_period_minutes", 60))
        self._candles_days_daily = int(mon.get("candles_days_daily", 400))
    
    async def execute(
        self,
        symbols: List[str],
        include_portfolio: bool = True
    ) -> dict:
        """
        Выполнить use case - сгенерировать отчёт.
        
        Args:
            symbols: Список тикеров для анализа
            include_portfolio: Включить ли тикеры из портфеля (пока не реализовано)
            
        Returns:
            Dict с отчётом в формате, совместимом со старым API
        """
        logger.info(f"Starting report generation for {len(symbols)} symbols")
        start_time = datetime.now()
        
        # Получаем акции через репозиторий
        stocks = await self._stock_repo.get_all(symbols)
        
        # Обогащаем метриками
        enriched_stocks = []
        for stock in stocks:
            try:
                # Получаем свечи для расчёта метрик
                if self._candles_cache_enabled:
                    candles = self._moex_client.get_candles_cached(
                        stock.symbol,
                        days=self._candles_days_daily,
                        refresh_days=self._candles_cache_refresh_days,
                        period_minutes=self._candles_period_minutes,
                    )
                else:
                    candles = self._moex_client.get_candles(
                        stock.symbol,
                        days=self._candles_days_daily,
                        period_minutes=self._candles_period_minutes,
                    )
                
                # Обогащаем метриками
                enriched = self._metrics_calc.enrich_stock_with_metrics(stock, candles)
                enriched_stocks.append(enriched)
                
            except Exception as e:
                logger.error(f"Error enriching {stock.symbol}: {e}")
                # Добавляем stock без метрик
                enriched_stocks.append(stock)
        
        # Формируем отчёт
        report = {
            "generated_at": start_time.isoformat(),
            "universe": [s.symbol for s in enriched_stocks],
            "by_symbol": {
                stock.symbol: self._format_stock_data(stock)
                for stock in enriched_stocks
            }
        }
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Report generation completed in {elapsed:.1f}s")
        
        return report
    
    def _format_stock_data(self, stock: Stock) -> dict:
        """
        Форматировать данные акции для отчёта.
        
        Args:
            stock: Доменная сущность акции
            
        Returns:
            Dict в формате, совместимом со старым API
        """
        # Используем метод to_dict из Stock entity
        data = stock.to_dict()
        
        # Добавляем метаданные для совместимости
        data["meta"] = {
            "board": None,  # Можно добавить из quote
            "error": None,
            "updated_at": data.get("updated_at")
        }
        
        return data
