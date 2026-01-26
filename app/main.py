"""Главный модуль приложения с интеграцией API и планировщика."""

import sys
import signal
from contextlib import asynccontextmanager

from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
import uvicorn
from typing import Optional, List

from app.api.server import app as api_app
from app.scheduler.daily_job import DailyJobScheduler
from app.application.dependencies import container

# Настройка DI для всего приложения
from dependency_injector.wiring import inject, Provide
container.wire(modules=[__name__, "app.api.server"])


# Глобальный экземпляр планировщика
scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения.
    
    Запускает планировщик при старте и останавливает при завершении.
    """
    global scheduler
    
    # Startup
    logger.info("Starting application...")
    
    # Запускаем планировщик
    scheduler = DailyJobScheduler()
    scheduler.start(run_immediately=False)
    
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    if scheduler:
        scheduler.stop()
    
    logger.info("Application stopped")


# Создаём новое приложение с lifespan
app = FastAPI(
    title="Stock Analytics",
    description="Система аналитики акций Московской биржи с автоматическим обновлением",
    version="0.1.0",
    lifespan=lifespan
)

# Подключаем статические файлы для GUI
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("Static files mounted at /static")
except RuntimeError:
    logger.warning("Static directory not found, GUI will not be available")

# Монтируем роуты из api_app
app.mount("/api", api_app)

# Добавляем корневой эндпоинт - отдаём HTML GUI
@app.get("/", response_class=HTMLResponse)
async def root():
    """Корневой эндпоинт - главная страница GUI."""
    index_path = Path("static/index.html")
    
    if index_path.exists():
        with open(index_path, encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    
    # Fallback если нет GUI
    return HTMLResponse(content=f"""
        <html>
            <head><title>Stock Analytics</title></head>
            <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px;">
                <h1>📊 Stock Analytics</h1>
                <p><strong>Status:</strong> Running</p>
                <p><strong>Version:</strong> 0.1.0</p>
                <p><strong>Scheduler:</strong> {"running" if scheduler and scheduler.scheduler.running else "stopped"}</p>
                <hr>
                <h2>Links:</h2>
                <ul>
                    <li><a href="/api/docs">📖 API Documentation (Swagger)</a></li>
                    <li><a href="/api/redoc">📄 API Documentation (ReDoc)</a></li>
                    <li><a href="/scheduler/status">⏰ Scheduler Status</a></li>
                </ul>
                <hr>
                <p><em>GUI not found. Make sure static/ directory exists with index.html</em></p>
            </body>
        </html>
    """)


@app.get("/scheduler/status")
async def scheduler_status():
    """Получить статус планировщика."""
    if not scheduler:
        return {
            "ok": False,
            "error": "Scheduler not initialized"
        }
    
    return {
        "ok": True,
        "data": {
            "running": scheduler.scheduler.running,
            "jobs": scheduler.get_job_info()
        }
    }


@app.post("/scheduler/run-now")
async def run_job_now(
    instrument_type: str = Query(default="all", description="Тип инструментов: all, stocks, bonds"),
    selected_bonds: Optional[str] = Query(default=None, description="Список выбранных облигаций через запятую")
):
    """
    Запустить задачу генерации отчёта немедленно.
    
    Args:
        instrument_type: Тип инструментов для анализа
            - "all" - все тикеры (акции + облигации)
            - "stocks" - только акции
            - "bonds" - только облигации (или выбранные, если указан selected_bonds)
        selected_bonds: Список выбранных облигаций через запятую (только для instrument_type=bonds)
    """
    if not scheduler:
        return {
            "ok": False,
            "error": "Scheduler not initialized"
        }
    
    # Если указаны конкретные облигации, передаём их
    bonds_list = None
    if selected_bonds:
        bonds_list = [b.strip() for b in selected_bonds.split(',') if b.strip()]
        logger.info(f"Selected bonds: {bonds_list}")
    
    logger.info(f"Manual job trigger requested via API (instrument_type: {instrument_type}, selected_bonds: {bonds_list})")
    
    try:
        success = scheduler.run_once(instrument_type=instrument_type, selected_bonds=bonds_list)
        
        type_label = {
            "all": "все тикеры",
            "stocks": "акции",
            "bonds": f"облигации ({len(bonds_list) if bonds_list else 'все'})"
        }.get(instrument_type, instrument_type)
        
        return {
            "ok": success,
            "message": f"Job completed successfully for {type_label}" if success else "Job failed, check logs"
        }
    except Exception as e:
        logger.error(f"Error running job manually: {e}")
        return {
            "ok": False,
            "error": str(e)
        }


# === Модуль предсказаний (без префикса /api) ===

@app.get("/predictor/signal")
async def get_predictor_signal(tickers: Optional[List[str]] = Query(default=None)):
    """Получить сигнал предсказания событий."""
    try:
        from app.predictor import generate_event_signals
        from app.config.loader import get_config
        
        if not tickers:
            config = get_config()
            tickers = [t.symbol for t in config.universe[:5]]
        
        signal = await generate_event_signals(target_companies=tickers)
        
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
async def get_predictor_history(limit: int = 10):
    """Получить историю сигналов предсказаний."""
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
        
        recent = history[-limit:] if len(history) > limit else history
        recent.reverse()
        
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
async def get_predictor_config():
    """Получить конфигурацию модуля предсказаний."""
    try:
        from app.predictor.config import PredictorConfig
        
        config = PredictorConfig.load()
        
        return {
            "ok": True,
            "data": {
                "news_sources": config.news_sources,
                "use_vacancies": config.use_vacancies,
                "positive_keywords": config.positive_keywords[:10],
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


def handle_shutdown(signum, frame):
    """Обработчик сигналов завершения."""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    
    if scheduler:
        scheduler.stop()
    
    sys.exit(0)


# Регистрируем обработчики сигналов
signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False  # Не используем reload с планировщиком
    )

