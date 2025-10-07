"""Движок правил для генерации рекомендаций."""

from typing import Optional, Dict
from .models import TickerSnapshot, RecoConfig, Recommendation
import asyncio
import logging

logger = logging.getLogger(__name__)


async def get_event_signal_async(ticker: str) -> Optional[Dict]:
    """
    Получение сигнала от модуля предсказаний (асинхронно).
    
    Args:
        ticker: Тикер для анализа
        
    Returns:
        Словарь с сигналом или None в случае ошибки
    """
    try:
        from app.predictor import generate_event_signals
        signal = await generate_event_signals(target_companies=[ticker])
        return signal
    except Exception as e:
        logger.warning(f"Не удалось получить сигнал предсказаний для {ticker}: {e}")
        return None


def get_event_signal(ticker: str) -> Optional[Dict]:
    """
    Получение сигнала от модуля предсказаний (синхронная обёртка).
    
    Args:
        ticker: Тикер для анализа
        
    Returns:
        Словарь с сигналом или None
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Если цикл уже работает, создаём задачу
            return None  # В этом случае используйте get_event_signal_async
        else:
            return loop.run_until_complete(get_event_signal_async(ticker))
    except Exception as e:
        logger.warning(f"Ошибка при получении сигнала: {e}")
        return None


def pct_diff(current: Optional[float], reference: Optional[float]) -> float:
    """Вычисляет процентную разницу между текущим и референсным значением."""
    if current is None or reference is None or reference == 0:
        return 0.0
    return (current - reference) / reference * 100.0


def make_reco(
    snapshot: TickerSnapshot, 
    config: RecoConfig,
    event_signal: Optional[Dict] = None
) -> Recommendation:
    """
    Генерирует рекомендацию на основе правил и scoring.
    
    Args:
        snapshot: Снимок данных по тикеру
        config: Конфигурация порогов
        event_signal: Опциональный сигнал от модуля предсказаний
        
    Returns:
        Recommendation: Рекомендация с действием и обоснованием
    """
    score = 0.0
    reasons = []
    confidence_factors = []
    
    # === 0. Анализ модуля предсказания событий ===
    if event_signal and config.event_predictor_enabled:
        signal_level = event_signal.get('signal_level', 'LOW')
        weights = config.event_predictor_weights
        
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
    if snapshot.dy_pct is not None:
        if snapshot.dy_pct >= config.dy_buy_min:
            score += 1.5
            reasons.append(f"✓ Дивиденды {snapshot.dy_pct:.1f}% ≥ {config.dy_buy_min}%")
            confidence_factors.append(1)
            
            if snapshot.dy_pct >= config.dy_very_high:
                score += 0.5
                reasons.append(f"✓ Очень высокая DY {snapshot.dy_pct:.1f}%")
                confidence_factors.append(1)
        elif snapshot.dy_pct < config.dy_buy_min * 0.5:
            score -= 0.5
            reasons.append(f"✗ Низкие дивиденды {snapshot.dy_pct:.1f}%")
    
    # === 2. Позиция относительно SMA200 ===
    if snapshot.sma200 and snapshot.price:
        d_vs_sma200 = pct_diff(snapshot.price, snapshot.sma200)
        
        if d_vs_sma200 <= config.max_discount_vs_sma200:
            score += 1.0
            reasons.append(f"✓ Цена {d_vs_sma200:.1f}% ниже SMA200 (дисконт)")
            confidence_factors.append(1)
        elif d_vs_sma200 >= config.min_premium_vs_sma200:
            score -= 1.0
            reasons.append(f"✗ Цена {d_vs_sma200:.1f}% выше SMA200 (премия)")
            confidence_factors.append(1)
        else:
            # Около SMA200 - нейтрально
            reasons.append(f"○ Цена около SMA200 ({d_vs_sma200:.1f}%)")
    
    # === 3. Краткосрочный тренд (20 дней) ===
    if snapshot.trend_pct_20d is not None:
        if snapshot.trend_pct_20d >= config.trend_up_min:
            score += 0.8
            reasons.append(f"✓ Восходящий тренд {snapshot.trend_pct_20d:.1f}%")
            confidence_factors.append(1)
        elif snapshot.trend_pct_20d <= config.trend_down_max:
            score -= 0.8
            reasons.append(f"✗ Нисходящий тренд {snapshot.trend_pct_20d:.1f}%")
            confidence_factors.append(1)
    
    # === 4. Позиция в 52W диапазоне (контртрендовый анализ) ===
    if snapshot.high_52w and snapshot.low_52w and snapshot.price:
        range_52w = snapshot.high_52w - snapshot.low_52w
        if range_52w > 0:
            position_in_range = (snapshot.price - snapshot.low_52w) / range_52w
            
            if position_in_range < config.near_52w_low_threshold:
                score += 0.5
                reasons.append(f"✓ Цена в нижней трети 52W ({position_in_range*100:.0f}%)")
                confidence_factors.append(0.5)
            elif position_in_range > config.near_52w_high_threshold:
                score -= 0.5
                reasons.append(f"✗ Цена у верхней границы 52W ({position_in_range*100:.0f}%)")
                confidence_factors.append(0.5)
    
    # === 5. Анализ технических сигналов ===
    if snapshot.signals:
        positive_signals = [
            'PRICE_BELOW_SMA200', 
            'SMA50_CROSS_UP_SMA200',
            'DY_GT_TARGET',
            'NEAR_52W_LOW'
        ]
        negative_signals = [
            'PRICE_ABOVE_SMA200',
            'SMA50_CROSS_DOWN_SMA200',
            'NEAR_52W_HIGH'
        ]
        
        for sig in snapshot.signals:
            if sig in positive_signals:
                score += 0.3
                confidence_factors.append(0.3)
            elif sig in negative_signals:
                score -= 0.3
                confidence_factors.append(0.3)
    
    # === Определение действия ===
    if score >= config.buy_score_cutoff:
        action = "BUY"
    elif score <= config.sell_score_cutoff:
        action = "SELL"
    else:
        action = "HOLD"
    
    # === Определение уверенности ===
    confidence_score = sum(confidence_factors)
    if confidence_score >= 3.0:
        confidence = "HIGH"
    elif confidence_score >= 1.5:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"
    
    # === Подсказка по размеру позиции ===
    sizing = _sizing_hint(action, snapshot, config, score)
    
    return Recommendation(
        action=action,
        score=round(score, 2),
        reasons=reasons,
        sizing_hint=sizing,
        confidence=confidence
    )


def _sizing_hint(
    action: str, 
    snapshot: TickerSnapshot, 
    config: RecoConfig,
    score: float
) -> Optional[str]:
    """Генерирует подсказку по размеру позиции."""
    if action == "BUY":
        # Сильный сигнал на покупку
        if score >= 4.0:
            return "Увеличить позицию до 2× от базовой"
        # Хорошие условия: большой дисконт к SMA200 + высокие дивиденды
        elif (snapshot.sma200 and snapshot.price and 
              (snapshot.price < 0.9 * snapshot.sma200) and 
              (snapshot.dy_pct and snapshot.dy_pct >= 12)):
            return "Увеличить позицию до 1.5× от базовой"
        else:
            return "Базовая доля (1×)"
    
    elif action == "SELL":
        if score <= -4.0:
            return "Закрыть позицию полностью"
        elif score <= -3.0:
            return "Сократить позицию на 50%"
        else:
            return "Сократить позицию на 25%"
    
    return None

