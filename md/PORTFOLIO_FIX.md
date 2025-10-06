# ✅ Исправлена ошибка 422 при сохранении портфеля

## Проблема

При попытке сохранить портфель через API возникала ошибка **422 Unprocessable Entity** из-за строгой валидации модели `Position`.

## Причины

### 1. **Символы в тикерах**
Старая валидация: `pattern=r'^[A-Z0-9]+$'` - только буквы и цифры.

**Проблемные тикеры:**
- `TGLD@` - содержит символ `@`
- `RU000A10AS85` - это нормально

### 2. **Два формата количества**
- В portfolio.json используется `qty`
- Модель ожидала `quantity`

### 3. **Дополнительные поля**
В portfolio.json были поля, которых не было в модели:
- `name` - название инструмента
- `current_value` - текущая стоимость

### 4. **Отсутствующий тип инструмента**
В JSON использовался тип `"fund"` (фонды), но в Enum были только `stock`, `bond`, `etf`, `currency`.

## Решение

### 1. Расширена валидация тикеров
```python
# Было:
symbol: str = Field(pattern=r'^[A-Z0-9]+$')

# Стало:
symbol: str = Field(min_length=1, max_length=50)  # Разрешаем любые символы
```

Теперь поддерживаются тикеры с:
- Спецсимволами: `TGLD@`, `SBER-$`, `SPB-AAPL`
- Кириллицей (если потребуется)
- Любыми другими символами

### 2. Поддержка обоих форматов количества
```python
quantity: Optional[int] = Field(None, ge=0)
qty: Optional[int] = Field(None, ge=0)  # Поддержка краткого формата

@field_validator('quantity', mode='after')
@classmethod
def sync_quantity(cls, v, info):
    """Синхронизация qty и quantity."""
    if v is None and info.data.get('qty') is not None:
        return info.data['qty']
    return v
```

Теперь можно использовать:
- `"quantity": 100` - полный формат
- `"qty": 100` - краткий формат
- Оба одновременно (приоритет у `quantity`)

### 3. Добавлены дополнительные поля
```python
name: Optional[str] = None  # Название инструмента
current_value: Optional[float] = None  # Текущая стоимость
```

### 4. Добавлен тип FUND
```python
class PositionType(str, Enum):
    STOCK = "stock"
    BOND = "bond"
    ETF = "etf"
    FUND = "fund"      # ⭐ NEW
    CURRENCY = "currency"
```

## Результат

**До исправления:**
```
422 Unprocessable Entity
- pattern check failed for symbol 'TGLD@'
- field required: quantity
- unexpected field: name, current_value
- invalid type: fund
```

**После исправления:**
```
✅ OK: Loaded 6 positions
Symbols: ['RU000A10AS85', 'SBGB', 'SBMX', 'RTKM', 'YDEX', 'TGLD@']
Types: [bond, fund, fund, stock, stock, fund]
SUCCESS!
```

## Поддерживаемые форматы

### Минимальный формат
```json
{
  "name": "My Portfolio",
  "currency": "RUB",
  "cash": 10000,
  "positions": [
    {
      "symbol": "SBER",
      "qty": 100
    }
  ]
}
```

### Полный формат
```json
{
  "name": "My Portfolio",
  "currency": "RUB",
  "cash": 10000,
  "positions": [
    {
      "symbol": "SBER",
      "quantity": 100,
      "avg_price": 250.50,
      "market": "moex",
      "type": "stock",
      "notes": "Основная позиция",
      "name": "Сбербанк",
      "current_value": 25050.00
    }
  ]
}
```

### Смешанный формат (как у вас)
```json
{
  "name": "Portfolio",
  "currency": "RUB",
  "cash": 1604.02,
  "positions": [
    {
      "symbol": "TGLD@",
      "name": "Золото (фонд доступное золото)",
      "qty": 244,
      "avg_price": 12.97,
      "current_value": 3164.68,
      "type": "fund"
    }
  ]
}
```

## Тестирование

```powershell
# Проверка модели
python test_portfolio_fix.py

# Проверка API
python -m pytest tests/test_api.py::test_save_portfolio -v

# Запуск всех тестов
python -m pytest tests/test_api.py -v
```

## Использование

### Через GUI

1. Откройте `http://localhost:8000/static/settings.html`
2. Перейдите на вкладку "💼 Портфель"
3. Редактируйте позиции
4. Нажмите "💾 Сохранить портфель"

Теперь всё работает! ✅

### Через API

```bash
curl -X POST http://localhost:8000/api/portfolio \
  -H "Content-Type: application/json" \
  -d @data/portfolio.json
```

## Обратная совместимость

✅ Старые портфели с `quantity` работают  
✅ Новые портфели с `qty` работают  
✅ Тикеры только с буквами/цифрами работают  
✅ Тикеры со спецсимволами работают  
✅ Все типы инструментов поддерживаются  

---

**Проблема полностью решена!** 🎉

