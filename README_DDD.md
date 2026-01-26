# 🏗️ DDD Миграция - Быстрый старт

## ✅ Что уже сделано

### Фаза 1: Базовая структура DDD

1. **Value Objects** (`app/domain/stock_analysis/value_objects/`)
   - `Price` - цена с валидацией и сравнением
   - `DividendYield` - дивидендная доходность
   - `Signal` - торговые сигналы

2. **Доменные сущности** (`app/domain/stock_analysis/entities/`)
   - `Stock` - акция с бизнес-правилами

3. **Репозитории** (`app/domain/stock_analysis/repositories/`)
   - `StockRepository` - интерфейс
   - `StockRepositoryImpl` - реализация через MOEX

4. **Доменные сервисы** (`app/domain/stock_analysis/services/`)
   - `MetricsCalculator` - расчёт метрик

5. **Use Cases** (`app/application/stock_analysis/`)
   - `GenerateReportUseCase` - генерация отчёта

6. **DI Container** (`app/application/dependencies.py`)
   - Настроен dependency-injector

---

## 🚀 Как использовать

### Пример 1: Использование Value Objects

```python
from app.domain.stock_analysis.value_objects import Price, DividendYield

# Создание цены
price = Price(value=250.0, currency="RUB")
print(price)  # "250.00 RUB"

# Сравнение цен
price2 = Price(value=280.0)
if price < price2:
    print("Цена ниже")
    
# Процентная разница
discount = price.percentage_diff(price2)
print(f"Дисконт: {discount:.2f}%")

# Дивидендная доходность
dy = DividendYield(value=8.5)
if dy.is_high(threshold=8.0):
    print("Высокая доходность!")
```

### Пример 2: Использование доменной сущности

```python
from app.domain.stock_analysis.entities import Stock
from app.domain.stock_analysis.value_objects import Price, DividendYield

# Создание акции
stock = Stock(
    symbol="SBER",
    price=Price(value=250.0),
    dividend_yield=DividendYield(value=8.5),
    sma_200=Price(value=280.0),
    signals=[]
)

# Использование бизнес-правил
if stock.is_undervalued():
    print("Акция недооценена!")
    
if stock.has_high_dividend_yield(8.0):
    print("Высокая дивидендная доходность!")

discount = stock.discount_to_sma200()
print(f"Дисконт к SMA200: {discount:.2f}%")
```

### Пример 3: Использование Use Case

```python
import asyncio
from app.application.dependencies import container

async def generate_report():
    # Получаем use case из контейнера
    use_case = container.generate_report_use_case()
    
    # Генерируем отчёт
    report = await use_case.execute(symbols=["SBER", "VTBR"])
    
    print(f"Обработано тикеров: {len(report['universe'])}")
    return report

# Запуск
asyncio.run(generate_report())
```

### Пример 4: Полный пример

См. `examples/ddd_example.py`

```bash
python examples/ddd_example.py
```

---

## 📁 Структура

```
app/
├── domain/                    # Domain Layer
│   └── stock_analysis/        # Bounded Context
│       ├── entities/          # Stock
│       ├── value_objects/     # Price, DividendYield, Signal
│       ├── services/          # MetricsCalculator
│       └── repositories/      # StockRepository (interface)
│
├── application/               # Application Layer
│   ├── stock_analysis/        # Use Cases
│   │   └── generate_report_use_case.py
│   └── dependencies.py        # DI Container
│
└── infrastructure/            # Infrastructure Layer
    └── persistence/
        └── repositories/
            └── stock_repository_impl.py  # Реализация
```

---

## 🔄 Интеграция со старым кодом

### Вариант 1: Постепенная миграция

Старый код продолжает работать, новый использует DDD:

```python
# Старый способ (продолжает работать)
from app.process.report import ReportGenerator
generator = ReportGenerator()
report = generator.generate_and_save()

# Новый способ (DDD)
from app.application.dependencies import container
use_case = container.generate_report_use_case()
report = await use_case.execute(symbols=["SBER"])
```

### Вариант 2: Адаптер

Создать адаптер, который использует новый Use Case:

```python
class ReportGeneratorAdapter:
    """Адаптер для совместимости со старым кодом."""
    
    def __init__(self):
        self._use_case = container.generate_report_use_case()
    
    def generate_and_save(self):
        # Использует новый use case
        report = asyncio.run(self._use_case.execute(...))
        # Сохраняет в старом формате
        # ...
```

---

## 🧪 Тестирование

### Тест Value Objects

```python
def test_price_comparison():
    price1 = Price(value=100.0)
    price2 = Price(value=200.0)
    
    assert price1 < price2
    assert price1.percentage_diff(price2) == -50.0
```

### Тест доменной сущности

```python
def test_stock_is_undervalued():
    stock = Stock(
        symbol="SBER",
        price=Price(value=250.0),
        sma_200=Price(value=280.0),
        signals=[]
    )
    
    assert stock.is_undervalued() == True
    assert stock.discount_to_sma200() < 0
```

### Тест Use Case (с моками)

```python
from unittest.mock import Mock, AsyncMock

def test_generate_report_use_case():
    # Создаём мок репозитория
    mock_repo = Mock()
    mock_repo.get_all = AsyncMock(return_value=[
        Stock(symbol="SBER", price=Price(250.0), ...)
    ])
    
    use_case = GenerateReportUseCase(
        stock_repository=mock_repo,
        ...
    )
    
    report = asyncio.run(use_case.execute(["SBER"]))
    assert len(report['universe']) == 1
```

---

## ✅ Интеграция завершена!

1. **API Integration** ✅
   - Создан endpoint `/api/report/generate` с DDD
   - Настроен DI в FastAPI
   - Создан адаптер для совместимости

2. **Планировщик** ✅
   - Добавлена опция использования DDD
   - `DailyJobScheduler(use_ddd=True)`

3. **Тестирование** ✅
   - Тесты для Value Objects
   - Тесты для доменной сущности
   - Тесты для Use Case

## 📚 Следующие шаги

1. **Миграция других модулей**
   - `reco/` → Recommendation Context
   - `predictor/` → Event Prediction Context
   - `portfolio/` → Portfolio Management Context

2. **Улучшения**
   - Добавить Domain Events
   - Добавить Unit of Work pattern
   - Добавить CQRS (если нужно)

---

## ❓ FAQ

**Q: Нужно ли переписывать весь код сразу?**  
A: Нет! Можно мигрировать постепенно, старый код продолжит работать.

**Q: Как тестировать без внешних зависимостей?**  
A: Используйте моки репозиториев. Доменная логика не зависит от MOEX API.

**Q: Можно ли использовать Pydantic модели?**  
A: Да, для DTO (Data Transfer Objects) в API. Но в домене используйте Value Objects и Entities.

---

*Документ обновлён: 2026-01-26*
