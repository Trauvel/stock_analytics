# 🎯 Recommendation Context - DDD Миграция

## ✅ Что сделано

### Domain Layer

#### Value Objects
- **`Action`** - действие рекомендации (BUY/HOLD/SELL)
  - `is_buy()`, `is_sell()`, `is_hold()`
  - Валидация и преобразование

- **`Confidence`** - уверенность рекомендации (LOW/MEDIUM/HIGH)
  - `from_score()` - создание из числового балла
  - `is_high()`, `is_medium()`, `is_low()`

#### Entities
- **`Recommendation`** - доменная сущность рекомендации
  - `is_buy_recommendation()` - проверка типа
  - `is_strong_signal()` - проверка силы сигнала
  - `has_high_confidence()` - проверка уверенности

#### Services
- **`RecommendationEngine`** - доменный сервис для генерации рекомендаций
  - Использует доменную сущность `Stock` из Stock Analysis Context
  - Применяет бизнес-правила для расчёта score
  - Генерирует обоснования и подсказки

### Application Layer

#### Use Cases
- **`GenerateRecommendationsUseCase`** - use case для генерации рекомендаций
  - Получает акции через репозиторий
  - Использует RecommendationEngine
  - Применяет фильтры (only, min_score)
  - Сортирует результаты

### Infrastructure

#### DI Container
- `RecommendationEngine` зарегистрирован в DI
- `GenerateRecommendationsUseCase` зарегистрирован в DI
- Конфигурация загружается из `config/reco.yaml`

### API Integration

#### Endpoint
- `GET /api/recommendations` - использует DDD Use Case
- Параметры: `only`, `min_score`, `symbols`
- Fallback на старый код при ошибках

---

## 📁 Структура

```
app/
├── domain/
│   └── recommendation/              # Recommendation Context
│       ├── entities/
│       │   └── recommendation.py     # Recommendation entity
│       ├── value_objects/
│       │   ├── action.py            # Action (BUY/HOLD/SELL)
│       │   └── confidence.py        # Confidence (LOW/MEDIUM/HIGH)
│       └── services/
│           └── recommendation_engine.py
│
├── application/
│   └── recommendation/
│       └── generate_recommendations_use_case.py
│
└── api/
    └── server.py                     # Endpoint /recommendations
```

---

## 🚀 Использование

### Через API

```bash
# Получить все рекомендации
curl "http://localhost:8000/api/recommendations"

# Только BUY рекомендации
curl "http://localhost:8000/api/recommendations?only=BUY"

# С минимальным score
curl "http://localhost:8000/api/recommendations?min_score=2.0"

# Для конкретных тикеров
curl "http://localhost:8000/api/recommendations?symbols=SBER&symbols=VTBR"
```

### Через код

```python
from app.application.dependencies import container

use_case = container.generate_recommendations_use_case()
recommendations = await use_case.execute(
    symbols=["SBER", "VTBR"],
    only=["BUY"],
    min_score=2.0
)

for rec in recommendations:
    print(f"{rec.symbol}: {rec.action} (score: {rec.score})")
    print(f"  Reasons: {', '.join(rec.reasons)}")
    print(f"  Confidence: {rec.confidence}")
```

---

## 🔄 Интеграция с Stock Analysis Context

Recommendation Context использует `Stock` из Stock Analysis Context:

```python
# RecommendationEngine получает Stock entity
recommendation = engine.generate(
    stock=stock,  # Из Stock Analysis Context
    event_signal=event_signal
)
```

Это пример **Context Mapping** - Recommendation Context зависит от Stock Analysis Context.

---

## 📊 Бизнес-правила

### Расчёт Score

1. **Дивиденды**: +1.5 если DY ≥ 8%, +0.5 если ≥ 15%
2. **SMA200**: +1.0 если дисконт ≤ -10%, -1.0 если премия ≥ 10%
3. **Тренд**: +0.8 если восходящий ≥ 0.5%, -0.8 если нисходящий ≤ -0.5%
4. **52W диапазон**: +0.5 если в нижней трети, -0.5 если у верхней границы
5. **Технические сигналы**: +0.3 за каждый бычий сигнал
6. **Event Prediction**: +1.5/-1.0 в зависимости от уровня сигнала

### Определение действия

- **BUY**: score ≥ 2.0
- **SELL**: score ≤ -2.0
- **HOLD**: -2.0 < score < 2.0

### Определение уверенности

- **HIGH**: confidence_score ≥ 3.0
- **MEDIUM**: 1.5 ≤ confidence_score < 3.0
- **LOW**: confidence_score < 1.5

---

## 🧪 Тестирование

### Пример теста

```python
from app.domain.recommendation.entities.recommendation import Recommendation
from app.domain.recommendation.value_objects import Action, ActionType, Confidence

def test_recommendation_is_buy():
    recommendation = Recommendation(
        symbol="SBER",
        action=Action(action_type=ActionType.BUY),
        score=3.0,
        reasons=["High dividend yield"],
        confidence=Confidence.from_score(3.5)
    )
    
    assert recommendation.is_buy_recommendation() == True
    assert recommendation.has_high_confidence() == True
    assert recommendation.is_strong_signal() == True
```

---

## ✅ Преимущества

1. **Чёткое разделение ответственности**
   - Recommendation Context не знает о MOEX API
   - Использует доменные сущности из Stock Analysis Context

2. **Тестируемость**
   - Можно легко создать mock Stock
   - Бизнес-правила тестируются изолированно

3. **Явные бизнес-правила**
   - Все правила в RecommendationEngine
   - Легко понять логику расчёта

4. **Типобезопасность**
   - Value Objects предотвращают ошибки
   - Action и Confidence валидируются

---

*Документ создан: 2026-01-26*
