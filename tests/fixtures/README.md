# Test Fixtures

Фикстуры для тестирования без реального доступа к MOEX API.

## Структура

- `iss_dividends_*.json` — моки ответов ISS API для дивидендов
- `iss_candles_*.json` — моки ответов для свечей

## Использование

```python
import json
from pathlib import Path

# Загрузка фикстуры
fixtures_dir = Path(__file__).parent / "fixtures"
with open(fixtures_dir / "iss_dividends_sber.json") as f:
    mock_data = json.load(f)
```

## Формат ISS API

### Дивиденды

URL: `https://iss.moex.com/iss/securities/{SECID}/dividends.json`

Структура:
```json
{
  "dividends": {
    "columns": ["secid", "isin", "registryclosedate", "value", "currencyid"],
    "data": [
      ["SBER", "RU0009029540", "2024-09-20", 34.84, "RUB"]
    ]
  }
}
```

### Свечи

Структура от moexalgo Ticker.candles():
```json
{
  "candles": {
    "columns": ["open", "close", "high", "low", "value", "volume", "begin", "end"],
    "data": [...]
  }
}
```

