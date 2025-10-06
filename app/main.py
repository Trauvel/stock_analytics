"""Главный модуль приложения с интеграцией API и планировщика."""

import sys
import signal
from contextlib import asynccontextmanager

from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
import uvicorn

from app.api.server import app as api_app
from app.scheduler.daily_job import DailyJobScheduler


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
async def run_job_now():
    """Запустить задачу генерации отчёта немедленно."""
    if not scheduler:
        return {
            "ok": False,
            "error": "Scheduler not initialized"
        }
    
    logger.info("Manual job trigger requested via API")
    
    try:
        success = scheduler.run_once()
        
        return {
            "ok": success,
            "message": "Job completed successfully" if success else "Job failed, check logs"
        }
    except Exception as e:
        logger.error(f"Error running job manually: {e}")
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

