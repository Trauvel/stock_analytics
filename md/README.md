# Stock Analytics

Система аналитики акций Московской биржи с автоматическим сбором данных и расчётом торговых сигналов.

## Возможности

- 🖥️ **Web GUI** — красивый веб-интерфейс для просмотра данных
- ⚙️ **Страница настроек** — управление портфелем, тикерами и параметрами через GUI ⭐
- 📊 Автоматический сбор данных с MOEX через moexalgo
- 📈 Расчёт технических индикаторов (SMA, 52W High/Low)
- 💰 Анализ дивидендной доходности
- 🚦 Генерация торговых сигналов
- 🌐 REST API для доступа к данным
- ⏰ Ежедневное автоматическое обновление данных (19:10 МСК)

## Установка

### 1. Клонирование репозитория

```bash
git clone <repo-url>
cd stock_analytics
```

### 2. Создание виртуального окружения

```bash
python -m venv venv
```

### 3. Активация окружения

**Windows:**
```bash
.\venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 4. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 5. Настройка конфигурации

Скопируйте `.env.example` в `.env` и настройте параметры:

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Отредактируйте `.env` под ваши нужды:
- `LOG_LEVEL` — уровень логирования (DEBUG, INFO, WARNING, ERROR)
- `DAILY_RUN_TIME` — время ежедневного запуска
- `SCHEDULER_ENABLED` — включить/выключить планировщик

## Запуск

### Вариант 1: API + Планировщик + GUI (рекомендуется)

```bash
python run_with_scheduler.py
```

**Откройте в браузере:** http://localhost:8000

- ✅ Веб-интерфейс с дашбордом
- ✅ **Страница настроек** (http://localhost:8000/static/settings.html) ⭐
- ✅ REST API на http://localhost:8000/api/docs
- ✅ Автоматическая генерация отчётов в 19:10 по Москве
- ✅ Управление через GUI или API

### Вариант 2: Только API

```bash
python run_server.py
```

- Только API сервер без планировщика
- Для ручного управления

### Вариант 3: Разовая генерация отчёта

```bash
python run_job_once.py
```

- Генерирует отчёт один раз и завершается
- Для тестирования или ручного запуска

### Документация API

После запуска сервера документация доступна по адресам:
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- Статус планировщика: `http://localhost:8000/scheduler/status`

## Эндпоинты API

### Основные
- `GET /api/health` — проверка состояния сервера
- `GET /api/tickers` — список отслеживаемых тикеров
- `GET /api/report/today` — последний сгенерированный отчёт
- `GET /api/report/summary` — краткая сводка по отчёту

### Портфель
- `POST /api/portfolio` — сохранение портфеля
- `GET /api/portfolio/view` — просмотр сохранённого портфеля

### Планировщик
- `GET /scheduler/status` — статус планировщика
- `POST /scheduler/run-now` — запустить генерацию отчёта немедленно

Подробнее: см. `docs/api.md`

## Структура проекта

```
app/
  config/       # Конфигурационные файлы
  ingest/       # Получение данных с MOEX
  process/      # Расчёт метрик и генерация отчётов
  store/        # Сохранение и загрузка данных
  api/          # FastAPI сервер
  scheduler/    # Планировщик задач
  utils/        # Утилиты (логирование и т.д.)
data/           # Данные (отчёты, raw данные)
docs/           # Документация
tests/          # Тесты
```

## Разработка

### Запуск тестов

```bash
# Все тесты
pytest tests/ -v

# Конкретный модуль
pytest tests/test_api.py -v

# С покрытием
pytest tests/ --cov=app --cov-report=html
```

### Генерация отчёта вручную

```bash
python run_job_once.py
```

### Проверка конфигурации

```python
from app.config.loader import get_config
from app.config.settings import settings

config = get_config()
settings.display()
```

### Логи

```bash
# Просмотр логов в реальном времени (Windows)
Get-Content data/logs/app.log -Wait -Tail 50

# Linux/Mac
tail -f data/logs/app.log
```

## Документация

- 📘 [Быстрый старт](docs/quickstart.md)
- 🖥️ [Web GUI](docs/gui.md) ⭐ **НОВОЕ!**
- 🔧 [Конфигурация](docs/configuration.md)
- 🌐 [API документация](docs/api.md)
- ⏰ [Планировщик](docs/scheduler.md)
- 📝 [Логирование](docs/logging.md)
- ❓ [FAQ](docs/faq.md)
- 📊 [Схемы данных](docs/README.md)

## Тесты

Всего: **59 тестов**

```bash
# Запуск всех тестов
pytest tests/ -v

# Результат
# 59 passed, 5 skipped (MOEX тесты требуют интернет)
```

## Статистика проекта

- **Модулей Python:** 21
- **Тестов:** 65 (все проходят)
- **Документации:** 9 файлов
- **Эндпоинтов API:** 9
- **Тикеров по умолчанию:** 15
- **Web GUI:** ✅ Встроенный дашборд

## Лицензия

MIT

