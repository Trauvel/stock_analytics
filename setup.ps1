# Stock Analytics - Первоначальная настройка
# Создаёт виртуальное окружение и устанавливает зависимости

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Stock Analytics - Установка" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверка Python
Write-Host "Проверка Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version
    Write-Host "[OK] $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python не найден!" -ForegroundColor Red
    Write-Host "Установите Python 3.8+ с https://www.python.org/" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Нажмите любую клавишу для выхода..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit
}

Write-Host ""

# Создание venv
if (Test-Path "venv") {
    Write-Host "[!] Виртуальное окружение уже существует" -ForegroundColor Yellow
    $response = Read-Host "Пересоздать? (y/n)"
    if ($response -eq "y" -or $response -eq "Y") {
        Write-Host "Удаление старого окружения..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force venv
    } else {
        Write-Host "Пропускаю создание venv" -ForegroundColor Gray
        & .\venv\Scripts\Activate.ps1
        Write-Host ""
        Write-Host "Обновление зависимостей..." -ForegroundColor Yellow
        pip install --upgrade -r requirements.txt
        Write-Host ""
        Write-Host "[OK] Готово!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Нажмите любую клавишу для выхода..." -ForegroundColor Gray
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        exit
    }
}

Write-Host ""
Write-Host "Создание виртуального окружения..." -ForegroundColor Yellow
python -m venv venv

if (!(Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "[ERROR] Не удалось создать виртуальное окружение!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Нажмите любую клавишу для выхода..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit
}

Write-Host "[OK] Виртуальное окружение создано" -ForegroundColor Green
Write-Host ""

# Активация
Write-Host "Активация..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Обновление pip
Write-Host "Обновление pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

Write-Host ""

# Установка зависимостей
Write-Host "Установка зависимостей..." -ForegroundColor Yellow
Write-Host "Это может занять несколько минут..." -ForegroundColor Gray
Write-Host ""

pip install -r requirements.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "[OK] Установка завершена!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Теперь вы можете запустить:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  start_server.ps1        - Запуск сервера с планировщиком" -ForegroundColor White
    Write-Host "  start_api_only.ps1      - Только API (без планировщика)" -ForegroundColor White
    Write-Host "  run_analysis.ps1        - Разовый анализ" -ForegroundColor White
    Write-Host "  open_browser.ps1        - Открыть в браузере" -ForegroundColor White
    Write-Host "  check_status.ps1        - Проверить статус" -ForegroundColor White
    Write-Host ""
    Write-Host "Для первого запуска рекомендуется:" -ForegroundColor Cyan
    Write-Host "  1. Проверить app/config/config.yaml" -ForegroundColor White
    Write-Host "  2. Запустить run_analysis.ps1" -ForegroundColor White
    Write-Host "  3. Запустить start_server.ps1" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "[ERROR] Ошибка при установке зависимостей!" -ForegroundColor Red
    Write-Host "Проверьте вывод выше для деталей" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Нажмите любую клавишу для выхода..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

