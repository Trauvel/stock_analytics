# 🔧 Исправление проблем с Ollama

## ✅ Исправлено

### 1. Конфигурация
Исправлена загрузка вложенного `llm` блока в `config/predictor.yaml`

Теперь правильно читает:
```yaml
llm:
  enabled: true
  model: mistral
```

---

## 🔍 Проверка Ollama

### Проблема: "ollama" не распознан как команда

**Причина:** Ollama установлен, но не в PATH (нужен перезапуск PowerShell)

### Решение 1: Перезапустите PowerShell ⭐

1. Закройте текущий PowerShell/терминал
2. Откройте новый
3. Попробуйте:
```bash
ollama list
```

### Решение 2: Используйте полный путь

```powershell
# Если Ollama в Program Files
& "C:\Program Files\Ollama\ollama.exe" list

# Если в LocalAppData
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" list
```

### Решение 3: Проверьте что Ollama запущен

1. Откройте Диспетчер задач (Ctrl+Shift+Esc)
2. Найдите процесс "Ollama"
3. Если нет - запустите Ollama из меню Пуск

---

## 🚀 Быстрая проверка

### После перезапуска PowerShell:

```bash
# 1. Проверьте что Ollama работает
ollama --version

# 2. Скачайте модель (если ещё не скачали)
ollama pull mistral

# 3. Проверьте что модель доступна
ollama list

# 4. Протестируйте модель
ollama run mistral "Привет! Ты работаешь?"
```

**Ожидаемый результат:**
```
NAME              ID           SIZE     MODIFIED
mistral:latest    xxxx         4.1 GB   X minutes ago
```

---

## 🐛 Если Ollama не запускается

### Вариант 1: Переустановите
```powershell
# Удалите
winget uninstall Ollama.Ollama

# Установите заново
winget install Ollama.Ollama
```

### Вариант 2: Скачайте вручную
1. Откройте: https://ollama.com/download/windows
2. Скачайте установщик
3. Запустите

---

## ✅ Проверка интеграции

### После того как Ollama заработает:

```bash
# 1. Установите Python библиотеку
pip install ollama

# 2. Протестируйте Python интеграцию
python -c "import ollama; print('Ollama module OK')"

# 3. Перезапустите сервер
python run_with_scheduler.py
```

### В логах сервера должно быть:

```
INFO: LLM доступен: True
INFO: Ollama доступен, модель mistral найдена
```

### Если видите:
```
WARNING: Ollama недоступен: ...
```

То Ollama либо не запущен, либо модель не скачана.

---

## 📝 Чек-лист

- [ ] Ollama установлен (проверьте в Диспетчере задач)
- [ ] PowerShell перезапущен
- [ ] `ollama list` работает
- [ ] Модель `mistral` скачана
- [ ] `pip install ollama` выполнен
- [ ] Конфигурация `llm.enabled: true`
- [ ] Сервер перезапущен

---

**После выполнения всех шагов - всё заработает!** 🚀

