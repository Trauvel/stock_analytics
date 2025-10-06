# Система логирования

Система логирования на основе **Loguru** с поддержкой JSON формата и контекстных логов.

## Конфигурация

Настройки логирования в `.env`:

```env
# Уровень логирования
LOG_LEVEL=INFO

# Путь к текстовому файлу логов
LOG_FILE=data/logs/app.log

# Путь к JSON файлу логов
LOG_JSON_FILE=data/logs/app.json.log

# Включить JSON формат для основного файла
LOG_FORMAT_JSON=false

# Ротация логов
LOG_ROTATION=10 MB

# Время хранения
LOG_RETENTION=30 days

# Debug режим (переопределяет LOG_LEVEL)
DEBUG=false
```

---

## Уровни логирования

- **DEBUG** — детальная информация для отладки
- **INFO** — общая информация о работе системы
- **WARNING** — предупреждения (не критичные проблемы)
- **ERROR** — ошибки выполнения

---

## Форматы вывода

### Консоль (цветной вывод)

```
2025-10-06 19:10:00.123 | INFO     | app.ingest.moex_client:get_quote:62 - Fetching quote for SBER
2025-10-06 19:10:01.456 | INFO     | app.ingest.moex_client:get_quote:95 - Quote for SBER: {'price': 290.7}
```

### Текстовый файл (`data/logs/app.log`)

```
2025-10-06 19:10:00.123 | INFO     | app.ingest.moex_client:get_quote:62 | Fetching quote for SBER
2025-10-06 19:10:01.456 | INFO     | app.ingest.moex_client:get_quote:95 | Quote for SBER: {'price': 290.7}
```

### JSON файл (`data/logs/app.json.log`)

```json
{
  "timestamp": "2025-10-06T19:10:00.123456+03:00",
  "level": "INFO",
  "module": "app.ingest.moex_client",
  "function": "get_quote",
  "line": 62,
  "message": "Fetching quote for SBER",
  "extra": {
    "ticker": "SBER",
    "operation": "fetch_quote"
  }
}
```

---

## Использование

### Базовое логирование

```python
from loguru import logger

logger.info("Информационное сообщение")
logger.debug("Отладочное сообщение")
logger.warning("Предупреждение")
logger.error("Ошибка")
logger.exception("Ошибка с traceback")
```

### Контекстное логирование

```python
from app.utils.context_logger import log_operation

# Логирование операции с тикером
with log_operation("fetch_data", ticker="SBER"):
    data = get_data("SBER")
    # Автоматически логируется начало, конец и время выполнения
```

### Логгер с контекстом тикера

```python
from app.utils.context_logger import get_ticker_logger

ticker_log = get_ticker_logger("GAZP")
ticker_log.info("Processing started")
ticker_log.debug("Fetching data...")
ticker_log.error("Failed to process")
```

### Добавление кастомного контекста

```python
from loguru import logger

# Добавляем контекст ко всем логам в блоке
with logger.contextualize(ticker="LKOH", user_id=123):
    logger.info("Processing ticker")
    # Лог будет содержать ticker и user_id в extra
```

---

## Ротация и хранение

### Ротация по размеру

```env
LOG_ROTATION=10 MB  # Новый файл каждые 10 МБ
```

### Ротация по времени

```env
LOG_ROTATION=1 day    # Новый файл каждый день
LOG_ROTATION=00:00    # Новый файл в полночь
LOG_ROTATION=1 week   # Новый файл каждую неделю
```

### Архивация

Старые логи автоматически сжимаются в `.zip` архивы.

### Очистка

```env
LOG_RETENTION=30 days  # Хранить 30 дней
LOG_RETENTION=1 week   # Хранить 1 неделю
```

---

## Примеры логов

### Успешная обработка тикера

```
2025-10-06 19:10:00 | INFO | app.process.report:_process_symbol:33 - Processing symbol: SBER
2025-10-06 19:10:00 | INFO | app.ingest.moex_client:get_quote:62 - Fetching quote for SBER
2025-10-06 19:10:01 | INFO | app.ingest.moex_client:get_quote:95 - Quote for SBER: {'price': 290.7}
2025-10-06 19:10:01 | INFO | app.ingest.moex_client:get_dividends:123 - Fetching dividends for SBER
2025-10-06 19:10:02 | INFO | app.ingest.moex_client:get_dividends:180 - Dividends TTM for SBER: 34.84 RUB
2025-10-06 19:10:05 | INFO | app.process.report:_process_symbol:69 - Successfully processed SBER: price=290.7, signals=2
```

### Ошибка при обработке

```
2025-10-06 19:10:10 | INFO | app.process.report:_process_symbol:33 - Processing symbol: YNDX
2025-10-06 19:10:10 | INFO | app.ingest.moex_client:get_quote:62 - Fetching quote for YNDX
2025-10-06 19:10:11 | ERROR | app.ingest.moex_client:get_quote:101 - Error fetching quote for YNDX: No candle data found
2025-10-06 19:10:11 | ERROR | app.process.report:_process_symbol:73 - Failed to process YNDX: No candle data found
```

### Сводка по завершению задачи

```
2025-10-06 19:11:30 | INFO | app.scheduler.daily_job:run_daily_job:56 - DAILY JOB COMPLETED SUCCESSFULLY
2025-10-06 19:11:30 | INFO | app.scheduler.daily_job:run_daily_job:57 -   Duration: 90.5s
2025-10-06 19:11:30 | INFO | app.scheduler.daily_job:run_daily_job:58 -   Processed: 15 symbols
2025-10-06 19:11:30 | INFO | app.scheduler.daily_job:run_daily_job:59 -   Successful: 13
2025-10-06 19:11:30 | INFO | app.scheduler.daily_job:run_daily_job:60 -   Failed: 2
2025-10-06 19:11:30 | INFO | app.scheduler.daily_job:run_daily_job:61 -   Total signals: 22
```

---

## Анализ логов

### Просмотр в реальном времени

```bash
# Windows PowerShell
Get-Content data/logs/app.log -Wait -Tail 50

# Linux/Mac
tail -f data/logs/app.log
```

### Фильтрация по уровню

```bash
# Только ошибки
grep "ERROR" data/logs/app.log

# Только для конкретного тикера
grep "SBER" data/logs/app.log
```

### Парсинг JSON логов

```python
import json

with open('data/logs/app.json.log') as f:
    for line in f:
        log = json.loads(line)
        if log['level'] == 'ERROR':
            print(f"{log['timestamp']}: {log['message']}")
```

---

## Troubleshooting

### Логи не создаются

1. Проверьте права доступа к директории `data/logs/`
2. Проверьте переменную `LOG_FILE` в `.env`

### Слишком много логов

```env
LOG_LEVEL=WARNING  # Логировать только WARNING и ERROR
```

### Недостаточно информации

```env
DEBUG=true  # Включить детальное логирование
```

### Логи занимают много места

```env
LOG_ROTATION=5 MB      # Чаще ротировать
LOG_RETENTION=7 days   # Меньше хранить
```

---

## Best Practices

1. **Используйте правильные уровни:**
   - INFO для обычных операций
   - DEBUG для детальной отладки
   - WARNING для потенциальных проблем
   - ERROR для реальных ошибок

2. **Добавляйте контекст:**
   ```python
   logger.bind(ticker="SBER").info("Processing")
   ```

3. **Логируйте время выполнения:**
   ```python
   with log_operation("expensive_operation"):
       # Автоматически логируется время
       process_data()
   ```

4. **Не логируйте чувствительные данные**

5. **Используйте structured logging (JSON) для автоматического анализа**

