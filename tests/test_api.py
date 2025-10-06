"""Тесты для FastAPI сервера."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from datetime import datetime

from app.api.server import app
from app.models import Portfolio, Position, PositionType


@pytest.fixture
def client():
    """Создать тестовый клиент."""
    return TestClient(app)


def test_root(client):
    """Тест корневого эндпоинта API."""
    response = client.get("/")
    assert response.status_code == 200
    
    # API возвращает JSON
    data = response.json()
    assert data["ok"] is True
    assert "message" in data


def test_health_check(client):
    """Тест проверки здоровья."""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["ok"] is True
    assert "timestamp" in data
    assert "version" in data


def test_get_tickers(client):
    """Тест получения списка тикеров."""
    response = client.get("/tickers")
    assert response.status_code == 200
    
    data = response.json()
    assert data["ok"] is True
    assert "data" in data
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0
    
    # Проверяем наличие основных тикеров
    tickers = data["data"]
    assert "SBER" in tickers
    assert "GAZP" in tickers


@patch('app.api.server.load_analysis_report')
def test_get_report_success(mock_load, client):
    """Тест успешного получения отчёта."""
    mock_report = {
        "generated_at": datetime.now().isoformat(),
        "universe": ["SBER", "GAZP"],
        "by_symbol": {}
    }
    mock_load.return_value = mock_report
    
    with patch('app.api.server.Path.exists', return_value=True):
        response = client.get("/report/today")
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["data"] is not None


def test_get_report_not_found(client):
    """Тест получения отчёта когда его нет."""
    with patch('app.api.server.Path.exists', return_value=False):
        response = client.get("/report/today")
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert data["error"] is not None


@patch('app.api.server.save_portfolio')
def test_save_portfolio(mock_save, client):
    """Тест сохранения портфеля."""
    portfolio_data = {
        "name": "Test Portfolio",
        "currency": "RUB",
        "cash": 100000.0,
        "positions": [
            {
                "symbol": "SBER",
                "quantity": 100,
                "avg_price": 265.30,
                "market": "moex",
                "type": "stock"
            }
        ]
    }
    
    response = client.post("/portfolio", json=portfolio_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["ok"] is True
    assert "message" in data
    
    # Проверяем что save_portfolio был вызван
    assert mock_save.called


@patch('app.api.server.save_portfolio')
def test_save_invalid_portfolio(mock_save, client):
    """Тест сохранения невалидного портфеля."""
    invalid_data = {
        "currency": "RUB",
        "positions": [
            {
                "symbol": "INVALID!@#",  # Невалидный тикер (спецсимволы)
                "quantity": -10,  # Отрицательное количество
            }
        ]
    }
    
    response = client.post("/portfolio", json=invalid_data)
    assert response.status_code == 422  # Validation error
    
    # save_portfolio НЕ должен быть вызван при ошибке валидации
    assert not mock_save.called


@patch('app.api.server.load_portfolio')
def test_get_portfolio_success(mock_load, client):
    """Тест успешного получения портфеля."""
    mock_portfolio = {
        "name": "Test",
        "currency": "RUB",
        "positions": []
    }
    mock_load.return_value = mock_portfolio
    
    response = client.get("/portfolio/view")
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["data"] is not None


@patch('app.api.server.load_portfolio')
def test_get_portfolio_not_found(mock_load, client):
    """Тест получения портфеля когда его нет."""
    mock_load.return_value = None
    
    response = client.get("/portfolio/view")
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert data["error"] is not None


@patch('app.api.server.load_analysis_report')
def test_get_report_summary(mock_load, client):
    """Тест получения сводки по отчёту."""
    mock_report = {
        "generated_at": datetime.now().isoformat(),
        "universe": ["SBER", "GAZP"],
        "by_symbol": {
            "SBER": {
                "price": 290.5,
                "dy_pct": 10.0,
                "signals": ["PRICE_ABOVE_SMA200", "DY_GT_TARGET"],
                "meta": {"error": None}
            },
            "GAZP": {
                "price": 120.0,
                "dy_pct": 5.0,
                "signals": ["PRICE_BELOW_SMA200"],
                "meta": {"error": None}
            }
        }
    }
    mock_load.return_value = mock_report
    
    with patch('app.api.server.Path.exists', return_value=True):
        response = client.get("/report/summary")
    
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["data"]["total_symbols"] == 2
    assert data["data"]["successful"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

