# Управление портфелем

Руководство по работе с портфелем в Stock Analytics.

---

## Способы управления

### 1. Через скрипт manage_portfolio.py (Рекомендуется)

Самый простой и безопасный способ.

#### Показать портфель

```bash
python manage_portfolio.py show
```

**Вывод:**
```
================================================================================
ТЕКУЩИЙ ПОРТФЕЛЬ
================================================================================

Название: Основной портфель
Валюта: RUB
Свободные средства: 50,000.00 RUB

Позиций: 3

--------------------------------------------------------------------------------
Тикер      Количество   Ср. цена     Сумма           Заметки
--------------------------------------------------------------------------------
SBER       100          265.30       26,530.00       Голубые фишки
GAZP       50           120.00       6,000.00        -
LKOH       10           6000.00      60,000.00       -
--------------------------------------------------------------------------------
Общая стоимость позиций: 92,530.00 RUB
Всего с кешем: 142,530.00 RUB
```

#### Создать новый (интерактивно)

```bash
python manage_portfolio.py create
```

Скрипт задаст вопросы:
- Название портфеля
- Валюта
- Свободные средства
- Позиции (тикер, количество, цена)

#### Создать из шаблона

```bash
python manage_portfolio.py template
```

Создаст готовый портфель с примерами.

#### Редактировать существующий

```bash
python manage_portfolio.py edit
```

Позволяет:
- Изменить название
- Добавить позицию
- Удалить позицию
- Изменить cash

---

### 2. Через REST API

#### Сохранить портфель

```bash
curl -X POST http://localhost:8000/api/portfolio \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Мой портфель",
    "currency": "RUB",
    "cash": 100000,
    "positions": [
      {
        "symbol": "SBER",
        "quantity": 100,
        "avg_price": 265.30,
        "type": "stock",
        "notes": "Голубые фишки"
      }
    ]
  }'
```

#### Просмотреть портфель

```bash
curl http://localhost:8000/api/portfolio/view
```

---

### 3. Через Python код

```python
from app.store.io import save_portfolio, load_portfolio
from datetime import datetime

# Создать портфель
portfolio_data = {
    "name": "Мой портфель",
    "currency": "RUB",
    "cash": 50000.0,
    "positions": [
        {
            "symbol": "SBER",
            "quantity": 100,
            "avg_price": 265.30,
            "market": "moex",
            "type": "stock",
            "notes": "Дивидендная стратегия"
        }
    ],
    "created_at": datetime.now().isoformat(),
    "updated_at": datetime.now().isoformat()
}

# Сохранить
save_portfolio(portfolio_data)

# Загрузить
portfolio = load_portfolio()
print(portfolio)
```

---

### 4. Ручное редактирование JSON (НЕ рекомендуется)

**Проблема:** Если вы редактируете `data/portfolio.json` вручную, тесты могут его перезаписать!

**Решение:**
1. Используйте `manage_portfolio.py` вместо ручного редактирования
2. Или НЕ запускайте `pytest tests/test_api.py` после ручных изменений

---

## Структура портфеля

### Минимальный портфель

```json
{
  "currency": "RUB",
  "positions": []
}
```

### Полный портфель

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
  ],
  "created_at": "2025-10-06T18:00:00",
  "updated_at": "2025-10-06T19:00:00"
}
```

### Поля позиции

- `symbol` (**обязательно**) — тикер (только A-Z и 0-9)
- `quantity` (**обязательно**) — количество (≥ 0)
- `avg_price` — средняя цена покупки
- `market` — рынок (по умолчанию "moex")
- `type` — тип инструмента ("stock", "bond", "etf", "currency")
- `notes` — заметки

---

## Примеры

### Дивидендная стратегия

```python
portfolio_data = {
    "name": "Дивидендный портфель",
    "currency": "RUB",
    "cash": 0,
    "positions": [
        {"symbol": "SBER", "quantity": 100, "avg_price": 265.30},
        {"symbol": "LKOH", "quantity": 10, "avg_price": 6000.00},
        {"symbol": "TATN", "quantity": 30, "avg_price": 580.00},
        {"symbol": "MTSS", "quantity": 40, "avg_price": 200.00}
    ]
}
```

### Голубые фишки

```python
portfolio_data = {
    "name": "Голубые фишки",
    "currency": "RUB",
    "cash": 25000.0,
    "positions": [
        {"symbol": "SBER", "quantity": 50, "avg_price": 270.00},
        {"symbol": "GAZP", "quantity": 40, "avg_price": 115.00},
        {"symbol": "LKOH", "quantity": 5, "avg_price": 6100.00},
        {"symbol": "GMKN", "quantity": 15, "avg_price": 120.00}
    ]
}
```

---

## Анализ портфеля

После создания портфеля можно анализировать его через API:

```python
import requests

# Загрузить портфель
portfolio_resp = requests.get('http://localhost:8000/api/portfolio/view')
portfolio = portfolio_resp.json()['data']

# Загрузить отчёт
report_resp = requests.get('http://localhost:8000/api/report/today')
report = report_resp.json()['data']

# Посчитать текущую стоимость
total_value = portfolio['cash']

for position in portfolio['positions']:
    symbol = position['symbol']
    quantity = position['quantity']
    
    # Текущая цена из отчёта
    current_price = report['by_symbol'][symbol]['price']
    
    # Стоимость позиции
    position_value = quantity * current_price
    total_value += position_value
    
    # P&L
    avg_price = position.get('avg_price', 0)
    if avg_price:
        profit = (current_price - avg_price) * quantity
        profit_pct = ((current_price / avg_price) - 1) * 100
        
        print(f"{symbol}: {profit:+,.2f} RUB ({profit_pct:+.2f}%)")

print(f"\nОбщая стоимость портфеля: {total_value:,.2f} RUB")
```

---

## Troubleshooting

### Портфель сбрасывается после запуска тестов

**Проблема:** После `pytest tests/` ваш портфель заменяется тестовыми данными.

**Решение:**
- ✅ **ИСПРАВЛЕНО!** Теперь тесты используют моки и не трогают реальный файл
- Перезапустите тесты: `pytest tests/test_api.py -v`

### Ошибка валидации при сохранении

**Проблема:** API возвращает 422 Validation Error.

**Причины:**
- Тикер содержит спецсимволы (только A-Z, 0-9)
- Отрицательное количество
- Неверный тип данных

**Решение:**
```python
# Правильно
{"symbol": "SBER", "quantity": 100}

# Неправильно
{"symbol": "sber!", "quantity": -10}
```

### Файл не найден

**Проблема:** `load_portfolio()` возвращает `None`.

**Решение:**
- Создайте портфель: `python manage_portfolio.py create`
- Или через API: `POST /api/portfolio`

---

## Best Practices

1. **Используйте manage_portfolio.py** для изменений
2. **НЕ редактируйте** `data/portfolio.json` вручную
3. **Делайте бэкапы** перед большими изменениями
4. **Версионируйте** портфель в git (но добавьте в .gitignore sensitive данные)

---

## Будущие улучшения

Планируется добавить:
- [ ] Автоматический расчёт P&L
- [ ] Распределение по секторам
- [ ] Ребалансировка
- [ ] Импорт из брокерских отчётов
- [ ] История изменений портфеля

