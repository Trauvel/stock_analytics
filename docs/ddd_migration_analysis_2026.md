# 🏗️ Анализ текущей архитектуры и план миграции на DDD

## 📊 Текущее состояние (Январь 2026)

### ✅ Что уже мигрировано на DDD

#### 1. **Portfolio Management Context** ✅ (100%)
- ✅ Domain: `Portfolio`, `Position` entities, Value Objects (`Currency`, `Money`, `Quantity`)
- ✅ Application: Use Cases (`GetPortfolioUseCase`, `SavePortfolioUseCase`, `AddPositionUseCase`, etc.)
- ✅ Infrastructure: `PortfolioRepositoryImpl`
- ✅ Domain Events: `PortfolioCreated`, `PositionAdded`, `PositionRemoved`
- ✅ Unit of Work: `PortfolioUnitOfWork`

#### 2. **Recommendation Context** ✅ (100%)
- ✅ Domain: `Recommendation` entity, Value Objects (`Action`, `Confidence`)
- ✅ Application: `GenerateRecommendationsUseCase`
- ✅ Domain Service: `RecommendationEngine`

#### 3. **Price History Context** ✅ (100%) - НОВЫЙ
- ✅ Domain: `PriceSnapshot` entity, `ChangeSignal` value object
- ✅ Application: `SaveSnapshotUseCase`, `AnalyzeChangesUseCase`
- ✅ Infrastructure: `PriceHistoryRepositoryImpl` (SQLite)
- ✅ Domain Service: `ChangeAnalyzer`

#### 4. **Stock Analysis Context** ⚠️ (Частично - ~60%)
- ✅ Domain: `Stock` entity, Value Objects (`Price`, `DividendYield`, `Signal`)
- ✅ Domain Service: `MetricsCalculator` (в domain)
- ✅ Application: `GenerateReportUseCase`
- ✅ Infrastructure: `StockRepositoryImpl`
- ⚠️ **НО**: Legacy `ReportGenerator` всё ещё используется в планировщике

---

### ❌ Что ещё не мигрировано

#### 1. **Report Generation** (Legacy)
**Файл:** `app/process/report.py`
- `ReportGenerator` - напрямую использует `MOEXClient` и `MetricsCalculator`
- Используется в `DailyJobScheduler`
- Есть адаптер `report_ddd_adapter.py`, но основной код legacy

**Проблемы:**
- Тесная связанность с инфраструктурой
- Сложно тестировать
- Смешение ответственности (генерация + сохранение)

#### 2. **Metrics Calculation** (Смешанное)
**Файл:** `app/process/metrics.py`
- `MetricsCalculator` используется и в DDD, и в legacy коде
- Дублирование логики

#### 3. **Event Prediction Context** (Не мигрирован)
**Модуль:** `app/predictor/`
- Полностью legacy код
- Нет DDD структуры
- Не интегрирован с остальными контекстами

#### 4. **MOEX Client** (Инфраструктура, но используется напрямую)
**Файл:** `app/ingest/moex_client.py`
- Используется напрямую в `ReportGenerator`
- Должен использоваться только через репозитории

---

## 🎯 План дальнейшей миграции

### Фаза 1: Завершение миграции Stock Analysis Context (1-2 недели)

#### Задача 1.1: Рефакторинг ReportGenerator
**Цель:** Полностью заменить `ReportGenerator` на `GenerateReportUseCase`

**Шаги:**
1. Убедиться, что `GenerateReportUseCase` покрывает все сценарии `ReportGenerator`
2. Обновить `DailyJobScheduler` для использования use case вместо `ReportGenerator`
3. Удалить `ReportGenerator` или пометить как deprecated
4. Обновить все места использования

**Файлы:**
- `app/scheduler/daily_job.py` - использовать use case
- `app/process/report.py` - удалить или оставить только для обратной совместимости
- `app/process/report_ddd_adapter.py` - можно удалить после миграции

#### Задача 1.2: Унификация MetricsCalculator
**Цель:** Использовать только DDD версию `MetricsCalculator`

**Шаги:**
1. Проверить, что `app/domain/stock_analysis/services/metrics_calculator.py` содержит всю логику
2. Удалить `app/process/metrics.py` или сделать его алиасом
3. Обновить импорты

---

### Фаза 2: Миграция Event Prediction Context (2-3 недели)

#### Задача 2.1: Создать DDD структуру
```
app/domain/event_prediction/
├── entities/
│   └── event_prediction.py
├── value_objects/
│   ├── event_type.py
│   └── prediction_confidence.py
├── services/
│   └── event_predictor.py
└── repositories/
    └── event_prediction_repository.py
```

#### Задача 2.2: Создать Use Cases
```
app/application/event_prediction/
├── predict_events_use_case.py
└── analyze_news_use_case.py
```

#### Задача 2.3: Мигрировать существующий код
- Перенести логику из `app/predictor/` в domain
- Обновить API endpoints
- Интегрировать с другими контекстами

---

### Фаза 3: Рефакторинг Infrastructure (1 неделя)

#### Задача 3.1: Изолировать MOEX Client
**Цель:** Использовать только через репозитории

**Шаги:**
1. Убедиться, что `MOEXClient` используется только в `StockRepositoryImpl`
2. Если есть прямые использования - обернуть в репозитории
3. Переместить `app/ingest/moex_client.py` → `app/infrastructure/external/moex/`

#### Задача 3.2: Унифицировать хранилище
- Все операции с файлами через репозитории
- Убрать прямые вызовы `app/store/io.py` из бизнес-логики

---

### Фаза 4: Очистка и оптимизация (1 неделя)

#### Задача 4.1: Удалить legacy код
- Удалить неиспользуемые файлы
- Обновить документацию
- Обновить тесты

#### Задача 4.2: Улучшить DI
- Убедиться, что все зависимости через DI контейнер
- Убрать прямые инстанцирования

---

## 📋 Приоритизация

### Высокий приоритет (сделать сейчас)
1. ✅ **Исправить ошибку в main.py** (global declaration) - СДЕЛАНО
2. **Завершить миграцию Stock Analysis Context**
   - Заменить `ReportGenerator` на `GenerateReportUseCase` в планировщике
   - Унифицировать `MetricsCalculator`

### Средний приоритет (следующие 1-2 месяца)
3. **Мигрировать Event Prediction Context**
4. **Рефакторинг Infrastructure**

### Низкий приоритет (когда будет время)
5. **Очистка legacy кода**
6. **Оптимизация DI**

---

## 🎯 Рекомендации

### ✅ Стоит продолжить миграцию, потому что:

1. **Уже 70% мигрировано**
   - Portfolio, Recommendation, Price History - полностью DDD
   - Stock Analysis - частично
   - Осталось только завершить Stock Analysis и мигрировать Event Prediction

2. **Преимущества уже видны**
   - Чёткое разделение слоёв
   - Легко тестировать
   - Легко расширять (добавлен Price History Context)

3. **Смешанная архитектура создаёт проблемы**
   - Сложно понять, какой код использовать
   - Дублирование логики
   - Сложнее поддерживать

### ⚠️ Риски:

1. **Временные затраты**: 4-6 недель на завершение миграции
2. **Возможные баги**: При рефакторинге могут появиться ошибки
3. **Обучение**: Нужно понимать DDD принципы

### 💡 Рекомендация:

**Продолжить миграцию**, но делать это постепенно:
1. Сначала завершить Stock Analysis Context (1-2 недели)
2. Потом Event Prediction (2-3 недели)
3. Затем рефакторинг Infrastructure (1 неделя)

**Не переписывать всё сразу** - это рискованно.

---

## 📊 Метрики прогресса

### Текущий прогресс: ~70%

- ✅ Portfolio Management: 100%
- ✅ Recommendation: 100%
- ✅ Price History: 100%
- ⚠️ Stock Analysis: 60%
- ❌ Event Prediction: 0%

### После завершения миграции: 100%

---

## 🔄 Следующие шаги

1. **Немедленно:**
   - ✅ Исправить ошибку в `main.py` (сделано)
   - Заменить `ReportGenerator` на `GenerateReportUseCase` в `DailyJobScheduler`

2. **На этой неделе:**
   - Завершить миграцию Stock Analysis Context
   - Обновить тесты

3. **В следующем месяце:**
   - Мигрировать Event Prediction Context
   - Рефакторинг Infrastructure

---

*Документ создан: 2026-01-27*
