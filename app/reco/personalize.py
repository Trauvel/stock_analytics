"""Персонализация рекомендаций с учётом портфеля."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger

from .service import get_recommendations
from .models import PersonalizedAction


def load_portfolio(path: Optional[str] = None) -> Dict[str, Any]:
    """
    Загружает портфель из JSON файла.
    
    Args:
        path: Путь к файлу. По умолчанию data/portfolio.json
        
    Returns:
        Dict: Данные портфеля
    """
    if path is None:
        project_root = Path(__file__).parent.parent.parent
        path = project_root / "data" / "portfolio.json"
    
    path = Path(path)
    
    if not path.exists():
        logger.warning(f"Portfolio file not found: {path}")
        return {"cash": 0, "positions": []}
    
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def calculate_portfolio_value(portfolio: Dict[str, Any]) -> float:
    """
    Рассчитывает общую стоимость портфеля.
    
    Args:
        portfolio: Данные портфеля
        
    Returns:
        float: Общая стоимость
    """
    cash = portfolio.get("cash", 0)
    positions_value = sum(
        pos.get("current_value", 0) 
        for pos in portfolio.get("positions", [])
    )
    return cash + positions_value


def get_personalized_actions() -> List[Dict[str, Any]]:
    """
    Генерирует персонализированные действия с учётом портфеля.
    
    Returns:
        List[Dict]: Список действий с предложениями по количеству
    """
    try:
        portfolio = load_portfolio()
        recommendations = get_recommendations()
        
        # Рассчитываем параметры портфеля
        total_value = calculate_portfolio_value(portfolio)
        cash = portfolio.get("cash", 0)
        base_target = 0.05 * total_value  # базовая доля 5%
        
        # Создаём словарь текущих позиций
        positions_map = {
            pos.get("symbol"): pos 
            for pos in portfolio.get("positions", [])
        }
        
        actions = []
        
        for reco in recommendations:
            symbol = reco["symbol"]
            price = reco["price"]
            action = reco["action"]
            
            if not price or price <= 0:
                continue
            
            current_pos = positions_map.get(symbol)
            current_qty = 0
            current_value = 0.0
            
            if current_pos:
                current_qty = current_pos.get("qty", 0) or current_pos.get("quantity", 0)
                current_value = current_pos.get("current_value", 0)
            
            qty_suggested = 0
            cash_impact = 0.0
            
            if action == "BUY":
                # Рассчитываем количество для покупки
                if reco.get("sizing_hint", "").startswith("Увеличить"):
                    # Увеличенная доля
                    if "2×" in reco["sizing_hint"]:
                        budget = min(base_target * 2, cash)
                    else:
                        budget = min(base_target * 1.5, cash)
                else:
                    # Базовая доля
                    budget = min(base_target, cash)
                
                qty_suggested = int(budget // price)
                cash_impact = -(qty_suggested * price)
                
            elif action == "SELL" and current_qty > 0:
                # Рассчитываем количество для продажи
                if "полностью" in reco.get("sizing_hint", ""):
                    qty_suggested = current_qty
                elif "50%" in reco.get("sizing_hint", ""):
                    qty_suggested = max(1, current_qty // 2)
                else:
                    qty_suggested = max(1, current_qty // 4)
                
                cash_impact = qty_suggested * price
            
            # Добавляем только если есть предложение
            if qty_suggested > 0 or action == "HOLD":
                actions.append({
                    "symbol": symbol,
                    "price": price,
                    "action": action,
                    "score": reco["score"],
                    "reasons": reco["reasons"],
                    "sizing_hint": reco.get("sizing_hint"),
                    "confidence": reco.get("confidence"),
                    "qty_suggested": qty_suggested,
                    "cash_impact": round(cash_impact, 2),
                    "current_position": current_qty,
                    "current_value": round(current_value, 2)
                })
        
        logger.info(f"Generated {len(actions)} personalized actions")
        return actions
        
    except Exception as e:
        logger.error(f"Error generating personalized actions: {e}")
        return []

