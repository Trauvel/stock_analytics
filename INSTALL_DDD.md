# Установка зависимостей для DDD

Для работы DDD архитектуры необходимо установить дополнительные зависимости.

## Установка dependency-injector

```bash
pip install dependency-injector>=4.41.0
```

Или установите все зависимости из requirements.txt:

```bash
pip install -r requirements.txt
```

## Проверка установки

```bash
python -c "import dependency_injector; print('OK')"
```

## Если возникают проблемы

1. Убедитесь, что используете правильную версию Python (3.8+)
2. Обновите pip: `python -m pip install --upgrade pip`
3. Попробуйте установить в виртуальное окружение:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   pip install dependency-injector
   ```
