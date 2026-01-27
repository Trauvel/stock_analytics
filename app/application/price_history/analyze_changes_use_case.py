"""Use case для анализа изменений цен."""

from typing import List
from loguru import logger

from app.domain.price_history.services.change_analyzer import ChangeAnalyzer
from app.domain.price_history.value_objects.change_signal import ChangeSignal


class AnalyzeChangesUseCase:
    """Use case для анализа изменений цен и генерации сигналов."""
    
    def __init__(self, change_analyzer: ChangeAnalyzer):
        """
        Инициализация use case.
        
        Args:
            change_analyzer: Анализатор изменений
        """
        self._change_analyzer = change_analyzer
    
    def execute(
        self,
        symbols: List[str],
        compare_periods: List[float] = None,
        filter_trading_hours: bool = True,
    ) -> List[ChangeSignal]:
        """
        Выполнить use case - проанализировать изменения для списка инструментов.
        
        Args:
            symbols: Список тикеров для анализа
            compare_periods: Периоды для сравнения в часах (по умолчанию [3, 24])
            
        Returns:
            List[ChangeSignal]: Список сигналов об изменениях
        """
        logger.info(f"Analyzing changes for {len(symbols)} symbols")
        
        signals = self._change_analyzer.detect_significant_changes(
            symbols=symbols,
            compare_periods=compare_periods,
            filter_trading_hours=filter_trading_hours,
        )
        
        logger.info(f"Found {len(signals)} significant changes")
        
        return signals
