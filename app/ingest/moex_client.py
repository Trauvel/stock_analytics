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
            symbol: Тикер инструмента (например, SBER) или ISIN (например, RU000A10AS85)
            
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
            
            # Проверяем, является ли symbol ISIN (начинается с RU, US и т.д. и имеет 12 символов)
            is_isin = len(symbol) == 12 and symbol[:2].isalpha()
            
            if is_isin:
                # Для облигаций (ISIN) используем ISS API напрямую
                return self._get_quote_via_iss(symbol)
            
            # Для обычных тикеров используем moexalgo
            ticker_obj = moexalgo.Ticker(symbol)
            
            # Получаем последние свечи (за последние 5 дней на случай выходных)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5)
            
            candles = ticker_obj.candles(
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                period='1h'
            )
            
            # Проверяем, является ли результат генератором
            if hasattr(candles, '__iter__') and not isinstance(candles, pd.DataFrame):
                # Преобразуем генератор в список, затем в DataFrame
                candles_list = list(candles)
                if not candles_list:
                    raise MOEXClientError(f"No candle data found for {symbol}")
                candles = pd.DataFrame(candles_list)
            
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
    
    def _get_quote_via_iss(self, isin: str) -> Dict[str, Any]:
        """
        Получить котировку облигации через ISS API по ISIN.
        
        Args:
            isin: ISIN код облигации (например, RU000A10AS85)
            
        Returns:
            dict: {
                'price': float,
                'lot': int,
                'board': str
            }
        """
        try:
            import requests
            
            # Сначала получаем SECID по ISIN
            url = f"https://iss.moex.com/iss/securities.json?q={isin}"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                raise MOEXClientError(f"Failed to fetch security info for {isin}: HTTP {response.status_code}")
            
            data = response.json()
            
            # Ищем в результатах
            if 'securities' not in data or 'data' not in data['securities']:
                raise MOEXClientError(f"No security found for ISIN {isin}")
            
            securities = data['securities']['data']
            if not securities:
                raise MOEXClientError(f"No security found for ISIN {isin}")
            
            # Берём первый результат (обычно он правильный)
            secid = securities[0][0]  # Первая колонка - это SECID
            
            logger.info(f"Found SECID {secid} for ISIN {isin}")
            
            # Теперь получаем котировку по SECID
            url = f"https://iss.moex.com/iss/engines/stock/markets/bonds/boards/TQCB/securities/{secid}.json"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                # Пробуем другие доски для облигаций
                boards = ['TQCB', 'TQOB', 'TQIR', 'TQOD']
                for board in boards:
                    url = f"https://iss.moex.com/iss/engines/stock/markets/bonds/boards/{board}/securities/{secid}.json"
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        break
                else:
                    raise MOEXClientError(f"Failed to fetch quote for {isin} (SECID: {secid})")
            
            data = response.json()
            
            # Ищем данные в marketdata
            if 'marketdata' not in data or 'data' not in data['marketdata']:
                raise MOEXClientError(f"No market data for {isin}")
            
            marketdata = data['marketdata']['data']
            if not marketdata:
                raise MOEXClientError(f"No market data for {isin}")
            
            columns = data['marketdata']['columns']
            row = marketdata[0]
            
            # Создаём словарь из колонок и значений
            market_dict = dict(zip(columns, row))
            
            # Пытаемся получить цену из разных полей
            price = None
            for price_field in ['LAST', 'LCURRENTPRICE', 'LEGALCLOSEPRICE', 'CLOSE']:
                if price_field in market_dict and market_dict[price_field] is not None:
                    try:
                        price = float(market_dict[price_field])
                        break
                    except (ValueError, TypeError):
                        continue
            
            if price is None:
                raise MOEXClientError(f"Could not extract price for {isin}")
            
            # Получаем лот из securities или используем дефолт
            lot = 1  # Для облигаций обычно лот = 1
            if 'securities' in data and 'data' in data['securities']:
                sec_columns = data['securities']['columns']
                sec_row = data['securities']['data'][0]
                sec_dict = dict(zip(sec_columns, sec_row))
                if 'LOTSIZE' in sec_dict and sec_dict['LOTSIZE'] is not None:
                    try:
                        lot = int(sec_dict['LOTSIZE'])
                    except (ValueError, TypeError):
                        pass
            
            board = 'TQCB'  # По умолчанию для облигаций
            
            result = {
                'price': price,
                'lot': lot,
                'board': board
            }
            
            logger.info(f"Quote for {isin} (SECID: {secid}): {result}")
            self._sleep_rate_limit()
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching quote via ISS for {isin}: {e}")
            raise MOEXClientError(f"Failed to fetch quote for {isin}: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        reraise=True
    )
    def get_dividends(self, symbol: str) -> float:
        """
        Получить сумму дивидендов за последние 12 месяцев (TTM).
        Для облигаций возвращает купонную доходность в процентах от номинала.
        
        Использует ISS API для получения истории дивидендных выплат или купонной доходности.
        
        Args:
            symbol: Тикер инструмента или ISIN код облигации
            
        Returns:
            float: Сумма дивидендов TTM в рублях (для акций) или купонная доходность в % (для облигаций)
        """
        try:
            # Проверяем, является ли symbol ISIN (облигация)
            is_isin = len(symbol) == 12 and symbol[:2].isalpha()
            
            if is_isin:
                # Для облигаций получаем купонную доходность
                return self._get_coupon_yield_for_bond(symbol)
            
            # Для акций получаем дивиденды
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
    
    def _get_coupon_yield_for_bond(self, isin: str) -> float:
        """
        Получить купонную доходность облигации через ISS API.
        
        Args:
            isin: ISIN код облигации
            
        Returns:
            float: Купонная доходность в процентах годовых (например, 8.5 для 8.5%)
        """
        try:
            import requests
            
            logger.info(f"Fetching coupon yield for bond {isin}")
            
            # Сначала получаем SECID по ISIN
            url = f"https://iss.moex.com/iss/securities.json?q={isin}"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch security info for {isin}: HTTP {response.status_code}")
                self._sleep_rate_limit()
                return 0.0
            
            data = response.json()
            
            if 'securities' not in data or 'data' not in data['securities']:
                logger.warning(f"No security found for ISIN {isin}")
                self._sleep_rate_limit()
                return 0.0
            
            securities = data['securities']['data']
            if not securities:
                logger.warning(f"No security found for ISIN {isin}")
                self._sleep_rate_limit()
                return 0.0
            
            secid = securities[0][0]
            logger.info(f"Found SECID {secid} for ISIN {isin}")
            
            # Пробуем получить купонную доходность из истории купонов
            # Это более надёжный способ для облигаций
            coupon_yield = None
            
            # Метод 1: Получаем последний купон из истории купонов
            try:
                url = f"https://iss.moex.com/iss/securities/{secid}/bondization.json"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'coupons' in data and 'data' in data['coupons']:
                        coupons = data['coupons']['data']
                        if coupons:
                            # Берём последний купон
                            coupon_columns = data['coupons']['columns']
                            last_coupon = dict(zip(coupon_columns, coupons[-1]))
                            
                            # Пробуем получить процент купона
                            if 'couponpercent' in last_coupon and last_coupon['couponpercent'] is not None:
                                try:
                                    coupon_yield = float(last_coupon['couponpercent'])
                                    logger.info(f"Found coupon yield from bondization for {isin}: {coupon_yield}%")
                                except (ValueError, TypeError):
                                    pass
                            
                            # Если нет couponpercent, пробуем рассчитать из couponvalue и facevalue
                            if coupon_yield is None and 'couponvalue' in last_coupon and 'facevalue' in last_coupon:
                                try:
                                    coupon_value = float(last_coupon['couponvalue'])
                                    face_value = float(last_coupon['facevalue'])
                                    if face_value > 0:
                                        # Если есть период купона, учитываем его
                                        if 'coupondate' in last_coupon and 'nextcoupondate' in last_coupon:
                                            # Есть даты, можно рассчитать годовую доходность
                                            coupon_yield = (coupon_value / face_value) * 100
                                        else:
                                            # Просто процент от номинала
                                            coupon_yield = (coupon_value / face_value) * 100
                                        logger.info(f"Calculated coupon yield from coupon value for {isin}: {coupon_yield}%")
                                except (ValueError, TypeError) as e:
                                    logger.debug(f"Could not calculate from coupon value: {e}")
                self._sleep_rate_limit()
            except Exception as e:
                logger.debug(f"Error fetching bondization for {isin}: {e}")
            
            # Метод 2: Получаем информацию об облигации с разных досок
            if coupon_yield is None:
                boards = ['TQCB', 'TQOB', 'TQIR', 'TQOD']
                
                for board in boards:
                    url = f"https://iss.moex.com/iss/engines/stock/markets/bonds/boards/{board}/securities/{secid}.json"
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Ищем в секции securities
                        if 'securities' in data and 'data' in data['securities']:
                            sec_columns = data['securities']['columns']
                            sec_rows = data['securities']['data']
                            
                            if sec_rows:
                                sec_dict = dict(zip(sec_columns, sec_rows[0]))
                                
                                # Пробуем разные поля
                                for field in ['COUPONPERCENTAGE', 'COUPONPERCENT', 'COUPONRATE']:
                                    if field in sec_dict and sec_dict[field] is not None:
                                        try:
                                            coupon_yield = float(sec_dict[field])
                                            logger.info(f"Found coupon yield from {field} for {isin}: {coupon_yield}%")
                                            break
                                        except (ValueError, TypeError):
                                            pass
                                
                                if coupon_yield is not None:
                                    break
                        
                        # Ищем в секции marketdata
                        if coupon_yield is None and 'marketdata' in data and 'data' in data['marketdata']:
                            md_columns = data['marketdata']['columns']
                            md_rows = data['marketdata']['data']
                            
                            if md_rows:
                                md_dict = dict(zip(md_columns, md_rows[0]))
                                
                                for field in ['YIELDATWAP', 'YIELD', 'YIELDTOOFFER']:
                                    if field in md_dict and md_dict[field] is not None:
                                        try:
                                            coupon_yield = float(md_dict[field])
                                            logger.info(f"Found yield from marketdata {field} for {isin}: {coupon_yield}%")
                                            break
                                        except (ValueError, TypeError):
                                            pass
                        
                        if coupon_yield is not None:
                            break
                    
                    self._sleep_rate_limit()
            
            # Метод 3: Пробуем получить из базовой информации о ценной бумаге
            if coupon_yield is None:
                try:
                    url = f"https://iss.moex.com/iss/securities/{secid}.json"
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if 'description' in data and 'data' in data['description']:
                            desc_columns = data['description']['columns']
                            desc_rows = data['description']['data']
                            
                            if desc_rows:
                                desc_dict = dict(zip(desc_columns, desc_rows[0]))
                                
                                # Ищем процент купона в описании
                                for field in ['COUPONPERCENTAGE', 'COUPONPERCENT', 'COUPONRATE']:
                                    if field in desc_dict and desc_dict[field] is not None:
                                        try:
                                            coupon_yield = float(desc_dict[field])
                                            logger.info(f"Found coupon yield from description {field} for {isin}: {coupon_yield}%")
                                            break
                                        except (ValueError, TypeError):
                                            pass
                    
                    self._sleep_rate_limit()
                except Exception as e:
                    logger.debug(f"Error fetching security description for {isin}: {e}")
            
            if coupon_yield is None:
                logger.warning(f"Could not find coupon yield for {isin} after trying all methods")
                self._sleep_rate_limit()
                return 0.0
            
            self._sleep_rate_limit()
            return coupon_yield
            
        except Exception as e:
            logger.warning(f"Error fetching coupon yield for {isin}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            self._sleep_rate_limit()
            return 0.0
    
    def _get_candles_via_iss(
        self,
        isin: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Получить свечи облигации через ISS API по ISIN.
        
        Args:
            isin: ISIN код облигации
            start_date: Начальная дата
            end_date: Конечная дата
            
        Returns:
            pd.DataFrame: Свечи с колонками [open, high, low, close, volume, begin, end]
        """
        try:
            import requests
            
            # Сначала получаем SECID по ISIN
            url = f"https://iss.moex.com/iss/securities.json?q={isin}"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                raise MOEXClientError(f"Failed to fetch security info for {isin}: HTTP {response.status_code}")
            
            data = response.json()
            
            if 'securities' not in data or 'data' not in data['securities']:
                raise MOEXClientError(f"No security found for ISIN {isin}")
            
            securities = data['securities']['data']
            if not securities:
                raise MOEXClientError(f"No security found for ISIN {isin}")
            
            secid = securities[0][0]
            logger.info(f"Found SECID {secid} for ISIN {isin}")
            
            # Получаем свечи через ISS API
            # Формат: https://iss.moex.com/iss/engines/stock/markets/bonds/boards/TQCB/securities/{secid}/candles.json
            boards = ['TQCB', 'TQOB', 'TQIR', 'TQOD']
            candles_data = None
            
            for board in boards:
                url = (
                    f"https://iss.moex.com/iss/engines/stock/markets/bonds/boards/{board}/"
                    f"securities/{secid}/candles.json"
                    f"?from={start_date.strftime('%Y-%m-%d')}"
                    f"&till={end_date.strftime('%Y-%m-%d')}"
                    f"&interval=24"
                )
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'candles' in data and 'data' in data['candles'] and data['candles']['data']:
                        candles_data = data
                        break
            
            if not candles_data:
                raise MOEXClientError(f"No candles data for {isin} (SECID: {secid})")
            
            # Преобразуем в DataFrame
            columns = candles_data['candles']['columns']
            rows = candles_data['candles']['data']
            
            df = pd.DataFrame(rows, columns=columns)
            
            # Маппинг колонок ISS API в наш формат
            # ISS API возвращает: open, close, high, low, value, volume, begin, end
            column_mapping = {
                'begin': 'begin',
                'end': 'end',
                'open': 'open',
                'close': 'close',
                'high': 'high',
                'low': 'low',
                'volume': 'volume'
            }
            
            # Проверяем наличие нужных колонок
            available_cols = set(df.columns)
            required_cols = set(column_mapping.keys())
            
            if not required_cols.issubset(available_cols):
                missing = required_cols - available_cols
                raise MOEXClientError(f"Missing columns in candles for {isin}: {missing}")
            
            # Выбираем нужные колонки и переименовываем
            result = df[list(column_mapping.keys())].copy()
            
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
            
            logger.info(f"Fetched {len(result)} candles for {isin} via ISS API")
            self._sleep_rate_limit()
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching candles via ISS for {isin}: {e}")
            raise MOEXClientError(f"Failed to fetch candles for {isin}: {e}")
    
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
            
            # Проверяем, является ли symbol ISIN
            is_isin = len(symbol) == 12 and symbol[:2].isalpha()
            
            if is_isin:
                # Для облигаций (ISIN) используем ISS API
                candles = self._get_candles_via_iss(symbol, start_date, end_date)
            else:
                # Для обычных тикеров используем moexalgo
                ticker_obj = moexalgo.Ticker(symbol)
                
                # Используем hourly candles (период 60) вместо daily
                candles = ticker_obj.candles(
                    start=start_date.strftime('%Y-%m-%d'),
                    end=end_date.strftime('%Y-%m-%d'),
                    period=60  # 1 hour
                )
                
                # Проверяем, является ли результат генератором
                if hasattr(candles, '__iter__') and not isinstance(candles, pd.DataFrame):
                    # Преобразуем генератор в список, затем в DataFrame
                    candles_list = list(candles)
                    if not candles_list:
                        raise MOEXClientError(f"No candles data for {symbol}")
                    candles = pd.DataFrame(candles_list)
            
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

