# 🚀 Быстрый старт: Модуль предсказаний

## 5 минут до первого запуска

### 1. Установите зависимости

```bash
pip install aiohttp beautifulsoup4 lxml
```

### 2. Запустите демонстрацию

```bash
python test_predictor_demo.py
```

Вы увидите:
- ✅ Анализ новостей для SBER, GAZP, YNDX
- ✅ Уровни сигналов (HIGH/MEDIUM/LOW/NEGATIVE)
- ✅ Топ релевантных новостей
- ✅ Сравнение рекомендаций с/без модуля

### 3. Используйте в коде

```python
import asyncio
from app.predictor import generate_event_signals

async def main():
    signal = await generate_event_signals(['SBER'])
    print(signal)

asyncio.run(main())
```

### 4. Настройте под себя

Отредактируйте `config/predictor.yaml`:

```yaml
positive_keywords:
  - ваше_слово
  - ещё_слово

news_sources:
  - https://your-rss-source.com
```

### 5. Запустите тесты

```bash
pytest tests/test_predictor.py -v
```

---

## Что дальше?

📖 Читайте полную документацию в `app/predictor/README.md`

🎯 Интегрируйте в систему рекомендаций (уже готово!)

🔧 Расширяйте функционал (добавляйте источники, ключевые слова)

---

**Вопросы?** Смотрите `PREDICTOR_MODULE_READY.md`

