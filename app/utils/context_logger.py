"""Контекстное логирование для операций с тикерами."""

from contextlib import contextmanager
from typing import Optional
from loguru import logger
import time


@contextmanager
def log_operation(operation: str, ticker: Optional[str] = None, **kwargs):
    """
    Контекстный менеджер для логирования операций.
    
    Args:
        operation: Название операции
        ticker: Тикер (опционально)
        **kwargs: Дополнительный контекст
        
    Usage:
        with log_operation("fetch_quote", ticker="SBER"):
            # ... операция ...
    """
    # Формируем контекст
    context = {"operation": operation}
    if ticker:
        context["ticker"] = ticker
    context.update(kwargs)
    
    # Добавляем контекст
    with logger.contextualize(**context):
        start_time = time.time()
        
        try:
            # Логируем начало
            msg = f"Starting {operation}"
            if ticker:
                msg += f" for {ticker}"
            logger.debug(msg)
            
            yield
            
            # Логируем успех
            elapsed = time.time() - start_time
            msg = f"Completed {operation}"
            if ticker:
                msg += f" for {ticker}"
            msg += f" in {elapsed:.2f}s"
            logger.debug(msg)
            
        except Exception as e:
            # Логируем ошибку
            elapsed = time.time() - start_time
            msg = f"Failed {operation}"
            if ticker:
                msg += f" for {ticker}"
            msg += f" after {elapsed:.2f}s: {e}"
            logger.error(msg)
            raise


class TickerLogger:
    """Логгер с контекстом тикера."""
    
    def __init__(self, ticker: str):
        """
        Инициализация.
        
        Args:
            ticker: Тикер для контекста
        """
        self.ticker = ticker
        self.logger = logger.bind(ticker=ticker)
    
    def info(self, message: str):
        """Info лог."""
        self.logger.info(f"[{self.ticker}] {message}")
    
    def debug(self, message: str):
        """Debug лог."""
        self.logger.debug(f"[{self.ticker}] {message}")
    
    def warning(self, message: str):
        """Warning лог."""
        self.logger.warning(f"[{self.ticker}] {message}")
    
    def error(self, message: str):
        """Error лог."""
        self.logger.error(f"[{self.ticker}] {message}")
    
    def exception(self, message: str):
        """Exception лог с traceback."""
        self.logger.exception(f"[{self.ticker}] {message}")


def get_ticker_logger(ticker: str) -> TickerLogger:
    """
    Создать логгер с контекстом тикера.
    
    Args:
        ticker: Тикер
        
    Returns:
        TickerLogger: Контекстный логгер
    """
    return TickerLogger(ticker)

