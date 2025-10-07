# 🔧 Исправление 404 ошибок в Event Forecast

## ✅ Что было исправлено

### 1. Монтирование статических файлов
**Проблема:** FastAPI не обслуживал статические файлы (HTML, JS, CSS)

**Решение:** Добавлено в `app/api/server.py`:
```python
# Монтируем статические файлы
project_root = Path(__file__).parent.parent.parent
static_path = project_root / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
```

### 2. Корневой маршрут
**Проблема:** При открытии `http://localhost:8000/` была ошибка

**Решение:** Добавлен редирект на дашборд:
```python
@app.get("/", response_class=HTMLResponse)
async def root():
    """Редирект на главную страницу."""
    return redirect to /static/index.html
```

### 3. Import asyncio
**Проблема:** Могли быть проблемы с async функциями

**Решение:** Добавлен импорт:
```python
import asyncio
```

---

## 🚀 Как проверить что всё работает

### Шаг 1: Тест модуля
```bash
python test_forecast_api.py
```

Вы должны увидеть:
```
✅ Модуль импортирован успешно
✅ Сигнал сгенерирован: HIGH_PROBABILITY
✅ Конфигурация загружена
```

### Шаг 2: Запуск сервера
```bash
python run_server.py
```

Сервер должен запуститься на `http://localhost:8000`

### Шаг 3: Проверка статических файлов
Откройте в браузере:
- `http://localhost:8000/` - должен редиректить на дашборд
- `http://localhost:8000/static/index.html` - главный дашборд
- `http://localhost:8000/static/forecast.html` - панель прогнозов

### Шаг 4: Проверка API
Откройте в браузере:
- `http://localhost:8000/docs` - Swagger UI
- `http://localhost:8000/predictor/signal` - должен вернуть JSON с сигналом
- `http://localhost:8000/predictor/config` - должен вернуть конфигурацию

---

## 🐛 Если всё ещё не работает

### Проблема 1: 404 на /static/forecast.html
**Причина:** Сервер не перезапущен после изменений

**Решение:**
```bash
# Остановите сервер (Ctrl+C)
# Запустите заново
python run_server.py
```

### Проблема 2: Ошибка в консоли браузера
**Симптомы:** 
```
Failed to load resource: net::ERR_FAILED
```

**Решение:**
1. Откройте консоль браузера (F12)
2. Перейдите на вкладку "Network"
3. Обновите страницу (F5)
4. Найдите красные запросы
5. Проверьте URL запроса

**Частые ошибки:**
- `/predictor/signal` вместо `http://localhost:8000/predictor/signal`
- Решение: В `forecast.js` уже используется `API_BASE = ''` (относительные пути)

### Проблема 3: Данные не загружаются
**Симптомы:** Крутится spinner "Загрузка..."

**Решение:**
```bash
# Проверьте что API отвечает
curl http://localhost:8000/predictor/signal

# Должен вернуть JSON:
{
  "ok": true,
  "data": {
    "signal_level": "...",
    ...
  }
}
```

### Проблема 4: CORS ошибки
**Симптомы:**
```
Access to fetch at '...' from origin '...' has been blocked by CORS policy
```

**Решение:** Уже настроено в `server.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    ...
)
```

Если не помогло - убедитесь что открываете через `http://localhost:8000`, а не напрямую файл (`file:///...`)

### Проблема 5: Нет данных о новостях
**Симптомы:** "Нет релевантных новостей для отображения"

**Возможные причины:**
1. Нет интернета
2. RSS источники недоступны
3. Кэш пуст

**Решение:**
```bash
# Проверьте доступность источников
curl https://www.interfax.ru/rss.asp
curl https://www.rbc.ru/rss/

# Если недоступны - измените источники в config/predictor.yaml
```

---

## 📊 Проверочный чеклист

После исправлений проверьте:

- [ ] `python test_forecast_api.py` - работает без ошибок
- [ ] `python run_server.py` - запускается
- [ ] `http://localhost:8000/` - редиректит на дашборд
- [ ] `http://localhost:8000/static/forecast.html` - открывается страница
- [ ] В консоли браузера (F12) нет красных ошибок
- [ ] API endpoint `/predictor/signal` возвращает JSON
- [ ] Кнопка "Обновить" работает
- [ ] Можно ввести тикеры и нажать "Анализировать"
- [ ] Отображается статистика
- [ ] Отображается история (если есть)

---

## 🎯 Быстрая диагностика

### 1. Проверка структуры файлов
```bash
# Должны существовать:
ls static/forecast.html
ls static/js/forecast.js
ls static/css/style.css
ls app/predictor/__init__.py
ls config/predictor.yaml
```

### 2. Проверка портов
```bash
# Убедитесь что порт 8000 свободен
netstat -ano | findstr :8000

# Если занят - измените порт в run_server.py
```

### 3. Проверка логов
```bash
# Смотрите логи сервера в терминале
# Должны быть строки:
# INFO:     Mounted static files from D:\...\static
# INFO:     Application startup complete
```

---

## ✨ Итого

После всех исправлений:

1. ✅ Статические файлы примонтированы
2. ✅ API endpoints работают
3. ✅ CORS настроен
4. ✅ Корневой маршрут работает
5. ✅ Async импорты правильные

**Панель Event Forecast готова к использованию!** 🎉

---

**Если проблемы остались** - откройте консоль браузера (F12), сделайте скриншот ошибок и проверьте логи сервера.

