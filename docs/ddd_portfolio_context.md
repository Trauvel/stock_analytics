# 💼 Portfolio Management Context - DDD Миграция

## ✅ Что сделано

### Domain Layer

#### Value Objects
- **`Currency`** - валюта (RUB, USD, EUR)
  - Валидация кода валюты (3 символа)
  - Методы `rub()`, `usd()`, `from_string()`

- **`Money`** - денежная сумма с валютой
  - Арифметические операции (`+`, `-`, `*`)
  - Сравнение сумм
  - Валидация валюты при операциях

- **`Quantity`** - количество акций/инструментов
  - Арифметические операции
  - Валидация (не может быть отрицательным)

#### Entities
- **`Position`** - позиция в портфеле
  - `calculate_cost()` - расчёт стоимости позиции
  - `calculate_pnl()` - расчёт прибыли/убытка
  - `calculate_pnl_percent()` - P&L в процентах
  - `add_quantity()`, `remove_quantity()` - изменение количества

- **`Portfolio`** - портфель инвестора
  - `total_positions_value()` - общая стоимость позиций
  - `total_value()` - общая стоимость портфеля (позиции + кеш)
  - `get_position()`, `has_position()` - работа с позициями
  - `add_position()` - добавление позиции (с объединением если уже есть)
  - `remove_position()` - удаление позиции
  - `update_cash()` - обновление кеша

### Application Layer

#### Use Cases
- **`GetPortfolioUseCase`** - получение портфеля
- **`SavePortfolioUseCase`** - сохранение портфеля
- **`AddPositionUseCase`** - добавление позиции
- **`RemovePositionUseCase`** - удаление позиции

### Infrastructure Layer

#### Repository
- **`PortfolioRepositoryImpl`** - реализация через файловое хранилище
  - Использует `app/store/io` для совместимости
  - Преобразует между доменными сущностями и JSON

### API Integration

#### Endpoints
- `POST /api/portfolio` - сохранение портфеля (DDD)
- `GET /api/portfolio/view` - получение портфеля (DDD)
- Fallback на старый код при ошибках

---

## 📁 Структура

```
app/
├── domain/
│   └── portfolio/                   # Portfolio Management Context
│       ├── entities/
│       │   ├── portfolio.py         # Portfolio entity
│       │   └── position.py           # Position entity
│       ├── value_objects/
│       │   ├── currency.py          # Currency
│       │   ├── money.py             # Money
│       │   └── quantity.py          # Quantity
│       └── repositories/
│           └── portfolio_repository.py  # Interface
│
├── application/
│   └── portfolio/
│       ├── get_portfolio_use_case.py
│       ├── save_portfolio_use_case.py
│       ├── add_position_use_case.py
│       └── remove_position_use_case.py
│
└── infrastructure/
    └── persistence/repositories/
        └── portfolio_repository_impl.py
```

---

## 🚀 Использование

### Через API

```bash
# Получить портфель
curl "http://localhost:8000/api/portfolio/view"

# Сохранить портфель
curl -X POST "http://localhost:8000/api/portfolio" \
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
        "type": "stock"
      }
    ]
  }'
```

### Через код

```python
from app.application.dependencies import container

# Получить портфель
get_use_case = container.get_portfolio_use_case()
portfolio = await get_use_case.execute()

if portfolio:
    print(f"Портфель: {portfolio.name}")
    print(f"Общая стоимость: {portfolio.total_value()}")
    print(f"Позиций: {len(portfolio.positions)}")

# Сохранить портфель
from app.domain.portfolio.entities.portfolio import Portfolio
from app.domain.portfolio.value_objects import Currency, Money
from app.domain.portfolio.entities.position import Position, PositionType
from app.domain.portfolio.value_objects import Quantity

portfolio = Portfolio(
    name="Мой портфель",
    currency=Currency.rub(),
    cash=Money(amount=100000.0, currency=Currency.rub()),
    positions=[
        Position(
            symbol="SBER",
            quantity=Quantity(value=100),
            avg_price=Money(amount=265.30, currency=Currency.rub()),
            position_type=PositionType.STOCK
        )
    ]
)

save_use_case = container.save_portfolio_use_case()
saved = await save_use_case.execute(portfolio)
```

---

## 📊 Бизнес-правила

### Портфель

1. **Валидация валюты**
   - Все позиции должны быть в валюте портфеля
   - Кеш должен быть в валюте портфеля

2. **Добавление позиции**
   - Если позиция уже есть, объединяются количества
   - Средняя цена пересчитывается как взвешенное среднее

3. **Расчёт стоимости**
   - Стоимость позиции = количество × средняя цена
   - Общая стоимость = сумма всех позиций + кеш

### Позиция

1. **P&L расчёт**
   - P&L = (текущая_цена - средняя_цена) × количество
   - P&L % = ((текущая_цена - средняя_цена) / средняя_цена) × 100

2. **Изменение количества**
   - Нельзя удалить больше, чем есть
   - Нельзя создать позицию с нулевым количеством

---

## 🔄 Интеграция с другими контекстами

### Stock Analysis Context

Portfolio может использовать данные из Stock Analysis для расчёта текущей стоимости:

```python
# Получаем акцию из Stock Analysis Context
stock = await stock_repository.get_by_symbol("SBER")

# Обновляем текущую стоимость позиции
if stock and stock.price:
    position.current_value = Money(
        amount=position.quantity.value * stock.price.value,
        currency=stock.price.currency
    )
```

### Recommendation Context

Portfolio может использоваться для персонализированных рекомендаций:

```python
# Получаем портфель
portfolio = await get_portfolio_use_case.execute()

# Генерируем рекомендации с учётом портфеля
recommendations = await generate_recommendations_use_case.execute(
    symbols=[pos.symbol for pos in portfolio.positions]
)
```

---

## 🧪 Тестирование

### Пример теста

```python
from app.domain.portfolio.entities.portfolio import Portfolio
from app.domain.portfolio.value_objects import Currency, Money, Quantity
from app.domain.portfolio.entities.position import Position, PositionType

def test_portfolio_total_value():
    portfolio = Portfolio(
        name="Test",
        currency=Currency.rub(),
        cash=Money(amount=50000.0, currency=Currency.rub()),
        positions=[
            Position(
                symbol="SBER",
                quantity=Quantity(value=100),
                avg_price=Money(amount=250.0, currency=Currency.rub()),
                position_type=PositionType.STOCK
            )
        ]
    )
    
    # Стоимость позиций: 100 × 250 = 25000
    # Общая стоимость: 25000 + 50000 = 75000
    assert portfolio.total_positions_value().amount == 25000.0
    assert portfolio.total_value().amount == 75000.0

def test_position_pnl():
    position = Position(
        symbol="SBER",
        quantity=Quantity(value=100),
        avg_price=Money(amount=250.0, currency=Currency.rub()),
        position_type=PositionType.STOCK
    )
    
    current_price = Money(amount=280.0, currency=Currency.rub())
    
    # P&L = (280 - 250) × 100 = 3000
    pnl = position.calculate_pnl(current_price)
    assert pnl.amount == 3000.0
    
    # P&L % = ((280 - 250) / 250) × 100 = 12%
    pnl_pct = position.calculate_pnl_percent(current_price)
    assert pnl_pct == 12.0
```

---

## ✅ Преимущества

1. **Чёткое разделение ответственности**
   - Portfolio не знает о файловой системе
   - Бизнес-правила инкапсулированы в сущностях

2. **Тестируемость**
   - Можно легко создать mock репозитория
   - Бизнес-правила тестируются изолированно

3. **Явные бизнес-правила**
   - Все правила в методах сущностей
   - Легко понять логику работы

4. **Типобезопасность**
   - Value Objects предотвращают ошибки
   - Currency, Money, Quantity валидируются

5. **Инкапсуляция**
   - Позиции не могут быть созданы с невалидными данными
   - Портфель гарантирует консистентность валют

---

*Документ создан: 2026-01-26*
