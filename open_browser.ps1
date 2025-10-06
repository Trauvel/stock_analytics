# Stock Analytics - Открыть в браузере
# Открывает GUI и документацию API

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Stock Analytics - Открыть в браузере" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$urls = @(
    @{Name="Главная (GUI)"; Url="http://localhost:8000"},
    @{Name="Настройки"; Url="http://localhost:8000/static/settings.html"},
    @{Name="API Docs"; Url="http://localhost:8000/api/docs"}
)

Write-Host "Выберите что открыть:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Главная страница (GUI)" -ForegroundColor White
Write-Host "2. Страница настроек" -ForegroundColor White
Write-Host "3. API документация" -ForegroundColor White
Write-Host "4. Всё сразу" -ForegroundColor White
Write-Host ""

$choice = Read-Host "Введите номер (1-4)"

switch ($choice) {
    "1" {
        Write-Host "Открываю главную страницу..." -ForegroundColor Green
        Start-Process $urls[0].Url
    }
    "2" {
        Write-Host "Открываю настройки..." -ForegroundColor Green
        Start-Process $urls[1].Url
    }
    "3" {
        Write-Host "Открываю API документацию..." -ForegroundColor Green
        Start-Process $urls[2].Url
    }
    "4" {
        Write-Host "Открываю все страницы..." -ForegroundColor Green
        foreach ($item in $urls) {
            Start-Process $item.Url
            Start-Sleep -Milliseconds 500
        }
    }
    default {
        Write-Host "Неверный выбор. Открываю главную страницу..." -ForegroundColor Yellow
        Start-Process $urls[0].Url
    }
}

Write-Host ""
Write-Host "[OK] Готово!" -ForegroundColor Green
Write-Host ""
Start-Sleep -Seconds 2

