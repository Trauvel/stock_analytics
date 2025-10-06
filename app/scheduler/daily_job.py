"""Планировщик ежедневных задач."""

import sys
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.config.loader import get_config
from app.process.report import ReportGenerator


class DailyJobScheduler:
    """Планировщик ежедневной генерации отчётов."""
    
    def __init__(self):
        """Инициализация планировщика."""
        self.config = get_config()
        self.scheduler = BackgroundScheduler(timezone=self.config.schedule.tz)
        self.report_generator = ReportGenerator()
    
    def run_daily_job(self):
        """
        Выполнить ежедневную задачу генерации отчёта.
        
        Этапы:
        1. Получение данных по всем тикерам
        2. Расчёт метрик
        3. Сохранение отчёта в data/analysis.json
        4. Сохранение копии в data/reports/DATE.json
        """
        logger.info("=" * 80)
        logger.info("STARTING DAILY JOB")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        
        try:
            # Генерируем и сохраняем отчёт
            report_dict = self.report_generator.generate_and_save(save_daily=True)
            
            # Статистика
            successful = sum(
                1 for data in report_dict['by_symbol'].values()
                if not data['meta'].get('error')
            )
            failed = len(report_dict['by_symbol']) - successful
            total_signals = sum(
                len(data.get('signals', []))
                for data in report_dict['by_symbol'].values()
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            logger.info("=" * 80)
            logger.info("DAILY JOB COMPLETED SUCCESSFULLY")
            logger.info(f"  Duration: {elapsed:.1f}s")
            logger.info(f"  Processed: {len(report_dict['by_symbol'])} symbols")
            logger.info(f"  Successful: {successful}")
            logger.info(f"  Failed: {failed}")
            logger.info(f"  Total signals: {total_signals}")
            logger.info("=" * 80)
            
            return True
            
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            
            logger.error("=" * 80)
            logger.error("DAILY JOB FAILED")
            logger.error(f"  Duration: {elapsed:.1f}s")
            logger.error(f"  Error: {e}")
            logger.error("=" * 80)
            logger.exception("Full traceback:")
            
            return False
    
    def start(self, run_immediately: bool = False):
        """
        Запустить планировщик.
        
        Args:
            run_immediately: Выполнить задачу сразу при запуске
        """
        # Парсим время из конфигурации (формат "HH:MM")
        hour, minute = self.config.schedule.daily_time.split(':')
        hour = int(hour)
        minute = int(minute)
        
        # Создаём cron триггер для ежедневного запуска
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            timezone=self.config.schedule.tz
        )
        
        # Добавляем задачу в планировщик
        self.scheduler.add_job(
            self.run_daily_job,
            trigger=trigger,
            id='daily_report_job',
            name='Daily Stock Analysis Report',
            replace_existing=True
        )
        
        logger.info(f"Scheduled daily job at {hour:02d}:{minute:02d} {self.config.schedule.tz}")
        
        # Запускаем планировщик
        self.scheduler.start()
        logger.info("Scheduler started")
        
        # Выполняем задачу сразу, если требуется
        if run_immediately:
            logger.info("Running job immediately as requested")
            self.run_daily_job()
        else:
            # Показываем когда будет следующий запуск
            jobs = self.scheduler.get_jobs()
            if jobs:
                next_run = jobs[0].next_run_time
                logger.info(f"Next scheduled run: {next_run}")
    
    def stop(self):
        """Остановить планировщик."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
    
    def run_once(self):
        """Выполнить задачу один раз без планировщика."""
        logger.info("Running job once (manual trigger)")
        return self.run_daily_job()
    
    def get_job_info(self):
        """
        Получить информацию о запланированных задачах.
        
        Returns:
            List[Dict]: Информация о задачах
        """
        jobs = self.scheduler.get_jobs()
        
        job_info = []
        for job in jobs:
            info = {
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            }
            job_info.append(info)
        
        return job_info

