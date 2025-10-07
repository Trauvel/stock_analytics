# Универсальный скрипт запуска Stock Analytics с Ollama

Write-Host ""
Write-Host "=" -NoNewline; Write-Host ("=" * 79)
Write-Host "  STOCK ANALYTICS - ПОЛНЫЙ ЗАПУСК"
Write-Host "=" -NoNewline; Write-Host ("=" * 79)
Write-Host ""

# Шаг 1: Запускаем Ollama
Write-Host "1️⃣  Запуск Ollama..." -ForegroundColor Cyan
Write-Host ""

$ollamaPath = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"

if (Test-Path $ollamaPath) {
    $ollamaProcess = Get-Process ollama -ErrorAction SilentlyContinue
    
    if (-not $ollamaProcess) {
        Start-Process $ollamaPath -ArgumentList "serve" -WindowStyle Hidden
        Write-Host "   ✅ Ollama запущен" -ForegroundColor Green
        Start-Sleep -Seconds 3
    } else {
        Write-Host "   ✅ Ollama уже работает" -ForegroundColor Green
    }
    
    # Проверяем доступность
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 3 -ErrorAction Stop
        Write-Host "   ✅ API доступен (http://localhost:11434)" -ForegroundColor Green
    } catch {
        Write-Host "   ⚠️  API не отвечает, но процесс запущен" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ⚠️  Ollama не установлен (LLM анализ будет отключен)" -ForegroundColor Yellow
    Write-Host "   Установите: winget install Ollama.Ollama" -ForegroundColor Cyan
}

Write-Host ""

# Шаг 2: Запускаем Stock Analytics
Write-Host "2️⃣  Запуск Stock Analytics с планировщиком..." -ForegroundColor Cyan
Write-Host ""
Write-Host "=" -NoNewline; Write-Host ("=" * 79)
Write-Host ""

# Запускаем основной сервер
python run_with_scheduler.py

