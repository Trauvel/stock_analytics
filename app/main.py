"""Главный модуль приложения с интеграцией API и планировщика."""

import base64
import os
import sys
import signal
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
import uvicorn
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from typing import Optional, List
from dotenv import load_dotenv

from app.api.server import app as api_app
from app.config.monitoring_loader import load_monitoring_config
from app.scheduler.daily_job import DailyJobScheduler
from app.scheduler.frequent_updates_job import FrequentUpdatesScheduler
from app.infrastructure.persistence.repositories.price_history_repository_impl import PriceHistoryRepositoryImpl
from app.application.dependencies import container
from app.utils.job_journal import tail_jsonl

# Загружаем переменные окружения из .env файла (UTF-8)
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path, override=False, encoding="utf-8")
    logger.info(f"Loaded environment variables from {env_path}")
else:
    logger.warning(f".env file not found at {env_path}")

# Настройка DI для всего приложения
from dependency_injector.wiring import inject, Provide
container.wire(modules=[__name__, "app.api.server"])


# Глобальные экземпляры планировщиков
scheduler = None
frequent_updates_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения.
    
    Запускает планировщик при старте и останавливает при завершении.
    """
    global scheduler, frequent_updates_scheduler
    
    # Startup
    logger.info("Starting application...")
    
    monitoring_cfg = load_monitoring_config()
    mon = (monitoring_cfg or {}).get("monitoring", {}) or {}
    ph = (monitoring_cfg or {}).get("price_history", {}) or {}
    update_interval_hours = int(mon.get("update_interval_hours", 3))
    days_to_keep = int(ph.get("days_to_keep", 30))
    logger.info(
        f"Monitoring config: update_interval_hours={update_interval_hours}, days_to_keep={days_to_keep}"
    )

    # Запускаем основной планировщик (ежедневный полный анализ)
    scheduler = DailyJobScheduler()
    scheduler.start(run_immediately=False)
    
    # Запускаем планировщик частых обновлений (каждые 3-4 часа)
    try:
        price_history_repo = PriceHistoryRepositoryImpl()
        frequent_updates_scheduler = FrequentUpdatesScheduler(
            price_history_repository=price_history_repo,
            update_interval_hours=update_interval_hours
        )
        
        # Добавляем задачу в основной планировщик для частых обновлений
        from apscheduler.triggers.interval import IntervalTrigger
        job = scheduler.scheduler.add_job(
            frequent_updates_scheduler.update_portfolio_tickers,
            trigger=IntervalTrigger(hours=update_interval_hours),
            id='frequent_updates_job',
            name='Frequent Portfolio Updates (every 3 hours)',
            replace_existing=True
            ,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=3600
        )
        logger.info(
            f"Frequent updates job scheduled: every {update_interval_hours}h, next_run={job.next_run_time}"
        )
    except Exception as e:
        logger.exception(f"Could not start frequent updates scheduler: {e}")
        frequent_updates_scheduler = None
    
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    # scheduler и frequent_updates_scheduler уже объявлены как global выше
    
    if scheduler:
        scheduler.stop()
    
    if frequent_updates_scheduler:
        # Очистка старых snapshots (оставляем последние 30 дней)
        try:
            # Берём срок хранения из monitoring.yaml (если доступно)
            try:
                cfg = getattr(frequent_updates_scheduler, "monitoring_cfg", None) or {}
                ph_cfg = (cfg or {}).get("price_history", {}) or {}
                days = int(ph_cfg.get("days_to_keep", 30))
            except Exception:
                days = 30

            deleted = frequent_updates_scheduler.price_history_repo.cleanup_old(days_to_keep=days)
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old price snapshots")
        except Exception as e:
            logger.warning(f"Error cleaning up old snapshots: {e}")
    
    logger.info("Application stopped")


# Создаём новое приложение с lifespan
app = FastAPI(
    title="Stock Analytics",
    description="Система аналитики акций Московской биржи с автоматическим обновлением",
    version="0.1.0",
    lifespan=lifespan
)


def _dashboard_auth_enabled() -> bool:
    """Проверяет, включена ли защита дашборда паролем."""
    return bool(os.getenv("DASHBOARD_PASSWORD", "").strip())


def _is_protected_path(path: str) -> bool:
    """Пути, требующие авторизации."""
    if path == "/" or path == "":
        return True
    for prefix in ("/static", "/api", "/scheduler", "/predictor"):
        if path == prefix or path.startswith(prefix + "/"):
            return True
    return False


class DashboardBasicAuthMiddleware(BaseHTTPMiddleware):
    """HTTP Basic Auth для дашборда и API по паролю из DASHBOARD_PASSWORD."""

    def __init__(self, app, expected_user: str, expected_password: str):
        super().__init__(app)
        self.expected_user = expected_user
        self.expected_password = expected_password

    async def dispatch(self, request: Request, call_next):
        if not _dashboard_auth_enabled():
            return await call_next(request)

        path = request.url.path
        if not _is_protected_path(path):
            return await call_next(request)

        if request.method == "OPTIONS":
            return await call_next(request)

        auth = request.headers.get("Authorization")
        if not auth or not auth.lower().startswith("basic "):
            return PlainTextResponse(
                "Unauthorized",
                status_code=401,
                headers={"WWW-Authenticate": "Basic realm=\"Dashboard\""},
            )

        try:
            decoded = base64.b64decode(auth[6:].strip()).decode("utf-8")
            user, _, password = decoded.partition(":")
            user = user.strip()
            password = password.strip()
            if user == self.expected_user and password == self.expected_password:
                return await call_next(request)
            # Диагностика при несовпадении (без вывода самих паролей)
            first_exp = ord(self.expected_password[0]) if self.expected_password else None
            first_recv = ord(password[0]) if password else None
            logger.warning(
                f"Dashboard auth failed: expected_user={self.expected_user!r}, "
                f"received_user={user!r}, expected_password_len={len(self.expected_password)}, "
                f"received_password_len={len(password)}, "
                f"first_char_expected_ord={first_exp}, first_char_received_ord={first_recv}"
            )
        except Exception as e:
            logger.warning(f"Dashboard auth error (decode/compare): {e}")

        return PlainTextResponse(
            "Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": "Basic realm=\"Dashboard\""},
        )


_dashboard_user = os.getenv("DASHBOARD_USER", "dashboard").strip() or "dashboard"
_dashboard_password = os.getenv("DASHBOARD_PASSWORD", "").strip()
if _dashboard_auth_enabled():
    app.add_middleware(
        DashboardBasicAuthMiddleware,
        expected_user=_dashboard_user,
        expected_password=_dashboard_password,
    )
    logger.info("Dashboard Basic Auth enabled (DASHBOARD_PASSWORD from .env)")
else:
    logger.info("Dashboard auth disabled (DASHBOARD_PASSWORD not set)")

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


@app.get("/scheduler/frequent/history")
async def frequent_updates_history(limit: int = Query(default=50, ge=1, le=500)):
    """Последние записи журнала запусков частой джобы."""
    items = tail_jsonl("data/job_runs/frequent_updates.jsonl", limit=limit)
    return {"ok": True, "data": {"items": items, "count": len(items)}}


@app.get("/scheduler/daily/history")
async def daily_job_history(limit: int = Query(default=50, ge=1, le=500)):
    """Последние записи журнала запусков ежедневной джобы."""
    items = tail_jsonl("data/job_runs/daily_job.jsonl", limit=limit)
    return {"ok": True, "data": {"items": items, "count": len(items)}}


@app.get("/scheduler/history")
async def scheduler_history(limit: int = Query(default=50, ge=1, le=500)):
    """Общий журнал запусков (daily + frequent)."""
    daily = tail_jsonl("data/job_runs/daily_job.jsonl", limit=limit)
    frequent = tail_jsonl("data/job_runs/frequent_updates.jsonl", limit=limit)
    return {
        "ok": True,
        "data": {
            "daily": {"items": daily, "count": len(daily)},
            "frequent": {"items": frequent, "count": len(frequent)},
        },
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

