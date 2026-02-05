"""Модели данных для системы рекомендаций."""

from dataclasses import dataclass
from typing import Literal, List, Optional


Action = Literal["BUY", "HOLD", "SELL"]


def _is_bond_symbol(symbol: str) -> bool:
    """Облигация по формату ISIN (12 символов, первые 2 — буквы)."""
    return len(symbol) == 12 and symbol[:2].isalpha() and symbol[2:].isalnum()


@dataclass
class TickerSnapshot:
    """Снимок состояния тикера для анализа."""
    symbol: str
    price: float
    sma20: Optional[float] = None
    sma50: Optional[float] = None
    sma200: Optional[float] = None
    dy_pct: Optional[float] = None  # дивидендная доходность / купон
    trend_pct_20d: Optional[float] = None  # тренд за 20 дней
    high_52w: Optional[float] = None
    low_52w: Optional[float] = None
    sector: Optional[str] = None
    vol_avg_20d: Optional[float] = None
    signals: List[str] = None
    is_bond: Optional[bool] = None  # если None — выводится из symbol
    
    def __post_init__(self):
        if self.signals is None:
            self.signals = []
        if self.is_bond is None:
            self.is_bond = _is_bond_symbol(self.symbol)


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
    # Дивиденды (нормализация: DY > dy_score_cap не усиливает BUY, триггер «проверить устойчивость»)
    dy_buy_min: float = 8.0  # минимальная DY для покупки
    dy_very_high: float = 15.0  # выше — не даём бонус, добавляем предупреждение
    dy_score_cap: float = 12.0  # для scoring считаем min(DY, dy_score_cap)

    # Позиция относительно SMA200
    max_discount_vs_sma200: float = -10.0  # дисконт (отрицательное значение)
    min_premium_vs_sma200: float = 10.0  # премия (положительное значение)
    # Для BUY: цена не ниже SMA200 или нужен сильный фундамент (buy_score_if_below_sma200)
    buy_score_if_below_sma200: float = 3.2  # минимальный score для BUY при цене ниже SMA200

    # Тренд
    trend_up_min: float = 0.5  # минимальный положительный тренд (%)
    trend_down_max: float = -0.5  # максимальный отрицательный тренд (%)

    # Score границы (BUY — редкость, 2–4 идеи)
    buy_score_cutoff: float = 2.8  # порог для BUY
    sell_score_cutoff: float = -2.0  # порог для SELL
    max_buy_count: int = 4  # макс. число рекомендаций BUY в отчёте (остальные → HOLD)

    # Дополнительные параметры
    near_52w_low_threshold: float = 0.3  # нижняя треть диапазона
    near_52w_high_threshold: float = 0.9  # верхняя граница диапазона

    # Модуль предсказания событий
    event_predictor_enabled: bool = True
    event_predictor_weights: dict = None

    def __post_init__(self):
        if self.event_predictor_weights is None:
            self.event_predictor_weights = {
                'HIGH_PROBABILITY': 1.5,
                'MEDIUM_PROBABILITY': 0.5,
                'NEGATIVE_SIGNAL': -1.0,
                'LOW': 0.0
            }


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

