# Конфигурация

Система поддерживает два уровня конфигурации:
1. **YAML конфигурация** (`app/config/config.yaml`) — основные настройки
2. **Переменные окружения** (`.env`) — настройки среды выполнения

---

## YAML конфигурация

Файл: `app/config/config.yaml`

### Базовые настройки

```yaml
# Базовая валюта
base_currency: RUB

# Целевая дивидендная доходность (%)
dividend_target_pct: 8
```

### Список тикеров

```yaml
universe:
  - symbol: SBER
    market: moex
  - symbol: GAZP
    market: moex
  # ... до 15 тикеров
```

### Технические индикаторы

```yaml
windows:
  sma: [20, 50, 200]  # Окна для SMA
```

### Выходные файлы

```yaml
output:
  analysis_file: data/analysis.json
  reports_dir: data/reports
  raw_data_dir: data/raw
```

### Расписание

```yaml
schedule:
  daily_time: "19:10"       # Время запуска (HH:MM)
  tz: "Europe/Moscow"       # Временная зона
```

### Ограничение скорости

```yaml
rate_limit:
  per_symbol_sleep_sec: 0.4  # Пауза между тикерами
```

---

## Переменные окружения

Файл: `.env` (создайте из `.env.example`)

### Создание .env файла

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

### Приоритет настроек

Переменные окружения **переопределяют** настройки из YAML.

**Пример:**
- `config.yaml`: `daily_time: "19:10"`
- `.env`: `DAILY_RUN_TIME=20:00`
- **Результат:** задача запустится в 20:00

### Обязательные переменные

Нет обязательных переменных — все имеют значения по умолчанию.

### Рекомендуемые настройки

**Для разработки:**
```env
DEBUG=true
LOG_LEVEL=DEBUG
API_RELOAD=true
SCHEDULER_ENABLED=false
```

**Для продакшена:**
```env
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT_JSON=true
SCHEDULER_ENABLED=true
LOG_RETENTION=90 days
```

---

## Программная загрузка конфигурации

### YAML конфиг

```python
from app.config.loader import get_config

config = get_config()

print(config.base_currency)  # "RUB"
print(config.dividend_target_pct)  # 8.0
print([t.symbol for t in config.universe])  # ["SBER", "GAZP", ...]
```

### Environment настройки

```python
from app.config.settings import settings

print(settings.LOG_LEVEL)  # "INFO"
print(settings.API_PORT)  # 8000
print(settings.DEBUG)  # False
```

### Валидация

Pydantic автоматически валидирует все настройки при загрузке.

**Пример ошибки:**
```python
# В config.yaml: dividend_target_pct: "invalid"
# Результат: ValidationError: value is not a valid float
```

---

## Структура настроек

```
.env                       # Переменные окружения (создайте из .env.example)
app/config/
  ├── config.yaml         # Основная конфигурация
  ├── loader.py           # Загрузчик YAML
  └── settings.py         # Загрузчик .env
```

---

## Примеры конфигураций

### Минимальная конфигурация

```yaml
base_currency: RUB
universe:
  - symbol: SBER
    market: moex
```

### Полная конфигурация

См. `app/config/config.yaml`

### Переопределение через .env

```env
# Переопределяем время запуска
DAILY_RUN_TIME=20:00

# Переопределяем rate limit
MOEX_RATE_LIMIT=0.5

# Отключаем планировщик
SCHEDULER_ENABLED=false
```

### Защита дашборда паролем

Если задан `DASHBOARD_PASSWORD` в `.env`, доступ к дашборду, статике, API и планировщику защищается HTTP Basic Auth. Браузер запросит логин и пароль при первом заходе.

```env
# Включить защиту (без переменной — без авторизации)
DASHBOARD_PASSWORD=ваш_секретный_пароль

# Опционально: логин (по умолчанию "dashboard")
DASHBOARD_USER=dashboard
```

- **Логин:** значение `DASHBOARD_USER` или `dashboard`
- **Пароль:** значение `DASHBOARD_PASSWORD`
- Защищаются: `/`, `/static/`, `/api/`, `/scheduler/`, `/predictor/`

**Если не пускает при верном пароле:**

1. **Кириллица вместо латиницы:** Буквы «с», «а», «о», «е» выглядят как `c`, `a`, `o`, `e`, но это разные символы. В `.env` и в окне ввода браузера должна быть одна и та же раскладка. Надёжнее использовать **только латиницу и цифры** в пароле.
2. **Проверьте логи:** при 401 в логах пишется `Dashboard auth failed: ... first_char_expected_ord=..., first_char_received_ord=...`. Если коды отличаются (например 1089 vs 99 для «с» vs `c`) — проблема в раскладке.
3. Пароль в `.env` — без кавычек, без лишних пробелов в начале/конце строки.

---

## Проверка конфигурации

### Через код

```python
from app.config.loader import get_config
from app.config.settings import settings

# Проверка YAML
config = get_config()
print(f"Universe: {len(config.universe)} tickers")

# Проверка .env
settings.display()
```

### Через тесты

```bash
pytest tests/test_config.py -v
pytest tests/test_logging.py -v
```

---

## Troubleshooting

### Конфигурация не загружается

1. Проверьте синтаксис YAML (отступы!)
2. Проверьте наличие файла `app/config/config.yaml`

### .env не применяется

1. Убедитесь что файл называется именно `.env`
2. Перезапустите приложение
3. Проверьте права доступа к файлу

### Настройки не применяются

Проверьте приоритет:
1. `.env` переопределяет `config.yaml`
2. Некоторые настройки применяются только при старте

