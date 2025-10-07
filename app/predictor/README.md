# Модуль предсказания новостных всплесков

## 📖 Описание

Модуль для раннего выявления возможных новостных всплесков и событий на основе анализа:
- RSS новостных лент (Интерфакс, РБК, Коммерсант)
- Публичных API вакансий (hh.ru)
- Ключевых слов и sentiment analysis

## 🏗️ Архитектура

```
app/predictor/
├── __init__.py        # Экспорт главных функций
├── collector.py       # Сбор данных из источников
├── analyzer.py        # NLP-анализ и scoring
├── signals.py         # Генерация сигналов
└── config.py          # Конфигурация модуля
```

## 🚀 Быстрый старт

### Установка зависимостей

```bash
pip install aiohttp beautifulsoup4 lxml
```

### Базовое использование

```python
import asyncio
from app.predictor import generate_event_signals

# Генерация сигнала для компании
async def main():
    signal = await generate_event_signals(target_companies=['SBER', 'Сбербанк'])
    
    print(f"Уровень сигнала: {signal['signal_level']}")
    print(f"Обоснование: {signal['reason']}")
    print(f"Статистика: {signal['stats']}")

asyncio.run(main())
```

## 📊 Уровни сигналов

| Уровень | Описание | Вес в рекомендациях |
|---------|----------|---------------------|
| `HIGH_PROBABILITY` | Высокая вероятность позитивных событий | +1.5 |
| `MEDIUM_PROBABILITY` | Умеренно позитивный фон | +0.5 |
| `NEGATIVE_SIGNAL` | Негативные события | -1.0 |
| `LOW` | Недостаточно данных | 0.0 |

## ⚙️ Конфигурация

Файл: `config/predictor.yaml`

```yaml
# Источники RSS новостей
news_sources:
  - https://www.interfax.ru/rss.asp
  - https://www.rbc.ru/rss/

# Использовать API вакансий
use_vacancies: true

# Позитивные ключевые слова
positive_keywords:
  - запуск
  - фьючерс
  - новая секция
  - API

# Негативные ключевые слова
negative_keywords:
  - санкции
  - убытки
  - приостановка

# Кэширование (секунды)
cache_ttl: 3600
```

## 🔗 Интеграция с системой рекомендаций

Модуль автоматически интегрируется в движок рекомендаций:

```python
from app.reco.engine import make_reco, get_event_signal
from app.reco.models import TickerSnapshot, RecoConfig

# Получаем сигнал предсказаний
event_signal = get_event_signal('SBER')

# Создаём рекомендацию с учётом сигнала
snapshot = TickerSnapshot(symbol='SBER', price=270.0, ...)
config = RecoConfig()

recommendation = make_reco(snapshot, config, event_signal=event_signal)
```

## 📝 Примеры

### Пример 1: Анализ нескольких компаний

```python
companies = ['SBER', 'GAZP', 'YNDX']
signal = await generate_event_signals(target_companies=companies)

# Проверяем результат
if signal['signal_level'] == 'HIGH_PROBABILITY':
    print("⚡ Обнаружены сильные позитивные сигналы!")
    print(f"Причина: {signal['reason']}")
```

### Пример 2: Работа с историей

```python
import json
from pathlib import Path

# Читаем историю сигналов
history_file = Path('data/events_history.json')
if history_file.exists():
    with open(history_file, 'r', encoding='utf-8') as f:
        history = json.load(f)
    
    # Анализируем тренды
    recent_signals = history[-10:]
    positive_count = sum(1 for s in recent_signals 
                        if s['signal_level'] == 'HIGH_PROBABILITY')
    
    print(f"Позитивных сигналов за последние 10 запусков: {positive_count}")
```

### Пример 3: Кастомная конфигурация

```python
from app.predictor.config import PredictorConfig
from app.predictor.signals import EventSignalGenerator

# Создаём кастомную конфигурацию
config = PredictorConfig(
    news_sources=['https://my-custom-rss.com/feed'],
    positive_keywords=['my', 'custom', 'keywords'],
    cache_ttl=7200  # 2 часа
)

# Используем генератор с кастомной конфигурацией
generator = EventSignalGenerator(config)
signal = await generator.generate_signal(['CUSTOM_TICKER'])
```

## 🧪 Тестирование

Запуск тестов:

```bash
pytest tests/test_predictor.py -v
```

Демонстрационный скрипт:

```bash
python test_predictor_demo.py
```

## 📈 Логика принятия решений

### HIGH_PROBABILITY

Выдаётся когда:
- 2+ новостей с высоким позитивным баллом
- Средний балл > 0.4

### MEDIUM_PROBABILITY

Выдаётся когда:
- 1 HIGH + 2+ MEDIUM новости
- 4+ MEDIUM новости и средний балл > 0.3
- 5+ релевантных новостей и средний балл > 0.2

### NEGATIVE_SIGNAL

Выдаётся когда:
- 3+ негативных новости

### LOW

Во всех остальных случаях

## 🔧 Расширение функционала

### Добавление нового источника

```python
# В config/predictor.yaml
news_sources:
  - https://your-new-source.com/rss
```

### Добавление новых ключевых слов

```python
# В config/predictor.yaml
positive_keywords:
  - ваше_новое_слово
  - ещё_одно_слово
```

### Кастомный анализатор

```python
from app.predictor.analyzer import NewsAnalyzer

class CustomAnalyzer(NewsAnalyzer):
    def analyze_item(self, item, target_companies=None):
        # Ваша кастомная логика
        result = super().analyze_item(item, target_companies)
        # Дополнительная обработка
        return result
```

## 📊 Мониторинг

### Логи

Логи модуля сохраняются в `data/logs/predictor.log`

### История событий

История сигналов сохраняется в `data/events_history.json` (последние 100 записей)

## ⚠️ Ограничения

1. **Rate Limiting**: hh.ru API ограничивает запросы (настройка `requests_per_minute`)
2. **Кэширование**: По умолчанию кэш на 1 час для снижения нагрузки на источники
3. **Русский язык**: Анализ заточен под русскоязычные новости

## 🎯 Roadmap

- [ ] Подключение GPT-модели для контекстного анализа
- [ ] Визуальная панель "Event Forecast" в GUI
- [ ] Webhook для Telegram-каналов
- [ ] A/B тестирование точности прогнозов
- [ ] Sentiment analysis для завуалированных фраз

## 📚 Связанные модули

- `app/reco/` - Система рекомендаций BUY/HOLD/SELL
- `app/ingest/` - Сбор данных с MOEX
- `app/process/` - Обработка и метрики

## 🤝 Вклад

При разработке новых фич:
1. Добавляйте тесты в `tests/test_predictor.py`
2. Обновляйте документацию
3. Проверяйте совместимость с `app/reco/engine.py`

