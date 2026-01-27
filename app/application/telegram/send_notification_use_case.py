"""Use case для отправки уведомлений в Telegram."""

from typing import List
from loguru import logger

from app.domain.price_history.value_objects.change_signal import ChangeSignal
from app.infrastructure.telegram.notifier import TelegramNotifier


class SendNotificationUseCase:
    """Use case для отправки уведомлений в Telegram."""
    
    def __init__(self, telegram_notifier: TelegramNotifier):
        """
        Инициализация use case.
        
        Args:
            telegram_notifier: Notifier для отправки уведомлений
        """
        self._notifier = telegram_notifier
    
    def execute(self, signals: List[ChangeSignal], group: bool = True, chat_id: str | None = None) -> int:
        """
        Выполнить use case - отправить уведомления о сигналах.
        
        Args:
            signals: Список сигналов для отправки
            group: Группировать ли сигналы в одно сообщение
            
        Returns:
            int: Количество отправленных сообщений
        """
        if not signals:
            logger.debug("No signals to send")
            return 0
        
        if not self._notifier.is_enabled():
            logger.warning("Telegram notifier is not enabled, skipping notifications")
            return 0
        
        logger.info(f"Sending {len(signals)} notifications to Telegram")
        
        sent_count = self._notifier.send_signals(signals, group=group, chat_id=chat_id)
        
        logger.info(f"Sent {sent_count} notification(s) to Telegram")
        
        return sent_count
