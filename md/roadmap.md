Отлично, идём по «быстрому» пути: **moexalgo + pandas-ta + APScheduler + FastAPI**. Ниже — пошаговый план без кода (чек-листы для Cursor). Если где-то захочешь — дам сниппеты.

---

# 0) Каркас проекта

**Структура**

```
app/
  config/
  ingest/
  process/
  store/
  api/
  scheduler/
  utils/
data/
docs/
tests/
```

**Файлы-заготовки**

* `requirements.txt` (список ниже)
* `.env.example` (TZ, LOG_LEVEL)
* `README.md` (как запустить)

**Зависимости (в requirements.txt)**

* `moexalgo` — данные MOEX
* `pandas`, `pandas-ta`, `numpy`
* `fastapi`, `uvicorn`
* `python-dotenv`, `pydantic`
* `APScheduler`
* `pyyaml`
* `orjson` (быстрый JSON), `pyarrow` (parquet)
* (опц.) `tenacity` (ретраи), `loguru` (логи)

---

# 1) Конфигурация

**Файл:** `app/config/config.yaml`
**Что описать:**

* `base_currency: RUB`
* `universe:` список тикеров `{symbol: SBER, market: moex}` (10–15 штук: SBER, GAZP, LKOH, NLMK, MGNT, YNDX, FIVE, MOEX, TATN, GMKN…)
* `windows: {sma: [20,50,200]}`
* `dividend_target_pct: 8`
* `output: {analysis_file: data/analysis.json, reports_dir: data/reports}`
* `schedule: {daily_time: "19:10", tz: "Europe/Moscow"}`
* `rate_limit: {per_symbol_sleep_sec: 0.4}`

**Проверка:** парсится, пути существуют.

---

# 2) Контракты (схемы данных)

**В `docs/` опиши JSON-схемы:**

* `schema.analysis.json` (итог отчёта):

  * `generated_at`, `universe`, `by_symbol[SYM]` с полями:

    * `price`, `lot`, `div_ttm`, `dy_pct`
    * `sma_20`, `sma_50`, `sma_200`
    * `dist_52w_low_pct`, `dist_52w_high_pct`
    * `signals` (массив строк)
    * `meta` (`board`, `error` если есть)
* `schema.portfolio.json` (вход портфеля)
* `schema.candle.json` (open, high, low, close, volume, begin, end)

**Проверка:** пример каждого JSON в `docs/examples/`.

---

# 3) Инжест через moexalgo

**Файл:** `app/ingest/moex_client.py`
**Что реализовать:**

* Инициализацию клиента moexalgo.
* Методы:

  1. `get_quote(symbol)` → цена (`LCURRENTPRICE`→`LAST`→`LEGALCLOSEPRICE`), лот, board.
  2. `get_dividends(symbol)` → сумма TTM (последние выплаты из ISS).
  3. `get_candles(symbol, days=400, interval='24h')` → дневные свечи (pandas DataFrame).

**Требования:**

* Таймауты, ретраи (можно на уровне moexalgo / tenacity).
* Пауза между тикерами: из конфига.
* Корректная нормализация столбцов и типов.

**Проверка:**

* На 3 тикерах получаются: актуальная цена, лот, 260+ свечей, дивиденды (если есть).

---

# 4) Хранилище

**Файл:** `app/store/io.py`
**Задачи:**

* `save_json(path, data)` (через orjson), `load_json(path)`
* `save_table_parquet(path, df)`, `load_table_parquet(path)`
* Структура сохранения:

  * `data/raw/{ticker}/candles.parquet`
  * `data/analysis.json`
  * `data/reports/YYYY-MM-DD.json`

**Проверка:** запись/чтение работают, директории создаются автоматически.

---

# 5) Метрики и сигналы

**Файл:** `app/process/metrics.py`
**Что посчитать:**

* SMA(20/50/200) по `close` (через pandas-ta)
* 52W high/low и расстояние в %:

  * `dist_52w_low_pct = (price / low52 - 1) * 100`
  * `dist_52w_high_pct = (high52 / price - 1) * 100`
* Дивиденды:

  * `div_ttm` из инжеста
  * `dy_pct = div_ttm / price * 100`
* Сигналы (строки):

  * `PRICE_BELOW_SMA200`
  * `SMA50_CROSS_UP_SMA200` (по последним двум точкам SMA50/200)
  * `DY_GT_TARGET` (если `dy_pct` ≥ из конфига)
  * (опц.) `VOL_SPIKE` (объём > 1.8× медианы 20д)

**Проверка:** ручная сверка на одном тикере, отсутствие делений на ноль.

---

# 6) Генерация отчёта

**Файл:** `app/process/report.py`
**Шаги:**

1. Идёшь по `universe`, собираешь quote/divs/candles.
2. Считаешь метрики, формируешь словарь по каждому тикеру.
3. Собираешь итоговый объект (`generated_at`, `universe`, `by_symbol`).
4. Пишешь `data/analysis.json` и дублируешь в `data/reports/DATE.json`.

**Краевые случаи:**

* Нет данных — пишешь `error` внутри `meta`, остальные поля `null`.

**Проверка:** валиден по схеме `schema.analysis.json`.

---

# 7) API слой (FastAPI)

**Файл:** `app/api/server.py`
**Эндпоинты:**

* `GET /health` → `{ok:true}`
* `GET /tickers` → список из конфига
* `GET /report/today` → содержимое `data/analysis.json`
* `POST /portfolio` → принимает JSON портфеля, сохраняет `data/portfolio.json`
* `GET /portfolio/view` → отдаёт сохранённый портфель

**Требования:**

* Стандартизируй ответы: `{ok: bool, data|error}`
* Простая валидация входа (pydantic).

**Проверка:** локальный запуск, ручные запросы через браузер/curl.

---

# 8) Планировщик

**Файл:** `app/scheduler/daily_job.py`
**Задачи:**

* Ежедневно по `schedule.daily_time` (в `Europe/Moscow`):

  1. Прогнать сбор данных по всем тикерам.
  2. Посчитать метрики.
  3. Записать `analysis.json` и отчёт за день.
* Использовать `APScheduler` (BackgroundScheduler).
* Логи успехов/ошибок.

**Проверка:** принудительный ручной запуск + автозапуск по времени.

---

# 9) Логи и настройки

**Файл:** `app/utils/logging.py`
**Сделать:**

* Конфиг логирования (уровни: DEBUG/INFO/WARN/ERROR из `.env`).
* Формат json-логов (время, модуль, сообщение, тикер).
* Вывод в файл `data/logs/app.log` + на консоль.

**Проверка:** видно ретраи/ошибки по тикерам и тайминги.

---

# 10) Тесты (без реального API)

**Каталог:** `tests/`
**Набор:**

* Фикстуры ответов ISS (JSON) в `tests/fixtures/`.
* `test_moex_client.py` — парсинг фикстур.
* `test_metrics.py` — SMA/52W/DY на синтетике.
* `test_report_schema.py` — проверка примера `analysis.json` на схему.

**Проверка:** тесты гоняются локально без сети.

---

# 11) Документация

**В `docs/`:**

* `run-local.md` — установка, запуск, эндпоинты.
* `faq.md` — типовые проблемы: пустые свечи, задержки ISS, лимиты.
* `roadmap.md` — что дальше (алерты, HTML-отчёты, облигации, ребаланс).

---

# 12) Критерии готовности MVP

* [ ] `analysis.json` успешно генерится для полного списка тикеров.
* [ ] Считаны SMA/52W/DY и базовые сигналы.
* [ ] API отдаёт `report/today`.
* [ ] Планировщик делает ежедневный прогон.
* [ ] Логи показывают ретраи и сводку по времени.
* [ ] Минимальные тесты проходят.

---

## Практика: как идти в Cursor

1. Создай структуру и пустые файлы по шагам 0–2.
2. Настрой `requirements.txt`, поставь окружение.
3. Реализуй ingest через moexalgo (quotes → candles → dividends).
4. Подключи `process/metrics`: посчитай SMA/DY/52W на 2–3 тикерах → сгенерируй первый `analysis.json`.
5. Добавь `store/io` для сохранения артефактов.
6. Запусти FastAPI и проверь `/health`, `/report/today`.
7. Включи APScheduler и убедись, что отчёт сам появляется в `data/reports/`.
8. Добей чек-лист MVP.

Если на каком-то шаге упремся — скажи номер шага, опишу точные команды/параметры и при необходимости дам готовые сниппеты под этот модуль.
