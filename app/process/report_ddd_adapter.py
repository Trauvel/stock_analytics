"""Адаптер для совместимости старого ReportGenerator с новым DDD Use Case."""

import asyncio
from typing import Dict, Any
from loguru import logger

from app.application.dependencies import container
from app.application.stock_analysis.generate_report_use_case import GenerateReportUseCase
from app.application.stock_analysis.get_universe_use_case import GetUniverseUseCase
from app.config.loader import get_config
from app.store.io import save_analysis_report, save_daily_report
from datetime import datetime


class ReportGeneratorDDDAdapter:
    """
    Адаптер, который использует новый DDD Use Case,
    но предоставляет интерфейс совместимый со старым ReportGenerator.
    """
    
    def __init__(self):
        """Инициализация адаптера."""
        self.config = get_config()
        self.use_case: GenerateReportUseCase = container.generate_report_use_case()
        self.get_universe_use_case = GetUniverseUseCase()
    
    def generate_and_save(
        self,
        save_daily: bool = True,
        include_portfolio: bool = True,
        instrument_type: str = "all"
    ) -> Dict[str, Any]:
        """
        Сгенерировать отчёт и сохранить его (совместимость со старым API).
        
        Args:
            save_daily: Сохранить ли копию в daily reports
            include_portfolio: Включить ли тикеры из портфеля
            instrument_type: Тип инструментов для анализа (all, stocks, bonds)
            
        Returns:
            Dict[str, Any]: Сериализованный отчёт
        """
        logger.info("=" * 80)
        logger.info("GENERATING ANALYSIS REPORT (via DDD)")
        if include_portfolio:
            logger.info("Including portfolio tickers in analysis")
        type_label = {
            "all": "все тикеры",
            "stocks": "только акции",
            "bonds": "только облигации"
        }.get(instrument_type, instrument_type)
        logger.info(f"Instrument type filter: {type_label}")
        logger.info("=" * 80)
        
        # Получаем список тикеров через use case
        symbols = self.get_universe_use_case.execute(include_portfolio=include_portfolio)
        
        # Фильтруем по типу инструментов
        if instrument_type != "all":
            original_count = len(symbols)
            original_symbols = symbols.copy()
            filtered_symbols = []
            
            logger.info(f"Starting filter: {original_count} symbols, filter type: {instrument_type}")
            
            for symbol in original_symbols:
                is_bond = len(symbol) == 12 and symbol[:2].isalpha()  # ISIN код
                
                logger.debug(f"Checking symbol: {symbol}, len={len(symbol)}, is_bond={is_bond}")
                
                if instrument_type == "stocks" and not is_bond:
                    filtered_symbols.append(symbol)
                    logger.debug(f"  -> Included as stock")
                elif instrument_type == "bonds" and is_bond:
                    filtered_symbols.append(symbol)
                    logger.debug(f"  -> Included as bond")
                else:
                    logger.debug(f"  -> Filtered out (is_bond={is_bond}, instrument_type={instrument_type})")
            
            symbols = filtered_symbols
            logger.info(f"Filtered from {original_count} to {len(symbols)} {type_label}")
            if len(symbols) > 0:
                logger.info(f"Filtered symbols: {', '.join(symbols)}")
            else:
                logger.warning(f"No {type_label} found! Original symbols were: {', '.join(original_symbols)}")
                logger.warning("Check if bonds use ISIN codes (12 characters starting with letters)")
                # Если после фильтрации ничего не осталось, не продолжаем
                return {
                    "generated_at": datetime.now().isoformat(),
                    "universe": [],
                    "by_symbol": {}
                }
        
        # Генерируем отчёт через Use Case (синхронная обёртка над async)
        logger.info(f"Generating report for {len(symbols)} filtered symbols: {', '.join(symbols)}")
        try:
            # Если уже есть event loop, используем его
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Если loop уже работает, создаём задачу
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            self.use_case.execute(symbols=symbols)
                        )
                        report_dict = future.result()
                else:
                    report_dict = loop.run_until_complete(
                        self.use_case.execute(symbols=symbols)
                    )
            except RuntimeError:
                # Нет event loop, создаём новый
                report_dict = asyncio.run(
                    self.use_case.execute(symbols=symbols)
                )
        except Exception as e:
            logger.error(f"Error generating report via DDD: {e}")
            raise
        
        # Сохраняем основной отчёт
        save_analysis_report(report_dict, self.config.output.analysis_file)
        
        # Сохраняем копию в daily reports
        if save_daily:
            save_daily_report(
                report_dict,
                date=datetime.fromisoformat(report_dict['generated_at']),
                reports_dir=self.config.output.reports_dir
            )
        
        # Статистика
        successful = sum(
            1 for data in report_dict['by_symbol'].values()
            if not data.get('meta', {}).get('error')
        )
        failed = len(report_dict['by_symbol']) - successful
        
        logger.info("=" * 80)
        logger.info(f"REPORT STATISTICS (DDD):")
        logger.info(f"  Total symbols: {len(report_dict['by_symbol'])}")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Failed: {failed}")
        
        # Сигналы
        total_signals = sum(
            len(data.get('signals', []))
            for data in report_dict['by_symbol'].values()
        )
        logger.info(f"  Total signals: {total_signals}")
        
        # Топ сигналов
        high_div_tickers = [
            symbol for symbol, data in report_dict['by_symbol'].items()
            if data.get('dy_pct') and data['dy_pct'] >= self.config.dividend_target_pct
        ]
        if high_div_tickers:
            logger.info(f"  High dividend yield: {', '.join(high_div_tickers)}")
        
        logger.info("=" * 80)
        
        return report_dict
