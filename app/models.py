"""Pydantic модели для данных приложения."""

from datetime import datetime
from typing import List, Optional
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class SignalType(str, Enum):
    """Типы торговых сигналов."""
    PRICE_BELOW_SMA200 = "PRICE_BELOW_SMA200"
    PRICE_ABOVE_SMA200 = "PRICE_ABOVE_SMA200"
    SMA50_CROSS_UP_SMA200 = "SMA50_CROSS_UP_SMA200"
    SMA50_CROSS_DOWN_SMA200 = "SMA50_CROSS_DOWN_SMA200"
    DY_GT_TARGET = "DY_GT_TARGET"
    VOL_SPIKE = "VOL_SPIKE"
    NEAR_52W_LOW = "NEAR_52W_LOW"
    NEAR_52W_HIGH = "NEAR_52W_HIGH"


class SymbolMeta(BaseModel):
    """Метаданные по тикеру."""
    board: Optional[str] = None
    error: Optional[str] = None
    updated_at: Optional[datetime] = None


class SymbolData(BaseModel):
    """Данные анализа по одному тикеру."""
    price: Optional[float] = None
    lot: Optional[int] = None
    div_ttm: Optional[float] = None
    dy_pct: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    high_52w: Optional[float] = None
    low_52w: Optional[float] = None
    dist_52w_low_pct: Optional[float] = None
    dist_52w_high_pct: Optional[float] = None
    signals: List[SignalType] = Field(default_factory=list)
    meta: SymbolMeta = Field(default_factory=SymbolMeta)


class AnalysisReport(BaseModel):
    """Итоговый отчёт анализа."""
    generated_at: datetime
    universe: List[str]
    by_symbol: dict[str, SymbolData]

    @field_validator('universe')
    @classmethod
    def validate_universe(cls, v):
        """Проверка, что список тикеров не пустой."""
        if not v:
            raise ValueError("Universe cannot be empty")
        return v


class Candle(BaseModel):
    """Свечные данные (OHLCV)."""
    open: float = Field(ge=0)
    high: float = Field(ge=0)
    low: float = Field(ge=0)
    close: float = Field(ge=0)
    volume: int = Field(ge=0)
    begin: datetime
    end: datetime
    value: Optional[float] = Field(None, ge=0)

    @model_validator(mode='after')
    def validate_high_low(self):
        """Проверка, что high >= low."""
        if self.high < self.low:
            raise ValueError('High must be >= low')
        return self


class PositionType(str, Enum):
    """Типы инструментов."""
    STOCK = "stock"
    BOND = "bond"
    ETF = "etf"
    FUND = "fund"
    CURRENCY = "currency"


class Position(BaseModel):
    """Позиция в портфеле."""
    symbol: str = Field(min_length=1, max_length=50)  # Разрешаем любые символы
    quantity: Optional[int] = Field(None, ge=0)
    qty: Optional[int] = Field(None, ge=0)  # Поддержка краткого формата
    avg_price: Optional[float] = Field(None, ge=0)
    market: str = "moex"
    type: PositionType = PositionType.STOCK
    notes: Optional[str] = None
    name: Optional[str] = None  # Дополнительное поле
    current_value: Optional[float] = None  # Текущая стоимость
    
    @field_validator('quantity', mode='after')
    @classmethod
    def sync_quantity(cls, v, info):
        """Синхронизация qty и quantity."""
        # Если quantity не указан, берем из qty
        if v is None and info.data.get('qty') is not None:
            return info.data['qty']
        return v


class Portfolio(BaseModel):
    """Пользовательский портфель."""
    name: Optional[str] = None
    currency: str = "RUB"
    cash: float = Field(default=0, ge=0)
    positions: List[Position] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

