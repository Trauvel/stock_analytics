"""Модуль генерации отчётов анализа."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
from loguru import logger

from app.config.loader import get_config
from app.ingest.moex_client import MOEXClient, MOEXClientError
from app.process.metrics import MetricsCalculator
from app.store.io import save_analysis_report, save_daily_report
from app.models import AnalysisReport, SymbolData, SymbolMeta


class ReportGenerator:
    """Генератор отчётов анализа акций."""
    
    def __init__(self):
        """Инициализация генератора."""
        self.config = get_config()
        self.client = MOEXClient()
        self.calculator = MetricsCalculator()
    
    def _load_portfolio_tickers(self) -> List[str]:
        """
        Загрузить тикеры из портфеля пользователя.
        
        Returns:
            List[str]: Список тикеров из портфеля
        """
        try:
            project_root = Path(__file__).parent.parent.parent
            portfolio_path = project_root / "data" / "portfolio.json"
            
            if not portfolio_path.exists():
                logger.debug("Portfolio file not found, skipping portfolio tickers")
                return []
            
            with open(portfolio_path, 'r', encoding='utf-8') as f:
                portfolio = json.load(f)
            
            # Извлекаем тикеры из позиций
            tickers = []
            for position in portfolio.get('positions', []):
                symbol = position.get('symbol')
                if symbol:
                    # Очищаем от спецсимволов если нужно
                    # Например TGLD@ -> TGLD
                    clean_symbol = symbol.rstrip('@')
                    tickers.append(clean_symbol)
            
            if tickers:
                logger.info(f"Loaded {len(tickers)} tickers from portfolio: {', '.join(tickers)}")
            
            return tickers
            
        except Exception as e:
            logger.warning(f"Failed to load portfolio tickers: {e}")
            return []
    
    def _get_combined_universe(self) -> List[str]:
        """
        Получить объединённый список тикеров из config и портфеля.
        
        Returns:
            List[str]: Уникальный список тикеров
        """
        # Тикеры из конфигурации
        config_tickers = [ticker.symbol for ticker in self.config.universe]
        
        # Тикеры из портфеля
        portfolio_tickers = self._load_portfolio_tickers()
        
        # Объединяем и убираем дубликаты, сохраняя порядок
        seen = set()
        combined = []
        
        # Сначала добавляем тикеры из конфига
        for ticker in config_tickers:
            if ticker not in seen:
                combined.append(ticker)
                seen.add(ticker)
        
        # Затем добавляем новые тикеры из портфеля
        for ticker in portfolio_tickers:
            if ticker not in seen:
                combined.append(ticker)
                seen.add(ticker)
                logger.info(f"Added portfolio ticker to analysis: {ticker}")
        
        return combined
    
    def _process_symbol(self, symbol: str) -> SymbolData:
        """
        Обработать один тикер: получить данные и рассчитать метрики.
        
        Args:
            symbol: Тикер для обработки
            
        Returns:
            SymbolData: Данные по тикеру (с ошибкой если что-то пошло не так)
        """
        logger.info(f"Processing symbol: {symbol}")
        
        try:
            # Получаем данные с MOEX
            quote = self.client.get_quote(symbol)
            divs = self.client.get_dividends(symbol)
            candles = self.client.get_candles(symbol, days=400)
            
            # Рассчитываем метрики
            metrics = self.calculator.calculate_all_metrics(
                candles=candles,
                current_price=quote['price'],
                div_ttm=divs
            )
            
            # Формируем данные по тикеру
            symbol_data = SymbolData(
                price=quote['price'],
                lot=quote['lot'],
                div_ttm=divs,
                dy_pct=metrics['dy_pct'],
                sma_20=metrics['sma_20'],
                sma_50=metrics['sma_50'],
                sma_200=metrics['sma_200'],
                high_52w=metrics['high_52w'],
                low_52w=metrics['low_52w'],
                dist_52w_low_pct=metrics['dist_52w_low_pct'],
                dist_52w_high_pct=metrics['dist_52w_high_pct'],
                signals=metrics['signals'],
                meta=SymbolMeta(
                    board=quote['board'],
                    error=None,
                    updated_at=datetime.now()
                )
            )
            
            logger.info(f"Successfully processed {symbol}: price={quote['price']}, signals={len(metrics['signals'])}")
            return symbol_data
            
        except Exception as e:
            logger.error(f"Failed to process {symbol}: {e}")
            
            # Возвращаем пустой объект с ошибкой
            return SymbolData(
                price=None,
                lot=None,
                div_ttm=None,
                dy_pct=None,
                sma_20=None,
                sma_50=None,
                sma_200=None,
                high_52w=None,
                low_52w=None,
                dist_52w_low_pct=None,
                dist_52w_high_pct=None,
                signals=[],
                meta=SymbolMeta(
                    board=None,
                    error=str(e),
                    updated_at=None
                )
            )
    
    def generate_report(self, include_portfolio: bool = True) -> AnalysisReport:
        """
        Сгенерировать полный отчёт по всем тикерам из universe и портфеля.
        
        Args:
            include_portfolio: Включить ли тикеры из портфеля (по умолчанию True)
        
        Returns:
            AnalysisReport: Итоговый отчёт
        """
        logger.info("Starting report generation")
        start_time = datetime.now()
        
        # Получаем объединённый список тикеров
        if include_portfolio:
            universe = self._get_combined_universe()
            logger.info(f"Processing {len(universe)} symbols (config + portfolio): {', '.join(universe)}")
        else:
            universe = [ticker.symbol for ticker in self.config.universe]
            logger.info(f"Processing {len(universe)} symbols (config only): {', '.join(universe)}")
        
        # Обрабатываем каждый тикер
        by_symbol = {}
        for symbol in universe:
            symbol_data = self._process_symbol(symbol)
            by_symbol[symbol] = symbol_data
        
        # Формируем итоговый отчёт
        report = AnalysisReport(
            generated_at=start_time,
            universe=universe,
            by_symbol=by_symbol
        )
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Report generation completed in {elapsed:.1f}s")
        
        return report
    
    def generate_and_save(self, save_daily: bool = True, include_portfolio: bool = True) -> Dict[str, Any]:
        """
        Сгенерировать отчёт и сохранить его.
        
        Args:
            save_daily: Сохранить ли копию в daily reports
            include_portfolio: Включить ли тикеры из портфеля
            
        Returns:
            Dict[str, Any]: Сериализованный отчёт
        """
        logger.info("=" * 80)
        logger.info("GENERATING ANALYSIS REPORT")
        if include_portfolio:
            logger.info("Including portfolio tickers in analysis")
        logger.info("=" * 80)
        
        # Генерируем отчёт
        report = self.generate_report(include_portfolio=include_portfolio)
        
        # Сериализуем в dict (Pydantic model_dump)
        report_dict = report.model_dump(mode='json')
        
        # Преобразуем datetime в ISO string
        report_dict['generated_at'] = report.generated_at.isoformat()
        
        # Преобразуем enum сигналов в строки
        for symbol, data in report_dict['by_symbol'].items():
            if data['signals']:
                data['signals'] = [sig if isinstance(sig, str) else sig for sig in data['signals']]
            if data['meta']['updated_at']:
                data['meta']['updated_at'] = data['meta']['updated_at']
        
        # Сохраняем основной отчёт
        save_analysis_report(report_dict, self.config.output.analysis_file)
        
        # Сохраняем копию в daily reports
        if save_daily:
            save_daily_report(
                report_dict,
                date=report.generated_at,
                reports_dir=self.config.output.reports_dir
            )
        
        # Статистика
        successful = sum(1 for data in report.by_symbol.values() if data.meta.error is None)
        failed = len(report.by_symbol) - successful
        
        logger.info("=" * 80)
        logger.info(f"REPORT STATISTICS:")
        logger.info(f"  Total symbols: {len(report.by_symbol)}")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Failed: {failed}")
        
        # Сигналы
        total_signals = sum(len(data.signals) for data in report.by_symbol.values())
        logger.info(f"  Total signals: {total_signals}")
        
        # Топ сигналов
        high_div_tickers = [
            symbol for symbol, data in report.by_symbol.items()
            if data.dy_pct and data.dy_pct >= self.config.dividend_target_pct
        ]
        if high_div_tickers:
            logger.info(f"  High dividend yield: {', '.join(high_div_tickers)}")
        
        logger.info("=" * 80)
        
        return report_dict
    
    def get_summary(self, report: AnalysisReport) -> Dict[str, Any]:
        """
        Получить краткую сводку по отчёту.
        
        Args:
            report: Отчёт анализа
            
        Returns:
            Dict с краткой статистикой
        """
        summary = {
            'total_symbols': len(report.universe),
            'successful': 0,
            'failed': 0,
            'with_signals': 0,
            'high_dividend': [],
            'above_sma200': [],
            'below_sma200': [],
            'avg_dy_pct': None
        }
        
        dy_values = []
        
        for symbol, data in report.by_symbol.items():
            if data.meta.error is None:
                summary['successful'] += 1
                
                if data.signals:
                    summary['with_signals'] += 1
                
                if data.dy_pct and data.dy_pct >= self.config.dividend_target_pct:
                    summary['high_dividend'].append(symbol)
                
                if data.dy_pct:
                    dy_values.append(data.dy_pct)
                
                # Проверяем позицию относительно SMA200
                if data.price and data.sma_200:
                    if data.price > data.sma_200:
                        summary['above_sma200'].append(symbol)
                    else:
                        summary['below_sma200'].append(symbol)
            else:
                summary['failed'] += 1
        
        # Средняя дивидендная доходность
        if dy_values:
            summary['avg_dy_pct'] = round(sum(dy_values) / len(dy_values), 2)
        
        return summary

