# 📊 Управление портфелем — Решение проблемы

## ❌ Проблема

**Вопрос:** Я меняю `data/portfolio.json` вручную, но после запуска тестов данные сбрасываются.

**Причина:** Тесты API перезаписывали реальный файл портфеля.

## ✅ Решение

**ИСПРАВЛЕНО!** Теперь тесты используют моки и НЕ трогают `data/portfolio.json`.

---

## 🎯 Правильные способы управления портфелем

### Способ 1: Скрипт manage_portfolio.py (РЕКОМЕНДУЕТСЯ)

#### Показать портфель
```bash
python manage_portfolio.py show
```

#### Создать новый (интерактивно)
```bash
python manage_portfolio.py create
```

Ответьте на вопросы:
```
Название портфеля [Мой портфель]: Основной
Валюта [RUB]: RUB
Свободные средства [0]: 50000

Добавьте позиции:
  Тикер: SBER
  Количество: 100
  Средняя цена покупки: 265.30
  Заметки: Голубые фишки
  [OK] Добавлено: SBER x 100 @ 265.30

  Тикер: GAZP
  Количество: 50
  Средняя цена покупки: 120.00
  Заметки:
  [OK] Добавлено: GAZP x 50 @ 120.00

  Тикер: [Enter для завершения]
```

#### Создать из шаблона
```bash
python manage_portfolio.py template
```

Создаст готовый пример с 3 позициями.

#### Редактировать существующий
```bash
python manage_portfolio.py edit
```

Меню:
```
1. Название
2. Добавить позицию
3. Удалить позицию
4. Изменить cash
```

---

### Способ 2: Через REST API

```bash
curl -X POST http://localhost:8000/api/portfolio \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Мой портфель",
    "currency": "RUB",
    "cash": 50000,
    "positions": [
      {"symbol": "SBER", "quantity": 100, "avg_price": 265.30},
      {"symbol": "GAZP", "quantity": 50, "avg_price": 120.00}
    ]
  }'
```

Проверка:
```bash
curl http://localhost:8000/api/portfolio/view
```

---

### Способ 3: Python скрипт

Создайте `my_portfolio.py`:

```python
from app.store.io import save_portfolio
from datetime import datetime

my_portfolio = {
    "name": "Мой портфель",
    "currency": "RUB",
    "cash": 50000.0,
    "positions": [
        {
            "symbol": "SBER",
            "quantity": 100,
            "avg_price": 265.30,
            "market": "moex",
            "type": "stock"
        },
        {
            "symbol": "LKOH",
            "quantity": 10,
            "avg_price": 6000.00,
            "market": "moex",
            "type": "stock"
        }
    ],
    "created_at": datetime.now().isoformat(),
    "updated_at": datetime.now().isoformat()
}

save_portfolio(my_portfolio)
print("✓ Портфель сохранён в data/portfolio.json")
```

Запуск:
```bash
python my_portfolio.py
```

---

## ⚠️ Что НЕ делать

### ❌ НЕ редактируйте вручную

**Проблема:**
```
Открыли data/portfolio.json в редакторе
→ Изменили данные
→ Сохранили
→ Запустили pytest tests/
→ Данные сбросились! 😢
```

**Почему:** До исправления тесты перезаписывали файл.

**Сейчас:** ✅ Исправлено! Тесты больше не трогают реальный файл.

---

## 🧪 Проверка исправления

### Тест 1: Ручное изменение + тесты

```bash
# 1. Создайте портфель
python manage_portfolio.py template

# 2. Проверьте что создался
python manage_portfolio.py show

# 3. Запустите тесты
pytest tests/test_api.py -v

# 4. Проверьте что НЕ изменился
python manage_portfolio.py show
```

**Результат:** Портфель должен остаться без изменений! ✅

### Тест 2: Создание через API

```bash
# Запустите сервер
python run_server.py

# В другом терминале
curl -X POST http://localhost:8000/api/portfolio \
  -H "Content-Type: application/json" \
  -d '{"currency":"RUB","positions":[{"symbol":"SBER","quantity":200}]}'

# Проверьте
python manage_portfolio.py show
```

---

## 📝 Рекомендации

### Для личного использования:
✅ Используйте **manage_portfolio.py**

### Для автоматизации:
✅ Используйте **REST API**

### Для разработки:
✅ Используйте **Python код** с `save_portfolio()`

### Для тестов:
✅ Тесты **автоматически используют моки** (исправлено!)

---

## 🎯 Итог

**Проблема решена!** 

Теперь:
- ✅ Тесты НЕ перезаписывают `data/portfolio.json`
- ✅ Есть удобный скрипт `manage_portfolio.py`
- ✅ Можно безопасно редактировать через скрипт или API
- ✅ Все тесты проходят (65/65)

**Используйте:**
```bash
python manage_portfolio.py show      # Просмотр
python manage_portfolio.py create    # Создание
python manage_portfolio.py edit      # Редактирование
```

Полная документация: [docs/portfolio.md](docs/portfolio.md)

