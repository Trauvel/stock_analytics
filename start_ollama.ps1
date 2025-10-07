# Скрипт для запуска Ollama сервера

Write-Host "=" -NoNewline; Write-Host ("=" * 69)
Write-Host "  ЗАПУСК OLLAMA SERVER"
Write-Host "=" -NoNewline; Write-Host ("=" * 69)
Write-Host ""

# Проверяем установлен ли Ollama
$ollamaPath = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"

if (-not (Test-Path $ollamaPath)) {
    Write-Host "❌ Ollama не найден по пути: $ollamaPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Установите Ollama:" -ForegroundColor Yellow
    Write-Host "  winget install Ollama.Ollama"
    Write-Host ""
    Write-Host "Или скачайте с: https://ollama.com/download" -ForegroundColor Cyan
    exit 1
}

# Проверяем не запущен ли уже
$ollamaProcess = Get-Process ollama -ErrorAction SilentlyContinue

if ($ollamaProcess) {
    Write-Host "✅ Ollama уже запущен (PID: $($ollamaProcess.Id))" -ForegroundColor Green
    Write-Host ""
    Write-Host "Проверка доступности API..."
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 3
        if ($response.StatusCode -eq 200) {
            $data = $response.Content | ConvertFrom-Json
            Write-Host "✅ API доступен" -ForegroundColor Green
            Write-Host ""
            Write-Host "Установленные модели:" -ForegroundColor Cyan
            foreach ($model in $data.models) {
                $size = [math]::Round($model.size / 1GB, 2)
                Write-Host "  - $($model.name) ($size GB)" -ForegroundColor White
            }
        }
    } catch {
        Write-Host "⚠️  API не отвечает, перезапускаем..." -ForegroundColor Yellow
        Stop-Process -Name ollama -Force
        Start-Sleep -Seconds 2
        Start-Process $ollamaPath -ArgumentList "serve" -WindowStyle Hidden
        Write-Host "✅ Ollama перезапущен" -ForegroundColor Green
    }
} else {
    Write-Host "🚀 Запускаем Ollama..." -ForegroundColor Cyan
    
    # Запускаем Ollama в фоне
    Start-Process $ollamaPath -ArgumentList "serve" -WindowStyle Hidden
    
    # Ждём запуска
    Write-Host "⏳ Ожидание запуска..."
    Start-Sleep -Seconds 5
    
    # Проверяем
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Ollama успешно запущен!" -ForegroundColor Green
            
            $data = $response.Content | ConvertFrom-Json
            Write-Host ""
            Write-Host "Установленные модели:" -ForegroundColor Cyan
            foreach ($model in $data.models) {
                $size = [math]::Round($model.size / 1GB, 2)
                Write-Host "  - $($model.name) ($size GB)" -ForegroundColor White
            }
        }
    } catch {
        Write-Host "❌ Не удалось подключиться к Ollama API" -ForegroundColor Red
        Write-Host "   Попробуйте запустить вручную: $ollamaPath serve" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""
Write-Host "=" -NoNewline; Write-Host ("=" * 69)
Write-Host "  OLLAMA ГОТОВ К РАБОТЕ"
Write-Host "=" -NoNewline; Write-Host ("=" * 69)
Write-Host ""
Write-Host "API доступен на: http://localhost:11434" -ForegroundColor Cyan
Write-Host ""
Write-Host "Для остановки:" -ForegroundColor Yellow
Write-Host "  Stop-Process -Name ollama" -ForegroundColor White
Write-Host ""

