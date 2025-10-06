"""Загрузка конфигурации для системы рекомендаций."""

from pathlib import Path
from typing import Optional
import yaml

from .models import RecoConfig


_config_cache: Optional[RecoConfig] = None


def load_reco_config(config_path: Optional[str] = None) -> RecoConfig:
    """
    Загружает конфигурацию рекомендаций из YAML файла.
    
    Args:
        config_path: Путь к файлу конфигурации. По умолчанию config/reco.yaml
        
    Returns:
        RecoConfig: Конфигурация правил
    """
    if config_path is None:
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "reco.yaml"
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        # Возвращаем дефолтную конфигурацию
        return RecoConfig()
    
    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    return RecoConfig(**data)


def get_reco_config() -> RecoConfig:
    """
    Получить закешированный экземпляр конфигурации.
    
    Returns:
        RecoConfig: Конфигурация правил
    """
    global _config_cache
    if _config_cache is None:
        _config_cache = load_reco_config()
    return _config_cache


def reload_reco_config(config_path: Optional[str] = None) -> RecoConfig:
    """
    Перезагрузить конфигурацию.
    
    Args:
        config_path: Путь к файлу конфигурации
        
    Returns:
        RecoConfig: Обновлённая конфигурация
    """
    global _config_cache
    _config_cache = load_reco_config(config_path)
    return _config_cache

