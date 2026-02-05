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
    
    is_bond = getattr(snapshot, 'is_bond', None)
    if is_bond is None:
        is_bond = len(snapshot.symbol) == 12 and snapshot.symbol[:2].isalpha()

    # Тип актива: commodity (золото и т.п.) не штрафуем за DY; fund — мягче тренд
    commodity_tickers = getattr(config, 'commodity_tickers', None) or ['TGLD']
    fund_tickers = getattr(config, 'fund_tickers', None) or []
    if snapshot.symbol in commodity_tickers:
        asset_type = 'commodity'
    elif snapshot.symbol in fund_tickers:
        asset_type = 'fund'
    else:
        asset_type = getattr(snapshot, 'effective_asset_type', 'bond' if is_bond else 'equity')

    # === 1. Анализ дивидендов / купона (для commodity не учитываем DY — защитный актив) ===
    if asset_type == 'commodity':
        reasons.append("○ Защитный актив (commodity): DY не учитывается")
        # Можно дать небольшой плюс за цену выше SMA200
        if snapshot.sma200 and snapshot.price and snapshot.price >= snapshot.sma200:
            score += 0.5
            reasons.append("✓ Цена выше SMA200")
            confidence_factors.append(0.5)
    elif snapshot.dy_pct is not None:
        dy_for_score = min(snapshot.dy_pct, config.dy_score_cap)  # нормализация
        if dy_for_score >= config.dy_buy_min:
            score += 1.5
            reasons.append(f"✓ Дивиденды/купон {snapshot.dy_pct:.1f}% ≥ {config.dy_buy_min}%")
            confidence_factors.append(1)
            if snapshot.dy_pct >= config.dy_very_high:
                reasons.append(f"⚠ Высокая DY {snapshot.dy_pct:.1f}% — проверить устойчивость")
                confidence_factors.append(0.5)
            elif snapshot.dy_pct > config.dy_score_cap:
                reasons.append(f"⚠ DY выше {config.dy_score_cap}% — проверить устойчивость")
        elif snapshot.dy_pct < config.dy_buy_min * 0.5 and asset_type != 'fund':
            score -= 0.5
            reasons.append(f"✗ Низкие дивиденды {snapshot.dy_pct:.1f}%")
    elif asset_type == 'fund':
        # Фонды: DY не обязательна, не штрафуем за отсутствие
        pass

    # === 2–5 для акций; для облигаций — только доходность, SMA/52W вторичны ===
    if not is_bond:
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
                reasons.append(f"○ Цена около SMA200 ({d_vs_sma200:.1f}%)")

        # === 3. Краткосрочный тренд (20 дней); для commodity/fund — мягче (вторичен) ===
        trend_weight = 0.4 if asset_type in ('commodity', 'fund') else 0.8
        if snapshot.trend_pct_20d is not None:
            if snapshot.trend_pct_20d >= config.trend_up_min:
                score += trend_weight
                reasons.append(f"✓ Восходящий тренд {snapshot.trend_pct_20d:.1f}%")
                confidence_factors.append(1)
            elif snapshot.trend_pct_20d <= config.trend_down_max:
                score -= trend_weight
                reasons.append(f"✗ Нисходящий тренд {snapshot.trend_pct_20d:.1f}%")
                confidence_factors.append(1)

        # === 4. Позиция в 52W диапазоне ===
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

        # === 5. Технические сигналы (для акций) ===
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
    else:
        # Облигации: доходность уже учтена выше; SMA/52W не используем для scoring
        reasons.append("○ Облигация: учтена доходность к купону")
        if snapshot.signals and 'DY_GT_TARGET' in snapshot.signals:
            score += 0.3
            confidence_factors.append(0.3)

    # === Определение действия: BUY / ACCUMULATE / HOLD / AVOID / SELL (4 уровня по отзыву) ===
    accumulate_min = getattr(config, 'accumulate_score_min', 0.5)
    avoid_max = getattr(config, 'avoid_score_max', -1.0)
    price_below_sma200 = (
        snapshot.sma200 and snapshot.price and snapshot.price < snapshot.sma200
    )

    if score <= config.sell_score_cutoff:
        action = "SELL"
    elif score <= avoid_max:
        action = "AVOID"
    elif score >= config.buy_score_cutoff:
        action = "BUY"
        # Для BUY: цена не ниже SMA200 или сильный фундамент (облигации/commodity не трогаем)
        if asset_type == 'equity' and price_below_sma200 and score < getattr(config, 'buy_score_if_below_sma200', 3.2):
            action = "ACCUMULATE"
            reasons.append("○ BUY → ACCUMULATE: цена ниже SMA200, можно докупать понемногу")
    elif score >= accumulate_min:
        action = "ACCUMULATE"
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
        if score >= 4.0:
            return "Увеличить позицию до 2× от базовой"
        elif (snapshot.sma200 and snapshot.price and
              (snapshot.price < 0.9 * snapshot.sma200) and
              (snapshot.dy_pct and snapshot.dy_pct >= config.dy_score_cap)):
            return "Увеличить позицию до 1.5× от базовой"
        return "Базовая доля (1×)"
    if action == "ACCUMULATE":
        return "Докупать понемногу"
    if action == "AVOID":
        return "Не докупать; при желании сократить"
    if action == "SELL":
        if score <= -4.0:
            return "Закрыть позицию полностью"
        if score <= -3.0:
            return "Сократить позицию на 50%"
        return "Сократить позицию на 25%"
    return None

