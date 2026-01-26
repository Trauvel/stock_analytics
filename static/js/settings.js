// Stock Analytics - Settings Page

const API_BASE = '/api';
let currentPortfolio = null;
let currentConfig = null;
let currentPortfolioId = null;
let portfoliosList = [];

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
async function loadPortfoliosList() {
    try {
        const response = await fetch(`${API_BASE}/portfolios`);
        const data = await response.json();
        
        if (data.ok && data.data) {
            portfoliosList = data.data;
            
            const select = document.getElementById('portfolio-select');
            select.innerHTML = '<option value="">-- Выберите портфель --</option>';
            
            portfoliosList.forEach(portfolio => {
                const option = document.createElement('option');
                option.value = portfolio.id;
                option.textContent = `${portfolio.name || `Портфель ${portfolio.id.substring(0, 8)}`} (${portfolio.positions_count} позиций)`;
                if (portfolio.id === currentPortfolioId) {
                    option.selected = true;
                }
                select.appendChild(option);
            });
            
            // Если есть портфели и не выбран текущий, выбираем первый
            if (portfoliosList.length > 0 && !currentPortfolioId) {
                currentPortfolioId = portfoliosList[0].id;
                select.value = currentPortfolioId;
                await loadPortfolio(currentPortfolioId);
            }
        } else {
            console.warn('No portfolios found');
            portfoliosList = [];
        }
    } catch (error) {
        console.error('Error loading portfolios list:', error);
    }
}

async function loadPortfolio(portfolioId = null) {
    try {
        const url = portfolioId 
            ? `${API_BASE}/portfolio/${portfolioId}`
            : `${API_BASE}/portfolio/view`;
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.ok && data.data) {
            currentPortfolio = data.data;
            currentPortfolioId = currentPortfolio.id;
            
            document.getElementById('portfolio-name').value = currentPortfolio.name || '';
            document.getElementById('portfolio-currency').value = currentPortfolio.currency || 'RUB';
            document.getElementById('portfolio-cash').value = currentPortfolio.cash || 0;
            
            // Показываем кнопку удаления, если это не дефолтный портфель
            const deleteBtn = document.getElementById('delete-portfolio-btn');
            if (currentPortfolioId && currentPortfolioId !== 'default') {
                deleteBtn.style.display = 'inline-block';
            } else {
                deleteBtn.style.display = 'none';
            }
            
            renderPositions();
        } else {
            // Создаём пустой портфель
            currentPortfolio = {
                id: null,
                name: '',
                currency: 'RUB',
                cash: 0,
                positions: []
            };
            currentPortfolioId = null;
            renderPositions();
        }
    } catch (error) {
        console.error('Error loading portfolio:', error);
        showAlert('Ошибка загрузки портфеля', 'danger');
    }
}

async function selectPortfolio() {
    const select = document.getElementById('portfolio-select');
    const portfolioId = select.value;
    
    if (portfolioId) {
        currentPortfolioId = portfolioId;
        await loadPortfolio(portfolioId);
    } else {
        currentPortfolio = {
            id: null,
            name: '',
            currency: 'RUB',
            cash: 0,
            positions: []
        };
        currentPortfolioId = null;
        renderPositions();
    }
}

function showCreatePortfolioModal() {
    const modal = new bootstrap.Modal(document.getElementById('createPortfolioModal'));
    modal.show();
}

async function createPortfolio() {
    try {
        const name = document.getElementById('new-portfolio-name').value.trim();
        const currency = document.getElementById('new-portfolio-currency').value;
        const cash = parseFloat(document.getElementById('new-portfolio-cash').value) || 0;
        
        if (!name) {
            showAlert('Введите название портфеля', 'danger');
            return;
        }
        
        const response = await fetch(`${API_BASE}/portfolios`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                name: name,
                currency: currency,
                cash: cash
            })
        });
        
        const data = await response.json();
        
        if (data.ok && data.data) {
            showAlert('Портфель успешно создан!', 'success');
            
            // Закрываем модальное окно
            const modal = bootstrap.Modal.getInstance(document.getElementById('createPortfolioModal'));
            modal.hide();
            
            // Очищаем форму
            document.getElementById('new-portfolio-name').value = '';
            document.getElementById('new-portfolio-cash').value = '0';
            
            // Обновляем список и загружаем новый портфель
            await loadPortfoliosList();
            currentPortfolioId = data.data.id;
            await loadPortfolio(currentPortfolioId);
        } else {
            showAlert(`Ошибка: ${data.error || 'Unknown error'}`, 'danger');
        }
    } catch (error) {
        console.error('Error creating portfolio:', error);
        showAlert('Ошибка создания портфеля', 'danger');
    }
}

async function deleteCurrentPortfolio() {
    if (!currentPortfolioId) {
        showAlert('Нет выбранного портфеля', 'warning');
        return;
    }
    
    if (currentPortfolioId === 'default') {
        showAlert('Нельзя удалить дефолтный портфель', 'warning');
        return;
    }
    
    if (!confirm(`Вы уверены, что хотите удалить портфель "${currentPortfolio?.name || currentPortfolioId}"? Это действие нельзя отменить.`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/portfolio/${currentPortfolioId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.ok) {
            showAlert('Портфель успешно удалён!', 'success');
            
            // Очищаем текущий портфель
            currentPortfolio = {
                id: null,
                name: '',
                currency: 'RUB',
                cash: 0,
                positions: []
            };
            currentPortfolioId = null;
            
            // Обновляем список и интерфейс
            await loadPortfoliosList();
            renderPositions();
        } else {
            showAlert(`Ошибка: ${data.message || 'Unknown error'}`, 'danger');
        }
    } catch (error) {
        console.error('Error deleting portfolio:', error);
        showAlert('Ошибка удаления портфеля', 'danger');
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

// Объявляем функцию глобально
async function importFromSber() {
    console.log('importFromSber called');
    
    const fileInput = document.getElementById('sber-html-file');
    const mergeCheckbox = document.getElementById('merge-positions');
    const statusDiv = document.getElementById('import-status');
    
    if (!fileInput) {
        console.error('fileInput not found');
        alert('Ошибка: элемент fileInput не найден');
        return;
    }
    
    if (!fileInput.files || fileInput.files.length === 0) {
        if (statusDiv) {
            statusDiv.innerHTML = '<div class="alert alert-warning">Выберите HTML файл отчёта Сбера</div>';
        } else {
            alert('Выберите HTML файл отчёта Сбера');
        }
        return;
    }
    
    const file = fileInput.files[0];
    const merge = mergeCheckbox ? mergeCheckbox.checked : true;
    
    console.log('File selected:', file.name, 'Merge:', merge);
    
    try {
        if (statusDiv) {
            statusDiv.innerHTML = '<div class="alert alert-info">⏳ Импорт в процессе...</div>';
        }
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('merge', merge.toString());
        if (currentPortfolioId) {
            formData.append('portfolio_id', currentPortfolioId);
        }
        
        console.log('Sending request to /api/portfolio/import/sber-html');
        
        const response = await fetch('/api/portfolio/import/sber-html', {
            method: 'POST',
            body: formData
        });
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Response error:', errorText);
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
        
        const data = await response.json();
        console.log('Response data:', data);
        
        if (data.ok) {
            if (statusDiv) {
                statusDiv.innerHTML = `<div class="alert alert-success">✅ ${data.message}</div>`;
            } else {
                alert(`✅ ${data.message}`);
            }
            // Перезагружаем портфель
            setTimeout(async () => {
                if (typeof loadPortfolio === 'function') {
                    await loadPortfolio(currentPortfolioId);
                    await loadPortfoliosList();
                }
            }, 1000);
        } else {
            const errorMsg = data.message || 'Ошибка импорта';
            if (statusDiv) {
                statusDiv.innerHTML = `<div class="alert alert-danger">❌ ${errorMsg}</div>`;
            } else {
                alert(`❌ ${errorMsg}`);
            }
        }
    } catch (error) {
        console.error('Error importing from Sber:', error);
        const errorMsg = error.message || 'Неизвестная ошибка';
        if (statusDiv) {
            statusDiv.innerHTML = `<div class="alert alert-danger">❌ Ошибка: ${errorMsg}</div>`;
        } else {
            alert(`❌ Ошибка: ${errorMsg}`);
        }
    }
}

// Также делаем доступной через window для совместимости
window.importFromSber = importFromSber;

async function clearPortfolio() {
    if (!confirm('Вы уверены, что хотите очистить весь портфель? Это действие нельзя отменить.')) {
        return;
    }
    
    try {
        // Создаём пустой портфель
        const portfolio = {
            id: currentPortfolioId, // Сохраняем ID
            name: document.getElementById('portfolio-name').value || 'Пустой портфель',
            currency: document.getElementById('portfolio-currency').value || 'RUB',
            cash: 0,
            positions: []
        };
        
        const response = await fetch(`${API_BASE}/portfolio`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(portfolio)
        });
        
        const data = await response.json();
        
        if (data.ok) {
            showAlert('Портфель успешно очищен!', 'success');
            await loadPortfolio(currentPortfolioId); // Перезагрузить
        } else {
            showAlert(`Ошибка: ${data.error || 'Unknown error'}`, 'danger');
        }
        
    } catch (error) {
        console.error('Error clearing portfolio:', error);
        showAlert('Ошибка очистки портфеля', 'danger');
    }
}

// Делаем доступной через window для совместимости
window.clearPortfolio = clearPortfolio;

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
            id: currentPortfolioId, // Сохраняем ID если есть
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
            
            // Обновляем ID если был создан новый портфель
            if (data.data && data.data.id) {
                currentPortfolioId = data.data.id;
            }
            
            await loadPortfolio(currentPortfolioId); // Перезагрузить
            await loadPortfoliosList(); // Обновить список
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
    loadPortfoliosList();
    loadConfig();
    loadSchedulerStatus();
});

