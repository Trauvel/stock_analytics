# 🏗️ Анализ архитектуры и рекомендации по переходу на DDD

## 📊 Текущая архитектура

### Структура проекта

```
app/
├── api/              # Presentation Layer (FastAPI)
├── config/           # Configuration
├── ingest/            # Infrastructure (MOEX Client)
├── process/           # Business Logic (Metrics, Reports)
├── predictor/         # Business Logic (Event Prediction)
├── reco/              # Business Logic (Recommendations)
├── scheduler/         # Infrastructure (Scheduler)
├── store/             # Infrastructure (Storage)
├── utils/             # Utilities
├── models.py          # Data Models (Pydantic)
└── main.py            # Application Entry Point
```

### Текущие проблемы

#### 1. **Смешение слоёв**
- API напрямую вызывает бизнес-логику и инфраструктуру
- Нет явного разделения на Domain, Application, Infrastructure
- Бизнес-правила разбросаны по модулям (`process/`, `predictor/`, `reco/`)

#### 2. **Тесная связанность**
- `ReportGenerator` напрямую использует `MOEXClient` и `MetricsCalculator`
- `reco/service.py` напрямую читает файлы из файловой системы
- Сложно тестировать из-за зависимостей от внешних сервисов

#### 3. **Отсутствие доменных сущностей**
- Данные представлены как Pydantic модели (DTO), а не доменные сущности
- Нет инкапсуляции бизнес-логики в сущностях
- Валидация и бизнес-правила смешаны

#### 4. **Нет явных границ контекстов**
- Все модули (`predictor`, `reco`, `process`) тесно связаны
- Нет четкого разделения на Bounded Contexts

---

## 🎯 Преимущества перехода на DDD

### 1. **Чёткое разделение ответственности**
- **Domain Layer**: Бизнес-логика, сущности, value objects
- **Application Layer**: Use cases, orchestration
- **Infrastructure Layer**: Внешние сервисы, хранилище
- **Presentation Layer**: API, UI

### 2. **Независимость доменной логики**
- Домен не зависит от инфраструктуры
- Легко менять реализации (MOEX → другой источник)
- Легко тестировать без моков внешних сервисов

### 3. **Явные доменные модели**
- `Stock`, `Portfolio`, `Recommendation` как сущности с поведением
- Value Objects: `Price`, `DividendYield`, `Signal`
- Доменные сервисы для сложной логики

### 4. **Bounded Contexts**
- **Stock Analysis Context**: Анализ акций, метрики
- **Recommendation Context**: Генерация рекомендаций
- **Event Prediction Context**: Предсказание событий
- **Portfolio Management Context**: Управление портфелем

---

## 📐 Предлагаемая DDD архитектура

### Структура по слоям

```
app/
├── domain/                    # Domain Layer (ядро)
│   ├── stock_analysis/        # Bounded Context: Анализ акций
│   │   ├── entities/
│   │   │   ├── stock.py       # Stock entity
│   │   │   └── candle.py      # Candle value object
│   │   ├── value_objects/
│   │   │   ├── price.py
│   │   │   ├── dividend_yield.py
│   │   │   └── signal.py
│   │   ├── services/
│   │   │   └── metrics_calculator.py
│   │   └── repositories/
│   │       └── stock_repository.py  # Interface
│   │
│   ├── recommendation/        # Bounded Context: Рекомендации
│   │   ├── entities/
│   │   │   └── recommendation.py
│   │   ├── services/
│   │   │   └── recommendation_engine.py
│   │   └── repositories/
│   │
│   ├── event_prediction/      # Bounded Context: Предсказания
│   │   ├── entities/
│   │   ├── services/
│   │   └── repositories/
│   │
│   └── portfolio/             # Bounded Context: Портфель
│       ├── entities/
│       │   ├── portfolio.py
│       │   └── position.py
│       └── repositories/
│
├── application/               # Application Layer (use cases)
│   ├── stock_analysis/
│   │   ├── generate_report_use_case.py
│   │   └── get_metrics_use_case.py
│   ├── recommendation/
│   │   └── generate_recommendations_use_case.py
│   └── portfolio/
│       └── manage_portfolio_use_case.py
│
├── infrastructure/            # Infrastructure Layer
│   ├── external/
│   │   └── moex/
│   │       └── moex_client.py
│   ├── persistence/
│   │   ├── repositories/
│   │   │   ├── stock_repository_impl.py
│   │   │   └── portfolio_repository_impl.py
│   │   └── storage/
│   │       └── file_storage.py
│   └── scheduling/
│       └── scheduler_service.py
│
├── presentation/              # Presentation Layer
│   ├── api/
│   │   ├── routes/
│   │   │   ├── stock_routes.py
│   │   │   ├── recommendation_routes.py
│   │   │   └── portfolio_routes.py
│   │   └── dependencies.py    # DI container
│   └── web/
│       └── static/
│
└── config/                    # Configuration
```

---

## 🔄 Примеры рефакторинга

### Пример 1: Stock Entity (Domain)

**Было** (`app/models.py`):
```python
class SymbolData(BaseModel):
    price: Optional[float] = None
    dy_pct: Optional[float] = None
    signals: List[SignalType] = []
```

**Станет** (`app/domain/stock_analysis/entities/stock.py`):
```python
from dataclasses import dataclass
from typing import List
from ..value_objects import Price, DividendYield, Signal

@dataclass
class Stock:
    """Доменная сущность акции."""
    symbol: str
    price: Price
    dividend_yield: DividendYield
    signals: List[Signal]
    
    def is_undervalued(self, sma200: Price) -> bool:
        """Бизнес-правило: акция недооценена."""
        return self.price < sma200
    
    def has_high_dividend_yield(self, threshold: float) -> bool:
        """Бизнес-правило: высокая дивидендная доходность."""
        return self.dividend_yield.value >= threshold
```

### Пример 2: Use Case (Application)

**Было** (`app/process/report.py`):
```python
class ReportGenerator:
    def __init__(self):
        self.client = MOEXClient()  # Прямая зависимость
        self.calculator = MetricsCalculator()
    
    def _process_symbol(self, symbol: str):
        quote = self.client.get_quote(symbol)  # Инфраструктура
        # ...
```

**Станет** (`app/application/stock_analysis/generate_report_use_case.py`):
```python
from app.domain.stock_analysis.repositories import StockRepository
from app.domain.stock_analysis.services import MetricsCalculator

class GenerateReportUseCase:
    """Use case для генерации отчёта."""
    
    def __init__(
        self,
        stock_repository: StockRepository,  # Интерфейс
        metrics_calculator: MetricsCalculator
    ):
        self._stock_repo = stock_repository
        self._metrics_calc = metrics_calculator
    
    async def execute(self, symbols: List[str]) -> AnalysisReport:
        """Выполнить use case."""
        stocks = []
        for symbol in symbols:
            stock = await self._stock_repo.get_by_symbol(symbol)
            metrics = self._metrics_calc.calculate(stock)
            stocks.append(metrics)
        
        return AnalysisReport(stocks=stocks)
```

### Пример 3: Repository Implementation (Infrastructure)

**Было**: Прямой вызов `MOEXClient` в бизнес-логике

**Станет** (`app/infrastructure/persistence/repositories/stock_repository_impl.py`):
```python
from app.domain.stock_analysis.repositories import StockRepository
from app.domain.stock_analysis.entities import Stock
from app.infrastructure.external.moex import MOEXClient

class StockRepositoryImpl(StockRepository):
    """Реализация репозитория через MOEX API."""
    
    def __init__(self, moex_client: MOEXClient):
        self._client = moex_client
    
    async def get_by_symbol(self, symbol: str) -> Stock:
        """Получить акцию по тикеру."""
        quote = await self._client.get_quote(symbol)
        dividends = await self._client.get_dividends(symbol)
        candles = await self._client.get_candles(symbol)
        
        return Stock.from_moex_data(symbol, quote, dividends, candles)
```

---

## ✅ План миграции

### Фаза 1: Подготовка (1-2 недели)
1. ✅ Создать структуру папок по DDD
2. ✅ Выделить доменные сущности из Pydantic моделей
3. ✅ Создать интерфейсы репозиториев
4. ✅ Настроить DI контейнер (dependency-injector)

### Фаза 2: Миграция Domain Layer (2-3 недели)
1. ✅ Создать Value Objects (Price, DividendYield, Signal)
2. ✅ Создать Entities (Stock, Portfolio, Recommendation)
3. ✅ Выделить Domain Services (MetricsCalculator → domain service)
4. ✅ Перенести бизнес-правила в сущности

### Фаза 3: Миграция Application Layer (2 недели)
1. ✅ Создать Use Cases для каждого сценария
2. ✅ Рефакторинг ReportGenerator → GenerateReportUseCase
3. ✅ Рефакторинг reco/service → GenerateRecommendationsUseCase

### Фаза 4: Миграция Infrastructure (1-2 недели)
1. ✅ Реализовать репозитории через интерфейсы
2. ✅ Обернуть MOEXClient в адаптер
3. ✅ Реализовать FileStorage через интерфейс

### Фаза 5: Миграция Presentation (1 неделя)
1. ✅ Обновить API routes для использования Use Cases
2. ✅ Настроить DI в FastAPI
3. ✅ Обновить тесты

---

## ⚠️ Риски и рекомендации

### Риски
1. **Большой объём работы**: ~6-10 недель рефакторинга
2. **Временная деградация**: Возможны баги во время миграции
3. **Обучение команды**: Нужно понимание DDD принципов

### Рекомендации
1. **Постепенная миграция**: Не переписывать всё сразу
2. **Сохранение обратной совместимости**: Старый API работает параллельно
3. **Тесты**: Покрыть тестами перед рефакторингом
4. **Документация**: Описать новую архитектуру

---

## 🤔 Стоит ли переходить?

### ✅ **ДА, если:**
- Планируете долгосрочную поддержку проекта (1+ год)
- Команда растёт (нужна понятная структура)
- Планируете добавлять новые фичи (легче расширять)
- Нужна независимость от внешних сервисов (легче тестировать)

### ❌ **НЕТ, если:**
- Проект небольшой и стабильный
- Нет времени на рефакторинг (6-10 недель)
- Команда не знакома с DDD
- Текущая архитектура работает и не вызывает проблем

---

## 📚 Рекомендуемые ресурсы

1. **Книги:**
   - "Domain-Driven Design" by Eric Evans
   - "Implementing Domain-Driven Design" by Vaughn Vernon

2. **Библиотеки для Python:**
   - `dependency-injector` - DI контейнер
   - `pydantic` - валидация (можно использовать для DTO)
   - `dataclasses` - для доменных сущностей

3. **Примеры проектов:**
   - FastAPI + DDD примеры на GitHub
   - Clean Architecture в Python

---

## 🎯 Вывод

**Текущая архитектура** работает, но имеет проблемы масштабируемости и тестируемости.

**DDD** решит эти проблемы, но потребует значительных усилий.

**Рекомендация**: Если проект будет развиваться и расти — **стоит переходить на DDD**. Если это стабильный MVP — можно оставить текущую архитектуру, но улучшить разделение слоёв.

---

*Документ создан: 2026-01-26*
