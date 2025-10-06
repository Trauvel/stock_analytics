# Stock Analytics - Запуск только API (без планировщика)
# Просто дважды кликните по этому файлу

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Stock Analytics - API Only" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверка виртуального окружения
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "[OK] Найдено виртуальное окружение" -ForegroundColor Green
    
    # Активация venv
    Write-Host "Активация виртуального окружения..." -ForegroundColor Yellow
    & .\venv\Scripts\Activate.ps1
    
    Write-Host ""
    Write-Host "Запуск API сервера (без планировщика)..." -ForegroundColor Yellow
    Write-Host "API: http://localhost:8000" -ForegroundColor Green
    Write-Host "GUI: http://localhost:8000" -ForegroundColor Green
    Write-Host "Docs: http://localhost:8000/api/docs" -ForegroundColor Green
    Write-Host ""
    Write-Host "Для остановки нажмите Ctrl+C" -ForegroundColor Cyan
    Write-Host ""
    
    # Запуск приложения
    python run_server.py
    
} else {
    Write-Host "[ERROR] Виртуальное окружение не найдено!" -ForegroundColor Red
    Write-Host "Запустите start_server.ps1 для автоматической настройки" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Нажмите любую клавишу для выхода..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

