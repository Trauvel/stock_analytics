"""Доменный сервис для генерации рекомендаций."""

from typing import Optional, Dict, List
from loguru import logger

from app.domain.stock_analysis.entities.stock import Stock
from app.domain.recommendation.entities.recommendation import Recommendation
from app.domain.recommendation.value_objects.action import Action, ActionType
from app.domain.recommendation.value_objects.confidence import Confidence


class RecommendationConfig:
    """Конфигурация для генерации рекомендаций."""
    
    def __init__(
        self,
        dy_buy_min: float = 8.0,
        dy_very_high: float = 15.0,
        max_discount_vs_sma200: float = -10.0,
        min_premium_vs_sma200: float = 10.0,
        trend_up_min: float = 0.5,
        trend_down_max: float = -0.5,
        buy_score_cutoff: float = 2.0,
        sell_score_cutoff: float = -2.0,
        near_52w_low_threshold: float = 0.3,
        near_52w_high_threshold: float = 0.9,
        event_predictor_enabled: bool = True,
        event_predictor_weights: Optional[Dict] = None
    ):
        self.dy_buy_min = dy_buy_min
        self.dy_very_high = dy_very_high
        self.max_discount_vs_sma200 = max_discount_vs_sma200
        self.min_premium_vs_sma200 = min_premium_vs_sma200
        self.trend_up_min = trend_up_min
        self.trend_down_max = trend_down_max
        self.buy_score_cutoff = buy_score_cutoff
        self.sell_score_cutoff = sell_score_cutoff
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
        
        # === 1. Анализ дивидендов ===
        if stock.dividend_yield:
            dy_value = stock.dividend_yield.value
            if dy_value >= self.config.dy_buy_min:
                score += 1.5
                reasons.append(f"✓ Дивиденды {dy_value:.1f}% ≥ {self.config.dy_buy_min}%")
                confidence_factors.append(1)
                
                if dy_value >= self.config.dy_very_high:
                    score += 0.5
                    reasons.append(f"✓ Очень высокая DY {dy_value:.1f}%")
                    confidence_factors.append(1)
            elif dy_value < self.config.dy_buy_min * 0.5:
                score -= 0.5
                reasons.append(f"✗ Низкие дивиденды {dy_value:.1f}%")
        
        # === 2. Позиция относительно SMA200 ===
        if stock.price and stock.sma_200:
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
        
        # === 3. Краткосрочный тренд (20 дней) ===
        if stock.price and stock.sma_20:
            trend_pct = stock.price.percentage_diff(stock.sma_20)
            if trend_pct >= self.config.trend_up_min:
                score += 0.8
                reasons.append(f"✓ Восходящий тренд {trend_pct:.1f}%")
                confidence_factors.append(1)
            elif trend_pct <= self.config.trend_down_max:
                score -= 0.8
                reasons.append(f"✗ Нисходящий тренд {trend_pct:.1f}%")
                confidence_factors.append(1)
        
        # === 4. Позиция в 52W диапазоне ===
        position = stock.position_in_52w_range()
        if position is not None:
            if position < self.config.near_52w_low_threshold:
                score += 0.5
                reasons.append(f"✓ Цена в нижней трети 52W ({position*100:.0f}%)")
                confidence_factors.append(0.5)
            elif position > self.config.near_52w_high_threshold:
                score -= 0.5
                reasons.append(f"✗ Цена у верхней границы 52W ({position*100:.0f}%)")
                confidence_factors.append(0.5)
        
        # === 5. Анализ технических сигналов ===
        if stock.signals:
            bullish_count = stock.bullish_signals_count()
            bearish_count = stock.bearish_signals_count()
            
            if bullish_count > bearish_count:
                score += 0.3 * (bullish_count - bearish_count)
                confidence_factors.append(0.3)
            elif bearish_count > bullish_count:
                score -= 0.3 * (bearish_count - bullish_count)
                confidence_factors.append(0.3)
        
        # === Определение действия ===
        if score >= self.config.buy_score_cutoff:
            action = Action(action_type=ActionType.BUY)
        elif score <= self.config.sell_score_cutoff:
            action = Action(action_type=ActionType.SELL)
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
                  stock.dividend_yield and stock.dividend_yield.value >= 12):
                return "Увеличить позицию до 1.5× от базовой"
            else:
                return "Базовая доля (1×)"
        
        elif action.is_sell():
            if score <= -4.0:
                return "Закрыть позицию полностью"
            elif score <= -3.0:
                return "Сократить позицию на 50%"
            else:
                return "Сократить позицию на 25%"
        
        return None
