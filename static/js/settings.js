// Stock Analytics - Settings Page

const API_BASE = '/api';
let currentPortfolio = null;
let currentConfig = null;

// === Утилиты ===
function showAlert(message, type = 'success') {
    const container = document.querySelector('.container');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        <strong>${type === 'success' ? '✓' : '✗'}</strong> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    container.insertBefore(alert, container.firstChild);
    
    setTimeout(() => alert.remove(), 5000);
}

// === Портфель ===
async function loadPortfolio() {
    try {
        const response = await fetch(`${API_BASE}/portfolio/view`);
        const data = await response.json();
        
        if (data.ok && data.data) {
            currentPortfolio = data.data;
            
            document.getElementById('portfolio-name').value = currentPortfolio.name || '';
            document.getElementById('portfolio-currency').value = currentPortfolio.currency || 'RUB';
            document.getElementById('portfolio-cash').value = currentPortfolio.cash || 0;
            
            renderPositions();
        } else {
            // Создаём пустой портфель
            currentPortfolio = {
                name: '',
                currency: 'RUB',
                cash: 0,
                positions: []
            };
            renderPositions();
        }
    } catch (error) {
        console.error('Error loading portfolio:', error);
        showAlert('Ошибка загрузки портфеля', 'danger');
    }
}

function renderPositions() {
    const container = document.getElementById('positions-list');
    
    if (!currentPortfolio.positions || currentPortfolio.positions.length === 0) {
        container.innerHTML = '<p class="text-muted">Нет позиций. Добавьте первую позицию.</p>';
        return;
    }
    
    container.innerHTML = currentPortfolio.positions.map((pos, idx) => {
        // Поддержка обоих форматов: qty и quantity
        const quantity = pos.qty || pos.quantity || 0;
        const notes = pos.notes || pos.name || '';
        
        return `
        <div class="card mb-2">
            <div class="card-body">
                <div class="row align-items-center">
                    <div class="col-md-2">
                        <label class="form-label">Тикер</label>
                        <input type="text" class="form-control" value="${pos.symbol}" 
                               onchange="updatePosition(${idx}, 'symbol', this.value)">
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Количество</label>
                        <input type="number" class="form-control" value="${quantity}" 
                               onchange="updatePosition(${idx}, 'quantity', parseInt(this.value))">
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Ср. цена</label>
                        <input type="number" class="form-control" value="${pos.avg_price || ''}" 
                               onchange="updatePosition(${idx}, 'avg_price', parseFloat(this.value))">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Заметки</label>
                        <input type="text" class="form-control" value="${notes}" 
                               onchange="updatePosition(${idx}, 'notes', this.value)">
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">&nbsp;</label>
                        <button class="btn btn-danger w-100" onclick="removePosition(${idx})">🗑️ Удалить</button>
                    </div>
                </div>
            </div>
        </div>
        `;
    }).join('');
}

function addPosition() {
    if (!currentPortfolio.positions) {
        currentPortfolio.positions = [];
    }
    
    currentPortfolio.positions.push({
        symbol: '',
        quantity: 0,
        avg_price: 0,
        market: 'moex',
        type: 'stock',
        notes: ''
    });
    
    renderPositions();
}

function removePosition(idx) {
    if (confirm(`Удалить позицию ${currentPortfolio.positions[idx].symbol}?`)) {
        currentPortfolio.positions.splice(idx, 1);
        renderPositions();
    }
}

function updatePosition(idx, field, value) {
    currentPortfolio.positions[idx][field] = value;
    // Синхронизация qty <-> quantity
    if (field === 'quantity') {
        currentPortfolio.positions[idx]['qty'] = value;
    }
}

async function savePortfolio() {
    try {
        // Собираем данные из формы
        const positions = currentPortfolio.positions
            .filter(p => p.symbol) // Только с тикерами
            .map(p => ({
                symbol: p.symbol,
                qty: p.qty || p.quantity || 0,
                quantity: p.qty || p.quantity || 0, // Для обратной совместимости
                avg_price: p.avg_price || 0,
                market: p.market || 'moex',
                type: p.type || 'stock',
                notes: p.notes || p.name || ''
            }));
        
        const portfolio = {
            name: document.getElementById('portfolio-name').value,
            currency: document.getElementById('portfolio-currency').value,
            cash: parseFloat(document.getElementById('portfolio-cash').value) || 0,
            positions: positions
        };
        
        const response = await fetch(`${API_BASE}/portfolio`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(portfolio)
        });
        
        const data = await response.json();
        
        if (data.ok) {
            showAlert('Портфель успешно сохранён!', 'success');
            loadPortfolio(); // Перезагрузить
        } else {
            showAlert(`Ошибка: ${data.error || 'Unknown error'}`, 'danger');
        }
        
    } catch (error) {
        console.error('Error saving portfolio:', error);
        showAlert('Ошибка сохранения портфеля', 'danger');
    }
}

// === Конфигурация ===
async function loadConfig() {
    try {
        const response = await fetch(`${API_BASE}/config`);
        const data = await response.json();
        
        if (data.ok) {
            currentConfig = data.data;
            
            // Заполняем параметры
            document.getElementById('dividend-target').value = currentConfig.dividend_target_pct;
            document.getElementById('sma-windows').value = currentConfig.windows.sma.join(', ');
            document.getElementById('rate-limit').value = currentConfig.rate_limit.per_symbol_sleep_sec;
            
            // Планировщик
            document.getElementById('daily-time').value = currentConfig.schedule.daily_time;
            document.getElementById('timezone').value = currentConfig.schedule.tz;
            
            // Список тикеров
            renderTickers();
        } else {
            showAlert(`Ошибка: ${data.error}`, 'danger');
        }
    } catch (error) {
        console.error('Error loading config:', error);
        showAlert('Ошибка загрузки конфигурации', 'danger');
    }
}

function renderTickers() {
    const container = document.getElementById('tickers-list');
    
    if (!currentConfig || !currentConfig.universe || currentConfig.universe.length === 0) {
        container.innerHTML = '<p class="text-muted">Нет тикеров</p>';
        return;
    }
    
    container.innerHTML = `
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>№</th>
                        <th>Тикер</th>
                        <th>Рынок</th>
                        <th>Действия</th>
                    </tr>
                </thead>
                <tbody>
                    ${currentConfig.universe.map((ticker, idx) => `
                        <tr>
                            <td>${idx + 1}</td>
                            <td><strong>${ticker.symbol}</strong></td>
                            <td>${ticker.market}</td>
                            <td>
                                <button class="btn btn-sm btn-danger" 
                                        onclick="removeTicker('${ticker.symbol}')">
                                    🗑️ Удалить
                                </button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

async function addTicker() {
    const symbol = document.getElementById('new-ticker').value.trim().toUpperCase();
    
    if (!symbol) {
        showAlert('Введите тикер', 'warning');
        return;
    }
    
    // Проверка формата
    if (!/^[A-Z0-9]+$/.test(symbol)) {
        showAlert('Тикер может содержать только A-Z и 0-9', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/config/add-ticker`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({symbol: symbol, market: 'moex'})
        });
        
        const data = await response.json();
        
        if (data.ok) {
            showAlert(`Тикер ${symbol} добавлен!`, 'success');
            document.getElementById('new-ticker').value = '';
            loadConfig(); // Перезагрузить
        } else {
            showAlert(`Ошибка: ${data.error}`, 'danger');
        }
        
    } catch (error) {
        console.error('Error adding ticker:', error);
        showAlert('Ошибка добавления тикера', 'danger');
    }
}

async function removeTicker(symbol) {
    if (!confirm(`Удалить тикер ${symbol}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/config/remove-ticker/${symbol}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.ok) {
            showAlert(`Тикер ${symbol} удалён`, 'success');
            loadConfig(); // Перезагрузить
        } else {
            showAlert(`Ошибка: ${data.error}`, 'danger');
        }
        
    } catch (error) {
        console.error('Error removing ticker:', error);
        showAlert('Ошибка удаления тикера', 'danger');
    }
}

async function saveParameters() {
    try {
        const smaWindows = document.getElementById('sma-windows').value
            .split(',')
            .map(s => parseInt(s.trim()))
            .filter(n => !isNaN(n));
        
        const updateData = {
            dividend_target_pct: parseFloat(document.getElementById('dividend-target').value),
            windows: {sma: smaWindows},
            rate_limit: {
                per_symbol_sleep_sec: parseFloat(document.getElementById('rate-limit').value)
            }
        };
        
        const response = await fetch(`${API_BASE}/config/update`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(updateData)
        });
        
        const data = await response.json();
        
        if (data.ok) {
            showAlert('Параметры сохранены!', 'success');
        } else {
            showAlert(`Ошибка: ${data.error}`, 'danger');
        }
        
    } catch (error) {
        console.error('Error saving parameters:', error);
        showAlert('Ошибка сохранения параметров', 'danger');
    }
}

async function saveScheduler() {
    try {
        const time = document.getElementById('daily-time').value;
        const tz = document.getElementById('timezone').value;
        
        const updateData = {
            schedule: {
                daily_time: time,
                tz: tz
            }
        };
        
        const response = await fetch(`${API_BASE}/config/update`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(updateData)
        });
        
        const data = await response.json();
        
        if (data.ok) {
            showAlert('Настройки планировщика сохранены! Перезапустите сервер.', 'warning');
        } else {
            showAlert(`Ошибка: ${data.error}`, 'danger');
        }
        
    } catch (error) {
        console.error('Error saving scheduler:', error);
        showAlert('Ошибка сохранения настроек', 'danger');
    }
}

async function loadSchedulerStatus() {
    try {
        const response = await fetch('/scheduler/status');
        const data = await response.json();
        
        if (data.ok) {
            const info = document.getElementById('scheduler-status-info');
            const jobs = data.data.jobs;
            
            if (jobs && jobs.length > 0) {
                const job = jobs[0];
                info.className = 'alert alert-success';
                info.innerHTML = `
                    <strong>✓ Планировщик работает</strong><br>
                    <small>Следующий запуск: ${job.next_run_time || 'N/A'}</small>
                `;
            } else {
                info.className = 'alert alert-warning';
                info.innerHTML = '<strong>⚠️ Планировщик не настроен</strong>';
            }
        }
    } catch (error) {
        console.error('Error loading scheduler status:', error);
    }
}

// === Инициализация ===
window.addEventListener('load', () => {
    loadPortfolio();
    loadConfig();
    loadSchedulerStatus();
});

