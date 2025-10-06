"""Ручной запуск задачи генерации отчёта (без планировщика)."""

from app.scheduler.daily_job import DailyJobScheduler
from loguru import logger

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("MANUAL REPORT GENERATION")
    logger.info("=" * 80)
    
    # Создаём планировщик (но не запускаем)
    scheduler = DailyJobScheduler()
    
    # Выполняем задачу один раз
    success = scheduler.run_once()
    
    if success:
        logger.info("=" * 80)
        logger.info("[SUCCESS] Report generated successfully!")
        logger.info("=" * 80)
        logger.info("Files created:")
        logger.info("  - data/analysis.json")
        logger.info("  - data/reports/YYYY-MM-DD.json")
    else:
        logger.error("=" * 80)
        logger.error("[FAILED] Report generation failed!")
        logger.error("=" * 80)
        logger.error("Check logs in data/logs/app.log for details")
    
    exit(0 if success else 1)

