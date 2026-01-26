# 🧪 Тестирование

## Быстрый старт

### Запуск основных тестов
```powershell
.\run_tests.ps1
```

### Быстрый прогон (только базовые тесты)
```powershell
.\run_tests_quick.ps1
# или
.\run_tests.ps1 -Quick
```

### Запуск только DDD тестов
```powershell
.\run_tests_ddd.ps1
# или
.\run_tests.ps1 -DDD -Verbose
```

### Запуск всех тестов
```powershell
.\run_tests_all.ps1
# или
.\run_tests.ps1 -All -Verbose
```

---

## Опции скрипта `run_tests.ps1`

### Параметры:
- `-Quick` - Быстрый прогон (только базовые тесты)
- `-DDD` - Запуск только DDD тестов
- `-All` - Запуск всех тестов (включая интеграционные)
- `-Verbose` - Подробный вывод
- `-TestPath` - Путь к тестам (по умолчанию `tests/`)

### Примеры:

```powershell
# Основные тесты с подробным выводом
.\run_tests.ps1 -Verbose

# Только DDD тесты
.\run_tests.ps1 -DDD

# Все тесты
.\run_tests.ps1 -All -Verbose

# Конкретный файл
.\run_tests.ps1 -TestPath "tests/test_config.py" -Verbose
```

---

## Структура тестов

### Базовые тесты (быстрые)
- `test_config.py` - Тесты конфигурации
- `test_ddd_value_objects.py` - Тесты Value Objects (DDD)
- `test_ddd_stock.py` - Тесты Stock entity (DDD)

### DDD тесты
- `test_ddd_value_objects.py` - Value Objects
- `test_ddd_stock.py` - Stock entity
- `test_ddd_use_case.py` - Use Cases

### Интеграционные тесты (медленные)
- `test_api.py` - API endpoints
- `test_moex_client.py` - MOEX клиент (требует интернет)
- `test_report.py` - Генерация отчётов
- `test_scheduler.py` - Планировщик
- `test_predictor.py` - Предсказания

---

## Прямой запуск через pytest

Если нужно запустить тесты напрямую:

```powershell
# Все тесты
python -m pytest tests/ -v

# Конкретный файл
python -m pytest tests/test_config.py -v

# Конкретный тест
python -m pytest tests/test_config.py::test_load_config -v

# С коротким traceback
python -m pytest tests/ -v --tb=short

# Остановка на первой ошибке
python -m pytest tests/ -v -x
```

---

## Решение проблем

### Ошибка: pytest не найден
```powershell
pip install -r requirements.txt
```

### Тесты зависают
- Используйте `-Quick` для быстрого прогона
- Проверьте, не запущены ли другие процессы Python
- Убедитесь, что нет проблем с импортами

### Ошибки импорта
- Убедитесь, что вы в корневой директории проекта
- Проверьте, что все зависимости установлены
- Проверьте, что `PYTHONPATH` настроен правильно

---

*Документ создан: 2026-01-27*
