# Планировщик задач

Система автоматического обновления данных по расписанию.

## Конфигурация

Настройки планировщика в `app/config/config.yaml`:

```yaml
schedule:
  daily_time: "19:10"     # Время запуска (HH:MM)
  tz: "Europe/Moscow"     # Временная зона
```

---

## Режимы работы

### 1. С планировщиком (автоматический режим)

Запускает API сервер + планировщик. Задача выполняется автоматически по расписанию.

```bash
python run_with_scheduler.py
```

**Возможности:**
- API доступен на http://localhost:8000
- Автоматический запуск в 19:10 по Москве
- Ручной триггер через API: `POST /scheduler/run-now`
- Проверка статуса: `GET /scheduler/status`

### 2. Ручной запуск (разовый режим)

Выполняет задачу один раз и завершается. Без API сервера.

```bash
python run_job_once.py
```

**Использование:**
- Тестирование генерации отчёта
- Ручное обновление данных
- Запуск через cron/Task Scheduler

### 3. Только API (без планировщика)

Запускает только API сервер без автоматического обновления.

```bash
python run_server.py
```

---

## Ежедневная задача

При каждом запуске (автоматическом или ручном) выполняется:

1. **Сбор данных** по всем тикерам из universe
   - Текущие котировки
   - Дивиденды TTM
   - Исторические свечи (~400 дней)

2. **Расчёт метрик**
   - SMA (20/50/200)
   - 52W High/Low
   - Дивидендная доходность
   - Торговые сигналы

3. **Сохранение отчётов**
   - `data/analysis.json` — последний отчёт
   - `data/reports/YYYY-MM-DD.json` — архивная копия

4. **Логирование**
   - Время выполнения
   - Статистика успехов/ошибок
   - Количество сигналов

---

## API управления планировщиком

### Проверка статуса

**GET** `/scheduler/status`

```json
{
  "ok": true,
  "data": {
    "running": true,
    "jobs": [
      {
        "id": "daily_report_job",
        "name": "Daily Stock Analysis Report",
        "next_run_time": "2025-10-07T19:10:00+03:00",
        "trigger": "cron[hour='19', minute='10']"
      }
    ]
  }
}
```

### Ручной запуск

**POST** `/scheduler/run-now`

Запускает задачу немедленно (не дожидаясь расписания).

```bash
curl -X POST http://localhost:8000/scheduler/run-now
```

**Ответ:**
```json
{
  "ok": true,
  "message": "Job completed successfully"
}
```

---

## Логирование

Все события записываются в:
- **Консоль** (цветной вывод)
- **Файл** `data/logs/app.log` (с ротацией)

**Уровни логов:**
- `INFO` — общая информация о выполнении
- `ERROR` — ошибки при обработке тикеров
- `DEBUG` — детальная информация (только в файл)

**Пример лога успешного выполнения:**
```
2025-10-06 19:10:00 | INFO | STARTING DAILY JOB
2025-10-06 19:10:00 | INFO | Processing 15 symbols: SBER, GAZP, ...
2025-10-06 19:10:05 | INFO | Successfully processed SBER: price=290.7
...
2025-10-06 19:11:30 | INFO | DAILY JOB COMPLETED SUCCESSFULLY
2025-10-06 19:11:30 | INFO |   Duration: 90.5s
2025-10-06 19:11:30 | INFO |   Processed: 15 symbols
2025-10-06 19:11:30 | INFO |   Successful: 13
2025-10-06 19:11:30 | INFO |   Failed: 2
2025-10-06 19:11:30 | INFO |   Total signals: 22
```

---

## Интеграция с системным планировщиком

### Windows Task Scheduler

Создайте задачу для ежедневного запуска:

```powershell
# Запуск run_job_once.py каждый день в 19:10
schtasks /create /tn "Stock Analytics" /tr "python D:\path\to\run_job_once.py" /sc daily /st 19:10
```

### Linux cron

Добавьте в crontab:

```bash
# Каждый день в 19:10 по Москве
10 19 * * * cd /path/to/stock_analytics && python run_job_once.py >> logs/cron.log 2>&1
```

---

## Мониторинг

### Проверка последнего отчёта

```bash
# Через API
curl http://localhost:8000/report/summary

# Проверка файла
ls -lh data/analysis.json
```

### Проверка логов

```bash
tail -f data/logs/app.log
```

### Статус планировщика

```bash
curl http://localhost:8000/scheduler/status
```

---

## Troubleshooting

### Задача не выполняется

1. Проверьте статус планировщика
2. Проверьте временную зону системы
3. Проверьте логи: `data/logs/app.log`

### Ошибки при генерации отчёта

1. Проверьте подключение к интернету
2. Проверьте доступность MOEX API
3. Запустите ручной тест: `python run_job_once.py`

### Планировщик не останавливается

Используйте Ctrl+C или отправьте SIGTERM сигнал процессу.

