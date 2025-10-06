# Stock Analytics - Запуск сервера с планировщиком
# Просто дважды кликните по этому файлу

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Stock Analytics - Запуск сервера" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверка виртуального окружения
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "[OK] Найдено виртуальное окружение" -ForegroundColor Green
    
    # Активация venv
    Write-Host "Активация виртуального окружения..." -ForegroundColor Yellow
    & .\venv\Scripts\Activate.ps1
    
    Write-Host ""
    Write-Host "Запуск сервера с планировщиком..." -ForegroundColor Yellow
    Write-Host "API: http://localhost:8000" -ForegroundColor Green
    Write-Host "GUI: http://localhost:8000" -ForegroundColor Green
    Write-Host "Docs: http://localhost:8000/api/docs" -ForegroundColor Green
    Write-Host ""
    Write-Host "Для остановки нажмите Ctrl+C" -ForegroundColor Cyan
    Write-Host ""
    
    # Запуск приложения
    python run_with_scheduler.py
    
} else {
    Write-Host "[ERROR] Виртуальное окружение не найдено!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Создайте виртуальное окружение:" -ForegroundColor Yellow
    Write-Host "  python -m venv venv" -ForegroundColor White
    Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host "  pip install -r requirements.txt" -ForegroundColor White
    Write-Host ""
    
    # Предложение создать автоматически
    $response = Read-Host "Создать виртуальное окружение автоматически? (y/n)"
    if ($response -eq "y" -or $response -eq "Y") {
        Write-Host ""
        Write-Host "Создание виртуального окружения..." -ForegroundColor Yellow
        python -m venv venv
        
        Write-Host "Активация..." -ForegroundColor Yellow
        & .\venv\Scripts\Activate.ps1
        
        Write-Host "Установка зависимостей..." -ForegroundColor Yellow
        pip install -r requirements.txt
        
        Write-Host ""
        Write-Host "[OK] Готово! Запустите скрипт снова." -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Нажмите любую клавишу для выхода..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

