"""Доменный сервис для генерации рекомендаций."""

from typing import Optional, Dict, List
from loguru import logger

from app.domain.stock_analysis.entities.stock import Stock
from app.domain.recommendation.entities.recommendation import Recommendation
from app.domain.recommendation.value_objects.action import Action, ActionType
from app.domain.recommendation.value_objects.confidence import Confidence


def _is_bond_symbol(symbol: str) -> bool:
    """Облигация по формату ISIN (12 символов, первые 2 — буквы)."""
    return len(symbol) == 12 and symbol[:2].isalpha() and symbol[2:].isalnum()


class RecommendationConfig:
    """Конфигурация для генерации рекомендаций (в т.ч. dy_score_cap, BUY = редкость)."""
    
    def __init__(
        self,
        dy_buy_min: float = 8.0,
        dy_very_high: float = 15.0,
        dy_score_cap: float = 12.0,
        max_discount_vs_sma200: float = -10.0,
        min_premium_vs_sma200: float = 10.0,
        buy_score_if_below_sma200: float = 3.2,
        trend_up_min: float = 0.5,
        trend_down_max: float = -0.5,
        buy_score_cutoff: float = 2.0,
        accumulate_score_min: float = 0.5,
        avoid_score_max: float = -1.0,
        sell_score_cutoff: float = -2.0,
        max_buy_count: int = 4,
        commodity_tickers: Optional[List[str]] = None,
        fund_tickers: Optional[List[str]] = None,
        near_52w_low_threshold: float = 0.3,
        near_52w_high_threshold: float = 0.9,
        event_predictor_enabled: bool = True,
        event_predictor_weights: Optional[Dict] = None
    ):
        self.dy_buy_min = dy_buy_min
        self.dy_very_high = dy_very_high
        self.dy_score_cap = dy_score_cap
        self.max_discount_vs_sma200 = max_discount_vs_sma200
        self.min_premium_vs_sma200 = min_premium_vs_sma200
        self.buy_score_if_below_sma200 = buy_score_if_below_sma200
        self.trend_up_min = trend_up_min
        self.trend_down_max = trend_down_max
        self.buy_score_cutoff = buy_score_cutoff
        self.accumulate_score_min = accumulate_score_min
        self.avoid_score_max = avoid_score_max
        self.sell_score_cutoff = sell_score_cutoff
        self.max_buy_count = max_buy_count
        self.commodity_tickers = commodity_tickers or ["TGLD"]
        self.fund_tickers = fund_tickers or []
        self.near_52w_low_threshold = near_52w_low_threshold
        self.near_52w_high_threshold = near_52w_high_threshold
        self.event_predictor_enabled = event_predictor_enabled
        self.event_predictor_weights = event_predictor_weights or {
            'HIGH_PROBABILITY': 1.5,
            'MEDIUM_PROBABILITY': 0.5,
            'NEGATIVE_SIGNAL': -1.0,
            'LOW': 0.0
        }


class RecommendationEngine:
    """Доменный сервис для генерации рекомендаций на основе акции."""
    
    def __init__(self, config: RecommendationConfig):
        """
        Инициализация движка рекомендаций.
        
        Args:
            config: Конфигурация порогов и правил
        """
        self.config = config
    
    def generate(
        self,
        stock: Stock,
        event_signal: Optional[Dict] = None
    ) -> Recommendation:
        """
        Сгенерировать рекомендацию для акции.
        
        Args:
            stock: Доменная сущность акции
            event_signal: Опциональный сигнал от модуля предсказаний
            
        Returns:
            Recommendation: Рекомендация с действием и обоснованием
        """
        score = 0.0
        reasons = []
        confidence_factors = []
        
        # === 0. Анализ модуля предсказания событий ===
        if event_signal and self.config.event_predictor_enabled:
            signal_level = event_signal.get('signal_level', 'LOW')
            weights = self.config.event_predictor_weights
            
            if signal_level in weights:
                weight = weights[signal_level]
                if weight != 0:
                    score += weight
                    
                    if signal_level == 'HIGH_PROBABILITY':
                        reasons.append(f"🔮 {event_signal.get('reason', 'Высокая вероятность позитивных событий')}")
                        confidence_factors.append(1.0)
                    elif signal_level == 'MEDIUM_PROBABILITY':
                        reasons.append(f"🔮 {event_signal.get('reason', 'Умеренно позитивный новостной фон')}")
                        confidence_factors.append(0.5)
                    elif signal_level == 'NEGATIVE_SIGNAL':
                        reasons.append(f"⚠️ {event_signal.get('reason', 'Негативный новостной фон')}")
                        confidence_factors.append(1.0)
        
        is_bond = _is_bond_symbol(stock.symbol)
        asset_type = "commodity" if stock.symbol in self.config.commodity_tickers else (
            "fund" if stock.symbol in self.config.fund_tickers else ("bond" if is_bond else "equity")
        )

        # === 1. Дивиденды (commodity не штрафуем за DY — защитный актив) ===
        if asset_type == "commodity":
            reasons.append("○ Защитный актив (commodity): DY не учитывается")
            if stock.price and stock.sma_200 and stock.price.to_float() >= stock.sma_200.to_float():
                score += 0.5
                reasons.append("✓ Цена выше SMA200")
                confidence_factors.append(0.5)
        elif stock.dividend_yield:
            dy_value = stock.dividend_yield.value
            dy_for_score = min(dy_value, getattr(self.config, 'dy_score_cap', 12.0))
            if dy_for_score >= self.config.dy_buy_min:
                score += 1.5
                reasons.append(f"✓ Дивиденды/купон {dy_value:.1f}% ≥ {self.config.dy_buy_min}%")
                confidence_factors.append(1)
                if dy_value >= self.config.dy_very_high:
                    reasons.append(f"⚠ Высокая DY {dy_value:.1f}% — проверить устойчивость")
                    confidence_factors.append(0.5)
                elif dy_value > getattr(self.config, 'dy_score_cap', 12.0):
                    reasons.append(f"⚠ DY выше порога — проверить устойчивость")
            elif dy_value < self.config.dy_buy_min * 0.5 and asset_type != "fund":
                score -= 0.5
                reasons.append(f"✗ Низкие дивиденды {dy_value:.1f}%")

        # === 2. Позиция относительно SMA200 (для акций) ===
        if not is_bond and stock.price and stock.sma_200:
            discount = stock.discount_to_sma200()
            if discount is not None:
                if discount <= self.config.max_discount_vs_sma200:
                    score += 1.0
                    reasons.append(f"✓ Цена {discount:.1f}% ниже SMA200 (дисконт)")
                    confidence_factors.append(1)
                elif discount >= self.config.min_premium_vs_sma200:
                    score -= 1.0
                    reasons.append(f"✗ Цена {discount:.1f}% выше SMA200 (премия)")
                    confidence_factors.append(1)
                else:
                    reasons.append(f"○ Цена около SMA200 ({discount:.1f}%)")
        
        # === 3. Краткосрочный тренд (20 дней); для commodity/fund — мягче ===
        trend_weight = 0.4 if asset_type in ("commodity", "fund") else 0.8
        if not is_bond and stock.price and stock.sma_20:
            trend_pct = stock.price.percentage_diff(stock.sma_20)
            if trend_pct >= self.config.trend_up_min:
                score += trend_weight
                reasons.append(f"✓ Восходящий тренд {trend_pct:.1f}%")
                confidence_factors.append(1)
            elif trend_pct <= self.config.trend_down_max:
                score -= trend_weight
                reasons.append(f"✗ Нисходящий тренд {trend_pct:.1f}%")
                confidence_factors.append(1)
        
        # === 4. Позиция в 52W диапазоне (только акции) ===
        if is_bond:
            reasons.append("○ Облигация: учтена доходность к купону")
        position = stock.position_in_52w_range() if not is_bond else None
        if position is not None:
            if position < self.config.near_52w_low_threshold:
                score += 0.5
                reasons.append(f"✓ Цена в нижней трети 52W ({position*100:.0f}%)")
                confidence_factors.append(0.5)
            elif position > self.config.near_52w_high_threshold:
                score -= 0.5
                reasons.append(f"✗ Цена у верхней границы 52W ({position*100:.0f}%)")
                confidence_factors.append(0.5)
        
        # === 5. Анализ технических сигналов (акции; облигации — только DY_GT_TARGET) ===
        if is_bond and stock.signals and any(s.signal_type == "DY_GT_TARGET" for s in stock.signals):
            score += 0.3
            confidence_factors.append(0.3)
        elif not is_bond and stock.signals:
            bullish_count = stock.bullish_signals_count()
            bearish_count = stock.bearish_signals_count()
            
            if bullish_count > bearish_count:
                score += 0.3 * (bullish_count - bearish_count)
                confidence_factors.append(0.3)
            elif bearish_count > bullish_count:
                score -= 0.3 * (bearish_count - bullish_count)
                confidence_factors.append(0.3)
        
        # === Определение действия: BUY / ACCUMULATE / HOLD / AVOID / SELL ===
        price_below_sma200 = (
            stock.price and stock.sma_200 and stock.price.to_float() < stock.sma_200.to_float()
        )
        buy_cutoff = getattr(self.config, 'buy_score_cutoff', 2.0)
        accum_min = getattr(self.config, 'accumulate_score_min', 0.5)
        avoid_max = getattr(self.config, 'avoid_score_max', -1.0)
        if score <= self.config.sell_score_cutoff:
            action = Action(action_type=ActionType.SELL)
        elif score <= avoid_max:
            action = Action(action_type=ActionType.AVOID)
        elif score >= buy_cutoff:
            action = Action(action_type=ActionType.BUY)
            if asset_type == "equity" and price_below_sma200:
                need = getattr(self.config, 'buy_score_if_below_sma200', 3.2)
                if score < need:
                    action = Action(action_type=ActionType.ACCUMULATE)
                    reasons.append("○ BUY → ACCUMULATE: цена ниже SMA200, можно докупать понемногу")
        elif score >= accum_min:
            action = Action(action_type=ActionType.ACCUMULATE)
        else:
            action = Action(action_type=ActionType.HOLD)
        
        # === Определение уверенности ===
        confidence_score = sum(confidence_factors)
        confidence = Confidence.from_score(confidence_score)
        
        # === Подсказка по размеру позиции ===
        sizing_hint = self._calculate_sizing_hint(action, stock, score)
        
        # Извлекаем price и dy_pct для отображения
        price_value = stock.price.to_float() if stock.price else None
        dy_pct_value = stock.dividend_yield.to_float() if stock.dividend_yield else None
        
        return Recommendation(
            symbol=stock.symbol,
            action=action,
            score=round(score, 2),
            reasons=reasons,
            confidence=confidence,
            sizing_hint=sizing_hint,
            price=price_value,
            dy_pct=dy_pct_value
        )
    
    def _calculate_sizing_hint(
        self,
        action: Action,
        stock: Stock,
        score: float
    ) -> Optional[str]:
        """Вычислить подсказку по размеру позиции."""
        if action.is_buy():
            if score >= 4.0:
                return "Увеличить позицию до 2× от базовой"
            elif (stock.sma_200 and stock.price and
                  stock.price < stock.sma_200 * 0.9 and
                  stock.dividend_yield and stock.dividend_yield.value >= getattr(self.config, 'dy_score_cap', 12.0)):
                return "Увеличить позицию до 1.5× от базовой"
            return "Базовая доля (1×)"
        if action.is_accumulate():
            return "Докупать понемногу"
        if action.is_avoid():
            return "Не докупать; при желании сократить"
        if action.is_sell():
            if score <= -4.0:
                return "Закрыть позицию полностью"
            elif score <= -3.0:
                return "Сократить позицию на 50%"
            else:
                return "Сократить позицию на 25%"
        
        return None
