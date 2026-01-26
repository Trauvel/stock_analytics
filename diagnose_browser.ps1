# Диагностика проблемы с браузером
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "ДИАГНОСТИКА ПРОБЛЕМЫ С БРАУЗЕРОМ" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan

# Проверяем статус сервера
Write-Host "`n1. Проверка статуса сервера:" -ForegroundColor Yellow
$serverStatus = netstat -an | Select-String ":8000"
if ($serverStatus) {
    Write-Host "   [OK] Сервер запущен на порту 8000" -ForegroundColor Green
    Write-Host "   $serverStatus" -ForegroundColor Gray
} else {
    Write-Host "   [ERROR] Сервер не запущен!" -ForegroundColor Red
    exit 1
}

# Тестируем подключение
Write-Host "`n2. Тестирование подключения:" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000" -TimeoutSec 5
    Write-Host "   [OK] HTTP запрос успешен (статус: $($response.StatusCode))" -ForegroundColor Green
    Write-Host "   Content-Type: $($response.Headers.'Content-Type')" -ForegroundColor Gray
} catch {
    Write-Host "   [ERROR] HTTP запрос не удался: $($_.Exception.Message)" -ForegroundColor Red
}

# Проверяем процессы браузера
Write-Host "`n3. Проверка запущенных браузеров:" -ForegroundColor Yellow
$browsers = @("chrome", "firefox", "msedge", "iexplore")
foreach ($browser in $browsers) {
    $processes = Get-Process -Name $browser -ErrorAction SilentlyContinue
    if ($processes) {
        Write-Host "   [INFO] $browser запущен ($($processes.Count) процессов)" -ForegroundColor Cyan
    }
}

# Проверяем настройки прокси
Write-Host "`n4. Проверка настроек прокси:" -ForegroundColor Yellow
try {
    $proxySettings = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings" -ErrorAction SilentlyContinue
    if ($proxySettings.ProxyEnable -eq 1) {
        Write-Host "   [WARN] Прокси включен: $($proxySettings.ProxyServer)" -ForegroundColor Yellow
    } else {
        Write-Host "   [OK] Прокси отключен" -ForegroundColor Green
    }
} catch {
    Write-Host "   [INFO] Не удалось проверить настройки прокси" -ForegroundColor Gray
}

Write-Host "`n===============================================" -ForegroundColor Cyan
Write-Host "РЕКОМЕНДАЦИИ:" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "1. Попробуйте следующие URL в браузере:" -ForegroundColor White
Write-Host "   - http://localhost:8000" -ForegroundColor Green
Write-Host "   - http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "   - http://192.168.31.36:8000" -ForegroundColor Green

Write-Host "`n2. Если не работает, попробуйте:" -ForegroundColor White
Write-Host "   - Режим инкогнито/приватный просмотр" -ForegroundColor Yellow
Write-Host "   - Другой браузер" -ForegroundColor Yellow
Write-Host "   - Отключить антивирус временно" -ForegroundColor Yellow
Write-Host "   - Очистить кэш браузера" -ForegroundColor Yellow

Write-Host "`n3. Для автоматического открытия используйте:" -ForegroundColor White
Write-Host "   .\open_browser.ps1" -ForegroundColor Green

Write-Host "`nНажмите любую клавишу для открытия браузера..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Открываем браузер
Write-Host "`nОткрываем браузер..." -ForegroundColor Green
Start-Process "http://localhost:8000"