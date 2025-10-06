"""Модели данных для системы рекомендаций."""

from dataclasses import dataclass
from typing import Literal, List, Optional


Action = Literal["BUY", "HOLD", "SELL"]


@dataclass
class TickerSnapshot:
    """Снимок состояния тикера для анализа."""
    symbol: str
    price: float
    sma20: Optional[float] = None
    sma50: Optional[float] = None
    sma200: Optional[float] = None
    dy_pct: Optional[float] = None  # дивидендная доходность
    trend_pct_20d: Optional[float] = None  # тренд за 20 дней
    high_52w: Optional[float] = None
    low_52w: Optional[float] = None
    sector: Optional[str] = None
    vol_avg_20d: Optional[float] = None
    signals: List[str] = None
    
    def __post_init__(self):
        if self.signals is None:
            self.signals = []


@dataclass
class Recommendation:
    """Рекомендация по тикеру."""
    action: Action
    score: float
    reasons: List[str]
    sizing_hint: Optional[str] = None
    confidence: str = "MEDIUM"  # LOW, MEDIUM, HIGH


@dataclass
class RecoConfig:
    """Конфигурация порогов для генерации рекомендаций."""
    # Дивиденды
    dy_buy_min: float = 8.0  # минимальная DY для покупки
    dy_very_high: float = 15.0  # очень высокая DY
    
    # Позиция относительно SMA200
    max_discount_vs_sma200: float = -10.0  # дисконт (отрицательное значение)
    min_premium_vs_sma200: float = 10.0  # премия (положительное значение)
    
    # Тренд
    trend_up_min: float = 0.5  # минимальный положительный тренд (%)
    trend_down_max: float = -0.5  # максимальный отрицательный тренд (%)
    
    # Score границы
    buy_score_cutoff: float = 2.0  # порог для BUY
    sell_score_cutoff: float = -2.0  # порог для SELL
    
    # Дополнительные параметры
    near_52w_low_threshold: float = 0.3  # нижняя треть диапазона
    near_52w_high_threshold: float = 0.9  # верхняя граница диапазона


@dataclass
class PersonalizedAction:
    """Персонализированное действие с учетом портфеля."""
    symbol: str
    action: Action
    score: float
    reasons: List[str]
    price: float
    qty_suggested: int
    cash_impact: float
    sizing_hint: Optional[str] = None
    current_position: Optional[int] = None
    current_value: Optional[float] = None

