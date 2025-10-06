"""Сервис для генерации рекомендаций."""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from loguru import logger

from .models import TickerSnapshot, Recommendation
from .engine import make_reco
from .config import get_reco_config


def load_analysis_report(path: Optional[str] = None) -> Dict[str, Any]:
    """
    Загружает отчёт анализа из JSON файла.
    
    Args:
        path: Путь к файлу. По умолчанию data/analysis.json
        
    Returns:
        Dict: Данные отчёта
    """
    if path is None:
        project_root = Path(__file__).parent.parent.parent
        path = project_root / "data" / "analysis.json"
    
    path = Path(path)
    
    if not path.exists():
        logger.warning(f"Analysis file not found: {path}")
        return {"by_symbol": {}}
    
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_snapshot(symbol: str, data: Dict[str, Any]) -> TickerSnapshot:
    """
    Создаёт снимок тикера из данных отчёта.
    
    Args:
        symbol: Тикер
        data: Данные по тикеру из analysis.json
        
    Returns:
        TickerSnapshot: Снимок данных
    """
    # Вычисляем тренд за 20 дней (если есть SMA20)
    trend_pct_20d = None
    if data.get('sma_20') and data.get('price'):
        trend_pct_20d = ((data['price'] - data['sma_20']) / data['sma_20']) * 100.0
    
    return TickerSnapshot(
        symbol=symbol,
        price=data.get('price', 0.0),
        sma20=data.get('sma_20'),
        sma50=data.get('sma_50'),
        sma200=data.get('sma_200'),
        dy_pct=data.get('dy_pct'),
        trend_pct_20d=trend_pct_20d,
        high_52w=data.get('high_52w'),
        low_52w=data.get('low_52w'),
        signals=data.get('signals', [])
    )


def get_recommendations(
    only: Optional[List[str]] = None,
    min_score: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Генерирует рекомендации для всех тикеров.
    
    Args:
        only: Фильтр по действиям (например ["BUY", "SELL"])
        min_score: Минимальный score для включения в результат
        
    Returns:
        List[Dict]: Список рекомендаций
    """
    config = get_reco_config()
    report = load_analysis_report()
    by_symbol = report.get('by_symbol', {})
    
    recommendations = []
    
    for symbol, data in by_symbol.items():
        try:
            # Пропускаем если нет данных о цене
            if not data.get('price'):
                continue
            
            # Создаём снимок
            snapshot = build_snapshot(symbol, data)
            
            # Генерируем рекомендацию
            reco = make_reco(snapshot, config)
            
            # Применяем фильтры
            if only and reco.action not in only:
                continue
            
            if min_score is not None and reco.score < min_score:
                continue
            
            # Формируем результат
            recommendations.append({
                "symbol": symbol,
                "price": snapshot.price,
                "dy_pct": snapshot.dy_pct,
                "action": reco.action,
                "score": reco.score,
                "reasons": reco.reasons,
                "sizing_hint": reco.sizing_hint,
                "confidence": reco.confidence
            })
        
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            continue
    
    # Сортировка: BUY по убыванию score, SELL по возрастанию
    def sort_key(r):
        if r['action'] == 'BUY':
            return (0, -r['score'])  # BUY первыми, по убыванию score
        elif r['action'] == 'SELL':
            return (2, r['score'])   # SELL последними, по возрастанию score
        else:
            return (1, -r['score'])  # HOLD в середине
    
    recommendations.sort(key=sort_key)
    
    logger.info(f"Generated {len(recommendations)} recommendations")
    return recommendations


def get_recommendations_summary() -> Dict[str, Any]:
    """
    Возвращает краткую сводку по рекомендациям.
    
    Returns:
        Dict: Статистика по рекомендациям
    """
    all_recos = get_recommendations()
    
    buy_count = sum(1 for r in all_recos if r['action'] == 'BUY')
    hold_count = sum(1 for r in all_recos if r['action'] == 'HOLD')
    sell_count = sum(1 for r in all_recos if r['action'] == 'SELL')
    
    # Топ-3 по BUY и SELL
    buy_recos = [r for r in all_recos if r['action'] == 'BUY'][:3]
    sell_recos = [r for r in all_recos if r['action'] == 'SELL'][:3]
    
    return {
        "total": len(all_recos),
        "by_action": {
            "BUY": buy_count,
            "HOLD": hold_count,
            "SELL": sell_count
        },
        "top_buys": buy_recos,
        "top_sells": sell_recos
    }

