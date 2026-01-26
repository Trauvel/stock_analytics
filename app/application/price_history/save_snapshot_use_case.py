"""Use case для сохранения снимка цены в историю."""

from datetime import datetime
from loguru import logger

from app.domain.price_history.entities.price_snapshot import PriceSnapshot
from app.domain.price_history.repositories.price_history_repository import PriceHistoryRepository


class SaveSnapshotUseCase:
    """Use case для сохранения снимка цены."""
    
    def __init__(self, price_history_repository: PriceHistoryRepository):
        """
        Инициализация use case.
        
        Args:
            price_history_repository: Репозиторий для работы с историей цен
        """
        self._price_history_repo = price_history_repository
    
    def execute(
        self,
        symbol: str,
        price: float,
        volume: float = None,
        sma_20: float = None,
        sma_50: float = None,
        sma_200: float = None,
        dy_pct: float = None,
        rsi: float = None,
        atr: float = None,
        timestamp: datetime = None
    ) -> None:
        """
        Выполнить use case - сохранить снимок цены.
        
        Args:
            symbol: Тикер инструмента
            price: Текущая цена
            volume: Объём торгов
            sma_20: SMA за 20 дней
            sma_50: SMA за 50 дней
            sma_200: SMA за 200 дней
            dy_pct: Дивидендная доходность
            rsi: RSI индикатор
            atr: ATR индикатор (волатильность)
            timestamp: Время снимка (если None, используется текущее время)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        snapshot = PriceSnapshot(
            symbol=symbol,
            timestamp=timestamp,
            price=price,
            volume=volume,
            sma_20=sma_20,
            sma_50=sma_50,
            sma_200=sma_200,
            dy_pct=dy_pct,
            rsi=rsi,
            atr=atr
        )
        
        self._price_history_repo.save(snapshot)
        logger.debug(f"Saved price snapshot for {symbol} at {timestamp}")
