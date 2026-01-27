"""Загрузчик конфигурации мониторинга (config/monitoring.yaml)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml
from loguru import logger


DEFAULT_MONITORING_CONFIG: Dict[str, Any] = {
    "telegram": {"enabled": True},
    "monitoring": {
        "update_interval_hours": 3,
        "candles_cache_enabled": True,
        "candles_cache_refresh_days": 7,
        "candles_period_minutes": 60,
        "candles_days_daily": 400,
        "candles_days_frequent": 400,
        "price_change_threshold_pct": 3.0,
        "volume_spike_threshold": 2.0,
        "use_adaptive_thresholds": True,
        "filter_trading_hours": True,
        "compare_periods": [{"hours": 3}, {"hours": 24}],
    },
    "notifications": {"only_portfolio": True, "min_priority": "LOW", "group_notifications": True},
    "price_history": {"days_to_keep": 30},
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Рекурсивно объединить два dict (override поверх base)."""
    result: Dict[str, Any] = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def load_monitoring_config() -> Dict[str, Any]:
    """
    Загрузить конфиг мониторинга из `config/monitoring.yaml`.

    Возвращает dict с дефолтами, чтобы приложение не падало при отсутствии файла.
    """
    project_root = Path(__file__).parent.parent.parent
    cfg_path = project_root / "config" / "monitoring.yaml"

    if not cfg_path.exists():
        logger.warning(f"Monitoring config not found: {cfg_path} (using defaults)")
        return dict(DEFAULT_MONITORING_CONFIG)

    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        merged = _deep_merge(DEFAULT_MONITORING_CONFIG, raw)
        return merged
    except Exception as e:
        logger.warning(f"Failed to load monitoring config {cfg_path}: {e} (using defaults)")
        return dict(DEFAULT_MONITORING_CONFIG)

