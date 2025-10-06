# Быстрый старт

Руководство по быстрому запуску Stock Analytics.

---

## 1. Установка

```bash
# Клонирование (если репозиторий)
git clone <repo-url>
cd stock_analytics

# Создание виртуального окружения
python -m venv venv

# Активация (Windows)
.\venv\Scripts\activate

# Активация (Linux/Mac)
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```

---

## 2. Конфигурация

```bash
# Копируем шаблон настроек
copy .env.example .env  # Windows
cp .env.example .env    # Linux/Mac
```

Базовые настройки уже готовы к работе! 

**Опционально:** отредактируйте `.env` если нужно изменить:
- Время запуска (по умолчанию 19:10)
- Уровень логирования (по умолчанию INFO)
- Порт API (по умолчанию 8000)

---

## 3. Первый запуск

### Генерация тестового отчёта

```bash
python run_job_once.py
```

Через ~60 секунд получите:
- `data/analysis.json` — отчёт по 15 тикерам
- `data/reports/YYYY-MM-DD.json` — архивная копия

### Запуск API сервера

```bash
python run_with_scheduler.py
```

Откройте в браузере:
- http://localhost:8000 — главная страница
- http://localhost:8000/api/docs — интерактивная документация

---

## 4. Первые запросы

### Через браузер

Откройте: http://localhost:8000/api/report/today

### Через cURL

```bash
# Проверка сервера
curl http://localhost:8000/api/health

# Список тикеров
curl http://localhost:8000/api/tickers

# Отчёт
curl http://localhost:8000/api/report/today

# Сводка
curl http://localhost:8000/api/report/summary
```

### Через Python

```python
import requests

# Получить сводку
response = requests.get('http://localhost:8000/api/report/summary')
data = response.json()

print(f"Обработано: {data['data']['successful']} тикеров")
print(f"Высокая доходность: {len(data['data']['high_dividend_tickers'])} тикеров")

# Топ-3 по дивидендной доходности
for item in data['data']['high_dividend_tickers'][:3]:
    print(f"{item['symbol']}: {item['dy_pct']:.2f}%")
```

---

## 5. Работа с портфелем

### Создание портфеля

```bash
curl -X POST http://localhost:8000/api/portfolio \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Мой портфель",
    "currency": "RUB",
    "cash": 100000,
    "positions": [
      {"symbol": "SBER", "quantity": 100, "avg_price": 265.30},
      {"symbol": "GAZP", "quantity": 50, "avg_price": 120.00}
    ]
  }'
```

### Просмотр портфеля

```bash
curl http://localhost:8000/api/portfolio/view
```

---

## 6. Автоматическое обновление

Планировщик автоматически генерирует отчёт каждый день в **19:10 по Москве**.

### Проверка статуса

```bash
curl http://localhost:8000/scheduler/status
```

### Ручной триггер

```bash
curl -X POST http://localhost:8000/scheduler/run-now
```

---

## 7. Просмотр логов

### В реальном времени (Windows)

```powershell
Get-Content data/logs/app.log -Wait -Tail 50
```

### В реальном времени (Linux/Mac)

```bash
tail -f data/logs/app.log
```

### Фильтрация ошибок

```bash
grep "ERROR" data/logs/app.log
```

---

## Что дальше?

### Настройка тикеров

Отредактируйте `app/config/config.yaml`:

```yaml
universe:
  - symbol: YOUR_TICKER
    market: moex
```

### Изменение параметров

- **Целевая дивидендная доходность:** `dividend_target_pct: 10`
- **Окна SMA:** `windows: sma: [10, 30, 100]`
- **Время запуска:** в `.env` установите `DAILY_RUN_TIME=20:00`

### Дополнительные возможности

- См. `docs/api.md` — полная документация API
- См. `docs/scheduler.md` — настройка планировщика
- См. `docs/logging.md` — система логирования
- См. `docs/configuration.md` — все настройки

---

## Типичные проблемы

### Порт 8000 занят

```env
# В .env измените порт
API_PORT=8080
```

### Нет интернета / MOEX недоступен

Проверьте логи: `data/logs/app.log`

### Ошибки при установке зависимостей

```bash
# Обновите pip
python -m pip install --upgrade pip

# Установите по одному
pip install moexalgo pandas fastapi uvicorn
```

---

## Поддержка

- 📖 Документация: `docs/`
- 🐛 Проблемы: проверьте `data/logs/app.log`
- ✅ Тесты: `pytest tests/ -v`

