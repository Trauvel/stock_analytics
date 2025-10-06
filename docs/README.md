# Документация Stock Analytics

## 📚 Содержание

1. [Быстрый старт](quickstart.md)
2. [Конфигурация](configuration.md)
3. [API](api.md)
4. [Планировщик](scheduler.md)
5. [Логирование](logging.md)
6. [Web GUI](gui.md)
7. [Страница настроек GUI](settings_gui.md) ⭐ **NEW**
8. [FAQ](faq.md)
9. [Будущие улучшения](roadmap_future.md)

---

## Схемы данных

### 1. Analysis Report (`schema.analysis.json`)

Схема итогового отчёта по анализу акций.

**Основные поля:**
- `generated_at` — дата и время генерации отчёта
- `universe` — список анализируемых тикеров
- `by_symbol` — данные по каждому тикеру

**Данные по тикеру (`SymbolData`):**
- `price` — текущая цена
- `lot` — размер лота
- `div_ttm` — дивиденды за последние 12 месяцев
- `dy_pct` — дивидендная доходность в процентах
- `sma_20`, `sma_50`, `sma_200` — скользящие средние
- `high_52w`, `low_52w` — экстремумы за 52 недели
- `dist_52w_low_pct`, `dist_52w_high_pct` — расстояние до экстремумов
- `signals` — массив торговых сигналов
- `meta` — метаданные (board, error, updated_at)

**Торговые сигналы:**
- `PRICE_BELOW_SMA200` — цена ниже SMA200
- `PRICE_ABOVE_SMA200` — цена выше SMA200
- `SMA50_CROSS_UP_SMA200` — золотой крест (SMA50 пересекла SMA200 снизу вверх)
- `SMA50_CROSS_DOWN_SMA200` — крест смерти (SMA50 пересекла SMA200 сверху вниз)
- `DY_GT_TARGET` — дивидендная доходность выше целевой
- `VOL_SPIKE` — всплеск объёма
- `NEAR_52W_LOW` — близко к минимуму 52 недель
- `NEAR_52W_HIGH` — близко к максимуму 52 недель

**Пример:** см. `examples/analysis.json`

---

### 2. Portfolio (`schema.portfolio.json`)

Схема пользовательского портфеля.

**Основные поля:**
- `name` — название портфеля
- `currency` — базовая валюта (по умолчанию RUB)
- `cash` — свободные денежные средства
- `positions` — список позиций
- `created_at`, `updated_at` — временные метки

**Позиция (`Position`):**
- `symbol` — тикер инструмента
- `quantity` — количество в штуках
- `avg_price` — средняя цена покупки
- `market` — рынок (moex, spb и т.д.)
- `type` — тип инструмента (stock, bond, etf, currency)
- `notes` — заметки

**Пример:** см. `examples/portfolio.json`

---

### 3. Candle (`schema.candle.json`)

Схема свечных данных (OHLCV).

**Поля:**
- `open` — цена открытия
- `high` — максимальная цена
- `low` — минимальная цена
- `close` — цена закрытия
- `volume` — объём торгов в штуках
- `begin` — время начала свечи
- `end` — время окончания свечи
- `value` — объём в валюте (опционально)

**Пример:** см. `examples/candles.json`

---

## Примеры использования

### Загрузка конфигурации

```python
from app.config.loader import get_config

config = get_config()
print(f"Отслеживаем {len(config.universe)} тикеров")
```

### Работа с моделями

```python
from app.models import AnalysisReport, Portfolio
import json

# Загрузка отчёта
with open('data/analysis.json') as f:
    report = AnalysisReport(**json.load(f))

# Работа с портфелем
portfolio = Portfolio(
    name="Мой портфель",
    currency="RUB",
    cash=100000
)
```

---

## Файловая структура данных

```
data/
├── analysis.json           # Последний отчёт
├── portfolio.json          # Сохранённый портфель
├── reports/                # Архив отчётов
│   ├── 2025-10-06.json
│   └── 2025-10-05.json
└── raw/                    # Сырые данные
    ├── SBER/
    │   └── candles.parquet
    └── GAZP/
        └── candles.parquet
```

