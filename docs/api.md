# API Документация

Stock Analytics REST API для доступа к данным анализа акций.

## Запуск сервера

```bash
python run_server.py
```

Или напрямую через uvicorn:

```bash
uvicorn app.api.server:app --reload --host 0.0.0.0 --port 8000
```

## Базовый URL

```
http://localhost:8000
```

## Интерактивная документация

После запуска сервера:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Эндпоинты

### 1. Проверка здоровья

**GET** `/health`

Проверка состояния сервера.

**Ответ:**
```json
{
  "ok": true,
  "timestamp": "2025-10-06T23:00:00",
  "version": "0.1.0"
}
```

---

### 2. Список тикеров

**GET** `/tickers`

Получить список всех отслеживаемых тикеров из конфигурации.

**Ответ:**
```json
{
  "ok": true,
  "data": ["SBER", "GAZP", "LKOH", "NLMK", "MGNT", ...]
}
```

---

### 3. Последний отчёт

**GET** `/report/today`

Получить последний сгенерированный отчёт анализа.

**Ответ (успех):**
```json
{
  "ok": true,
  "data": {
    "generated_at": "2025-10-06T19:10:00",
    "universe": ["SBER", "GAZP", ...],
    "by_symbol": {
      "SBER": {
        "price": 290.5,
        "lot": 10,
        "div_ttm": 34.84,
        "dy_pct": 11.98,
        "sma_20": 286.27,
        "sma_50": 283.62,
        "sma_200": 288.21,
        "high_52w": 303.8,
        "low_52w": 279.14,
        "dist_52w_low_pct": 4.14,
        "dist_52w_high_pct": 4.51,
        "signals": ["PRICE_ABOVE_SMA200", "DY_GT_TARGET"],
        "meta": {
          "board": "TQBR",
          "error": null,
          "updated_at": "2025-10-06T19:05:00"
        }
      }
    }
  },
  "error": null
}
```

**Ответ (нет отчёта):**
```json
{
  "ok": false,
  "data": null,
  "error": "No report found. Generate report first."
}
```

---

### 4. Сводка по отчёту

**GET** `/report/summary`

Получить краткую статистику по отчёту.

**Ответ:**
```json
{
  "ok": true,
  "data": {
    "generated_at": "2025-10-06T19:10:00",
    "total_symbols": 15,
    "successful": 13,
    "failed": 2,
    "high_dividend_tickers": [
      {"symbol": "VTBR", "dy_pct": 37.75},
      {"symbol": "MOEX", "dy_pct": 26.79},
      {"symbol": "MGNT", "dy_pct": 18.44}
    ],
    "tickers_with_signals": 13,
    "total_signals": 22
  }
}
```

---

### 5. Сохранить портфель

**POST** `/portfolio`

Сохранить пользовательский портфель.

**Тело запроса:**
```json
{
  "name": "Основной портфель",
  "currency": "RUB",
  "cash": 50000.0,
  "positions": [
    {
      "symbol": "SBER",
      "quantity": 100,
      "avg_price": 265.30,
      "market": "moex",
      "type": "stock",
      "notes": "Голубые фишки"
    }
  ]
}
```

**Ответ:**
```json
{
  "ok": true,
  "message": "Portfolio saved successfully with 1 positions"
}
```

**Ошибка валидации:**
```json
{
  "detail": [
    {
      "loc": ["body", "positions", 0, "symbol"],
      "msg": "String should match pattern '^[A-Z0-9]+$'",
      "type": "string_pattern_mismatch"
    }
  ]
}
```

---

### 6. Просмотр портфеля

**GET** `/portfolio/view`

Получить сохранённый портфель.

**Ответ (успех):**
```json
{
  "ok": true,
  "data": {
    "name": "Основной портфель",
    "currency": "RUB",
    "cash": 50000.0,
    "positions": [
      {
        "symbol": "SBER",
        "quantity": 100,
        "avg_price": 265.30,
        "market": "moex",
        "type": "stock"
      }
    ],
    "created_at": "2025-10-06T18:00:00",
    "updated_at": "2025-10-06T19:00:00"
  },
  "error": null
}
```

**Ответ (нет портфеля):**
```json
{
  "ok": false,
  "data": null,
  "error": "No portfolio found. Create one first using POST /portfolio"
}
```

---

## Примеры использования

### cURL

```bash
# Health check
curl http://localhost:8000/health

# Список тикеров
curl http://localhost:8000/tickers

# Отчёт
curl http://localhost:8000/report/today

# Сводка
curl http://localhost:8000/report/summary

# Сохранить портфель
curl -X POST http://localhost:8000/portfolio \
  -H "Content-Type: application/json" \
  -d '{"currency":"RUB","positions":[{"symbol":"SBER","quantity":100}]}'

# Просмотр портфеля
curl http://localhost:8000/portfolio/view
```

### Python

```python
import requests

# Получить отчёт
response = requests.get("http://localhost:8000/report/today")
report = response.json()

if report['ok']:
    for symbol in report['data']['universe']:
        data = report['data']['by_symbol'][symbol]
        print(f"{symbol}: {data['price']} RUB, DY: {data['dy_pct']}%")
```

---

## Коды ответов

- `200 OK` - Успешный запрос
- `400 Bad Request` - Ошибка в данных запроса
- `422 Unprocessable Entity` - Ошибка валидации Pydantic
- `500 Internal Server Error` - Внутренняя ошибка сервера

---

## Формат ответов

Все эндпоинты следуют стандартному формату:

**Успех:**
```json
{
  "ok": true,
  "data": { ... }
}
```

**Ошибка:**
```json
{
  "ok": false,
  "error": "Error description"
}
```

