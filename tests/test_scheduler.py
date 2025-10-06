"""Тесты для планировщика."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from app.scheduler.daily_job import DailyJobScheduler


@pytest.fixture
def mock_config():
    """Мок конфигурации."""
    config = Mock()
    config.schedule.daily_time = "19:10"
    config.schedule.tz = "Europe/Moscow"
    config.universe = [Mock(symbol='SBER')]
    config.dividend_target_pct = 8.0
    config.output.analysis_file = 'data/test_analysis.json'
    config.output.reports_dir = 'data/test_reports'
    return config


@patch('app.scheduler.daily_job.get_config')
@patch('app.scheduler.daily_job.ReportGenerator')
def test_scheduler_init(mock_generator, mock_get_config, mock_config):
    """Тест инициализации планировщика."""
    mock_get_config.return_value = mock_config
    
    scheduler = DailyJobScheduler()
    
    assert scheduler.config == mock_config
    assert scheduler.scheduler is not None
    assert scheduler.report_generator is not None


@patch('app.scheduler.daily_job.get_config')
@patch('app.scheduler.daily_job.ReportGenerator')
def test_run_daily_job_success(mock_generator_class, mock_get_config, mock_config):
    """Тест успешного выполнения задачи."""
    mock_get_config.return_value = mock_config
    
    # Настраиваем мок генератора
    mock_gen = Mock()
    mock_gen.generate_and_save.return_value = {
        'by_symbol': {
            'SBER': {
                'meta': {'error': None},
                'signals': ['PRICE_ABOVE_SMA200']
            }
        }
    }
    mock_generator_class.return_value = mock_gen
    
    scheduler = DailyJobScheduler()
    result = scheduler.run_daily_job()
    
    assert result is True
    assert mock_gen.generate_and_save.called


@patch('app.scheduler.daily_job.get_config')
@patch('app.scheduler.daily_job.ReportGenerator')
def test_run_daily_job_error(mock_generator_class, mock_get_config, mock_config):
    """Тест обработки ошибки при выполнении задачи."""
    mock_get_config.return_value = mock_config
    
    # Настраиваем мок для выброса ошибки
    mock_gen = Mock()
    mock_gen.generate_and_save.side_effect = Exception("Test error")
    mock_generator_class.return_value = mock_gen
    
    scheduler = DailyJobScheduler()
    result = scheduler.run_daily_job()
    
    assert result is False


@patch('app.scheduler.daily_job.get_config')
@patch('app.scheduler.daily_job.ReportGenerator')
def test_scheduler_start(mock_generator_class, mock_get_config, mock_config):
    """Тест запуска планировщика."""
    mock_get_config.return_value = mock_config
    mock_generator_class.return_value = Mock()
    
    scheduler = DailyJobScheduler()
    scheduler.start(run_immediately=False)
    
    assert scheduler.scheduler.running is True
    
    # Проверяем, что задача добавлена
    jobs = scheduler.scheduler.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == 'daily_report_job'
    
    # Останавливаем
    scheduler.stop()
    assert scheduler.scheduler.running is False


@patch('app.scheduler.daily_job.get_config')
@patch('app.scheduler.daily_job.ReportGenerator')
def test_scheduler_run_immediately(mock_generator_class, mock_get_config, mock_config):
    """Тест немедленного запуска задачи при старте."""
    mock_get_config.return_value = mock_config
    
    mock_gen = Mock()
    mock_gen.generate_and_save.return_value = {
        'by_symbol': {
            'SBER': {'meta': {'error': None}, 'signals': []}
        }
    }
    mock_generator_class.return_value = mock_gen
    
    scheduler = DailyJobScheduler()
    scheduler.start(run_immediately=True)
    
    # Проверяем, что задача была выполнена
    assert mock_gen.generate_and_save.called
    
    scheduler.stop()


@patch('app.scheduler.daily_job.get_config')
@patch('app.scheduler.daily_job.ReportGenerator')
def test_get_job_info(mock_generator_class, mock_get_config, mock_config):
    """Тест получения информации о задачах."""
    mock_get_config.return_value = mock_config
    mock_generator_class.return_value = Mock()
    
    scheduler = DailyJobScheduler()
    scheduler.start(run_immediately=False)
    
    job_info = scheduler.get_job_info()
    
    assert len(job_info) == 1
    assert job_info[0]['id'] == 'daily_report_job'
    assert job_info[0]['name'] == 'Daily Stock Analysis Report'
    assert 'next_run_time' in job_info[0]
    
    scheduler.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

