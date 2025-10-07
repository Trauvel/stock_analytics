Отлично, вот **чёткий roadmap для Cursor**, как внедрить модуль “Предсказание событий” (раннее выявление возможных новостных всплесков).
Он полностью совместим с твоей системой `Stock Analytics` и работает в Python, используя `aiohttp`, `BeautifulSoup` и `transformers` (или `vaderSentiment` для лёгких моделей).

---

## 🚀 Roadmap: Модуль предсказания новостных всплесков (SPBE-подобных кейсов)

---

### **1️⃣ Цель**

Собирать и анализировать публичные признаки готовящихся действий компаний
(новые продукты, API, вакансии, интервью, публикации), чтобы заранее формировать сигнал:
`event_prediction: HIGH_PROBABILITY / MEDIUM / LOW`

---

### **2️⃣ Структура проекта**

```
/modules
 ├── news_predictor/
 │   ├── __init__.py
 │   ├── collector.py         # сбор данных
 │   ├── analyzer.py          # NLP-анализ
 │   ├── signals.py           # логика предсказаний
 │   └── config.yaml          # настройки ключей и приоритетов
```

---

### **3️⃣ collector.py**

**Задача:** собирать свежие данные из нескольких источников.

#### Источники:

* **RSS и API**: `interfax.ru`, `rbc.ru`, `kommersant.ru`, `moex.com`, `spbexchange.ru/news`
* **GitHub и API-документации компаний** (например, `spbexchange/api`)
* **Вакансии**: `hh.ru`, `superjob.ru` по ключам компании
* **Форумы и телеграм-каналы** (опционально, через парсинг HTML)

#### Пример:

```python
# collector.py
import aiohttp
from bs4 import BeautifulSoup

async def fetch_news(session, url):
    async with session.get(url) as resp:
        html = await resp.text()
        soup = BeautifulSoup(html, "html.parser")
        return [item.text for item in soup.select("item title")]

async def collect_data():
    urls = [
        "https://www.interfax.ru/rss.asp",
        "https://www.kommersant.ru/RSS/news.xml",
        "https://spbexchange.ru/news/rss"
    ]
    async with aiohttp.ClientSession() as session:
        results = []
        for url in urls:
            results += await fetch_news(session, url)
        return results
```

---

### **4️⃣ analyzer.py**

**Задача:** определить тональность и релевантность новостей.

Ключевые слова:

```yaml
positive_triggers:
  - "запуск"
  - "фьючерс"
  - "новая секция"
  - "развитие продукта"
  - "тестирование платформы"
  - "лицензия"
  - "расширение торгов"
  - "API"
negative_triggers:
  - "расследование"
  - "приостановка"
  - "санкции"
```

#### Пример кода:

```python
# analyzer.py
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re

def analyze_news(news_list):
    analyzer = SentimentIntensityAnalyzer()
    events = []
    for text in news_list:
        sentiment = analyzer.polarity_scores(text)["compound"]
        if re.search(r"запуск|фьючерс|новая секция|API", text.lower()):
            score = "HIGH_PROBABILITY" if sentiment > 0 else "MEDIUM"
            events.append({"text": text, "score": score})
    return events
```

---

### **5️⃣ signals.py**

**Задача:** агрегировать результаты и отдавать прогноз в главный анализатор.

```python
# signals.py
from .collector import collect_data
from .analyzer import analyze_news

async def generate_event_signals():
    news = await collect_data()
    analyzed = analyze_news(news)
    summary = {"HIGH": 0, "MEDIUM": 0}
    for item in analyzed:
        if item["score"] == "HIGH_PROBABILITY":
            summary["HIGH"] += 1
        elif item["score"] == "MEDIUM":
            summary["MEDIUM"] += 1

    if summary["HIGH"] >= 2:
        return "HIGH_PROBABILITY"
    elif summary["MEDIUM"] >= 3:
        return "MEDIUM_PROBABILITY"
    return "LOW"
```

---

### **6️⃣ config.yaml**

```yaml
sources:
  news:
    - https://www.interfax.ru/rss.asp
    - https://rbc.ru/rss/
    - https://spbexchange.ru/news/rss
  vacancies:
    - https://api.hh.ru/vacancies?text=СПБ Биржа
keywords:
  positive:
    - запуск
    - фьючерс
    - секция
    - API
    - тестирование
    - лицензия
  negative:
    - санкции
    - расследование
    - убытки
```

---

### **7️⃣ Интеграция с `Stock Analytics`**

В `reco.yaml` добавить:

```yaml
event_predictor:
  enabled: true
  weight:
    HIGH_PROBABILITY: +15
    MEDIUM_PROBABILITY: +5
    LOW: 0
```

И в основном цикле:

```python
from modules.news_predictor.signals import generate_event_signals

prediction = await generate_event_signals()
if prediction == "HIGH_PROBABILITY":
    action = "BUY"
    reason = "Позитивный новостной фон и признаки расширения рынка"
```

---

### **8️⃣ Тестирование**

* Добавить тестовую компанию (`SPBE`, `YNDX`, `VTBR`)
* Подставить старые новости (июль–сентябрь 2025)
* Проверить, что система ловит “запуск срочного рынка” как HIGH_PROBABILITY

---

### **9️⃣ Расширения**

* Подключить **GPT-модель для контекстного анализа** (определять тональность даже при завуалированных фразах).
* Добавить визуальную панель “Event Forecast” в GUI.
* Сохранять результаты в `events_log.json`.

---
