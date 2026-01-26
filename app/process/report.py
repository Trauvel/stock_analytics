"""
Модуль генерации отчётов анализа.

⚠️ DEPRECATED: Этот модуль устарел и будет удалён в будущих версиях.
Используйте app.application.stock_analysis.generate_report_use_case.GenerateReportUseCase вместо этого.

Для обратной совместимости используйте app.process.report_ddd_adapter.ReportGeneratorDDDAdapter.
"""

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
    """
    Генератор отчётов анализа акций.
    
    ⚠️ DEPRECATED: Используйте app.process.report_ddd_adapter.ReportGeneratorDDDAdapter
    или app.application.stock_analysis.generate_report_use_case.GenerateReportUseCase
    """
    """Генератор отчётов анализа акций."""
    
    def __init__(self, save_snapshots: bool = True):
        """
        Инициализация генератора.
        
        Args:
            save_snapshots: Сохранять ли snapshots в историю (по умолчанию True)
        """
        self.config = get_config()
        self.client = MOEXClient()
        self.calculator = MetricsCalculator()
        self.save_snapshots = save_snapshots
        
        # Инициализируем use case для сохранения snapshots (опционально)
        self._snapshot_use_case = None
        if save_snapshots:
            try:
                from app.application.dependencies import container
                self._snapshot_use_case = container.save_snapshot_use_case()
            except Exception as e:
                logger.warning(f"Could not initialize snapshot use case: {e}. Snapshots will not be saved.")
                self.save_snapshots = False
    
    def _load_portfolio_tickers(self) -> List[str]:
        """
        Загрузить тикеры из всех портфелей пользователя.
        
        Returns:
            List[str]: Список тикеров из всех портфелей
        """
        try:
            project_root = Path(__file__).parent.parent.parent
            portfolios_dir = project_root / "data" / "portfolios"
            old_portfolio_path = project_root / "data" / "portfolio.json"
            
            tickers = []
            seen = set()
            
            # Загружаем из нового формата (несколько портфелей)
            if portfolios_dir.exists():
                index_path = portfolios_dir / "index.json"
                if index_path.exists():
                    with open(index_path, 'r', encoding='utf-8') as f:
                        index = json.load(f)
                    
                    for portfolio_id in index.get('ids', []):
                        portfolio_file = portfolios_dir / f"{portfolio_id}.json"
                        if portfolio_file.exists():
                            try:
                                with open(portfolio_file, 'r', encoding='utf-8') as f:
                                    portfolio = json.load(f)
                                
                                for position in portfolio.get('positions', []):
                                    symbol = position.get('symbol')
                                    if symbol and symbol not in seen:
                                        clean_symbol = symbol.rstrip('@')
                                        tickers.append(clean_symbol)
                                        seen.add(symbol)
                            except Exception as e:
                                logger.warning(f"Error loading portfolio {portfolio_id}: {e}")
                                continue
            
            # Загружаем из старого формата (если есть)
            if old_portfolio_path.exists():
                try:
                    with open(old_portfolio_path, 'r', encoding='utf-8') as f:
                        portfolio = json.load(f)
                    
                    for position in portfolio.get('positions', []):
                        symbol = position.get('symbol')
                        if symbol and symbol not in seen:
                            clean_symbol = symbol.rstrip('@')
                            tickers.append(clean_symbol)
                            seen.add(symbol)
                except Exception as e:
                    logger.warning(f"Error loading old portfolio: {e}")
            
            if tickers:
                logger.info(f"Loaded {len(tickers)} tickers from portfolio(s): {', '.join(tickers)}")
            
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
                div_ttm=divs,
                symbol=symbol
            )
            
            # Получаем объём из последней свечи
            volume = None
            if not candles.empty and 'volume' in candles.columns:
                volume = float(candles['volume'].iloc[-1]) if len(candles) > 0 else None
            
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
                rsi=metrics.get('rsi'),
                signals=metrics['signals'],
                meta=SymbolMeta(
                    board=quote['board'],
                    error=None,
                    updated_at=datetime.now()
                )
            )
            
            # Сохраняем snapshot в историю (если включено)
            if self.save_snapshots and self._snapshot_use_case:
                try:
                    self._snapshot_use_case.execute(
                        symbol=symbol,
                        price=quote['price'],
                        volume=volume,
                        sma_20=metrics['sma_20'],
                        sma_50=metrics['sma_50'],
                        sma_200=metrics['sma_200'],
                        dy_pct=metrics['dy_pct'],
                        rsi=metrics.get('rsi'),
                        atr=metrics.get('atr')
                    )
                except Exception as e:
                    logger.warning(f"Failed to save snapshot for {symbol}: {e}")
            
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
    
    def generate_report(self, include_portfolio: bool = True, instrument_type: str = "all", selected_bonds: Optional[List[str]] = None) -> AnalysisReport:
        """
        Сгенерировать полный отчёт по всем тикерам из universe и портфеля.
        
        Args:
            include_portfolio: Включить ли тикеры из портфеля (по умолчанию True)
            instrument_type: Тип инструментов для анализа
                - "all" - все тикеры (акции + облигации)
                - "stocks" - только акции
                - "bonds" - только облигации (или выбранные, если указан selected_bonds)
            selected_bonds: Список выбранных облигаций (только для instrument_type=bonds)
        
        Returns:
            AnalysisReport: Итоговый отчёт
        """
        logger.info(f"Starting report generation (instrument_type: {instrument_type}, selected_bonds: {selected_bonds})")
        start_time = datetime.now()
        
        # Получаем объединённый список тикеров
        if include_portfolio:
            universe = self._get_combined_universe()
            logger.info(f"Processing {len(universe)} symbols (config + portfolio): {', '.join(universe)}")
        else:
            universe = [ticker.symbol for ticker in self.config.universe]
            logger.info(f"Processing {len(universe)} symbols (config only): {', '.join(universe)}")
        
        # Фильтруем по типу инструментов
        if instrument_type != "all":
            original_count = len(universe)
            original_universe = universe.copy()
            filtered_universe = []
            
            logger.info(f"Starting filter: {original_count} symbols, filter type: {instrument_type}")
            
            # Если указаны конкретные облигации, используем только их
            if instrument_type == "bonds" and selected_bonds:
                logger.info(f"Using selected bonds: {', '.join(selected_bonds)}")
                for symbol in selected_bonds:
                    if symbol in original_universe:
                        filtered_universe.append(symbol)
                    else:
                        logger.warning(f"Selected bond {symbol} not found in universe")
            else:
                # Обычная фильтрация
                for symbol in original_universe:
                    is_bond = len(symbol) == 12 and symbol[:2].isalpha()  # ISIN код
                    
                    logger.debug(f"Checking symbol: {symbol}, len={len(symbol)}, is_bond={is_bond}")
                    
                    if instrument_type == "stocks" and not is_bond:
                        filtered_universe.append(symbol)
                        logger.debug(f"  -> Included as stock")
                    elif instrument_type == "bonds" and is_bond:
                        filtered_universe.append(symbol)
                        logger.debug(f"  -> Included as bond")
                    else:
                        logger.debug(f"  -> Filtered out (is_bond={is_bond}, instrument_type={instrument_type})")
            
            universe = filtered_universe
            type_label = "акции" if instrument_type == "stocks" else "облигации"
            logger.info(f"Filtered from {original_count} to {len(universe)} {type_label}")
            
            if len(universe) > 0:
                logger.info(f"Filtered symbols: {', '.join(universe)}")
            else:
                logger.warning(f"No {type_label} found after filtering!")
                logger.warning(f"Original symbols were: {', '.join(original_universe)}")
                logger.warning("Check if bonds use ISIN codes (12 characters starting with letters like RU000A10AS85)")
        
        # Обрабатываем каждый тикер (только отфильтрованные)
        logger.info(f"Processing {len(universe)} symbols after filtering")
        by_symbol = {}
        for symbol in universe:
            logger.info(f"Processing symbol: {symbol} (instrument_type filter: {instrument_type})")
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
    
    def generate_and_save(
        self, 
        save_daily: bool = True, 
        include_portfolio: bool = True,
        instrument_type: str = "all",
        selected_bonds: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Сгенерировать отчёт и сохранить его.
        
        Args:
            save_daily: Сохранить ли копию в daily reports
            include_portfolio: Включить ли тикеры из портфеля
            instrument_type: Тип инструментов для анализа (all, stocks, bonds)
            
        Returns:
            Dict[str, Any]: Сериализованный отчёт
        """
        logger.info("=" * 80)
        logger.info("GENERATING ANALYSIS REPORT")
        if include_portfolio:
            logger.info("Including portfolio tickers in analysis")
        type_label = {
            "all": "все тикеры",
            "stocks": "только акции",
            "bonds": "только облигации"
        }.get(instrument_type, instrument_type)
        logger.info(f"Instrument type filter: {type_label}")
        logger.info("=" * 80)
        
        # Генерируем отчёт
        report = self.generate_report(
            include_portfolio=include_portfolio,
            instrument_type=instrument_type,
            selected_bonds=selected_bonds
        )
        
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

