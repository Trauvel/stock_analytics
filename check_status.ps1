# Stock Analytics - Проверка статуса
# Проверяет работает ли сервер и показывает информацию

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Stock Analytics - Проверка статуса" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверка наличия файлов
Write-Host "Проверка файлов..." -ForegroundColor Yellow

$files = @(
    @{Path="venv\Scripts\python.exe"; Name="Виртуальное окружение"},
    @{Path="app\config\config.yaml"; Name="Конфигурация"},
    @{Path="data\analysis.json"; Name="Отчёт анализа"},
    @{Path="data\portfolio.json"; Name="Портфель"},
    @{Path="config\reco.yaml"; Name="Правила рекомендаций"}
)

foreach ($file in $files) {
    if (Test-Path $file.Path) {
        Write-Host "  [OK] $($file.Name)" -ForegroundColor Green
    } else {
        Write-Host "  [X]  $($file.Name)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Проверка сервера..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    $health = $response.Content | ConvertFrom-Json
    
    Write-Host "  [OK] Сервер работает" -ForegroundColor Green
    Write-Host "  Версия: $($health.version)" -ForegroundColor Gray
    Write-Host "  Время: $($health.timestamp)" -ForegroundColor Gray
    Write-Host ""
    
    # Проверка планировщика
    Write-Host "Проверка планировщика..." -ForegroundColor Yellow
    try {
        $scheduler = Invoke-WebRequest -Uri "http://localhost:8000/scheduler/status" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        $schedData = $scheduler.Content | ConvertFrom-Json
        
        if ($schedData.data.running) {
            Write-Host "  [OK] Планировщик работает" -ForegroundColor Green
            Write-Host "  Задач: $($schedData.data.jobs.Count)" -ForegroundColor Gray
        } else {
            Write-Host "  [!]  Планировщик не активен" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  [!]  Планировщик недоступен (возможно запущен API only)" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "URLs:" -ForegroundColor Yellow
    Write-Host "  GUI:  http://localhost:8000" -ForegroundColor Cyan
    Write-Host "  API:  http://localhost:8000/api/docs" -ForegroundColor Cyan
    Write-Host ""
    
} catch {
    Write-Host "  [X]  Сервер не работает" -ForegroundColor Red
    Write-Host ""
    Write-Host "Запустите сервер:" -ForegroundColor Yellow
    Write-Host "  start_server.ps1        - С планировщиком" -ForegroundColor White
    Write-Host "  start_api_only.ps1      - Только API" -ForegroundColor White
    Write-Host ""
}

# Последний отчёт
if (Test-Path "data\analysis.json") {
    $report = Get-Content "data\analysis.json" -Raw | ConvertFrom-Json
    Write-Host "Последний отчёт:" -ForegroundColor Yellow
    Write-Host "  Время: $($report.generated_at)" -ForegroundColor Gray
    Write-Host "  Тикеров: $($report.universe.Count)" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "Нажмите любую клавишу для выхода..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

