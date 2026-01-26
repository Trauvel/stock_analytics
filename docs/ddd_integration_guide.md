# 🔌 Руководство по интеграции DDD

## ✅ Что уже интегрировано

### 1. API Endpoint

Новый endpoint `/api/report/generate` использует DDD Use Case:

```bash
# POST запрос для генерации отчёта через DDD
curl -X POST "http://localhost:8000/api/report/generate?symbols=SBER&symbols=VTBR"
```

### 2. Планировщик

Планировщик может использовать DDD адаптер:

```python
from app.scheduler.daily_job import DailyJobScheduler

# Использовать DDD
scheduler = DailyJobScheduler(use_ddd=True)

# Или старый способ
scheduler = DailyJobScheduler(use_ddd=False)  # по умолчанию
```

### 3. Адаптер для совместимости

`ReportGeneratorDDDAdapter` предоставляет интерфейс, совместимый со старым `ReportGenerator`:

```python
from app.process.report_ddd_adapter import ReportGeneratorDDDAdapter

adapter = ReportGeneratorDDDAdapter()
report = adapter.generate_and_save(save_daily=True)
```

---

## 🔄 Как переключиться на DDD

### Вариант 1: Постепенная миграция (рекомендуется)

Старый код продолжает работать, новый использует DDD:

```python
# Старый способ (продолжает работать)
from app.process.report import ReportGenerator
generator = ReportGenerator()
report = generator.generate_and_save()

# Новый способ (DDD)
from app.application.dependencies import container
use_case = container.generate_report_use_case()
report = await use_case.execute(symbols=["SBER", "VTBR"])
```

### Вариант 2: Использование адаптера

Заменить `ReportGenerator` на `ReportGeneratorDDDAdapter`:

```python
# Было
from app.process.report import ReportGenerator
generator = ReportGenerator()

# Стало
from app.process.report_ddd_adapter import ReportGeneratorDDDAdapter
generator = ReportGeneratorDDDAdapter()

# Интерфейс тот же!
report = generator.generate_and_save()
```

### Вариант 3: Прямое использование Use Case

Использовать Use Case напрямую:

```python
from app.application.dependencies import container
import asyncio

use_case = container.generate_report_use_case()
report = asyncio.run(use_case.execute(symbols=["SBER", "VTBR"]))
```

---

## 🧪 Тестирование

### Запуск тестов

```bash
# Все тесты DDD
pytest tests/test_ddd_*.py -v

# Только Value Objects
pytest tests/test_ddd_value_objects.py -v

# Только доменная сущность
pytest tests/test_ddd_stock.py -v

# Только Use Case
pytest tests/test_ddd_use_case.py -v
```

### Покрытие тестами

```bash
pytest tests/test_ddd_*.py --cov=app.domain --cov=app.application --cov-report=html
```

---

## 📊 Сравнение старого и нового подхода

### Старый подход

```python
from app.process.report import ReportGenerator

generator = ReportGenerator()
# Прямые зависимости от MOEXClient и MetricsCalculator
# Сложно тестировать
# Бизнес-логика смешана с инфраструктурой
report = generator.generate_and_save()
```

### Новый подход (DDD)

```python
from app.application.dependencies import container

use_case = container.generate_report_use_case()
# Чёткое разделение слоёв
# Легко тестировать (моки репозиториев)
# Бизнес-логика в домене
report = await use_case.execute(symbols=["SBER"])
```

---

## 🔧 Настройка DI

DI контейнер настроен в `app/application/dependencies.py`:

```python
from app.application.dependencies import container

# Получить use case
use_case = container.generate_report_use_case()

# Получить репозиторий
repo = container.stock_repository()

# Получить доменный сервис
calc = container.metrics_calculator()
```

### Настройка в FastAPI

DI автоматически настроен в `app/api/server.py`:

```python
from dependency_injector.wiring import inject, Provide

@app.post("/report/generate")
@inject
async def generate_report(
    use_case: GenerateReportUseCase = Provide[container.generate_report_use_case]
):
    report = await use_case.execute(symbols=["SBER"])
    return report
```

---

## 🚀 Следующие шаги

1. **Миграция других модулей**
   - `reco/` → Recommendation Context
   - `predictor/` → Event Prediction Context
   - `portfolio/` → Portfolio Management Context

2. **Улучшения**
   - Добавить Domain Events для отслеживания изменений
   - Добавить Unit of Work pattern для транзакций
   - Добавить CQRS если нужна оптимизация чтения/записи

3. **Оптимизация**
   - Кеширование в репозитории
   - Batch операции для получения нескольких акций
   - Асинхронные операции для параллельной обработки

---

## ❓ FAQ

**Q: Можно ли использовать оба подхода одновременно?**  
A: Да! Старый код продолжает работать. Можно мигрировать постепенно.

**Q: Как переключить планировщик на DDD?**  
A: Измените `DailyJobScheduler(use_ddd=True)` в `app/scheduler/daily_job.py` или передайте параметр при создании.

**Q: Нужно ли обновлять тесты?**  
A: Старые тесты продолжают работать. Новые тесты для DDD находятся в `tests/test_ddd_*.py`.

**Q: Как добавить новый Use Case?**  
A: 
1. Создайте Use Case в `app/application/<context>/`
2. Добавьте в DI контейнер в `app/application/dependencies.py`
3. Создайте endpoint в `app/api/server.py`

---

*Документ обновлён: 2026-01-26*
