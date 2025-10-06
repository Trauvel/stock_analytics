# 🔄 Как перезапустить сервер для загрузки GUI

## Проблема решена!

GUI теперь настроен правильно в `app/main.py`.

---

## 🚀 Перезапуск сервера

### Шаг 1: Остановите текущий сервер

Если сервер запущен в отдельном окне PowerShell:
- Перейдите в то окно
- Нажмите **Ctrl + C**
- Дождитесь сообщения "Application stopped"

Или найдите и завершите процесс:
```powershell
# Найти процесс на порту 8000
netstat -ano | findstr :8000

# Завершить процесс (замените <PID> на номер процесса)
taskkill /PID <PID> /F
```

### Шаг 2: Запустите сервер заново

```bash
python run_with_scheduler.py
```

### Шаг 3: Откройте браузер

```
http://localhost:8000
```

**Теперь вы увидите:**
- ✅ Красивый Bootstrap дашборд
- ✅ Таблицы с данными
- ✅ Кнопки управления
- ✅ Автообновление

---

## ✅ Что было исправлено

### ДО (проблема):
```
app/main.py:
  @app.get("/")
  return {"message": "..."} ← Возвращал JSON
```

### ПОСЛЕ (исправлено):
```
app/main.py:
  @app.get("/", response_class=HTMLResponse)
  return HTMLResponse(content=html) ← Возвращает HTML
  
  # + StaticFiles для CSS/JS
  app.mount("/static", StaticFiles(...))
```

---

## 🎨 Что вы увидите

### Главная страница (/)

**Верхняя панель:**
```
📊 Stock Analytics     [🔄 Обновить] [▶️ Запустить сейчас]
```

**Статистика:**
```
┌─────────────┬──────────┬──────────┬─────────┐
│ Всего: 15   │ Успешно: │ Ошибки:  │ Сигналы:│
│             │    13    │    2     │   22    │
└─────────────┴──────────┴──────────┴─────────┘
```

**Вкладки:**
- 💰 Высокие дивиденды
- 📋 Все тикеры  
- 🚦 Сигналы

### API (/api/docs)

Swagger документация для разработчиков.

### Планировщик (/scheduler/status)

JSON со статусом планировщика.

---

## 🧪 Проверка

После перезапуска:

```bash
# Проверка 1: Главная страница
curl http://localhost:8000

# Должен вернуть HTML (начинается с <!DOCTYPE html>)
```

```bash
# Проверка 2: API всё ещё работает
curl http://localhost:8000/api/health

# Должен вернуть JSON: {"ok": true, ...}
```

---

## 📝 Запомните

**Используйте правильные URL:**

| Что | URL | Формат |
|-----|-----|--------|
| **GUI** | http://localhost:8000 | HTML |
| API Root | http://localhost:8000/api | JSON |
| API Docs | http://localhost:8000/api/docs | HTML |
| Health | http://localhost:8000/api/health | JSON |
| Report | http://localhost:8000/api/report/today | JSON |
| Scheduler | http://localhost:8000/scheduler/status | JSON |

---

## ⚡ Быстрый перезапуск

```bash
# Остановить (Ctrl+C в окне сервера)
# ИЛИ
taskkill /F /IM python.exe  # Осторожно - убивает все Python процессы!

# Запустить
python run_with_scheduler.py

# Открыть
start http://localhost:8000
```

---

**После перезапуска GUI будет работать!** 🎨✨

