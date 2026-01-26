# Скрипт для запуска тестов проекта stock_analytics
# Использование: .\run_tests.ps1 [опции]

param(
    [string]$TestPath = "tests/",
    [switch]$Verbose = $false,
    [switch]$Quick = $false,
    [switch]$DDD = $false,
    [switch]$All = $false
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Запуск тестов stock_analytics" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Переходим в директорию проекта
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Проверяем наличие pytest
$pytestCheck = python -m pytest --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Ошибка: pytest не установлен или Python не найден" -ForegroundColor Red
    Write-Host "Установите зависимости: pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

Write-Host "Python и pytest найдены" -ForegroundColor Green
Write-Host ""

# Формируем команду pytest
$pytestArgs = @()

if ($Verbose) {
    $pytestArgs += "-v"
} else {
    $pytestArgs += "-q"  # quiet mode
}

$pytestArgs += "--tb=short"  # короткий traceback

# Определяем какие тесты запускать
if ($DDD) {
    Write-Host "Запуск только DDD тестов..." -ForegroundColor Yellow
    $testFiles = @(
        "tests/test_ddd_value_objects.py",
        "tests/test_ddd_stock.py",
        "tests/test_ddd_use_case.py"
    )
    $pytestArgs += $testFiles
} elseif ($Quick) {
    Write-Host "Быстрый прогон (только базовые тесты)..." -ForegroundColor Yellow
    $testFiles = @(
        "tests/test_config.py",
        "tests/test_ddd_value_objects.py",
        "tests/test_ddd_stock.py"
    )
    $pytestArgs += $testFiles
} elseif ($All) {
    Write-Host "Запуск всех тестов..." -ForegroundColor Yellow
    $pytestArgs += $TestPath
} else {
    Write-Host "Запуск основных тестов (без интеграционных)..." -ForegroundColor Yellow
    $testFiles = @(
        "tests/test_config.py",
        "tests/test_ddd_value_objects.py",
        "tests/test_ddd_stock.py",
        "tests/test_ddd_use_case.py",
        "tests/test_models.py",
        "tests/test_storage.py"
    )
    $pytestArgs += $testFiles
}

Write-Host ""
Write-Host "Команда: python -m pytest $($pytestArgs -join ' ')" -ForegroundColor Gray
Write-Host ""

# Запускаем тесты
$startTime = Get-Date
python -m pytest $pytestArgs
$exitCode = $LASTEXITCODE
$endTime = Get-Date
$duration = $endTime - $startTime

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($exitCode -eq 0) {
    Write-Host "  Тесты завершены успешно!" -ForegroundColor Green
} else {
    Write-Host "  Тесты завершены с ошибками" -ForegroundColor Red
}
Write-Host "  Время выполнения: $($duration.TotalSeconds.ToString('F2')) сек" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

exit $exitCode
