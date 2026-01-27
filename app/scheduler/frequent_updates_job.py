"""Планировщик для частых обновлений данных (каждые 3-4 часа)."""

from datetime import datetime
from typing import Optional, List
from loguru import logger

from app.config.loader import get_config
from app.config.monitoring_loader import load_monitoring_config
from app.ingest.moex_client import MOEXClient
# Используем DDD версию MetricsCalculator
from app.domain.stock_analysis.services.metrics_calculator import MetricsCalculator
from app.domain.price_history.repositories.price_history_repository import PriceHistoryRepository
from app.application.price_history.save_snapshot_use_case import SaveSnapshotUseCase
from app.domain.price_history.services.change_analyzer import ChangeAnalyzer
from app.application.price_history.analyze_changes_use_case import AnalyzeChangesUseCase
from app.infrastructure.telegram.notifier import TelegramNotifier
from app.application.telegram.send_notification_use_case import SendNotificationUseCase
from app.utils.job_journal import append_jsonl


class FrequentUpdatesScheduler:
    """Планировщик для частых обновлений данных по инструментам из портфеля."""
    
    def __init__(
        self,
        price_history_repository: PriceHistoryRepository,
        update_interval_hours: int = 3
    ):
        """
        Инициализация планировщика.
        
        Args:
            price_history_repository: Репозиторий для сохранения истории
            update_interval_hours: Интервал обновления в часах (по умолчанию 3)
        """
        self.config = get_config()
        self.monitoring_cfg = load_monitoring_config()
        self.client = MOEXClient()
        # Используем DDD версию MetricsCalculator
        self.calculator = MetricsCalculator(dividend_target_pct=self.config.dividend_target_pct)
        self.price_history_repo = price_history_repository
        self.update_interval_hours = update_interval_hours

        mon = (self.monitoring_cfg or {}).get("monitoring", {}) or {}
        self.price_change_threshold_pct = float(mon.get("price_change_threshold_pct", 3.0))
        self.volume_spike_threshold = float(mon.get("volume_spike_threshold", 2.0))
        self.use_adaptive_thresholds = bool(mon.get("use_adaptive_thresholds", True))
        self.filter_trading_hours = bool(mon.get("filter_trading_hours", True))
        self.compare_periods = [
            float(p.get("hours"))
            for p in (mon.get("compare_periods") or [{"hours": 3}, {"hours": 24}])
            if isinstance(p, dict) and p.get("hours") is not None
        ] or [3.0, 24.0]

        # Свечи: кэш/глубина/период
        self.candles_cache_enabled = bool(mon.get("candles_cache_enabled", True))
        self.candles_cache_refresh_days = int(mon.get("candles_cache_refresh_days", 7))
        self.candles_period_minutes = int(mon.get("candles_period_minutes", 60))
        self.candles_days_frequent = int(mon.get("candles_days_frequent", 400))

        notif = (self.monitoring_cfg or {}).get("notifications", {}) or {}
        self.group_notifications = bool(notif.get("group_notifications", True))
        self.min_priority = str(notif.get("min_priority", "LOW")).upper()
        
        # Инициализируем use cases
        self.save_snapshot_use_case = SaveSnapshotUseCase(price_history_repository)
        
        # Инициализируем анализатор изменений
        self.change_analyzer = ChangeAnalyzer(
            price_history_repository=price_history_repository,
            price_change_threshold_pct=self.price_change_threshold_pct,
            volume_spike_threshold=self.volume_spike_threshold,
            use_adaptive_thresholds=self.use_adaptive_thresholds
        )
        
        self.analyze_changes_use_case = AnalyzeChangesUseCase(self.change_analyzer)
        
        # Инициализируем Telegram notifier (опционально)
        try:
            self.telegram_notifier = TelegramNotifier()
            self.send_notification_use_case = SendNotificationUseCase(self.telegram_notifier)
        except Exception as e:
            logger.warning(f"Could not initialize Telegram notifier: {e}")
            self.telegram_notifier = None
            self.send_notification_use_case = None
    
    def _load_portfolio_tickers(self) -> List[str]:
        """
        Загрузить тикеры из всех портфелей пользователя.
        
        Returns:
            List[str]: Список тикеров из всех портфелей
        """
        try:
            from pathlib import Path
            import json
            
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
    
    def update_portfolio_tickers(self) -> dict:
        """
        Обновить данные по всем тикерам из портфеля.
        
        Returns:
            Dict с результатами обновления
        """
        run_id = f"frequent_updates:{datetime.now().isoformat()}"
        append_jsonl(
            "data/job_runs/frequent_updates.jsonl",
            {
                "job": "frequent_updates",
                "event": "start",
                "run_id": run_id,
                "interval_hours": self.update_interval_hours,
                "compare_periods": self.compare_periods,
                "filter_trading_hours": self.filter_trading_hours,
                "candles_days": self.candles_days_frequent,
                "candles_cache": self.candles_cache_enabled,
            },
        )

        logger.info("=" * 80)
        logger.info("STARTING FREQUENT UPDATE JOB")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        
        # Получаем тикеры из портфеля
        tickers = self._load_portfolio_tickers()
        
        if not tickers:
            logger.warning("No tickers found in portfolio. Skipping update.")
            append_jsonl(
                "data/job_runs/frequent_updates.jsonl",
                {
                    "job": "frequent_updates",
                    "event": "finish",
                    "run_id": run_id,
                    "success": False,
                    "processed": 0,
                    "successful": 0,
                    "failed": 0,
                    "error": "No tickers in portfolio",
                },
            )
            return {
                'success': False,
                'processed': 0,
                'successful': 0,
                'failed': 0,
                'error': 'No tickers in portfolio'
            }
        
        logger.info(f"Updating {len(tickers)} tickers from portfolio: {', '.join(tickers)}")
        
        successful = 0
        failed = 0
        
        for symbol in tickers:
            try:
                logger.info(f"Updating {symbol}...")
                
                # Получаем данные с MOEX
                quote = self.client.get_quote(symbol)
                divs = self.client.get_dividends(symbol)
                if self.candles_cache_enabled:
                    candles = self.client.get_candles_cached(
                        symbol,
                        days=self.candles_days_frequent,
                        refresh_days=self.candles_cache_refresh_days,
                        period_minutes=self.candles_period_minutes,
                    )
                else:
                    candles = self.client.get_candles(
                        symbol,
                        days=self.candles_days_frequent,
                        period_minutes=self.candles_period_minutes,
                    )
                
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
                
                # Сохраняем snapshot
                self.save_snapshot_use_case.execute(
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
                
                successful += 1
                logger.info(f"✓ Successfully updated {symbol}")
                
            except Exception as e:
                failed += 1
                logger.error(f"✗ Failed to update {symbol}: {e}")
                continue
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        logger.info("=" * 80)
        logger.info("FREQUENT UPDATE JOB COMPLETED")
        logger.info(f"  Duration: {elapsed:.1f}s")
        logger.info(f"  Processed: {len(tickers)}")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Failed: {failed}")
        logger.info("=" * 80)
        
        # Анализируем изменения и генерируем сигналы
        signals = []
        if successful > 0:
            try:
                logger.info("Analyzing price changes...")
                signals = self.analyze_changes_use_case.execute(
                    symbols=[t for t in tickers],  # Только успешно обновлённые
                    compare_periods=self.compare_periods,
                    filter_trading_hours=self.filter_trading_hours,
                )
                logger.info(f"Found {len(signals)} significant changes")
                
                # Отправляем уведомления в Telegram (если есть сигналы и бот настроен)
                if signals and self.send_notification_use_case:
                    try:
                        # Фильтр по минимальному приоритету (LOW/MEDIUM/HIGH)
                        try:
                            from app.domain.price_history.value_objects.change_signal import SignalPriority
                            order = {
                                SignalPriority.LOW: 0,
                                SignalPriority.MEDIUM: 1,
                                SignalPriority.HIGH: 2,
                            }
                            min_p = SignalPriority(self.min_priority)
                            signals_to_send = [s for s in signals if order.get(s.priority, 0) >= order[min_p]]
                        except Exception:
                            signals_to_send = signals

                        sent_count = self.send_notification_use_case.execute(
                            signals_to_send,
                            group=self.group_notifications,
                        )
                        logger.info(f"Sent {sent_count} Telegram notification(s)")
                    except Exception as e:
                        logger.error(f"Error sending Telegram notifications: {e}")
                        
            except Exception as e:
                logger.error(f"Error analyzing changes: {e}")

        append_jsonl(
            "data/job_runs/frequent_updates.jsonl",
            {
                "job": "frequent_updates",
                "event": "finish",
                "run_id": run_id,
                "success": True,
                "processed": len(tickers),
                "successful": successful,
                "failed": failed,
                "duration_seconds": elapsed,
                "signals_count": len(signals),
            },
        )
        
        return {
            'success': True,
            'processed': len(tickers),
            'successful': successful,
            'failed': failed,
            'duration_seconds': elapsed,
            'signals': [s.to_dict() for s in signals]
        }
