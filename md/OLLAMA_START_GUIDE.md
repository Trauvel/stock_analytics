# 🚀 Запуск Ollama для Stock Analytics

## ✅ Быстрый запуск (один скрипт)

### Вариант 1: Всё сразу (рекомендуется) ⭐

```powershell
.\start_all.ps1
```

Этот скрипт автоматически:
1. Запустит Ollama (если установлен)
2. Проверит доступность API
3. Запустит Stock Analytics с планировщиком

---

### Вариант 2: По отдельности

#### Запуск только Ollama:
```powershell
.\start_ollama.ps1
```

#### Потом Stock Analytics:
```powershell
python run_with_scheduler.py
```

---

## 🔧 Ручной запуск Ollama

### Способ 1: Через командную строку
```powershell
# Добавить в PATH (если нужно)
$env:Path += ";$env:LOCALAPPDATA\Programs\Ollama"

# Запустить сервер
ollama serve
```

Оставьте этот терминал открытым. Ollama будет работать в нём.

### Способ 2: Фоновый процесс
```powershell
Start-Process "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" -ArgumentList "serve" -WindowStyle Hidden
```

### Способ 3: Из меню Пуск
1. Найдите "Ollama" в меню Пуск
2. Запустите приложение
3. Ollama запустится в трее

---

## ✅ Проверка что Ollama работает

### Быстрая проверка:
```powershell
curl http://localhost:11434/api/tags
```

**Ожидаемый результат:**
```json
{
  "models": [
    {
      "name": "mistral:latest",
      "size": 4372824384,
      ...
    }
  ]
}
```

**Статус:** 200 OK = ✅ Работает!

### Проверка процесса:
```powershell
Get-Process ollama
```

Должен показать запущенный процесс.

---

## 🐛 Если Ollama не запускается

### Проблема: "Порт 11434 занят"

```powershell
# Найдите процесс на порту
netstat -ano | findstr :11434

# Завершите старый процесс
Stop-Process -Name ollama -Force

# Запустите заново
ollama serve
```

### Проблема: "Не найден ollama.exe"

**Проверьте установку:**
```powershell
Test-Path "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
```

Если `False`:
```powershell
# Переустановите
winget install Ollama.Ollama
```

### Проблема: "Модель не найдена"

```powershell
# Проверьте список моделей
ollama list

# Если пусто - скачайте
ollama pull mistral
```

---

## ⚙️ Автозапуск Ollama (опционально)

### Добавить в автозагрузку Windows:

1. Нажмите `Win + R`
2. Введите: `shell:startup`
3. Создайте ярлык на:
   ```
   C:\Users\Trauvel\AppData\Local\Programs\Ollama\ollama.exe
   ```
4. В свойствах ярлыка добавьте аргумент: `serve`
5. Установите "Свернутое окно"

Теперь Ollama будет запускаться при входе в Windows.

---

## 📝 Чек-лист

После запуска проверьте:

- [ ] Ollama процесс запущен (`Get-Process ollama`)
- [ ] API доступен (`curl http://localhost:11434/api/tags`)
- [ ] Модель установлена (`ollama list`)
- [ ] Stock Analytics запущен (`python run_with_scheduler.py`)
- [ ] В логах: "Ollama доступен, модель mistral найдена"
- [ ] Event Forecast работает (`http://localhost:8000/static/forecast.html`)

---

## 🎯 Итоговая команда

**Для быстрого старта каждый раз:**

```powershell
# Запустить всё одной командой
.\start_all.ps1
```

Или добавьте алиас в PowerShell профиль:
```powershell
# Откройте профиль
notepad $PROFILE

# Добавьте функцию
function Start-StockAnalytics {
    cd "D:\learn\python\stock_analytics"
    .\start_all.ps1
}

# Теперь можете запускать из любого места:
Start-StockAnalytics
```

---

**Ollama работает! Теперь перезапустите Stock Analytics!** 🚀

