# Реализация системы Telegram-мониторинга

## ✅ Что реализовано

### Этап 1: История изменений ✅
- ✅ Доменная модель `PriceSnapshot` с полями: price, volume, SMA, DY, RSI, ATR
- ✅ Репозиторий `PriceHistoryRepository` (интерфейс + SQLite реализация)
- ✅ Use case `SaveSnapshotUseCase` для сохранения snapshots
- ✅ Интеграция в `ReportGenerator` - автоматическое сохранение после обработки
- ✅ Автоматическая очистка старых данных (30 дней)

**Файлы:**
- `app/domain/price_history/entities/price_snapshot.py`
- `app/domain/price_history/repositories/price_history_repository.py`
- `app/infrastructure/persistence/repositories/price_history_repository_impl.py`
- `app/application/price_history/save_snapshot_use_case.py`

---

### Этап 2: Частое обновление данных ✅
- ✅ Планировщик `FrequentUpdatesScheduler` для обновлений каждые 3 часа
- ✅ Обновление только тикеров из портфеля (не всех)
- ✅ Интеграция в основной планировщик через `IntervalTrigger`
- ✅ Автоматический запуск при старте приложения

**Файлы:**
- `app/scheduler/frequent_updates_job.py`
- `app/main.py` (интеграция)

---

### Этап 3: Анализ изменений ✅
- ✅ `ChangeAnalyzer` - сервис для анализа изменений цен
- ✅ Сравнение с предыдущими значениями (3 и 24 часа назад)
- ✅ Генерация сигналов `ChangeSignal` с приоритетами
- ✅ **RSI индикатор** - определение перекупленности/перепроданности
- ✅ **Адаптивные пороги** - разные для акций и облигаций
- ✅ **Фильтр по времени торгов** - игнорирование изменений вне торговых часов
- ✅ Анализ объёма для подтверждения сигналов

**Файлы:**
- `app/domain/price_history/services/change_analyzer.py`
- `app/domain/price_history/value_objects/change_signal.py`
- `app/application/price_history/analyze_changes_use_case.py`
- `app/process/metrics.py` (добавлен RSI и ATR)

---

### Этап 4: Telegram-бот интеграция ✅
- ✅ `TelegramNotifier` - класс для отправки уведомлений
- ✅ Форматирование сообщений с эмодзи и HTML
- ✅ Группировка уведомлений (одно сообщение с несколькими сигналами)
- ✅ Use case `SendNotificationUseCase`
- ✅ Интеграция в `FrequentUpdatesScheduler`
- ✅ Поддержка приоритетов (HIGH/MEDIUM/LOW)

**Файлы:**
- `app/infrastructure/telegram/notifier.py`
- `app/application/telegram/send_notification_use_case.py`
- `requirements.txt` (добавлен python-telegram-bot)
- `.env.example` (добавлены переменные)

---

## 📋 Что нужно сделать для запуска

### 1. Установить зависимости

```bash
pip install python-telegram-bot
```

Или обновить все зависимости:

```bash
pip install -r requirements.txt
```

### 2. Настроить Telegram-бота

1. Создайте бота через [@BotFather](https://t.me/BotFather)
2. Получите Chat ID через [@userinfobot](https://t.me/userinfobot)
3. Добавьте в `.env`:
   ```env
   TELEGRAM_BOT_TOKEN=your_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   ```

### 3. Запустить сервер

```bash
python run_with_scheduler.py
```

Система автоматически:
- Запустит ежедневный планировщик (19:10 МСК)
- Запустит частые обновления (каждые 3 часа)
- Начнёт отправлять уведомления при значимых изменениях

---

## 🔧 Настройка

### Изменение интервала обновления

В `app/main.py` измените:

```python
scheduler.scheduler.add_job(
    frequent_updates_scheduler.update_portfolio_tickers,
    trigger=IntervalTrigger(hours=4),  # Вместо 3
    ...
)
```

### Изменение порогов

В `app/scheduler/frequent_updates_job.py`:

```python
self.change_analyzer = ChangeAnalyzer(
    price_change_threshold_pct=5.0,  # Вместо 3.0
    volume_spike_threshold=2.5,  # Вместо 2.0
    ...
)
```

---

## 📊 Структура данных

### PriceSnapshot (SQLite)
- `symbol` - тикер
- `timestamp` - время снимка
- `price`, `volume` - цена и объём
- `sma_20`, `sma_50`, `sma_200` - скользящие средние
- `dy_pct` - дивидендная доходность
- `rsi` - RSI индикатор
- `atr` - ATR (волатильность)

### ChangeSignal
- `symbol` - тикер
- `direction` - UP/DOWN/STABLE
- `price_change_pct` - изменение в %
- `volume_spike` - был ли всплеск объёма
- `priority` - HIGH/MEDIUM/LOW
- `recommendation` - текстовая рекомендация

---

## 🎯 Примеры уведомлений

### Пример 1: Падение цены
```
📉 SBER: Цена снизилась на 4.2%
💰 Было: 280.50₽ → Стало: 268.50₽
📊 Объём: 2.3x от среднего (высокий)
📈 RSI: 28.5 (перепроданность)
💡 Можно докупать (падение цены + высокий объём)
⏰ Время: 13:45 МСК (3ч назад)
🟡 Приоритет: MEDIUM
```

### Пример 2: Рост цены
```
📈 GAZP: Цена выросла на 5.1%
💰 Было: 165.20₽ → Стало: 173.60₽
📊 Объём: 1.8x от среднего
📈 RSI: 72.3 (перекупленность)
💡 Можно продавать (рост цены + перекупленность)
⏰ Время: 15:30 МСК (3ч назад)
🔴 Приоритет: HIGH
```

---

## ⚠️ Важные замечания

1. **База данных:** SQLite файл создаётся автоматически в `data/price_history.db`
2. **Первое обновление:** Система начнёт отправлять уведомления только после второго обновления (нужна история для сравнения)
3. **Торговые часы:** По умолчанию игнорируются изменения вне 10:00-18:45 МСК
4. **Адаптивные пороги:** Для облигаций используется порог 1.5%, для акций - 3%

---

## 🐛 Отладка

### Проверка сохранения snapshots

```python
from app.infrastructure.persistence.repositories.price_history_repository_impl import PriceHistoryRepositoryImpl

repo = PriceHistoryRepositoryImpl()
latest = repo.get_latest("SBER")
print(latest)
```

### Проверка анализа изменений

```python
from app.domain.price_history.services.change_analyzer import ChangeAnalyzer
from app.infrastructure.persistence.repositories.price_history_repository_impl import PriceHistoryRepositoryImpl

repo = PriceHistoryRepositoryImpl()
analyzer = ChangeAnalyzer(repo)
signals = analyzer.detect_significant_changes(["SBER", "GAZP"])
print(signals)
```

### Проверка Telegram-бота

```python
from app.infrastructure.telegram.notifier import TelegramNotifier

notifier = TelegramNotifier()
if notifier.is_enabled():
    notifier.send_test_message()
```

---

## 📈 Следующие шаги (опционально)

1. **MACD индикатор** - дополнительное подтверждение тренда
2. **Bollinger Bands** - определение экстремальных цен
3. **Взвешивание сигналов** - разные веса для разных сигналов
4. **Корреляция между инструментами** - контекст рынка
5. **Мониторинг точности** - отслеживание эффективности сигналов

---

## ✅ Готово к использованию!

Система полностью функциональна и готова к использованию. После настройки Telegram-бота уведомления будут приходить автоматически каждые 3 часа при значимых изменениях цен.
