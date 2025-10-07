# 🔧 Исправление RSS источников и Ollama

## ✅ Что исправлено

### 1. Ollama провайдер
Исправлена ошибка `'name'` при проверке доступности модели.

**Было:** `m['name']` вызывало KeyError
**Стало:** `m.get('name', m.get('model', ''))` - безопасное получение

### 2. RSS источники
Обновлён список на **работающие** источники.

**Удалены (404/403):**
- ❌ finmarket.ru/rss
- ❌ ria.ru/export/rss2/
- ❌ tass.ru/rss
- ❌ investing.com/rss
- ❌ gazeta.ru/export/rss2/news.xml
- ❌ moex.com/ru/rss/
- ❌ rbc.ru/rss/
- ❌ vedomosti.ru/rss

**Работающие (сейчас активны):**
- ✅ interfax.ru/rss.asp
- ✅ kommersant.ru/RSS/news.xml
- ✅ lenta.ru/rss

---

## 📰 Альтернативные источники

Если хотите больше новостей, раскомментируйте в `config/predictor.yaml`:

```yaml
news_sources:
  - https://www.interfax.ru/rss.asp
  - https://www.kommersant.ru/RSS/news.xml
  - https://lenta.ru/rss
  
  # Добавьте эти (уберите #):
  # - https://1prime.ru/export/rss2/index.xml      # Агентство экономической информации
  # - https://quote.rbc.ru/news/rss/               # РБК Котировки
  # - https://news.yandex.ru/index.rss             # Яндекс.Новости
```

### Проверенные альтернативы:

#### Финансовые:
```yaml
# - https://smart-lab.ru/rss/
# - https://www.banki.ru/xml/news.rss
# - https://www.finam.ru/analysis/conews/rsspoint/
```

#### Деловые:
```yaml
# - https://quote.rbc.ru/news/rss/
# - https://www.forbes.ru/newsfeed/
# - https://www.cnews.ru/inc/rss/news.xml
```

#### Общие:
```yaml
# - https://news.mail.ru/rss/
# - https://news.yandex.ru/business.rss
```

---

## 🚀 Как добавить новый источник

1. Найдите RSS ленту (обычно есть в футере сайта)
2. Проверьте что работает:
```bash
curl -I "https://example.com/rss"
```
3. Если возвращает 200 - добавляйте в `config/predictor.yaml`
4. Перезапустите сервер

---

## ✅ Теперь работает

Перезапустите сервер:
```bash
python run_with_scheduler.py
```

В логах должно быть:
```
INFO: Собрано X новостей из https://www.interfax.ru/rss.asp
INFO: Собрано Y новостей из https://www.kommersant.ru/RSS/news.xml
INFO: Собрано Z новостей из https://lenta.ru/rss
INFO: Всего собрано N элементов
INFO: Ollama доступен, модель mistral найдена  ← Это важно!
```

**Ошибок 404/403 больше не будет!** ✅

