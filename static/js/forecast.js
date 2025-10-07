/**
 * Event Forecast - JavaScript для панели предсказаний
 */

const API_BASE = '';
let currentTickers = [];
let refreshInterval = null;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    console.log('Event Forecast initialized');
    loadConfiguration();
    loadForecast();
    loadHistory();
    
    // Автообновление каждые 5 минут
    refreshInterval = setInterval(refreshForecast, 300000);
});

/**
 * Загрузка конфигурации модуля
 */
async function loadConfiguration() {
    try {
        const response = await fetch(`${API_BASE}/predictor/config`);
        const result = await response.json();
        
        if (result.ok) {
            const config = result.data;
            
            document.getElementById('sources-count').textContent = config.news_sources.length;
            document.getElementById('use-vacancies').textContent = config.use_vacancies ? 'Да' : 'Нет';
            document.getElementById('cache-ttl').textContent = config.cache_ttl;
            
            // Добавляем быстрые кнопки для популярных тикеров
            addTickerSuggestions();
        }
    } catch (error) {
        console.error('Error loading configuration:', error);
    }
}

/**
 * Загрузка прогноза
 */
async function loadForecast(tickers = null) {
    try {
        showLoading();
        
        let url = `${API_BASE}/predictor/signal`;
        if (tickers && tickers.length > 0) {
            const tickerParams = tickers.map(t => `tickers=${encodeURIComponent(t)}`).join('&');
            url += `?${tickerParams}`;
            currentTickers = tickers;
        }
        
        const response = await fetch(url);
        const result = await response.json();
        
        if (result.ok) {
            displayForecast(result.data);
        } else {
            showError(result.error);
        }
    } catch (error) {
        console.error('Error loading forecast:', error);
        showError('Ошибка при загрузке прогноза');
    }
}

/**
 * Отображение прогноза
 */
function displayForecast(data) {
    const { signal_level, reason, stats, top_items, companies } = data;
    
    // Обновляем иконку и текст сигнала
    updateSignalDisplay(signal_level);
    
    // Обновляем статистику
    document.getElementById('total-analyzed').textContent = stats.total || 0;
    document.getElementById('positive-count').textContent = stats.relevant || 0;
    document.getElementById('avg-score').textContent = (stats.avg_score || 0).toFixed(2);
    
    document.getElementById('high-count').textContent = stats.HIGH_PROBABILITY || 0;
    document.getElementById('medium-count').textContent = stats.MEDIUM_PROBABILITY || 0;
    document.getElementById('negative-count').textContent = stats.NEGATIVE || 0;
    
    // Обновляем обоснование
    document.getElementById('signal-reason').innerHTML = `
        <div class="alert alert-info mb-0">
            <strong>📝 Обоснование:</strong><br>
            ${reason}
        </div>
    `;
    
    // Обновляем карточку сигнала
    const card = document.getElementById('signal-detail-card');
    card.className = `card signal-level-card mb-3 signal-${signal_level}`;
    
    // Отображаем топ новости
    displayTopNews(top_items || []);
    
    // Обновляем значок
    document.getElementById('news-badge').textContent = (top_items || []).length;
}

/**
 * Обновление отображения уровня сигнала
 */
function updateSignalDisplay(level) {
    const icons = {
        'HIGH_PROBABILITY': '🚀',
        'MEDIUM_PROBABILITY': '📊',
        'NEGATIVE_SIGNAL': '⚠️',
        'LOW': '😐'
    };
    
    const labels = {
        'HIGH_PROBABILITY': 'Высокая вероятность',
        'MEDIUM_PROBABILITY': 'Средняя вероятность',
        'NEGATIVE_SIGNAL': 'Негативный сигнал',
        'LOW': 'Низкий сигнал'
    };
    
    const colors = {
        'HIGH_PROBABILITY': 'text-success',
        'MEDIUM_PROBABILITY': 'text-warning',
        'NEGATIVE_SIGNAL': 'text-danger',
        'LOW': 'text-secondary'
    };
    
    document.getElementById('main-signal-icon').textContent = icons[level] || '🔮';
    document.getElementById('current-signal').innerHTML = `
        <span class="${colors[level]}">${labels[level] || level}</span>
    `;
}

/**
 * Отображение топ новостей
 */
function displayTopNews(items) {
    const container = document.getElementById('top-news-list');
    
    if (items.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-4">
                <p>Нет релевантных новостей для отображения</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = items.map((item, index) => {
        const categoryClass = getCategoryClass(item.category);
        const keywords = item.matched_keywords || [];
        
        return `
            <div class="news-item ${categoryClass}">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h6 class="mb-0">${index + 1}. ${escapeHtml(item.title)}</h6>
                    <span class="badge bg-${getCategoryBadge(item.category)}">${item.category}</span>
                </div>
                ${item.description ? `<p class="text-muted small mb-2">${escapeHtml(item.description.substring(0, 150))}...</p>` : ''}
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        ${keywords.slice(0, 5).map(kw => {
                            const isPositive = kw.startsWith('+');
                            const color = isPositive ? 'success' : 'danger';
                            const text = kw.substring(1);
                            return `<span class="badge bg-${color} keyword-badge">${text}</span>`;
                        }).join('')}
                    </div>
                    <small class="text-muted">
                        Балл: <strong class="${item.score > 0 ? 'text-success' : 'text-danger'}">${item.score.toFixed(2)}</strong>
                    </small>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Получение класса для категории новости
 */
function getCategoryClass(category) {
    if (category === 'HIGH_PROBABILITY' || category === 'MEDIUM_PROBABILITY') {
        return 'positive';
    } else if (category === 'NEGATIVE') {
        return 'negative';
    }
    return '';
}

/**
 * Получение цвета бейджа для категории
 */
function getCategoryBadge(category) {
    const badges = {
        'HIGH_PROBABILITY': 'success',
        'MEDIUM_PROBABILITY': 'warning',
        'NEGATIVE': 'danger',
        'NEUTRAL': 'secondary'
    };
    return badges[category] || 'secondary';
}

/**
 * Загрузка истории сигналов
 */
async function loadHistory() {
    try {
        const response = await fetch(`${API_BASE}/predictor/history?limit=5`);
        const result = await response.json();
        
        if (result.ok) {
            displayHistory(result.data.items || []);
        }
    } catch (error) {
        console.error('Error loading history:', error);
    }
}

/**
 * Отображение истории
 */
function displayHistory(items) {
    const container = document.getElementById('history-timeline');
    
    if (items.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-3">
                История пуста
            </div>
        `;
        return;
    }
    
    container.innerHTML = items.map(item => {
        const markerClass = getMarkerClass(item.signal_level);
        const timestamp = new Date(item.timestamp).toLocaleString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        return `
            <div class="timeline-item">
                <div class="timeline-marker ${markerClass}"></div>
                <div class="card border-0 shadow-sm">
                    <div class="card-body p-2">
                        <small class="text-muted d-block">${timestamp}</small>
                        <strong class="d-block">${formatSignalLevel(item.signal_level)}</strong>
                        <small class="text-muted">${(item.stats?.total || 0)} новостей</small>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Получение класса маркера для истории
 */
function getMarkerClass(level) {
    const classes = {
        'HIGH_PROBABILITY': 'high',
        'MEDIUM_PROBABILITY': 'medium',
        'NEGATIVE_SIGNAL': 'negative',
        'LOW': 'low'
    };
    return classes[level] || 'low';
}

/**
 * Форматирование уровня сигнала
 */
function formatSignalLevel(level) {
    const labels = {
        'HIGH_PROBABILITY': '🚀 Высокий',
        'MEDIUM_PROBABILITY': '📊 Средний',
        'NEGATIVE_SIGNAL': '⚠️ Негативный',
        'LOW': '😐 Низкий'
    };
    return labels[level] || level;
}

/**
 * Добавление быстрых кнопок для популярных тикеров
 */
function addTickerSuggestions() {
    const container = document.getElementById('ticker-suggestions');
    const popularTickers = [
        ['SBER', 'GAZP', 'YNDX'],
        ['VTBR', 'LKOH', 'GMKN'],
        ['SPBE', 'MOEX', 'RTKM']
    ];
    
    container.innerHTML = popularTickers.map(group => {
        const groupName = group.join(', ');
        return `
            <button class="btn btn-sm btn-outline-primary" 
                    onclick="quickAnalyze(['${group.join("','")}'])">
                ${groupName}
            </button>
        `;
    }).join('');
}

/**
 * Быстрый анализ по группе тикеров
 */
function quickAnalyze(tickers) {
    document.getElementById('ticker-input').value = tickers.join(', ');
    analyzeCustomTickers();
}

/**
 * Анализ пользовательских тикеров
 */
function analyzeCustomTickers() {
    const input = document.getElementById('ticker-input').value;
    if (!input.trim()) {
        alert('Введите хотя бы один тикер');
        return;
    }
    
    const tickers = input.split(',').map(t => t.trim().toUpperCase()).filter(t => t);
    loadForecast(tickers);
}

/**
 * Обновление прогноза
 */
function refreshForecast() {
    const icon = document.getElementById('refresh-icon');
    icon.classList.add('pulse');
    
    if (currentTickers.length > 0) {
        loadForecast(currentTickers);
    } else {
        loadForecast();
    }
    
    loadHistory();
    
    setTimeout(() => {
        icon.classList.remove('pulse');
    }, 2000);
}

/**
 * Показать загрузку
 */
function showLoading() {
    document.getElementById('top-news-list').innerHTML = `
        <div class="text-center text-muted py-4">
            <div class="spinner-border" role="status">
                <span class="visually-hidden">Загрузка...</span>
            </div>
            <p class="mt-2">Анализируем новости...</p>
        </div>
    `;
}

/**
 * Показать ошибку
 */
function showError(message) {
    document.getElementById('top-news-list').innerHTML = `
        <div class="alert alert-danger">
            <strong>Ошибка:</strong> ${escapeHtml(message)}
        </div>
    `;
}

/**
 * Экранирование HTML
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Очистка при выгрузке страницы
window.addEventListener('beforeunload', () => {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});

