"""Реализация репозитория акций через MOEX API."""

from typing import List, Optional
from datetime import datetime
import pandas as pd
from loguru import logger

from app.domain.stock_analysis.entities.stock import Stock
from app.domain.stock_analysis.repositories.stock_repository import StockRepository
from app.domain.stock_analysis.value_objects.price import Price
from app.domain.stock_analysis.value_objects.dividend_yield import DividendYield
from app.ingest.moex_client import MOEXClient, MOEXClientError


class StockRepositoryImpl(StockRepository):
    """Реализация репозитория через MOEX API."""
    
    def __init__(self, moex_client: MOEXClient):
        """
        Инициализация репозитория.
        
        Args:
            moex_client: Клиент для работы с MOEX API
        """
        self._client = moex_client
    
    async def get_by_symbol(self, symbol: str) -> Optional[Stock]:
        """
        Получить акцию по тикеру.
        
        Args:
            symbol: Тикер акции
            
        Returns:
            Stock или None если не удалось получить данные
        """
        try:
            logger.info(f"Fetching stock data for {symbol}")
            
            # Получаем данные с MOEX (синхронные вызовы, но обёрнуты в async для будущей миграции)
            quote = self._client.get_quote(symbol)
            divs = self._client.get_dividends(symbol)
            # candles не нужны здесь, они будут получены в use case
            
            # Создаём доменную сущность
            price = Price.from_float(quote['price'])
            dividend_yield = None
            if price and divs > 0:
                dividend_yield = DividendYield.from_float((divs / price.value) * 100)
            
            stock = Stock(
                symbol=symbol,
                price=price,
                dividend_yield=dividend_yield,
                sma_20=None,  # Будет рассчитано в сервисе
                sma_50=None,
                sma_200=None,
                high_52w=None,
                low_52w=None,
                signals=[],  # Будет сгенерировано в сервисе
                lot=quote.get('lot'),
                div_ttm=divs,
                updated_at=datetime.now()
            )
            
            logger.info(f"Successfully fetched stock data for {symbol}")
            return stock
            
        except MOEXClientError as e:
            logger.error(f"MOEX client error for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching stock data for {symbol}: {e}")
            return None
    
    async def get_all(self, symbols: List[str]) -> List[Stock]:
        """
        Получить список акций по тикерам.
        
        Args:
            symbols: Список тикеров
            
        Returns:
            Список акций (может быть короче symbols, если некоторые не найдены)
        """
        stocks = []
        
        for symbol in symbols:
            stock = await self.get_by_symbol(symbol)
            if stock:
                stocks.append(stock)
        
        return stocks
    
    async def save(self, stock: Stock) -> None:
        """
        Сохранить акцию.
        
        Примечание: В текущей реализации сохранение не требуется,
        так как данные берутся из внешнего API.
        """
        logger.warning(f"Save operation not implemented for {stock.symbol}")
        # В будущем можно добавить кеширование в локальное хранилище
        pass
