"""Модуль для сохранения и загрузки данных."""

from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

import pandas as pd
import orjson
from loguru import logger


class StorageError(Exception):
    """Базовое исключение для ошибок хранилища."""
    pass


def ensure_dir(path: Path) -> None:
    """
    Создать директорию, если её не существует.
    
    Args:
        path: Путь к директории или файлу (создаётся родительская директория)
    """
    if path.suffix:  # Это файл
        path.parent.mkdir(parents=True, exist_ok=True)
    else:  # Это директория
        path.mkdir(parents=True, exist_ok=True)


def save_json(path: str | Path, data: Dict[str, Any]) -> None:
    """
    Сохранить данные в JSON файл используя orjson для скорости.
    
    Args:
        path: Путь к файлу
        data: Данные для сохранения
        
    Raises:
        StorageError: Если не удалось сохранить файл
    """
    try:
        path = Path(path)
        ensure_dir(path)
        
        # orjson.dumps возвращает bytes, поэтому пишем в бинарном режиме
        json_bytes = orjson.dumps(
            data,
            option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE
        )
        
        with open(path, 'wb') as f:
            f.write(json_bytes)
        
        logger.debug(f"Saved JSON to {path}")
        
    except Exception as e:
        logger.error(f"Failed to save JSON to {path}: {e}")
        raise StorageError(f"Failed to save JSON: {e}")


def load_json(path: str | Path) -> Dict[str, Any]:
    """
    Загрузить данные из JSON файла.
    
    Args:
        path: Путь к файлу
        
    Returns:
        Dict[str, Any]: Загруженные данные
        
    Raises:
        StorageError: Если не удалось загрузить файл
    """
    try:
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        with open(path, 'rb') as f:
            data = orjson.loads(f.read())
        
        logger.debug(f"Loaded JSON from {path}")
        return data
        
    except Exception as e:
        logger.error(f"Failed to load JSON from {path}: {e}")
        raise StorageError(f"Failed to load JSON: {e}")


def save_table_parquet(path: str | Path, df: pd.DataFrame) -> None:
    """
    Сохранить DataFrame в Parquet файл.
    
    Args:
        path: Путь к файлу
        df: DataFrame для сохранения
        
    Raises:
        StorageError: Если не удалось сохранить файл
    """
    try:
        path = Path(path)
        ensure_dir(path)
        
        df.to_parquet(path, engine='pyarrow', compression='snappy', index=False)
        
        logger.debug(f"Saved Parquet table to {path} ({len(df)} rows)")
        
    except Exception as e:
        logger.error(f"Failed to save Parquet to {path}: {e}")
        raise StorageError(f"Failed to save Parquet: {e}")


def load_table_parquet(path: str | Path) -> pd.DataFrame:
    """
    Загрузить DataFrame из Parquet файла.
    
    Args:
        path: Путь к файлу
        
    Returns:
        pd.DataFrame: Загруженные данные
        
    Raises:
        StorageError: Если не удалось загрузить файл
    """
    try:
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        df = pd.read_parquet(path, engine='pyarrow')
        
        logger.debug(f"Loaded Parquet table from {path} ({len(df)} rows)")
        return df
        
    except Exception as e:
        logger.error(f"Failed to load Parquet from {path}: {e}")
        raise StorageError(f"Failed to load Parquet: {e}")


def save_candles(symbol: str, df: pd.DataFrame, base_dir: str | Path = "data/raw") -> Path:
    """
    Сохранить свечи для тикера.
    
    Args:
        symbol: Тикер инструмента
        df: DataFrame со свечами
        base_dir: Базовая директория для сырых данных
        
    Returns:
        Path: Путь к сохранённому файлу
    """
    base_dir = Path(base_dir)
    file_path = base_dir / symbol / "candles.parquet"
    
    save_table_parquet(file_path, df)
    
    logger.info(f"Saved {len(df)} candles for {symbol} to {file_path}")
    return file_path


def load_candles(symbol: str, base_dir: str | Path = "data/raw") -> Optional[pd.DataFrame]:
    """
    Загрузить свечи для тикера.
    
    Args:
        symbol: Тикер инструмента
        base_dir: Базовая директория для сырых данных
        
    Returns:
        Optional[pd.DataFrame]: DataFrame со свечами или None если файл не найден
    """
    base_dir = Path(base_dir)
    file_path = base_dir / symbol / "candles.parquet"
    
    if not file_path.exists():
        logger.warning(f"No candles file found for {symbol} at {file_path}")
        return None
    
    df = load_table_parquet(file_path)
    logger.info(f"Loaded {len(df)} candles for {symbol} from {file_path}")
    
    return df


def save_analysis_report(data: Dict[str, Any], file_path: str | Path = "data/analysis.json") -> None:
    """
    Сохранить отчёт анализа.
    
    Args:
        data: Данные отчёта
        file_path: Путь к файлу
    """
    save_json(file_path, data)
    logger.info(f"Saved analysis report to {file_path}")


def save_daily_report(data: Dict[str, Any], date: Optional[datetime] = None, 
                     reports_dir: str | Path = "data/reports") -> Path:
    """
    Сохранить ежедневный отчёт.
    
    Args:
        data: Данные отчёта
        date: Дата отчёта (по умолчанию сегодня)
        reports_dir: Директория для отчётов
        
    Returns:
        Path: Путь к сохранённому файлу
    """
    if date is None:
        date = datetime.now()
    
    reports_dir = Path(reports_dir)
    file_name = f"{date.strftime('%Y-%m-%d')}.json"
    file_path = reports_dir / file_name
    
    save_json(file_path, data)
    logger.info(f"Saved daily report to {file_path}")
    
    return file_path


def load_analysis_report(file_path: str | Path = "data/analysis.json") -> Dict[str, Any]:
    """
    Загрузить отчёт анализа.
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        Dict[str, Any]: Данные отчёта
    """
    data = load_json(file_path)
    logger.info(f"Loaded analysis report from {file_path}")
    return data


def save_portfolio(data: Dict[str, Any], file_path: str | Path = "data/portfolio.json") -> None:
    """
    Сохранить портфель.
    
    Args:
        data: Данные портфеля
        file_path: Путь к файлу
    """
    save_json(file_path, data)
    logger.info(f"Saved portfolio to {file_path}")


def load_portfolio(file_path: str | Path = "data/portfolio.json") -> Optional[Dict[str, Any]]:
    """
    Загрузить портфель.
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        Optional[Dict[str, Any]]: Данные портфеля или None если файл не найден
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        logger.warning(f"Portfolio file not found at {file_path}")
        return None
    
    data = load_json(file_path)
    logger.info(f"Loaded portfolio from {file_path}")
    
    return data

