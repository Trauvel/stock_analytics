const API_BASE = '/api';

function _qs(name) {
    const url = new URL(window.location.href);
    return url.searchParams.get(name);
}

function _setAlert(type, text) {
    const el = document.getElementById('login-alert');
    if (!el) return;
    el.className = `alert alert-${type}`;
    el.textContent = text;
}

async function doLogin() {
    const username = (document.getElementById('login-username')?.value || '').trim();
    const password = document.getElementById('login-password')?.value || '';
    if (!username || !password) {
        _setAlert('warning', 'Введите логин и пароль.');
        return;
    }
    try {
        const resp = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await resp.json();
        if (!data.ok) {
            _setAlert('danger', data.error || 'Не удалось войти');
            return;
        }
        _setAlert('success', 'Вход выполнен.');
        const next = _qs('next') || '/static/index.html';
        setTimeout(() => { window.location.href = next; }, 250);
    } catch (e) {
        console.error(e);
        _setAlert('danger', 'Ошибка входа');
    }
}

async function doRegister() {
    const invite_code = (document.getElementById('reg-invite')?.value || '').trim();
    const username = (document.getElementById('reg-username')?.value || '').trim();
    const password = document.getElementById('reg-password')?.value || '';
    if (!invite_code || !username || !password) {
        _setAlert('warning', 'Для регистрации нужны invite code, логин и пароль.');
        return;
    }
    try {
        const resp = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ invite_code, username, password })
        });
        const data = await resp.json();
        if (!data.ok) {
            _setAlert('danger', (data.detail || data.error) || 'Не удалось зарегистрироваться');
            return;
        }
        _setAlert('success', 'Зарегистрировано. Выполняю вход...');
        // авто-логин
        await doLoginWith(username, password);
    } catch (e) {
        console.error(e);
        _setAlert('danger', 'Ошибка регистрации');
    }
}

async function doLoginWith(username, password) {
    const resp = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });
    const data = await resp.json();
    if (!data.ok) {
        _setAlert('warning', 'Пользователь создан, но вход не выполнен. Попробуйте войти вручную.');
        return;
    }
    const next = _qs('next') || '/static/index.html';
    setTimeout(() => { window.location.href = next; }, 250);
}

window.doLogin = doLogin;
window.doRegister = doRegister;

