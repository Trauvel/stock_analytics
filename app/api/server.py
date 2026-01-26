"""FastAPI сервер для доступа к данным анализа."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import yaml

from fastapi import FastAPI, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from loguru import logger
import asyncio

from app.config.loader import get_config
from app.store.io import (
    load_analysis_report,
    save_portfolio,
    load_portfolio,
    StorageError
)
from app.models import Portfolio
from app.application.dependencies import container
from app.application.stock_analysis.generate_report_use_case import GenerateReportUseCase
from app.application.recommendation.generate_recommendations_use_case import GenerateRecommendationsUseCase
from app.application.portfolio.get_portfolio_use_case import GetPortfolioUseCase
from app.application.portfolio.save_portfolio_use_case import SavePortfolioUseCase
from app.application.portfolio.import_sber_html_use_case import ImportSberHTMLUseCase
from app.application.portfolio.list_portfolios_use_case import ListPortfoliosUseCase
from app.application.portfolio.create_portfolio_use_case import CreatePortfolioUseCase
from app.application.portfolio.delete_portfolio_use_case import DeletePortfolioUseCase
from app.api.portfolio_helpers import convert_pydantic_to_domain_portfolio
from app.api.dependencies import (
    get_portfolio_use_case,
    get_save_portfolio_use_case,
    get_import_sber_html_use_case,
    get_list_portfolios_use_case,
    get_create_portfolio_use_case,
    get_delete_portfolio_use_case
)


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

# Настройка DI для FastAPI
from fastapi import Depends
from app.api.dependencies import (
    get_generate_report_use_case,
    get_generate_recommendations_use_case,
    get_portfolio_use_case,
    get_save_portfolio_use_case,
    get_import_sber_html_use_case
)
container.wire(modules=[__name__])

@app.get("/", response_class=HTMLResponse)
async def root():
    """Редирект на главную страницу."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="refresh" content="0; url=/static/index.html" />
    </head>
    <body>
        <p>Redirecting to <a href="/static/index.html">dashboard</a>...</p>
    </body>
    </html>
    """

@app.get("/api", response_model=MessageResponse)
async def api_root():
    """API корневой эндпоинт."""
    return MessageResponse(
        ok=True,
        message="Stock Analytics API. Visit /docs for documentation."
    )


@app.get("/bonds")
async def get_bonds_list():
    """
    Получить список всех облигаций из портфеля и конфига.
    
    Returns:
        Dict: Список облигаций (ISIN коды)
    """
    try:
        from app.application.stock_analysis.get_universe_use_case import GetUniverseUseCase
        
        # Используем DDD use case для получения списка тикеров
        get_universe_use_case = GetUniverseUseCase()
        all_tickers = get_universe_use_case.execute(include_portfolio=True)
        logger.debug(f"Total tickers found: {len(all_tickers)}")
        
        # Фильтруем только облигации (ISIN коды)
        bonds = []
        for ticker in all_tickers:
            # Проверяем, является ли тикер ISIN кодом (облигацией)
            # ISIN: 12 символов, первые 2 - буквы, остальные - буквы/цифры
            is_bond = len(ticker) == 12 and ticker[:2].isalpha() and ticker[2:].isalnum()
            if is_bond:
                bonds.append(ticker)
        
        logger.info(f"Found {len(bonds)} bonds out of {len(all_tickers)} total tickers")
        if bonds:
            logger.debug(f"Bonds: {', '.join(bonds)}")
        
        return {
            "ok": True,
            "data": bonds
        }
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error getting bonds list: {e}\n{error_details}")
        return {
            "ok": False,
            "data": [],
            "error": str(e)
        }


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
    min_score: Optional[float] = None,
    symbols: Optional[List[str]] = Query(default=None)
):
    """
    Получить рекомендации BUY/HOLD/SELL из сохранённого отчёта.
    
    Использует данные из data/analysis.json (не ходит в MOEX).
    
    Args:
        only: Фильтр по действиям (BUY, HOLD, SELL)
        min_score: Минимальный score
        symbols: Список тикеров (игнорируется, берутся из отчёта)
        
    Returns:
        Dict: Список рекомендаций
    """
    try:
        # Используем старый способ - из сохранённого отчёта
        # Это не ходит в MOEX, а берёт данные из data/analysis.json
        from app.reco.service import get_recommendations
        from app.config.loader import get_config
        from pathlib import Path
        
        # Проверяем наличие файла отчёта
        config = get_config()
        analysis_file = Path(config.output.analysis_file)
        
        if not analysis_file.exists():
            logger.warning(f"Analysis file not found: {analysis_file}")
            return {
                "ok": True,
                "data": {
                    "items": [],
                    "count": 0
                }
            }
        
        recos = get_recommendations(only=only, min_score=min_score)
        
        logger.info(f"Returned {len(recos)} recommendations from saved report")
        
        return {
            "ok": True,
            "data": {
                "items": recos,
                "count": len(recos)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        import traceback
        traceback.print_exc()
        return {
            "ok": False,
            "error": str(e),
            "data": {
                "items": [],
                "count": 0
            }
        }


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
async def save_portfolio_data(
    portfolio: Portfolio,
    use_case: SavePortfolioUseCase = Depends(get_save_portfolio_use_case)
):
    """
    Сохранить портфель пользователя (через DDD Use Case).
    
    Args:
        portfolio: Данные портфеля (Pydantic модель)
        
    Returns:
        MessageResponse: Результат операции
    """
    try:
        logger.info(f"Saving portfolio via DDD: {len(portfolio.positions)} positions")
        
        # Преобразуем Pydantic модель в доменную сущность
        domain_portfolio = convert_pydantic_to_domain_portfolio(portfolio)
        
        # Сохраняем через Use Case
        saved_portfolio = await use_case.execute(domain_portfolio)
        
        logger.info(f"Portfolio saved successfully via DDD: {len(saved_portfolio.positions)} positions, ID: {saved_portfolio.id}")
        
        # Возвращаем портфель в data для обновления ID на клиенте
        portfolio_data = saved_portfolio.to_dict()
        
        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "message": f"Portfolio saved successfully with {len(saved_portfolio.positions)} positions",
                "data": portfolio_data
            }
        )
        
    except Exception as e:
        logger.error(f"Error saving portfolio via DDD: {e}")
        # Fallback на старый способ
        try:
            config = get_config()
            portfolio_dict = portfolio.model_dump(mode='json')
            if not portfolio_dict.get('created_at'):
                portfolio_dict['created_at'] = datetime.now().isoformat()
            portfolio_dict['updated_at'] = datetime.now().isoformat()
            save_portfolio(portfolio_dict)
            return MessageResponse(
                ok=True,
                message=f"Portfolio saved (fallback) with {len(portfolio.positions)} positions"
            )
        except Exception as fallback_error:
            logger.error(f"Fallback also failed: {fallback_error}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to save portfolio: {str(e)}"
            )


@app.post("/portfolio/import/sber-html", response_model=MessageResponse)
async def import_portfolio_from_sber_html(
    file: UploadFile = File(...),
    merge: bool = Form(default=True),
    portfolio_id: Optional[str] = Form(default=None),
    use_case: ImportSberHTMLUseCase = Depends(get_import_sber_html_use_case)
):
    """
    Импортировать портфель из HTML отчёта Сбера.
    
    Args:
        file: HTML файл отчёта Сбера
        merge: Если True, объединить с существующим портфелем
        portfolio_id: ID портфеля для импорта (если не указан, используется дефолтный)
        
    Returns:
        MessageResponse: Результат импорта
    """
    try:
        from pathlib import Path
        import tempfile
        
        logger.info(f"Importing portfolio from Sber HTML file: {file.filename} (portfolio_id: {portfolio_id})")
        
        # Сохраняем загруженный файл во временную директорию
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='wb') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            # Импортируем через Use Case
            portfolio = await use_case.execute(
                html_file_path=tmp_path,
                merge_with_existing=merge,
                portfolio_id=portfolio_id
            )
            
            return MessageResponse(
                ok=True,
                message=f"Импортировано {len(portfolio.positions)} позиций, кеш: {portfolio.cash.amount:.2f} {portfolio.currency.code}"
            )
        finally:
            # Удаляем временный файл
            Path(tmp_path).unlink(missing_ok=True)
            
    except Exception as e:
        logger.error(f"Error importing portfolio from Sber HTML: {e}")
        import traceback
        traceback.print_exc()
        return MessageResponse(
            ok=False,
            message=f"Ошибка импорта: {str(e)}"
        )


@app.get("/portfolio/view", response_model=PortfolioResponse)
async def get_portfolio_data(
    portfolio_id: Optional[str] = Query(None, description="ID портфеля (если не указан, возвращает дефолтный)"),
    use_case: GetPortfolioUseCase = Depends(get_portfolio_use_case)
):
    """
    Получить сохранённый портфель (через DDD Use Case).
    
    Args:
        portfolio_id: ID портфеля (если не указан, возвращает дефолтный)
    
    Returns:
        PortfolioResponse: Данные портфеля или ошибка
    """
    try:
        logger.info(f"Getting portfolio via DDD: {portfolio_id or 'default'}")
        
        # Получаем через Use Case
        domain_portfolio = await use_case.execute(portfolio_id)
        
        if domain_portfolio is None:
            return PortfolioResponse(
                ok=False,
                data=None,
                error="No portfolio found. Create one first using POST /portfolios"
            )
        
        # Преобразуем в формат API
        portfolio_data = domain_portfolio.to_dict()
        
        logger.info(f"Returned portfolio via DDD: {len(domain_portfolio.positions)} positions")
        
        return PortfolioResponse(
            ok=True,
            data=portfolio_data,
            error=None
        )
        
    except Exception as e:
        logger.error(f"Error loading portfolio via DDD: {e}")
        return PortfolioResponse(
            ok=False,
            data=None,
            error=f"Failed to load portfolio: {str(e)}"
        )


# === Множественные портфели ===

class PortfolioListItem(BaseModel):
    """Элемент списка портфелей."""
    id: str
    name: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    positions_count: int
    total_value: Optional[float]


class PortfoliosListResponse(BaseModel):
    """Ответ со списком портфелей."""
    ok: bool
    data: List[PortfolioListItem]
    error: Optional[str] = None


class CreatePortfolioRequest(BaseModel):
    """Запрос на создание портфеля."""
    name: str
    currency: str = "RUB"
    cash: float = 0.0


@app.get("/portfolios", response_model=PortfoliosListResponse)
async def list_portfolios(
    use_case: ListPortfoliosUseCase = Depends(get_list_portfolios_use_case)
):
    """
    Получить список всех портфелей.
    
    Returns:
        PortfoliosListResponse: Список портфелей
    """
    try:
        logger.info("Listing all portfolios")
        
        portfolios = await use_case.execute()
        
        portfolio_items = []
        for portfolio in portfolios:
            total_value = None
            if portfolio.total_value():
                total_value = portfolio.total_value().amount
            
            portfolio_items.append(PortfolioListItem(
                id=portfolio.id or "unknown",
                name=portfolio.name,
                created_at=portfolio.created_at.isoformat() if portfolio.created_at else None,
                updated_at=portfolio.updated_at.isoformat() if portfolio.updated_at else None,
                positions_count=len(portfolio.positions),
                total_value=total_value
            ))
        
        logger.info(f"Returned {len(portfolio_items)} portfolios")
        
        return PortfoliosListResponse(
            ok=True,
            data=portfolio_items,
            error=None
        )
        
    except Exception as e:
        logger.error(f"Error listing portfolios: {e}")
        return PortfoliosListResponse(
            ok=False,
            data=[],
            error=f"Failed to list portfolios: {str(e)}"
        )


@app.post("/portfolios", response_model=PortfolioResponse)
async def create_portfolio(
    request: CreatePortfolioRequest,
    use_case: CreatePortfolioUseCase = Depends(get_create_portfolio_use_case)
):
    """
    Создать новый портфель.
    
    Args:
        request: Данные для создания портфеля
    
    Returns:
        PortfolioResponse: Созданный портфель
    """
    try:
        logger.info(f"Creating portfolio: {request.name}")
        
        portfolio = await use_case.execute(
            name=request.name,
            currency=request.currency,
            cash=request.cash
        )
        
        portfolio_data = portfolio.to_dict()
        
        logger.info(f"Created portfolio {portfolio.id}: {request.name}")
        
        return PortfolioResponse(
            ok=True,
            data=portfolio_data,
            error=None
        )
        
    except Exception as e:
        logger.error(f"Error creating portfolio: {e}")
        return PortfolioResponse(
            ok=False,
            data=None,
            error=f"Failed to create portfolio: {str(e)}"
        )


@app.get("/portfolio/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio_by_id(
    portfolio_id: str,
    use_case: GetPortfolioUseCase = Depends(get_portfolio_use_case)
):
    """
    Получить портфель по ID.
    
    Args:
        portfolio_id: ID портфеля
    
    Returns:
        PortfolioResponse: Данные портфеля или ошибка
    """
    try:
        logger.info(f"Getting portfolio by ID: {portfolio_id}")
        
        domain_portfolio = await use_case.execute(portfolio_id)
        
        if domain_portfolio is None:
            return PortfolioResponse(
                ok=False,
                data=None,
                error=f"Portfolio {portfolio_id} not found"
            )
        
        portfolio_data = domain_portfolio.to_dict()
        
        logger.info(f"Returned portfolio {portfolio_id}: {len(domain_portfolio.positions)} positions")
        
        return PortfolioResponse(
            ok=True,
            data=portfolio_data,
            error=None
        )
        
    except Exception as e:
        logger.error(f"Error loading portfolio {portfolio_id}: {e}")
        return PortfolioResponse(
            ok=False,
            data=None,
            error=f"Failed to load portfolio: {str(e)}"
        )


@app.delete("/portfolio/{portfolio_id}", response_model=MessageResponse)
async def delete_portfolio(
    portfolio_id: str,
    use_case: DeletePortfolioUseCase = Depends(get_delete_portfolio_use_case)
):
    """
    Удалить портфель по ID.
    
    Args:
        portfolio_id: ID портфеля
    
    Returns:
        MessageResponse: Результат операции
    """
    try:
        logger.info(f"Deleting portfolio: {portfolio_id}")
        
        await use_case.execute(portfolio_id)
        
        logger.info(f"Deleted portfolio: {portfolio_id}")
        
        return MessageResponse(
            ok=True,
            message=f"Portfolio {portfolio_id} deleted successfully"
        )
        
    except Exception as e:
        logger.error(f"Error deleting portfolio {portfolio_id}: {e}")
        return MessageResponse(
            ok=False,
            message=f"Failed to delete portfolio: {str(e)}"
        )


# === Модуль предсказаний ===

@app.get("/predictor/signal")
async def get_event_signal_api(
    tickers: Optional[List[str]] = Query(default=None, description="Список тикеров для анализа")
):
    """
    Получить сигнал предсказания событий для указанных тикеров.
    
    Args:
        tickers: Список тикеров для анализа
        
    Returns:
        Dict: Сигнал предсказания с уровнем и обоснованием
    """
    try:
        from app.predictor import generate_event_signals
        
        # Если тикеры не указаны, используем все из конфига
        if not tickers:
            config = get_config()
            tickers = [t.symbol for t in config.universe[:5]]  # Первые 5 для быстроты
        
        # Генерируем сигнал
        signal = await generate_event_signals(target_companies=tickers)
        
        logger.info(f"Generated event signal for {len(tickers)} tickers: {signal['signal_level']}")
        
        return {
            "ok": True,
            "data": signal
        }
        
    except Exception as e:
        logger.error(f"Error generating event signal: {e}")
        return {
            "ok": False,
            "error": str(e)
        }


@app.get("/predictor/history")
async def get_event_history_api(limit: int = 10):
    """
    Получить историю событийных сигналов.
    
    Args:
        limit: Максимальное количество записей
        
    Returns:
        Dict: История сигналов
    """
    try:
        import json
        from pathlib import Path
        
        history_file = Path("data/events_history.json")
        
        if not history_file.exists():
            return {
                "ok": True,
                "data": {
                    "items": [],
                    "count": 0
                }
            }
        
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        # Возвращаем последние N записей
        recent = history[-limit:] if len(history) > limit else history
        recent.reverse()  # Новые сверху
        
        return {
            "ok": True,
            "data": {
                "items": recent,
                "count": len(recent),
                "total": len(history)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting event history: {e}")
        return {
            "ok": False,
            "error": str(e)
        }


@app.get("/predictor/config")
async def get_predictor_config_api():
    """
    Получить конфигурацию модуля предсказаний.
    
    Returns:
        Dict: Конфигурация predictor
    """
    try:
        from app.predictor.config import PredictorConfig
        
        config = PredictorConfig.load()
        
        return {
            "ok": True,
            "data": {
                "news_sources": config.news_sources,
                "use_vacancies": config.use_vacancies,
                "positive_keywords": config.positive_keywords[:10],  # Топ 10
                "negative_keywords": config.negative_keywords[:10],
                "cache_ttl": config.cache_ttl,
                "events_log_path": config.events_log_path
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting predictor config: {e}")
        return {
            "ok": False,
            "error": str(e)
        }


@app.post("/report/generate", response_model=ReportResponse)
async def generate_report_ddd(
    symbols: Optional[List[str]] = Query(default=None),
    use_case: GenerateReportUseCase = Depends(get_generate_report_use_case)
):
    """
    Сгенерировать отчёт через DDD Use Case (новая архитектура).
    
    Args:
        symbols: Список тикеров для анализа (если не указан, берётся из конфига)
        
    Returns:
        ReportResponse: Сгенерированный отчёт
    """
    try:
        # Если тикеры не указаны, берём из конфига
        if not symbols:
            config = get_config()
            symbols = [ticker.symbol for ticker in config.universe]
        
        logger.info(f"Generating report via DDD for {len(symbols)} symbols")
        
        # Генерируем отчёт через Use Case
        report_data = await use_case.execute(symbols=symbols)
        
        # Сохраняем отчёт (для совместимости со старым кодом)
        from app.store.io import save_analysis_report
        config = get_config()
        save_analysis_report(report_data, config.output.analysis_file)
        
        logger.info(f"Report generated successfully via DDD: {len(report_data.get('universe', []))} symbols")
        
        return ReportResponse(
            ok=True,
            data=report_data,
            error=None
        )
        
    except Exception as e:
        logger.error(f"Error generating report via DDD: {e}")
        return ReportResponse(
            ok=False,
            data=None,
            error=str(e)
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


# Монтируем статические файлы (ВАЖНО: в самом конце, после всех routes!)
project_root = Path(__file__).parent.parent.parent
static_path = project_root / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    logger.info(f"Mounted static files from {static_path}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

