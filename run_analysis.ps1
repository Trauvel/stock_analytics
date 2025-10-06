# Stock Analytics - Разовый запуск анализа
# Генерирует отчёт один раз и завершается

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Stock Analytics - Разовый анализ" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверка виртуального окружения
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "[OK] Найдено виртуальное окружение" -ForegroundColor Green
    
    # Активация venv
    Write-Host "Активация виртуального окружения..." -ForegroundColor Yellow
    & .\venv\Scripts\Activate.ps1
    
    Write-Host ""
    Write-Host "Запуск анализа..." -ForegroundColor Yellow
    Write-Host "Это может занять несколько минут..." -ForegroundColor Gray
    Write-Host ""
    
    # Запуск джоба
    $startTime = Get-Date
    python run_job_once.py
    $endTime = Get-Date
    $duration = $endTime - $startTime
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "[OK] Анализ завершён!" -ForegroundColor Green
    Write-Host "Время выполнения: $($duration.TotalSeconds.ToString('0.0')) сек" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Отчёты сохранены в:" -ForegroundColor Yellow
    Write-Host "  - data/analysis.json" -ForegroundColor White
    Write-Host "  - data/reports/$(Get-Date -Format 'yyyy-MM-dd').json" -ForegroundColor White
    Write-Host ""
    
} else {
    Write-Host "[ERROR] Виртуальное окружение не найдено!" -ForegroundColor Red
    Write-Host "Запустите start_server.ps1 для автоматической настройки" -ForegroundColor Yellow
}

Write-Host "Нажмите любую клавишу для выхода..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

