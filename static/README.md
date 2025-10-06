# Static Files - Веб-интерфейс

Статические файлы для веб-интерфейса Stock Analytics.

## Структура

```
static/
├── index.html          # Главная страница дашборда
├── css/
│   └── style.css      # Кастомные стили
└── js/
    └── app.js         # JavaScript логика
```

## Зависимости

Все зависимости загружаются с CDN (требуется интернет):
- **Bootstrap 5.3.0** — UI компоненты и стили
- **Bootstrap Icons** — иконки (встроены в Bootstrap)

## Функции

### index.html
- Структура страницы
- 3 вкладки (Дивиденды, Все тикеры, Сигналы)
- Статистика сверху
- Кнопки управления

### css/style.css
- Кастомные цвета
- Анимации
- Стили для таблиц и карточек
- Responsive дизайн

### js/app.js
- Загрузка данных из API
- Обновление таблиц
- Поиск и фильтрация
- Запуск генерации отчёта
- Автообновление каждые 5 минут

## API Endpoints (используемые в GUI)

- `GET /api/report/today` — получение отчёта
- `GET /api/report/summary` — получение сводки
- `POST /scheduler/run-now` — запуск генерации

## Кастомизация

### Добавление новой вкладки

1. **HTML** (в index.html):
```html
<li class="nav-item">
    <button class="nav-link" data-bs-toggle="tab" data-bs-target="#my-tab">
        Моя вкладка
    </button>
</li>

<div class="tab-pane fade" id="my-tab">
    <!-- Контент -->
</div>
```

2. **JavaScript** (в app.js):
```javascript
function updateMyTab(report) {
    // Логика обновления
}

// Вызов в loadReport()
updateMyTab(currentReport);
```

### Изменение темы

В `style.css`:
```css
body {
    background-color: #1a1a1a;  /* Тёмный фон */
    color: #ffffff;             /* Белый текст */
}
```

## Без интернета

Если нужно работать без CDN:

1. Скачайте Bootstrap локально
2. Положите в `static/vendor/`
3. Измените пути в `index.html`:
```html
<link href="/static/vendor/bootstrap.min.css" rel="stylesheet">
```

## Тестирование

GUI тестируется через:
- Ручное тестирование в браузере
- API тесты (проверяют endpoint `/`)
- Консоль браузера (F12) для отладки

## Развёртывание

При деплое на сервер:
1. Убедитесь что `static/` копируется
2. Настройте nginx для раздачи статики (опционально)
3. Или используйте встроенный StaticFiles FastAPI

