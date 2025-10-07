"""
Модуль предсказания новостных всплесков.
Анализирует новости, вакансии и публичные данные для раннего выявления событий.
"""
from .signals import generate_event_signals

__all__ = ["generate_event_signals"]

