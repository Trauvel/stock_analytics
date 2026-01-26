"""Реализация репозитория истории цен через SQLite."""

import sqlite3
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta
from loguru import logger

from app.domain.price_history.entities.price_snapshot import PriceSnapshot
from app.domain.price_history.repositories.price_history_repository import PriceHistoryRepository


class PriceHistoryRepositoryImpl(PriceHistoryRepository):
    """Реализация репозитория через SQLite для эффективной работы с временными рядами."""
    
    def __init__(self, db_path: str = "data/price_history.db"):
        """
        Инициализация репозитория.
        
        Args:
            db_path: Путь к файлу базы данных SQLite
        """
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Создаём таблицу при инициализации
        self._init_database()
    
    def _init_database(self) -> None:
        """Инициализировать базу данных и создать таблицу, если её нет."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()
                
                # Создаём таблицу для снимков цен
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS price_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        price REAL NOT NULL,
                        volume REAL,
                        sma_20 REAL,
                        sma_50 REAL,
                        sma_200 REAL,
                        dy_pct REAL,
                        rsi REAL,
                        atr REAL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(symbol, timestamp)
                    )
                """)
                
                # Создаём индексы для быстрого поиска
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_symbol_timestamp 
                    ON price_snapshots(symbol, timestamp)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp 
                    ON price_snapshots(timestamp)
                """)
                
                conn.commit()
                logger.debug(f"Price history database initialized at {self._db_path}")
                
        except Exception as e:
            logger.error(f"Error initializing price history database: {e}")
            raise
    
    def save(self, snapshot: PriceSnapshot) -> None:
        """Сохранить снимок цены."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()
                
                # Используем INSERT OR REPLACE для обновления существующих записей
                cursor.execute("""
                    INSERT OR REPLACE INTO price_snapshots 
                    (symbol, timestamp, price, volume, sma_20, sma_50, sma_200, dy_pct, rsi, atr)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    snapshot.symbol,
                    snapshot.timestamp.isoformat(),
                    snapshot.price,
                    snapshot.volume,
                    snapshot.sma_20,
                    snapshot.sma_50,
                    snapshot.sma_200,
                    snapshot.dy_pct,
                    snapshot.rsi,
                    snapshot.atr
                ))
                
                conn.commit()
                logger.debug(f"Saved price snapshot for {snapshot.symbol} at {snapshot.timestamp}")
                
        except Exception as e:
            logger.error(f"Error saving price snapshot: {e}")
            raise
    
    def get_latest(self, symbol: str) -> Optional[PriceSnapshot]:
        """Получить последний снимок для инструмента."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM price_snapshots
                    WHERE symbol = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (symbol,))
                
                row = cursor.fetchone()
                if row:
                    return self._row_to_snapshot(row)
                return None
                
        except Exception as e:
            logger.error(f"Error getting latest snapshot for {symbol}: {e}")
            return None
    
    def get_at_time(
        self, 
        symbol: str, 
        timestamp: datetime
    ) -> Optional[PriceSnapshot]:
        """Получить снимок для инструмента на определённое время."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Ищем точное совпадение или ближайший снимок
                cursor.execute("""
                    SELECT * FROM price_snapshots
                    WHERE symbol = ? AND timestamp = ?
                    LIMIT 1
                """, (symbol, timestamp.isoformat()))
                
                row = cursor.fetchone()
                if row:
                    return self._row_to_snapshot(row)
                return None
                
        except Exception as e:
            logger.error(f"Error getting snapshot at time for {symbol}: {e}")
            return None
    
    def get_in_range(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[PriceSnapshot]:
        """Получить все снимки для инструмента в диапазоне времени."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM price_snapshots
                    WHERE symbol = ? 
                    AND timestamp >= ? 
                    AND timestamp <= ?
                    ORDER BY timestamp ASC
                """, (
                    symbol,
                    start_time.isoformat(),
                    end_time.isoformat()
                ))
                
                rows = cursor.fetchall()
                return [self._row_to_snapshot(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting snapshots in range for {symbol}: {e}")
            return []
    
    def get_before_time(
        self,
        symbol: str,
        timestamp: datetime,
        hours_ago: float
    ) -> Optional[PriceSnapshot]:
        """Получить снимок, который был создан примерно N часов назад."""
        try:
            target_time = timestamp - timedelta(hours=hours_ago)
            
            # Ищем снимок в диапазоне ±30 минут от целевого времени
            start_time = target_time - timedelta(minutes=30)
            end_time = target_time + timedelta(minutes=30)
            
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Ищем ближайший снимок к целевому времени
                cursor.execute("""
                    SELECT * FROM price_snapshots
                    WHERE symbol = ?
                    AND timestamp >= ?
                    AND timestamp <= ?
                    ORDER BY ABS(julianday(timestamp) - julianday(?)) ASC
                    LIMIT 1
                """, (
                    symbol,
                    start_time.isoformat(),
                    end_time.isoformat(),
                    target_time.isoformat()
                ))
                
                row = cursor.fetchone()
                if row:
                    return self._row_to_snapshot(row)
                return None
                
        except Exception as e:
            logger.error(f"Error getting snapshot before time for {symbol}: {e}")
            return None
    
    def cleanup_old(self, days_to_keep: int = 30) -> int:
        """Удалить старые снимки, оставив только последние N дней."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM price_snapshots
                    WHERE timestamp < ?
                """, (cutoff_date.isoformat(),))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old price snapshots (older than {days_to_keep} days)")
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"Error cleaning up old snapshots: {e}")
            return 0
    
    def _row_to_snapshot(self, row: sqlite3.Row) -> PriceSnapshot:
        """Преобразовать строку из БД в PriceSnapshot."""
        return PriceSnapshot(
            symbol=row['symbol'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            price=row['price'],
            volume=row['volume'],
            sma_20=row['sma_20'],
            sma_50=row['sma_50'],
            sma_200=row['sma_200'],
            dy_pct=row['dy_pct'],
            rsi=row['rsi'],
            atr=row.get('atr')
        )
