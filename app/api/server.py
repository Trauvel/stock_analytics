"""FastAPI сервер для доступа к данным анализа."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import yaml

from fastapi import FastAPI, HTTPException, status, Query
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from loguru import logger

from app.config.loader import get_config
from app.store.io import (
    load_analysis_report,
    save_portfolio,
    load_portfolio,
    StorageError
)
from app.models import Portfolio


# Pydantic модели для API
class HealthResponse(BaseModel):
    """Ответ проверки здоровья."""
    ok: bool
    timestamp: str
    version: str = "0.1.0"


class TickersResponse(BaseModel):
    """Список тикеров."""
    ok: bool
    data: List[str]


class ReportResponse(BaseModel):
    """Ответ с отчётом."""
    ok: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class PortfolioResponse(BaseModel):
    """Ответ с портфелем."""
    ok: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class MessageResponse(BaseModel):
    """Общий ответ с сообщением."""
    ok: bool
    message: str


# Создаём приложение FastAPI
app = FastAPI(
    title="Stock Analytics API",
    description="API для анализа акций Московской биржи",
    version="0.1.0"
)

# CORS middleware для доступа из браузера
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_model=MessageResponse)
async def api_root():
    """API корневой эндпоинт."""
    return MessageResponse(
        ok=True,
        message="Stock Analytics API. Visit /docs for documentation."
    )


@app.get("/config")
async def get_config_api():
    """
    Получить текущую конфигурацию.
    
    Returns:
        Dict: Конфигурация системы
    """
    try:
        config = get_config()
        
        return {
            "ok": True,
            "data": {
                "base_currency": config.base_currency,
                "dividend_target_pct": config.dividend_target_pct,
                "universe": [{"symbol": t.symbol, "market": t.market} for t in config.universe],
                "windows": {"sma": config.windows.sma},
                "schedule": {
                    "daily_time": config.schedule.daily_time,
                    "tz": config.schedule.tz
                },
                "rate_limit": {
                    "per_symbol_sleep_sec": config.rate_limit.per_symbol_sleep_sec
                }
            }
        }
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return {"ok": False, "error": str(e)}


@app.post("/config/update")
async def update_config_api(config_update: dict):
    """
    Обновить конфигурацию (частично).
    
    Args:
        config_update: Поля для обновления
        
    Returns:
        Dict: Результат обновления
    """
    try:
        import yaml
        
        config_path = Path(__file__).parent.parent.parent / "app" / "config" / "config.yaml"
        
        # Загружаем текущий конфиг
        with open(config_path, 'r', encoding='utf-8') as f:
            current_config = yaml.safe_load(f)
        
        # Обновляем поля
        for key, value in config_update.items():
            if key in current_config:
                current_config[key] = value
        
        # Сохраняем
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(current_config, f, allow_unicode=True, default_flow_style=False)
        
        logger.info(f"Config updated: {list(config_update.keys())}")
        
        # Перезагружаем конфиг
        from app.config.loader import reload_config
        reload_config()
        
        return {
            "ok": True,
            "message": "Configuration updated successfully. Restart server to apply all changes."
        }
        
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return {"ok": False, "error": str(e)}


@app.post("/config/add-ticker")
async def add_ticker(ticker_data: dict):
    """
    Добавить тикер в universe.
    
    Args:
        ticker_data: {"symbol": "TICKER", "market": "moex"}
    """
    try:
        import yaml
        
        config_path = Path(__file__).parent.parent.parent / "app" / "config" / "config.yaml"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Проверяем что тикер еще нет
        existing = [t['symbol'] for t in config['universe']]
        if ticker_data['symbol'] in existing:
            return {"ok": False, "error": f"Ticker {ticker_data['symbol']} already exists"}
        
        # Добавляем
        config['universe'].append(ticker_data)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        
        logger.info(f"Added ticker: {ticker_data['symbol']}")
        
        return {"ok": True, "message": f"Ticker {ticker_data['symbol']} added"}
        
    except Exception as e:
        logger.error(f"Error adding ticker: {e}")
        return {"ok": False, "error": str(e)}


@app.delete("/config/remove-ticker/{symbol}")
async def remove_ticker(symbol: str):
    """
    Удалить тикер из universe.
    
    Args:
        symbol: Тикер для удаления
    """
    try:
        import yaml
        
        config_path = Path(__file__).parent.parent.parent / "app" / "config" / "config.yaml"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Удаляем
        original_len = len(config['universe'])
        config['universe'] = [t for t in config['universe'] if t['symbol'] != symbol]
        
        if len(config['universe']) == original_len:
            return {"ok": False, "error": f"Ticker {symbol} not found"}
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        
        logger.info(f"Removed ticker: {symbol}")
        
        return {"ok": True, "message": f"Ticker {symbol} removed"}
        
    except Exception as e:
        logger.error(f"Error removing ticker: {e}")
        return {"ok": False, "error": str(e)}


# === Рекомендации ===

@app.get("/recommendations")
async def get_recommendations_api(
    only: Optional[List[str]] = Query(default=None),
    min_score: Optional[float] = None
):
    """
    Получить рекомендации BUY/HOLD/SELL.
    
    Args:
        only: Фильтр по действиям (BUY, HOLD, SELL)
        min_score: Минимальный score
        
    Returns:
        Dict: Список рекомендаций
    """
    try:
        from app.reco.service import get_recommendations
        
        recos = get_recommendations(only=only, min_score=min_score)
        
        return {
            "ok": True,
            "data": {
                "items": recos,
                "count": len(recos)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        return {"ok": False, "error": str(e)}


@app.get("/recommendations/summary")
async def get_recommendations_summary_api():
    """
    Получить сводку по рекомендациям.
    
    Returns:
        Dict: Статистика
    """
    try:
        from app.reco.service import get_recommendations_summary
        
        summary = get_recommendations_summary()
        
        return {
            "ok": True,
            "data": summary
        }
        
    except Exception as e:
        logger.error(f"Error getting recommendations summary: {e}")
        return {"ok": False, "error": str(e)}


@app.get("/recommendations/personalized")
async def get_personalized_recommendations():
    """
    Получить персонализированные рекомендации с учётом портфеля.
    
    Returns:
        Dict: Персонализированные действия
    """
    try:
        from app.reco.personalize import get_personalized_actions
        
        actions = get_personalized_actions()
        
        return {
            "ok": True,
            "data": {
                "items": actions,
                "count": len(actions)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting personalized recommendations: {e}")
        return {"ok": False, "error": str(e)}


@app.get("/reco/config")
async def get_reco_config_api():
    """
    Получить конфигурацию правил рекомендаций.
    
    Returns:
        Dict: Конфигурация
    """
    try:
        from app.reco.config import get_reco_config
        
        cfg = get_reco_config()
        
        return {
            "ok": True,
            "data": {
                "dy_buy_min": cfg.dy_buy_min,
                "dy_very_high": cfg.dy_very_high,
                "max_discount_vs_sma200": cfg.max_discount_vs_sma200,
                "min_premium_vs_sma200": cfg.min_premium_vs_sma200,
                "trend_up_min": cfg.trend_up_min,
                "trend_down_max": cfg.trend_down_max,
                "buy_score_cutoff": cfg.buy_score_cutoff,
                "sell_score_cutoff": cfg.sell_score_cutoff,
                "near_52w_low_threshold": cfg.near_52w_low_threshold,
                "near_52w_high_threshold": cfg.near_52w_high_threshold
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting reco config: {e}")
        return {"ok": False, "error": str(e)}


@app.post("/reco/config/update")
async def update_reco_config_api(config_update: dict):
    """
    Обновить конфигурацию правил рекомендаций.
    
    Args:
        config_update: Обновляемые поля
        
    Returns:
        Dict: Результат
    """
    try:
        config_path = Path(__file__).parent.parent.parent / "config" / "reco.yaml"
        
        # Загружаем текущий конфиг
        with open(config_path, 'r', encoding='utf-8') as f:
            current = yaml.safe_load(f) or {}
        
        # Обновляем
        current.update(config_update)
        
        # Сохраняем
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(current, f, allow_unicode=True, default_flow_style=False)
        
        # Перезагружаем
        from app.reco.config import reload_reco_config
        reload_reco_config()
        
        logger.info(f"Reco config updated: {list(config_update.keys())}")
        
        return {
            "ok": True,
            "message": "Reco configuration updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error updating reco config: {e}")
        return {"ok": False, "error": str(e)}


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Проверка состояния сервера.
    
    Returns:
        HealthResponse: Статус сервера
    """
    return HealthResponse(
        ok=True,
        timestamp=datetime.now().isoformat()
    )


@app.get("/tickers", response_model=TickersResponse)
async def get_tickers():
    """
    Получить список отслеживаемых тикеров из конфигурации.
    
    Returns:
        TickersResponse: Список тикеров
    """
    try:
        config = get_config()
        tickers = [ticker.symbol for ticker in config.universe]
        
        logger.info(f"Returned {len(tickers)} tickers")
        
        return TickersResponse(
            ok=True,
            data=tickers
        )
    except Exception as e:
        logger.error(f"Error getting tickers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/report/today", response_model=ReportResponse)
async def get_today_report():
    """
    Получить последний сгенерированный отчёт анализа.
    
    Returns:
        ReportResponse: Отчёт или ошибка
    """
    try:
        config = get_config()
        analysis_file = Path(config.output.analysis_file)
        
        if not analysis_file.exists():
            return ReportResponse(
                ok=False,
                data=None,
                error="No report found. Generate report first."
            )
        
        # Загружаем отчёт
        report_data = load_analysis_report(analysis_file)
        
        logger.info(f"Returned report with {len(report_data.get('universe', []))} symbols")
        
        return ReportResponse(
            ok=True,
            data=report_data,
            error=None
        )
        
    except StorageError as e:
        logger.error(f"Storage error loading report: {e}")
        return ReportResponse(
            ok=False,
            data=None,
            error=f"Failed to load report: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error getting report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/portfolio", response_model=MessageResponse)
async def save_portfolio_data(portfolio: Portfolio):
    """
    Сохранить портфель пользователя.
    
    Args:
        portfolio: Данные портфеля (Pydantic модель)
        
    Returns:
        MessageResponse: Результат операции
    """
    try:
        config = get_config()
        
        # Добавляем временные метки
        portfolio_dict = portfolio.model_dump(mode='json')
        
        if not portfolio_dict.get('created_at'):
            portfolio_dict['created_at'] = datetime.now().isoformat()
        
        portfolio_dict['updated_at'] = datetime.now().isoformat()
        
        # Сохраняем
        save_portfolio(portfolio_dict)
        
        logger.info(f"Saved portfolio with {len(portfolio.positions)} positions")
        
        return MessageResponse(
            ok=True,
            message=f"Portfolio saved successfully with {len(portfolio.positions)} positions"
        )
        
    except Exception as e:
        logger.error(f"Error saving portfolio: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to save portfolio: {str(e)}"
        )


@app.get("/portfolio/view", response_model=PortfolioResponse)
async def get_portfolio_data():
    """
    Получить сохранённый портфель.
    
    Returns:
        PortfolioResponse: Данные портфеля или ошибка
    """
    try:
        portfolio_data = load_portfolio()
        
        if portfolio_data is None:
            return PortfolioResponse(
                ok=False,
                data=None,
                error="No portfolio found. Create one first using POST /portfolio"
            )
        
        logger.info(f"Returned portfolio with {len(portfolio_data.get('positions', []))} positions")
        
        return PortfolioResponse(
            ok=True,
            data=portfolio_data,
            error=None
        )
        
    except Exception as e:
        logger.error(f"Error loading portfolio: {e}")
        return PortfolioResponse(
            ok=False,
            data=None,
            error=f"Failed to load portfolio: {str(e)}"
        )


@app.get("/report/summary")
async def get_report_summary():
    """
    Получить краткую сводку по отчёту.
    
    Returns:
        Dict: Статистика по отчёту
    """
    try:
        config = get_config()
        analysis_file = Path(config.output.analysis_file)
        
        if not analysis_file.exists():
            return {
                "ok": False,
                "error": "No report found"
            }
        
        report_data = load_analysis_report(analysis_file)
        
        # Вычисляем статистику
        total = len(report_data['universe'])
        successful = sum(
            1 for data in report_data['by_symbol'].values()
            if not data['meta'].get('error')
        )
        failed = total - successful
        
        # Тикеры с высокой доходностью
        high_div = [
            (symbol, data['dy_pct'])
            for symbol, data in report_data['by_symbol'].items()
            if data.get('dy_pct') and data['dy_pct'] >= config.dividend_target_pct
        ]
        high_div.sort(key=lambda x: x[1], reverse=True)
        
        # Тикеры с сигналами
        with_signals = [
            (symbol, len(data['signals']))
            for symbol, data in report_data['by_symbol'].items()
            if data.get('signals')
        ]
        
        summary = {
            "ok": True,
            "data": {
                "generated_at": report_data['generated_at'],
                "total_symbols": total,
                "successful": successful,
                "failed": failed,
                "high_dividend_tickers": [
                    {"symbol": sym, "dy_pct": dy} for sym, dy in high_div
                ],
                "tickers_with_signals": len(with_signals),
                "total_signals": sum(count for _, count in with_signals)
            }
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        return {
            "ok": False,
            "error": str(e)
        }


# Обработчик ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Глобальный обработчик ошибок."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "ok": False,
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

