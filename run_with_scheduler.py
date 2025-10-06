"""Запуск API сервера с планировщиком."""

import uvicorn
from loguru import logger

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("STOCK ANALYTICS - Starting with Scheduler")
    logger.info("=" * 80)
    logger.info("")
    logger.info("API will be available at: http://localhost:8000")
    logger.info("  - API Documentation: http://localhost:8000/api/docs")
    logger.info("  - Scheduler Status:  http://localhost:8000/scheduler/status")
    logger.info("  - Manual Trigger:    POST http://localhost:8000/scheduler/run-now")
    logger.info("")
    logger.info("Daily job scheduled at 19:10 Europe/Moscow")
    logger.info("")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 80)
    
    # Запускаем приложение с планировщиком
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False  # Важно: не используем reload с планировщиком!
    )

