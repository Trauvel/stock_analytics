# 🚀 DDD Улучшения - Domain Events и Unit of Work

## ✅ Что реализовано

### 1. Domain Events

#### Базовая инфраструктура
- **`DomainEvent`** - базовый класс для всех событий
  - `event_id` - уникальный идентификатор
  - `occurred_at` - время возникновения
  - `aggregate_id` - идентификатор агрегата
  - `to_dict()` - сериализация

- **`DomainEventPublisher`** - публикатор событий
  - `subscribe()` - подписка на события
  - `publish()` - публикация события
  - Глобальный экземпляр через `get_event_publisher()`

- **`Entity`** - базовый класс для сущностей
  - `add_domain_event()` - добавление события
  - `get_domain_events()` - получение событий
  - `publish_events()` - публикация всех событий

#### Stock Analysis Events
- **`StockAnalyzed`** - акция проанализирована
- **`StockPriceChanged`** - цена акции изменилась

#### Portfolio Events
- **`PortfolioCreated`** - портфель создан
- **`PositionAdded`** - позиция добавлена
- **`PositionRemoved`** - позиция удалена
- **`PortfolioValueChanged`** - стоимость портфеля изменилась

#### Event Handlers
- Обработчики для всех событий в `app/infrastructure/events/event_handlers.py`
- Автоматическая регистрация при инициализации DI контейнера
- Логирование всех событий

### 2. Unit of Work Pattern

#### Базовый интерфейс
- **`UnitOfWork`** - абстрактный класс
  - `__enter__()`, `__exit__()` - контекстный менеджер
  - `commit()` - фиксация изменений
  - `rollback()` - откат изменений

#### Реализации
- **`StockAnalysisUnitOfWork`** - для Stock Analysis Context
- **`PortfolioUnitOfWork`** - для Portfolio Management Context
  - Кеширование портфеля в рамках транзакции
  - Автоматическая публикация событий при commit

---

## 📁 Структура

```
app/
├── domain/
│   └── shared/                      # Общие компоненты
│       ├── domain_event.py          # DomainEvent, DomainEventPublisher
│       ├── entity.py                 # Entity (базовый класс)
│       └── unit_of_work.py          # UnitOfWork, реализации
│
├── domain/
│   ├── stock_analysis/
│   │   └── events/
│   │       └── stock_events.py       # StockAnalyzed, StockPriceChanged
│   │
│   └── portfolio/
│       └── events/
│           └── portfolio_events.py  # PortfolioCreated, PositionAdded, etc.
│
└── infrastructure/
    └── events/
        └── event_handlers.py        # Обработчики событий
```

---

## 🚀 Использование

### Domain Events

#### Публикация событий в сущности

```python
from app.domain.portfolio.entities.portfolio import Portfolio
from app.domain.portfolio.value_objects import Currency, Money
from app.domain.portfolio.entities.position import Position, PositionType
from app.domain.portfolio.value_objects import Quantity

# Создаём портфель
portfolio = Portfolio(
    name="Мой портфель",
    currency=Currency.rub(),
    cash=Money(amount=100000.0, currency=Currency.rub()),
    positions=[]
)

# Добавляем позицию (автоматически создаётся событие PositionAdded)
position = Position(
    symbol="SBER",
    quantity=Quantity(value=100),
    avg_price=Money(amount=250.0, currency=Currency.rub()),
    position_type=PositionType.STOCK
)

updated_portfolio = portfolio.add_position(position)

# Публикуем события
updated_portfolio.publish_events()
# События автоматически обработаются зарегистрированными handlers
```

#### Подписка на события

```python
from app.domain.shared.domain_event import get_event_publisher
from app.domain.portfolio.events.portfolio_events import PositionAdded

def my_custom_handler(event: PositionAdded):
    print(f"Custom handler: {event.symbol} added!")

# Подписываемся
publisher = get_event_publisher()
publisher.subscribe(PositionAdded, my_custom_handler)
```

### Unit of Work

#### Использование для Portfolio

```python
from app.domain.shared.unit_of_work import PortfolioUnitOfWork
from app.application.dependencies import container

# Используем Unit of Work
async def update_portfolio():
    uow = PortfolioUnitOfWork(container.portfolio_repository())
    
    with uow:
        # Получаем портфель (кешируется)
        portfolio = await uow.get_portfolio()
        
        if portfolio:
            # Добавляем позицию
            new_position = Position(...)
            updated = portfolio.add_position(new_position)
            
            # Сохраняем в кеш
            await uow.save_portfolio(updated)
        
        # При выходе из with автоматически делается commit
        # Все события публикуются, портфель сохраняется
```

#### Использование для Stock Analysis

```python
from app.domain.shared.unit_of_work import StockAnalysisUnitOfWork
from app.application.dependencies import container

async def analyze_stocks():
    uow = StockAnalysisUnitOfWork(container.stock_repository())
    
    with uow:
        # Получаем акции
        stocks = await uow.stocks.get_all(["SBER", "VTBR"])
        
        # Обрабатываем...
        for stock in stocks:
            # События накапливаются в stock._domain_events
        
        # При выходе из with автоматически делается commit
```

---

## 📊 Преимущества

### Domain Events

1. **Отслеживание изменений**
   - Все важные изменения фиксируются как события
   - Можно восстановить историю изменений

2. **Развязка компонентов**
   - Сущности не знают о обработчиках
   - Легко добавлять новые обработчики

3. **Аудит и логирование**
   - Все события логируются
   - Можно сохранять в БД для аудита

4. **Интеграция с внешними системами**
   - События можно отправлять в очереди (RabbitMQ, Kafka)
   - Можно триггерить уведомления

### Unit of Work

1. **Транзакционность**
   - Все изменения фиксируются атомарно
   - Откат при ошибках

2. **Производительность**
   - Кеширование в рамках транзакции
   - Batch операции

3. **Консистентность**
   - Гарантия целостности данных
   - События публикуются только после commit

---

## 🔄 Примеры интеграции

### Use Case с Unit of Work

```python
class SavePortfolioUseCase:
    def __init__(self, portfolio_repository: PortfolioRepository):
        self._repo = portfolio_repository
    
    async def execute(self, portfolio: Portfolio) -> Portfolio:
        from app.domain.shared.unit_of_work import PortfolioUnitOfWork
        
        uow = PortfolioUnitOfWork(self._repo)
        
        with uow:
            # Сохраняем в кеш
            await uow.save_portfolio(portfolio)
            
            # При выходе из with:
            # 1. Публикуются все события
            # 2. Портфель сохраняется
            # 3. Если ошибка - rollback
        
        return portfolio
```

### Event Handler для сохранения истории

```python
from app.domain.portfolio.events.portfolio_events import PositionAdded
from app.domain.shared.domain_event import get_event_publisher

def save_to_history(event: PositionAdded):
    """Сохранить событие в историю."""
    import json
    from pathlib import Path
    
    history_file = Path("data/portfolio_history.json")
    
    # Загружаем историю
    if history_file.exists():
        with open(history_file, 'r') as f:
            history = json.load(f)
    else:
        history = []
    
    # Добавляем событие
    history.append(event.to_dict())
    
    # Сохраняем
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2)

# Подписываемся
publisher = get_event_publisher()
publisher.subscribe(PositionAdded, save_to_history)
```

---

## 🧪 Тестирование

### Тест Domain Events

```python
from app.domain.portfolio.events.portfolio_events import PositionAdded
from app.domain.shared.domain_event import DomainEventPublisher

def test_event_publishing():
    publisher = DomainEventPublisher()
    events_received = []
    
    def handler(event):
        events_received.append(event)
    
    publisher.subscribe(PositionAdded, handler)
    
    event = PositionAdded(symbol="SBER", quantity=100, avg_price=250.0)
    publisher.publish(event)
    
    assert len(events_received) == 1
    assert events_received[0].symbol == "SBER"
```

### Тест Unit of Work

```python
from app.domain.shared.unit_of_work import PortfolioUnitOfWork
from unittest.mock import Mock, AsyncMock

def test_unit_of_work_commit():
    mock_repo = Mock()
    mock_repo.save = AsyncMock()
    
    uow = PortfolioUnitOfWork(mock_repo)
    
    with uow:
        portfolio = Portfolio(...)
        await uow.save_portfolio(portfolio)
        # При выходе из with должен быть вызван commit
    
    # Проверяем что save был вызван
    mock_repo.save.assert_called_once()
```

---

## 📚 Следующие шаги

1. **Event Store**
   - Сохранение всех событий в БД
   - Event Sourcing для восстановления состояния

2. **Асинхронная обработка**
   - Отправка событий в очереди
   - Background workers для обработки

3. **CQRS**
   - Разделение на команды (write) и запросы (read)
   - Оптимизация для чтения

---

*Документ создан: 2026-01-26*
