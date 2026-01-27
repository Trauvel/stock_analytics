// Stock Analytics - Frontend JavaScript

const API_BASE = '/api';
let currentReport = null;
let _lastSummary = null;
let _lastRecos = null;
let _lastExportPayload = null;
let _lastExportFilename = null;

// === Auth / роли ===
let AUTH = { enabled: false, authenticated: false, user: null };

async function loadAuthMe() {
    try {
        const resp = await fetch(`${API_BASE}/auth/me`);
        const data = await resp.json();
        if (!data?.ok) return AUTH;
        const d = data.data || {};
        AUTH.enabled = !!d.enabled;
        AUTH.authenticated = !!d.authenticated;
        AUTH.user = d.user || null;
        return AUTH;
    } catch (e) {
        console.warn('auth/me failed:', e);
        return AUTH;
    }
}

function applyRoleUI() {
    if (!AUTH.enabled) return;
    const loginLink = document.getElementById('login-link');
    const runBtn = document.querySelector('button[onclick="showRunJobModal()"]');

    if (!AUTH.authenticated) {
        if (loginLink) loginLink.classList.remove('d-none');
        if (runBtn) runBtn.classList.add('d-none');
        return;
    }

    const role = (AUTH.user?.role || '').toLowerCase();
    const isAdmin = role === 'admin';
    if (!isAdmin && runBtn) runBtn.classList.add('d-none');
    if (loginLink) loginLink.classList.add('d-none');
}

// === Подсказки по сигналам (для "Детально") ===
const SIGNAL_META = {
    PRICE_ABOVE_SMA200: {
        color: 'success',
        name: '↗ Выше SMA200',
        description: 'Цена выше 200-дневной SMA. Обычно это признак долгосрочного восходящего тренда (бычий фон).'
    },
    PRICE_BELOW_SMA200: {
        color: 'danger',
        name: '↘ Ниже SMA200',
        description: 'Цена ниже 200-дневной SMA. Обычно это признак долгосрочного нисходящего тренда (медвежий фон).'
    },
    SMA50_CROSS_UP_SMA200: {
        color: 'success',
        name: '⭐ Золотой крест',
        description: 'SMA50 пересекла SMA200 снизу вверх. Часто трактуется как усиление/смена тренда вверх (бычий сигнал).'
    },
    SMA50_CROSS_DOWN_SMA200: {
        color: 'danger',
        name: '💀 Крест смерти',
        description: 'SMA50 пересекла SMA200 сверху вниз. Часто трактуется как ослабление/смена тренда вниз (медвежий сигнал).'
    },
    DY_GT_TARGET: {
        color: 'primary',
        name: '💵 Высокая DY',
        description: 'Дивидендная (или купонная) доходность выше целевого порога из настроек. Может быть аргументом в пользу покупки/удержания.'
    },
    VOL_SPIKE: {
        color: 'warning',
        name: '📈 Всплеск объёма',
        description: 'Объём торгов заметно выше обычного. Может подтверждать силу движения цены или повышенный интерес к инструменту.'
    },
    NEAR_52W_LOW: {
        color: 'info',
        name: '📉 Близко к 52W Low',
        description: 'Цена находится в нижней части диапазона за 52 недели. Иногда трактуется как “дешевле обычного”, но это не гарантия разворота.'
    },
    NEAR_52W_HIGH: {
        color: 'info',
        name: '📈 Близко к 52W High',
        description: 'Цена находится у верхней части диапазона за 52 недели. Иногда трактуется как перегретость/риск отката, но может быть и сильный тренд.'
    },
    RSI_OVERSOLD: {
        color: 'secondary',
        name: '🧊 RSI перепродан',
        description: 'RSI ниже ~30. Часто трактуется как перепроданность (возможен отскок), но на сильном тренде может держаться долго.'
    },
    RSI_OVERBOUGHT: {
        color: 'secondary',
        name: '🔥 RSI перекуплен',
        description: 'RSI выше ~70. Часто трактуется как перекупленность (возможна коррекция), но на сильном тренде может держаться долго.'
    }
};

function escapeHtmlAttr(text) {
    if (text === null || text === undefined) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function initTooltips(root = document) {
    // Bootstrap Tooltip: переинициализируем, чтобы подсказки работали после перерендера
    if (typeof bootstrap === 'undefined' || !bootstrap.Tooltip) return;
    const els = root.querySelectorAll('[data-bs-toggle="tooltip"]');
    els.forEach(el => {
        const existing = bootstrap.Tooltip.getInstance(el);
        if (existing) existing.dispose();
        new bootstrap.Tooltip(el);
    });
}

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

    return signals.map(signal => {
        const meta = SIGNAL_META[signal] || { color: 'secondary', name: signal, description: signal };
        const title = escapeHtmlAttr(meta.description || meta.name || signal);
        return `<span class="badge bg-${meta.color} signal-badge" role="button" tabindex="0" data-bs-toggle="tooltip" data-bs-placement="top" title="${title}">${meta.name}</span>`;
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
        _lastSummary = summaryData?.data || null;
        
        // Обновляем статистику
        updateStatistics(summaryData.data);
        
        // Обновляем таблицы
        updateHighDividendTable(summaryData.data);
        updateAllTickersTable(currentReport);
        updateSignalsView(currentReport);

        // Подсказки по сигналам
        initTooltips(document);
        
        // Обновляем время
        document.getElementById('last-update').textContent = formatDateTime(currentReport.generated_at);
        
    } catch (error) {
        console.error('Error loading report:', error);
        showError('Ошибка загрузки данных');
    }
}

// === Экспорт отчёта (для ChatGPT) ===
function _compactClone(value) {
    // Удаляем null/undefined, пустые массивы/объекты
    if (value === null || value === undefined) return undefined;
    if (Array.isArray(value)) {
        const arr = value
            .map(_compactClone)
            .filter(v => v !== undefined);
        return arr.length ? arr : undefined;
    }
    if (typeof value === 'object') {
        const out = {};
        for (const [k, v] of Object.entries(value)) {
            const cv = _compactClone(v);
            if (cv !== undefined) out[k] = cv;
        }
        return Object.keys(out).length ? out : undefined;
    }
    return value;
}

async function _ensureExportDataLoaded() {
    if (!currentReport) {
        const reportData = await fetchAPI('/report/today');
        if (reportData?.ok && reportData?.data) currentReport = reportData.data;
    }
    if (!_lastSummary) {
        const summaryData = await fetchAPI('/report/summary');
        if (summaryData?.ok && summaryData?.data) _lastSummary = summaryData.data;
    }
    if (!_lastRecos) {
        const resp = await fetch(`${API_BASE}/recommendations`);
        const data = await resp.json();
        if (data?.ok && data?.data?.items) _lastRecos = data.data.items;
    }
}

function _buildExportPayload(options) {
    const generatedAt = currentReport?.generated_at || null;
    const payload = {
        meta: {
            exported_at: new Date().toISOString(),
            report_generated_at: generatedAt,
            app: 'stock_analytics',
            version: 'export-1'
        }
    };

    if (options.includeSummary) payload.summary = _lastSummary;
    if (options.includeReport) payload.report = currentReport;
    if (options.includeRecos) payload.recommendations = _lastRecos;

    if (options.mode === 'compact') {
        const compacted = _compactClone(payload);
        return compacted || payload;
    }
    return payload;
}

async function refreshExportPayload() {
    const textEl = document.getElementById('export-text');
    const statusEl = document.getElementById('export-status');
    if (textEl) textEl.value = 'Загрузка...';
    if (statusEl) statusEl.textContent = '';

    try {
        await _ensureExportDataLoaded();

        const includeReport = document.getElementById('export-include-report')?.checked ?? true;
        const includeSummary = document.getElementById('export-include-summary')?.checked ?? true;
        const includeRecos = document.getElementById('export-include-recos')?.checked ?? true;
        const mode = document.getElementById('export-mode')?.value || 'compact';

        _lastExportPayload = _buildExportPayload({ includeReport, includeSummary, includeRecos, mode });
        const jsonText = JSON.stringify(_lastExportPayload, null, 2);
        if (textEl) textEl.value = jsonText;

        const safeTs = (currentReport?.generated_at || new Date().toISOString()).replace(/[:.]/g, '-');
        _lastExportFilename = `stock_analytics_report_${safeTs}.json`;

        if (statusEl) {
            statusEl.textContent = `Готово. Размер: ${Math.round(jsonText.length / 1024)} KB. Файл: ${_lastExportFilename}`;
        }
    } catch (e) {
        console.error('Export error:', e);
        if (textEl) textEl.value = `Ошибка экспорта: ${e?.message || e}`;
        if (statusEl) statusEl.textContent = 'Проверьте, что отчёт существует (сначала нажмите «Обновить» или «Запустить сейчас»).';
    }
}

function showExportModal() {
    const modalEl = document.getElementById('exportModal');
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
    refreshExportPayload();
}

async function copyExportToClipboard() {
    const textEl = document.getElementById('export-text');
    const statusEl = document.getElementById('export-status');
    try {
        const text = textEl?.value || '';
        await navigator.clipboard.writeText(text);
        if (statusEl) statusEl.textContent = 'Скопировано в буфер обмена.';
    } catch (e) {
        console.error('Clipboard error:', e);
        if (statusEl) statusEl.textContent = 'Не удалось скопировать (браузер запретил). Можно выделить текст и скопировать вручную.';
    }
}

function downloadExportJson() {
    const textEl = document.getElementById('export-text');
    const jsonText = textEl?.value || '';
    const blob = new Blob([jsonText], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = _lastExportFilename || 'stock_analytics_report.json';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
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
    
    container.innerHTML = Object.entries(signalGroups).map(([signal, items]) => {
        const meta = SIGNAL_META[signal] || { color: 'secondary', name: signal, description: signal };
        const type = meta.color || 'secondary';
        const name = meta.name || signal;
        const title = escapeHtmlAttr(meta.description || name || signal);
        
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
                    <div class="card-header bg-${type} text-white" data-bs-toggle="tooltip" data-bs-placement="top" title="${title}">
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

    initTooltips(container);
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

let bondsList = [];

async function showRunJobModal() {
    const modal = new bootstrap.Modal(document.getElementById('runJobModal'));
    modal.show();
    
    // Загружаем список облигаций
    await loadBondsList();
}

async function loadBondsList() {
    const bondsListElement = document.getElementById('bonds-list');
    if (!bondsListElement) {
        console.error('bonds-list element not found');
        return;
    }
    
    try {
        const response = await fetch('/api/bonds');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.ok && Array.isArray(data.data)) {
            bondsList = data.data;
            renderBondsList();
        } else {
            const errorMsg = data.error || 'Неизвестная ошибка';
            console.error('Failed to load bonds:', errorMsg);
            bondsListElement.innerHTML = 
                `<div class="text-center text-danger"><small>Ошибка загрузки облигаций: ${errorMsg}</small></div>`;
        }
    } catch (error) {
        console.error('Error loading bonds:', error);
        bondsListElement.innerHTML = 
            `<div class="text-center text-danger"><small>Ошибка загрузки облигаций: ${error.message || error}</small></div>`;
    }
}

function renderBondsList() {
    const container = document.getElementById('bonds-list');
    
    if (!container) {
        console.error('bonds-list container not found');
        return;
    }
    
    if (!Array.isArray(bondsList) || bondsList.length === 0) {
        container.innerHTML = '<div class="text-center text-muted"><small>Облигации не найдены в портфеле или конфиге</small></div>';
        return;
    }
    
    let html = '';
    bondsList.forEach(bond => {
        // Экранируем HTML для безопасности
        const safeBond = bond.replace(/[&<>"']/g, function(match) {
            const escapeMap = {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            };
            return escapeMap[match];
        });
        
        html += `
            <div class="form-check">
                <input class="form-check-input bond-checkbox" type="checkbox" value="${safeBond}" id="bond-${safeBond.replace(/[^a-zA-Z0-9]/g, '_')}" checked>
                <label class="form-check-label" for="bond-${safeBond.replace(/[^a-zA-Z0-9]/g, '_')}">
                    <code>${safeBond}</code>
                </label>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function toggleBondsSelection() {
    const selectedType = document.querySelector('input[name="instrumentType"]:checked').value;
    const bondsSelection = document.getElementById('bonds-selection');
    
    if (selectedType === 'bonds') {
        bondsSelection.style.display = 'block';
    } else {
        bondsSelection.style.display = 'none';
    }
}

function selectAllBonds() {
    document.querySelectorAll('.bond-checkbox').forEach(checkbox => {
        checkbox.checked = true;
    });
}

function deselectAllBonds() {
    document.querySelectorAll('.bond-checkbox').forEach(checkbox => {
        checkbox.checked = false;
    });
}

async function runJobNow() {
    // Получаем выбранный тип инструментов
    const selectedType = document.querySelector('input[name="instrumentType"]:checked').value;
    
    // Получаем выбранные облигации (если тип = bonds)
    let selectedBonds = null;
    if (selectedType === 'bonds') {
        const checkedBoxes = document.querySelectorAll('.bond-checkbox:checked');
        selectedBonds = Array.from(checkedBoxes).map(cb => cb.value);
        
        if (selectedBonds.length === 0) {
            showError('Выберите хотя бы одну облигацию');
            return;
        }
    }
    
    // Закрываем модальное окно
    const modal = bootstrap.Modal.getInstance(document.getElementById('runJobModal'));
    modal.hide();
    
    try {
        const button = document.querySelector('button[onclick="showRunJobModal()"]');
        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = '⏳ Генерация...';
        
        // Формируем URL с параметрами
        let url = `/scheduler/run-now?instrument_type=${selectedType}`;
        if (selectedBonds && selectedBonds.length > 0) {
            url += `&selected_bonds=${selectedBonds.join(',')}`;
        }
        
        // Отправляем запрос с параметром фильтрации
        const response = await fetch(url, { method: 'POST' });
        const data = await response.json();
        
        if (data.ok) {
            let typeLabel = selectedType === 'all' ? 'все тикеры' : 
                            selectedType === 'stocks' ? 'акции' : 
                            selectedBonds ? `облигации (${selectedBonds.length} шт.)` : 'облигации';
            showSuccess(`Отчёт успешно сгенерирован для ${typeLabel}!`);
            // Перезагружаем данные
            setTimeout(() => loadReport(), 1000);
        } else {
            showError('Ошибка генерации: ' + (data.error || data.message || 'Unknown error'));
        }
        
        button.disabled = false;
        button.textContent = originalText;
        
    } catch (error) {
        console.error('Error running job:', error);
        showError('Ошибка запуска задачи');
        const button = document.querySelector('button[onclick="showRunJobModal()"]');
        button.disabled = false;
        button.textContent = '▶️ Запустить сейчас';
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
window.addEventListener('load', async () => {
    await loadAuthMe();
    applyRoleUI();

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

// Экспорт в глобальную область видимости (onclick)
window.showExportModal = showExportModal;
window.refreshExportPayload = refreshExportPayload;
window.copyExportToClipboard = copyExportToClipboard;
window.downloadExportJson = downloadExportJson;

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

function buildRecommendationReasons(reco) {
    const baseReasons = Array.isArray(reco.reasons) ? reco.reasons.map(r => String(r)) : [];
    const extra = [];

    const sd = currentReport?.by_symbol?.[reco.symbol];
    if (sd && !sd.meta?.error) {
        // RSI
        if (sd.rsi !== null && sd.rsi !== undefined) {
            const rsiVal = Number(sd.rsi);
            let rsiNote = '';
            if (!isNaN(rsiVal)) {
                if (rsiVal < 30) rsiNote = ' (перепроданность)';
                else if (rsiVal > 70) rsiNote = ' (перекупленность)';
                extra.push(`RSI: ${rsiVal.toFixed(1)}${rsiNote}`);
            }
        }

        // SMA200 контекст
        if (sd.price && sd.sma_200) {
            const price = Number(sd.price);
            const sma200 = Number(sd.sma_200);
            if (!isNaN(price) && !isNaN(sma200) && sma200 > 0) {
                const diffPct = ((price / sma200 - 1) * 100);
                const side = diffPct >= 0 ? 'выше' : 'ниже';
                extra.push(`Цена ${side} SMA200 на ${Math.abs(diffPct).toFixed(1)}% (SMA200: ${sma200.toFixed(2)}₽)`);
            }
        }

        // 52W контекст
        if (sd.low_52w && sd.high_52w) {
            const low = Number(sd.low_52w);
            const high = Number(sd.high_52w);
            if (!isNaN(low) && !isNaN(high)) {
                extra.push(`52W диапазон: ${low.toFixed(2)}₽ .. ${high.toFixed(2)}₽`);
            }
        }
        if (sd.dist_52w_low_pct !== null && sd.dist_52w_low_pct !== undefined) {
            const v = Number(sd.dist_52w_low_pct);
            if (!isNaN(v)) extra.push(`От 52W Low: +${v.toFixed(1)}%`);
        }
        if (sd.dist_52w_high_pct !== null && sd.dist_52w_high_pct !== undefined) {
            const v = Number(sd.dist_52w_high_pct);
            if (!isNaN(v)) extra.push(`До 52W High: -${v.toFixed(1)}%`);
        }

        // Сигналы (человеческие названия)
        if (Array.isArray(sd.signals) && sd.signals.length) {
            const names = sd.signals.map(s => SIGNAL_META?.[s]?.name || s).join(', ');
            extra.push(`Сигналы: ${names}`);
        }

        // DY
        if (sd.dy_pct !== null && sd.dy_pct !== undefined) {
            const dy = Number(sd.dy_pct);
            if (!isNaN(dy)) extra.push(`DY: ${dy.toFixed(2)}%`);
        }

        // Обновление данных
        if (sd.meta?.updated_at) {
            extra.push(`Данные обновлены: ${formatDateTime(sd.meta.updated_at)}`);
        }
    }

    // Дедупликация
    const all = [...baseReasons];
    for (const line of extra) {
        if (!all.includes(line)) all.push(line);
    }

    return {
        reasonsCount: all.length,
        reasonsHtml: all.map(r => `<li>${escapeHtmlAttr(r)}</li>`).join('')
    };
}

function renderRecommendation(reco) {
    const cardClass = {
        'BUY': 'border-success',
        'HOLD': 'border-secondary',
        'SELL': 'border-danger'
    }[reco.action];
    
    const rr = buildRecommendationReasons(reco);
    
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
                        <summary class="text-muted" style="cursor: pointer;">Обоснование (${rr.reasonsCount})</summary>
                        <ul class="small mt-2 mb-0">
                            ${rr.reasonsHtml}
                        </ul>
                    </details>
                </div>
            </div>
        </div>
    `;
}

async function loadRecommendations() {
    try {
        // Чтобы "обоснование" могло использовать новые метрики из отчёта
        if (!currentReport) {
            const reportData = await fetchAPI('/report/today');
            if (reportData?.ok && reportData?.data) {
                currentReport = reportData.data;
            }
        }

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

