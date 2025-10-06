// Stock Analytics - Frontend JavaScript

const API_BASE = '/api';
let currentReport = null;

// Утилиты
function formatNumber(num, decimals = 2) {
    if (num === null || num === undefined) return 'N/A';
    return Number(num).toFixed(decimals);
}

function formatDateTime(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleString('ru-RU');
}

function getTrendIndicator(price, sma200) {
    if (!price || !sma200) return '<span class="trend-neutral">—</span>';
    
    if (price > sma200) {
        const diff = ((price / sma200 - 1) * 100).toFixed(1);
        return `<span class="trend-up">↗ +${diff}%</span>`;
    } else {
        const diff = ((1 - price / sma200) * 100).toFixed(1);
        return `<span class="trend-down">↘ -${diff}%</span>`;
    }
}

function getSignalBadges(signals) {
    if (!signals || signals.length === 0) return '<span class="text-muted">—</span>';
    
    const signalColors = {
        'PRICE_ABOVE_SMA200': 'success',
        'PRICE_BELOW_SMA200': 'danger',
        'SMA50_CROSS_UP_SMA200': 'success',
        'SMA50_CROSS_DOWN_SMA200': 'danger',
        'DY_GT_TARGET': 'primary',
        'VOL_SPIKE': 'warning'
    };
    
    const signalNames = {
        'PRICE_ABOVE_SMA200': '↗ Выше SMA200',
        'PRICE_BELOW_SMA200': '↘ Ниже SMA200',
        'SMA50_CROSS_UP_SMA200': '⭐ Золотой крест',
        'SMA50_CROSS_DOWN_SMA200': '💀 Крест смерти',
        'DY_GT_TARGET': '💵 Высокая DY',
        'VOL_SPIKE': '📈 Всплеск объёма'
    };
    
    return signals.map(signal => {
        const color = signalColors[signal] || 'secondary';
        const name = signalNames[signal] || signal;
        return `<span class="badge bg-${color} signal-badge">${name}</span>`;
    }).join(' ');
}

// API функции
async function fetchAPI(endpoint) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

async function loadReport() {
    try {
        // Показываем индикатор загрузки
        showLoading();
        
        // Получаем отчёт
        const reportData = await fetchAPI('/report/today');
        const summaryData = await fetchAPI('/report/summary');
        
        if (!reportData.ok) {
            showError('Отчёт не найден. Запустите генерацию отчёта.');
            return;
        }
        
        currentReport = reportData.data;
        
        // Обновляем статистику
        updateStatistics(summaryData.data);
        
        // Обновляем таблицы
        updateHighDividendTable(summaryData.data);
        updateAllTickersTable(currentReport);
        updateSignalsView(currentReport);
        
        // Обновляем время
        document.getElementById('last-update').textContent = formatDateTime(currentReport.generated_at);
        
    } catch (error) {
        console.error('Error loading report:', error);
        showError('Ошибка загрузки данных');
    }
}

function updateStatistics(summary) {
    document.getElementById('total-symbols').textContent = summary.total_symbols;
    document.getElementById('successful-symbols').textContent = summary.successful;
    document.getElementById('failed-symbols').textContent = summary.failed;
    document.getElementById('total-signals').textContent = summary.total_signals;
}

function updateHighDividendTable(summary) {
    const tbody = document.getElementById('high-div-tbody');
    
    if (!summary.high_dividend_tickers || summary.high_dividend_tickers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">Нет тикеров с высокой доходностью</td></tr>';
        return;
    }
    
    tbody.innerHTML = summary.high_dividend_tickers.map(item => {
        const symbolData = currentReport.by_symbol[item.symbol];
        if (!symbolData) return '';
        
        const trend = getTrendIndicator(symbolData.price, symbolData.sma_200);
        const signals = getSignalBadges(symbolData.signals);
        
        return `
            <tr class="fade-in">
                <td><strong>${item.symbol}</strong></td>
                <td>${formatNumber(symbolData.price)}</td>
                <td>${formatNumber(symbolData.div_ttm)}</td>
                <td><span class="badge bg-success">${formatNumber(item.dy_pct)}%</span></td>
                <td>${formatNumber(symbolData.sma_200)}</td>
                <td>${trend}</td>
                <td>${signals}</td>
            </tr>
        `;
    }).join('');
}

function updateAllTickersTable(report) {
    const tbody = document.getElementById('all-tickers-tbody');
    
    tbody.innerHTML = report.universe.map(symbol => {
        const data = report.by_symbol[symbol];
        
        if (data.meta.error) {
            return `
                <tr class="table-danger fade-in">
                    <td><strong>${symbol}</strong></td>
                    <td colspan="9" class="text-danger">❌ ${data.meta.error}</td>
                </tr>
            `;
        }
        
        const signals = getSignalBadges(data.signals);
        
        return `
            <tr class="fade-in">
                <td><strong>${symbol}</strong></td>
                <td>${formatNumber(data.price)}</td>
                <td>${data.lot || 'N/A'}</td>
                <td>${data.dy_pct ? formatNumber(data.dy_pct) + '%' : 'N/A'}</td>
                <td>${formatNumber(data.sma_20)}</td>
                <td>${formatNumber(data.sma_50)}</td>
                <td>${formatNumber(data.sma_200)}</td>
                <td>${formatNumber(data.low_52w)}</td>
                <td>${formatNumber(data.high_52w)}</td>
                <td>${signals}</td>
            </tr>
        `;
    }).join('');
}

function updateSignalsView(report) {
    const container = document.getElementById('signals-container');
    
    // Группируем по типам сигналов
    const signalGroups = {};
    
    report.universe.forEach(symbol => {
        const data = report.by_symbol[symbol];
        if (!data.signals || data.signals.length === 0) return;
        
        data.signals.forEach(signal => {
            if (!signalGroups[signal]) {
                signalGroups[signal] = [];
            }
            signalGroups[signal].push({symbol, data});
        });
    });
    
    if (Object.keys(signalGroups).length === 0) {
        container.innerHTML = '<div class="col-12"><p class="text-center">Нет активных сигналов</p></div>';
        return;
    }
    
    const signalNames = {
        'PRICE_ABOVE_SMA200': '↗ Выше SMA200',
        'PRICE_BELOW_SMA200': '↘ Ниже SMA200',
        'SMA50_CROSS_UP_SMA200': '⭐ Золотой крест',
        'SMA50_CROSS_DOWN_SMA200': '💀 Крест смерти',
        'DY_GT_TARGET': '💵 Высокая дивидендная доходность',
        'VOL_SPIKE': '📈 Всплеск объёма'
    };
    
    const signalTypes = {
        'PRICE_ABOVE_SMA200': 'success',
        'PRICE_BELOW_SMA200': 'danger',
        'SMA50_CROSS_UP_SMA200': 'success',
        'SMA50_CROSS_DOWN_SMA200': 'danger',
        'DY_GT_TARGET': 'primary',
        'VOL_SPIKE': 'warning'
    };
    
    container.innerHTML = Object.entries(signalGroups).map(([signal, items]) => {
        const type = signalTypes[signal] || 'secondary';
        const name = signalNames[signal] || signal;
        
        const tickersList = items.map(item => {
            const dyBadge = item.data.dy_pct ? 
                `<small class="text-muted">(DY: ${formatNumber(item.data.dy_pct)}%)</small>` : '';
            return `
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span><strong>${item.symbol}</strong> ${dyBadge}</span>
                    <span class="text-muted">${formatNumber(item.data.price)} ₽</span>
                </div>
            `;
        }).join('');
        
        return `
            <div class="col-md-6 mb-3">
                <div class="card signal-card signal-${type}">
                    <div class="card-header bg-${type} text-white">
                        <h6 class="mb-0">${name}</h6>
                    </div>
                    <div class="card-body">
                        <div class="mb-2">
                            <span class="badge bg-${type}">${items.length} тикеров</span>
                        </div>
                        ${tickersList}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function showLoading() {
    // Можно добавить спиннер загрузки
}

function showError(message) {
    const container = document.querySelector('.container-fluid');
    const alert = document.createElement('div');
    alert.className = 'alert alert-danger alert-dismissible fade show';
    alert.innerHTML = `
        <strong>Ошибка!</strong> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    container.insertBefore(alert, container.firstChild);
}

function showSuccess(message) {
    const container = document.querySelector('.container-fluid');
    const alert = document.createElement('div');
    alert.className = 'alert alert-success alert-dismissible fade show';
    alert.innerHTML = `
        <strong>Успех!</strong> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    container.insertBefore(alert, container.firstChild);
    
    // Автоматически закрыть через 3 секунды
    setTimeout(() => alert.remove(), 3000);
}

async function runJobNow() {
    if (!confirm('Запустить генерацию отчёта сейчас? Это займёт ~60 секунд.')) {
        return;
    }
    
    try {
        const button = event.target;
        button.disabled = true;
        button.textContent = '⏳ Генерация...';
        
        const response = await fetch('/scheduler/run-now', { method: 'POST' });
        const data = await response.json();
        
        if (data.ok) {
            showSuccess('Отчёт успешно сгенерирован!');
            // Перезагружаем данные
            setTimeout(() => loadReport(), 1000);
        } else {
            showError('Ошибка генерации: ' + data.error);
        }
        
        button.disabled = false;
        button.textContent = '▶️ Запустить сейчас';
        
    } catch (error) {
        console.error('Error running job:', error);
        showError('Ошибка запуска задачи');
    }
}

// Поиск по таблице
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search-ticker');
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const rows = document.querySelectorAll('#all-tickers-tbody tr');
            
            rows.forEach(row => {
                const ticker = row.cells[0]?.textContent.toLowerCase() || '';
                row.style.display = ticker.includes(searchTerm) ? '' : 'none';
            });
        });
    }
});

// Автозагрузка при открытии страницы
window.addEventListener('load', () => {
    loadReport();
    
    // Автообновление каждые 5 минут
    setInterval(() => {
        console.log('Auto-refreshing data...');
        loadReport();
        loadRecommendations();
    }, 5 * 60 * 1000);
    
    // Загрузка рекомендаций
    loadRecommendations();
});

// === Рекомендации ===

let currentFilter = 'all';

function getActionBadge(action, score, confidence) {
    const badges = {
        'BUY': `<span class="badge bg-success fs-6 py-2 px-3">🟢 ПОКУПАТЬ</span>`,
        'HOLD': `<span class="badge bg-secondary fs-6 py-2 px-3">⚪ ДЕРЖАТЬ</span>`,
        'SELL': `<span class="badge bg-danger fs-6 py-2 px-3">🔴 ПРОДАВАТЬ</span>`
    };
    
    const confidenceBadge = confidence === 'HIGH' ? '⭐⭐⭐' : confidence === 'MEDIUM' ? '⭐⭐' : '⭐';
    return `${badges[action]} <small class="text-muted ms-2">${confidenceBadge} Score: ${score}</small>`;
}

function renderRecommendation(reco) {
    const cardClass = {
        'BUY': 'border-success',
        'HOLD': 'border-secondary',
        'SELL': 'border-danger'
    }[reco.action];
    
    const reasons = reco.reasons.map(r => `<li>${r}</li>`).join('');
    
    return `
        <div class="col-12 col-md-6 col-lg-4 mb-3 reco-card" data-action="${reco.action}">
            <div class="card h-100 ${cardClass}">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h4 class="card-title mb-0">${reco.symbol}</h4>
                        <span class="badge bg-light text-dark">${formatNumber(reco.price)} ₽</span>
                    </div>
                    
                    <div class="mb-3">
                        ${getActionBadge(reco.action, reco.score, reco.confidence)}
                    </div>
                    
                    ${reco.dy_pct ? `<p class="mb-2"><strong>Дивиденды:</strong> ${formatNumber(reco.dy_pct, 1)}%</p>` : ''}
                    
                    ${reco.sizing_hint ? `<p class="text-primary mb-2"><small><strong>💡 ${reco.sizing_hint}</strong></small></p>` : ''}
                    
                    <details class="mt-2">
                        <summary class="text-muted" style="cursor: pointer;">Обоснование (${reco.reasons.length})</summary>
                        <ul class="small mt-2 mb-0">
                            ${reasons}
                        </ul>
                    </details>
                </div>
            </div>
        </div>
    `;
}

async function loadRecommendations() {
    try {
        const response = await fetch(`${API_BASE}/recommendations`);
        const data = await response.json();
        
        if (!data.ok) {
            throw new Error(data.error || 'Failed to load recommendations');
        }
        
        const recos = data.data.items;
        
        // Обновляем счетчики
        const counts = {
            BUY: recos.filter(r => r.action === 'BUY').length,
            HOLD: recos.filter(r => r.action === 'HOLD').length,
            SELL: recos.filter(r => r.action === 'SELL').length
        };
        
        document.getElementById('buy-count').textContent = counts.BUY;
        document.getElementById('hold-count').textContent = counts.HOLD;
        document.getElementById('sell-count').textContent = counts.SELL;
        
        // Рендерим рекомендации
        renderRecommendationsList(recos);
        
        // Настраиваем фильтры
        setupRecommendationsFilters();
        
    } catch (error) {
        console.error('Error loading recommendations:', error);
        document.getElementById('recommendations-list').innerHTML = `
            <div class="alert alert-danger">
                Ошибка загрузки рекомендаций: ${error.message}
            </div>
        `;
    }
}

function renderRecommendationsList(recos) {
    const container = document.getElementById('recommendations-list');
    
    if (recos.length === 0) {
        container.innerHTML = '<div class="alert alert-info">Нет рекомендаций</div>';
        return;
    }
    
    const html = `
        <div class="row">
            ${recos.map(reco => renderRecommendation(reco)).join('')}
        </div>
    `;
    
    container.innerHTML = html;
}

function setupRecommendationsFilters() {
    const buttons = document.querySelectorAll('[data-filter]');
    
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            // Обновляем активную кнопку
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Применяем фильтр
            const filter = btn.getAttribute('data-filter');
            currentFilter = filter;
            
            const cards = document.querySelectorAll('.reco-card');
            cards.forEach(card => {
                const action = card.getAttribute('data-action');
                if (filter === 'all' || action === filter) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    });
}

