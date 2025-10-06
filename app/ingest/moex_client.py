"""Клиент для получения данных с Московской биржи через moexalgo."""

import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

import pandas as pd
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import moexalgo

from app.config.loader import get_config


class MOEXClientError(Exception):
    """Базовое исключение для ошибок клиента MOEX."""
    pass


class MOEXClient:
    """Клиент для работы с данными MOEX через moexalgo."""
    
    def __init__(self, rate_limit_sleep: Optional[float] = None):
        """
        Инициализация клиента.
        
        Args:
            rate_limit_sleep: Пауза между запросами в секундах (если None, берётся из конфига)
        """
        self.config = get_config()
        self.rate_limit_sleep = rate_limit_sleep or self.config.rate_limit.per_symbol_sleep_sec
        
    def _sleep_rate_limit(self):
        """Пауза для соблюдения rate limit."""
        if self.rate_limit_sleep > 0:
            time.sleep(self.rate_limit_sleep)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True
    )
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Получить текущую котировку по тикеру.
        
        Args:
            symbol: Тикер инструмента (например, SBER)
            
        Returns:
            dict: {
                'price': float,       # Текущая цена
                'lot': int,          # Размер лота
                'board': str         # Режим торгов
            }
            
        Raises:
            MOEXClientError: Если не удалось получить данные
        """
        try:
            logger.info(f"Fetching quote for {symbol}")
            
            # Получаем данные через Ticker API moexalgo
            ticker_obj = moexalgo.Ticker(symbol)
            
            # Получаем последние свечи (за последние 5 дней на случай выходных)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5)
            
            candles = ticker_obj.candles(
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                period='1h'
            )
            
            if candles.empty:
                raise MOEXClientError(f"No candle data found for {symbol}")
            
            # Берём последнюю свечу
            latest = candles.iloc[-1]
            price = float(latest['close'])
            
            # Получаем информацию о лоте
            # Для большинства акций на ММВБ лот = 10
            lot = 10
            board = 'TQBR'
            
            result = {
                'price': price,
                'lot': lot,
                'board': board
            }
            
            logger.info(f"Quote for {symbol}: {result}")
            self._sleep_rate_limit()
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            raise MOEXClientError(f"Failed to fetch quote for {symbol}: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True
    )
    def get_dividends(self, symbol: str) -> float:
        """
        Получить сумму дивидендов за последние 12 месяцев (TTM).
        
        Использует ISS API для получения истории дивидендных выплат.
        
        Args:
            symbol: Тикер инструмента
            
        Returns:
            float: Сумма дивидендов TTM (0 если дивидендов нет)
        """
        try:
            logger.info(f"Fetching dividends for {symbol}")
            
            # Получаем данные по дивидендам через ISS API
            # URL: https://iss.moex.com/iss/securities/{SECID}/dividends.json
            import requests
            
            url = f"https://iss.moex.com/iss/securities/{symbol}/dividends.json"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch dividends for {symbol}: HTTP {response.status_code}")
                self._sleep_rate_limit()
                return 0.0
            
            data = response.json()
            
            # Проверяем наличие данных
            if 'dividends' not in data or 'data' not in data['dividends']:
                logger.warning(f"No dividends data structure for {symbol}")
                self._sleep_rate_limit()
                return 0.0
            
            columns = data['dividends']['columns']
            rows = data['dividends']['data']
            
            if not rows:
                logger.info(f"No dividend history for {symbol}")
                self._sleep_rate_limit()
                return 0.0
            
            # Преобразуем в DataFrame для удобства
            df = pd.DataFrame(rows, columns=columns)
            
            # Находим индексы нужных колонок
            date_col = 'registryclosedate'
            value_col = 'value'
            
            if date_col not in df.columns or value_col not in df.columns:
                logger.warning(f"Missing required columns in dividends for {symbol}")
                self._sleep_rate_limit()
                return 0.0
            
            # Преобразуем даты
            df[date_col] = pd.to_datetime(df[date_col])
            
            # Фильтруем по последним 12 месяцам
            cutoff_date = datetime.now() - timedelta(days=365)
            recent_divs = df[df[date_col] >= cutoff_date]
            
            if recent_divs.empty:
                logger.info(f"No recent dividends (last 12 months) for {symbol}")
                self._sleep_rate_limit()
                return 0.0
            
            # Суммируем дивиденды
            total = float(recent_divs[value_col].sum())
            
            logger.info(f"Dividends TTM for {symbol}: {total} RUB ({len(recent_divs)} payments)")
            self._sleep_rate_limit()
            
            return total
            
        except Exception as e:
            logger.warning(f"Error fetching dividends for {symbol}: {e}")
            # Дивиденды не критичны, возвращаем 0
            self._sleep_rate_limit()
            return 0.0
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True
    )
    def get_candles(
        self,
        symbol: str,
        days: int = 400,
        interval: str = '24h'
    ) -> pd.DataFrame:
        """
        Получить исторические свечи по тикеру.
        
        Args:
            symbol: Тикер инструмента
            days: Количество дней истории (по умолчанию 400 для 52 недель + запас)
            interval: Интервал свечей ('24h' для дневных)
            
        Returns:
            pd.DataFrame: Свечи с колонками [open, high, low, close, volume, begin, end]
            
        Raises:
            MOEXClientError: Если не удалось получить данные
        """
        try:
            logger.info(f"Fetching {days} days of candles for {symbol}")
            
            # Вычисляем даты
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Получаем свечи через Ticker API
            ticker_obj = moexalgo.Ticker(symbol)
            
            # Используем hourly candles (период 60) вместо daily
            # TODO: Найти корректный способ получения дневных свечей
            candles = ticker_obj.candles(
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                period=60  # 1 hour
            )
            
            if candles.empty:
                raise MOEXClientError(f"No candles data for {symbol}")
            
            # Нормализуем колонки
            # moexalgo возвращает: begin, end, open, close, high, low, value, volume
            required_columns = ['open', 'high', 'low', 'close', 'volume', 'begin', 'end']
            
            for col in required_columns:
                if col not in candles.columns:
                    raise MOEXClientError(f"Missing column {col} in candles for {symbol}")
            
            # Оставляем только нужные колонки
            result = candles[required_columns].copy()
            
            # Преобразуем типы
            result['open'] = result['open'].astype(float)
            result['high'] = result['high'].astype(float)
            result['low'] = result['low'].astype(float)
            result['close'] = result['close'].astype(float)
            result['volume'] = result['volume'].astype(int)
            
            # Преобразуем даты
            result['begin'] = pd.to_datetime(result['begin'])
            result['end'] = pd.to_datetime(result['end'])
            
            # Сортируем по дате
            result = result.sort_values('begin').reset_index(drop=True)
            
            logger.info(f"Fetched {len(result)} candles for {symbol}")
            self._sleep_rate_limit()
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching candles for {symbol}: {e}")
            raise MOEXClientError(f"Failed to fetch candles for {symbol}: {e}")
    
    def get_all_data(self, symbol: str) -> Dict[str, Any]:
        """
        Получить все данные по тикеру (котировка, дивиденды, свечи).
        
        Args:
            symbol: Тикер инструмента
            
        Returns:
            dict: {
                'quote': {...},
                'dividends': float,
                'candles': pd.DataFrame,
                'error': str or None
            }
        """
        result = {
            'quote': None,
            'dividends': 0.0,
            'candles': None,
            'error': None
        }
        
        try:
            # Получаем котировку
            result['quote'] = self.get_quote(symbol)
            
            # Получаем дивиденды
            result['dividends'] = self.get_dividends(symbol)
            
            # Получаем свечи
            result['candles'] = self.get_candles(symbol)
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error fetching all data for {symbol}: {e}")
        
        return result

