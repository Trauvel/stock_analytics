"""Модуль для отправки уведомлений в Telegram."""

import os
from pathlib import Path
from typing import List, Optional
from loguru import logger
from dotenv import load_dotenv

from app.domain.price_history.value_objects.change_signal import ChangeSignal, SignalPriority


class TelegramNotifier:
    """Класс для отправки уведомлений в Telegram."""
    
    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None
    ):
        """
        Инициализация notifier.
        
        Args:
            bot_token: Токен Telegram бота (если None, берётся из переменных окружения)
            chat_id: ID чата для отправки (если None, берётся из переменных окружения)
        """
        # Убеждаемся, что .env файл загружен
        # Путь: app/infrastructure/telegram/notifier.py -> корень проекта
        project_root = Path(__file__).parent.parent.parent.parent
        env_path = project_root / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=False)
            logger.debug(f"Loaded .env from {env_path}")
        else:
            logger.debug(f".env file not found at {env_path}")
        
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        # chat_id может быть строкой или числом, конвертируем в строку
        chat_id_env = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        self.chat_id = str(chat_id_env) if chat_id_env else None
        
        # Логируем для отладки (без показа токена)
        if self.bot_token:
            logger.info(f"Telegram bot token found (length: {len(self.bot_token)})")
        else:
            logger.warning("TELEGRAM_BOT_TOKEN not found in environment variables")
        
        if self.chat_id:
            logger.info(f"Telegram chat_id found: {self.chat_id}")
        else:
            logger.warning("TELEGRAM_CHAT_ID not found in environment variables")
        
        self._bot = None
        self._initialized = False
        
        if self.bot_token and self.chat_id:
            self._initialize_bot()
        else:
            logger.warning("Telegram bot token or chat_id not provided. Notifications will be disabled.")
    
    def _initialize_bot(self) -> None:
        """Инициализировать Telegram бота."""
        try:
            from telegram import Bot
            from telegram.error import TelegramError
            import asyncio
            
            # python-telegram-bot 20+ использует async, но мы можем использовать синхронную обёртку
            self._bot = Bot(token=self.bot_token)
            
            # Проверяем, что бот валиден (получаем информацию о боте)
            import threading
            
            async def check_bot():
                try:
                    bot_info = await self._bot.get_me()
                    logger.info(f"Telegram bot verified: @{bot_info.username} ({bot_info.first_name})")
                    return True
                except TelegramError as e:
                    logger.error(f"Invalid Telegram bot token: {e}")
                    return False
            
            def run_bot_check():
                try:
                    # Создаём новый event loop для этого потока
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(check_bot())
                    finally:
                        new_loop.close()
                except Exception as e:
                    logger.error(f"Error in bot check thread: {e}")
                    return False
            
            # Запускаем в отдельном потоке
            result = [False]
            thread = threading.Thread(target=lambda: result.__setitem__(0, run_bot_check()))
            thread.daemon = True
            thread.start()
            thread.join(timeout=5)
            
            if thread.is_alive():
                logger.warning("Bot verification timed out")
                is_valid = False
            else:
                is_valid = result[0]
            
            if not is_valid:
                self._initialized = False
                return
            
            self._initialized = True
            logger.info("Telegram bot initialized successfully")
            
            # Проверяем доступность чата перед отправкой уведомления
            if self.check_chat_access():
                # Отправляем уведомление о запуске сервера
                try:
                    startup_message = "🚀 <b>Stock Analytics Server</b>\n\nСервер успешно запущен и готов к работе!"
                    if self.send_notification(startup_message):
                        logger.info("Startup notification sent to Telegram")
                    else:
                        logger.warning("Failed to send startup notification")
                except Exception as e:
                    logger.warning(f"Could not send startup notification to Telegram: {e}")
            else:
                logger.warning("Chat access check failed, skipping startup notification")
        except ImportError:
            logger.error("python-telegram-bot not installed. Install it with: pip install python-telegram-bot")
            self._initialized = False
        except Exception as e:
            logger.error(f"Error initializing Telegram bot: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            self._initialized = False
    
    def is_enabled(self) -> bool:
        """Проверить, включены ли уведомления."""
        return self._initialized and self._bot is not None
    
    def check_chat_access(self) -> bool:
        """
        Проверить доступность чата для отправки сообщений.
        
        Returns:
            bool: True если чат доступен
        """
        if not self.is_enabled():
            return False
        
        try:
            import asyncio
            from telegram.error import TelegramError
            import threading
            
            
            # Создаём новый event loop в отдельном потоке для избежания конфликтов
            def run_in_thread():
                try:
                    # Импортируем Bot внутри функции (важно для работы в отдельном потоке)
                    from telegram import Bot
                    
                    # Создаём новый event loop для этого потока
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        # Создаём новый Bot объект в этом потоке (важно для правильной работы с event loop)
                        bot = Bot(token=self.bot_token)
                        
                        async def check_with_new_bot():
                            try:
                                # Пробуем получить информацию о чате
                                chat = await bot.get_chat(chat_id=self.chat_id)
                                logger.info(f"Chat access verified: {chat.type} - {chat.title or chat.first_name or 'N/A'}")
                                return True
                            except TelegramError as e:
                                error_msg = str(e)
                                if "Not Found" in error_msg or "chat not found" in error_msg.lower():
                                    logger.error(
                                        f"Chat not found. Chat ID: {self.chat_id}\n"
                                        f"Возможные причины:\n"
                                        f"  1. Неправильный chat_id\n"
                                        f"  2. Бот не добавлен в чат/канал\n"
                                        f"  3. Для каналов: бот должен быть администратором\n"
                                        f"  4. Бот был удалён из чата"
                                    )
                                elif "Forbidden" in error_msg or "bot was blocked" in error_msg.lower():
                                    logger.error(f"Bot was blocked or removed from chat. Chat ID: {self.chat_id}")
                                else:
                                    logger.error(f"Error checking chat access: {error_msg}")
                                return False
                        
                        return new_loop.run_until_complete(check_with_new_bot())
                    finally:
                        # Даём время на завершение всех задач перед закрытием
                        try:
                            pending = asyncio.all_tasks(new_loop)
                            if pending:
                                new_loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        except Exception:
                            pass
                        finally:
                            new_loop.close()
                except Exception as e:
                    logger.error(f"Error in async thread: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
                    return False
            
            # Запускаем в отдельном потоке
            result = [False]
            thread = threading.Thread(target=lambda: result.__setitem__(0, run_in_thread()))
            thread.daemon = True
            thread.start()
            thread.join(timeout=10)
            
            if thread.is_alive():
                logger.warning("Chat access check timed out")
                return False
            
            return result[0]
        except Exception as e:
            logger.error(f"Error checking chat access: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def format_signal_message(self, signal: ChangeSignal) -> str:
        """
        Форматировать сообщение для сигнала об изменении.
        
        Args:
            signal: Сигнал об изменении
            
        Returns:
            str: Отформатированное сообщение
        """
        # Эмодзи в зависимости от направления
        emoji = "📉" if signal.direction.value == "DOWN" else "📈" if signal.direction.value == "UP" else "➡️"
        
        # Приоритет
        priority_emoji = {
            SignalPriority.HIGH: "🔴",
            SignalPriority.MEDIUM: "🟡",
            SignalPriority.LOW: "🟢"
        }.get(signal.priority, "⚪")
        
        message = f"{emoji} <b>{signal.symbol}</b> "
        # Окно сравнения
        message += f"<i>({signal.hours_ago:.0f}ч)</i>: "
        
        if signal.direction.value == "DOWN":
            message += f"Цена снизилась на <b>{abs(signal.price_change_pct):.2f}%</b>\n"
            message += f"💰 Было: {signal.price_before:.2f}₽ → Стало: {signal.price_after:.2f}₽\n"
        elif signal.direction.value == "UP":
            message += f"Цена выросла на <b>{signal.price_change_pct:.2f}%</b>\n"
            message += f"💰 Было: {signal.price_before:.2f}₽ → Стало: {signal.price_after:.2f}₽\n"
        else:
            message += f"Цена изменилась на {signal.price_change_pct:.2f}%\n"

        # Порог срабатывания
        if signal.threshold_used_pct is not None:
            message += f"🎯 Порог: {signal.threshold_used_pct:.2f}%\n"
        
        # Объём
        if signal.volume_spike:
            if signal.volume_multiplier is not None:
                message += f"📊 Объём: {signal.volume_multiplier:.1f}x (высокий)\n"
            else:
                message += f"📊 Объём: высокий\n"
        else:
            message += f"📊 Объём: нормальный\n"

        if signal.volume_after is not None and signal.volume_before is not None:
            message += f"   └ {signal.volume_before:.0f} → {signal.volume_after:.0f}\n"

        # SMA (контекст тренда)
        if signal.sma_200 is not None:
            if signal.price_vs_sma200_pct is not None:
                side = "выше" if signal.price_vs_sma200_pct >= 0 else "ниже"
                message += f"📏 SMA200: {signal.sma_200:.2f}₽ (цена {side} на {abs(signal.price_vs_sma200_pct):.1f}%)\n"
            else:
                message += f"📏 SMA200: {signal.sma_200:.2f}₽\n"
        else:
            # Если SMA200 нет, но есть SMA20/50 — тоже полезно
            if signal.sma_50 is not None:
                message += f"📏 SMA50: {signal.sma_50:.2f}₽\n"
            if signal.sma_20 is not None:
                message += f"📏 SMA20: {signal.sma_20:.2f}₽\n"
        
        # RSI
        if signal.rsi is not None:
            if signal.rsi < 30:
                message += f"📈 RSI: {signal.rsi:.1f} (перепроданность)\n"
            elif signal.rsi > 70:
                message += f"📈 RSI: {signal.rsi:.1f} (перекупленность)\n"
            else:
                message += f"📈 RSI: {signal.rsi:.1f}\n"

        # ATR (волатильность)
        if signal.atr is not None:
            message += f"🌪️ ATR: {signal.atr:.2f}\n"

        # DY/купон
        if signal.dy_pct is not None:
            message += f"💵 DY: {signal.dy_pct:.2f}%\n"
        
        # Рекомендация
        message += f"💡 <b>{signal.recommendation}</b>\n"
        
        # Время
        message += f"⏰ Время: {signal.timestamp.strftime('%H:%M МСК')} ({signal.hours_ago:.0f}ч назад)\n"
        
        # Приоритет
        message += f"{priority_emoji} Приоритет: {signal.priority.value}"
        
        return message
    
    def send_notification(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Отправить уведомление в Telegram.
        
        Args:
            message: Текст сообщения
            parse_mode: Режим парсинга (HTML или Markdown)
            
        Returns:
            bool: True если отправлено успешно
        """
        if not self.is_enabled():
            logger.warning("Telegram bot not initialized, skipping notification")
            return False
        
        try:
            # python-telegram-bot 20+ использует async API
            import asyncio
            from telegram.error import TelegramError
            import threading
            
            # Создаём новый event loop в отдельном потоке для избежания конфликтов
            def run_in_thread():
                try:
                    # Импортируем Bot внутри функции (важно для работы в отдельном потоке)
                    from telegram import Bot
                    
                    # Создаём новый event loop для этого потока
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        # Создаём новый Bot объект в этом потоке (важно для правильной работы с event loop)
                        bot = Bot(token=self.bot_token)
                        
                        async def send_with_new_bot():
                            await bot.send_message(
                                chat_id=self.chat_id,
                                text=message,
                                parse_mode=parse_mode
                            )
                        
                        new_loop.run_until_complete(send_with_new_bot())
                        return True
                    finally:
                        # Даём время на завершение всех задач перед закрытием
                        try:
                            pending = asyncio.all_tasks(new_loop)
                            if pending:
                                new_loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        except Exception:
                            pass
                        finally:
                            new_loop.close()
                except Exception as e:
                    logger.error(f"Error in send notification thread: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
                    return False
            
            # Запускаем в отдельном потоке
            result = [False]
            thread = threading.Thread(target=lambda: result.__setitem__(0, run_in_thread()))
            thread.daemon = True
            thread.start()
            thread.join(timeout=10)
            
            if thread.is_alive():
                logger.warning("Send notification timed out")
                return False
            
            if result[0]:
                logger.info(f"Sent Telegram notification to chat {self.chat_id}")
            
            return result[0]
            
        except TelegramError as e:
            # Специфичные ошибки Telegram API
            error_msg = str(e)
            if "Not Found" in error_msg or "chat not found" in error_msg.lower():
                logger.error(
                    f"Telegram chat not found. Chat ID: {self.chat_id}. "
                    f"Убедитесь, что:\n"
                    f"  1. Бот добавлен в чат/канал\n"
                    f"  2. Chat ID правильный (можно получить через @userinfobot)\n"
                    f"  3. Для каналов: бот должен быть администратором"
                )
            elif "Unauthorized" in error_msg or "invalid token" in error_msg.lower():
                logger.error(
                    f"Telegram bot token invalid. "
                    f"Проверьте TELEGRAM_BOT_TOKEN в .env файле"
                )
            elif "Forbidden" in error_msg or "bot was blocked" in error_msg.lower():
                logger.error(
                    f"Telegram bot was blocked by user. Chat ID: {self.chat_id}"
                )
            else:
                logger.error(f"Telegram API error: {error_msg}")
            return False
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False
    
    def send_signals(self, signals: List[ChangeSignal], group: bool = True) -> int:
        """
        Отправить сигналы об изменениях в Telegram.
        
        Args:
            signals: Список сигналов
            group: Группировать ли сигналы в одно сообщение
            
        Returns:
            int: Количество отправленных сообщений
        """
        if not signals:
            return 0
        
        if not self.is_enabled():
            logger.warning("Telegram bot not initialized, skipping notifications")
            return 0
        
        sent_count = 0
        
        if group and len(signals) > 1:
            # Группируем сигналы в одно сообщение
            message = "<b>📊 Изменения цен:</b>\n\n"
            
            for i, signal in enumerate(signals, 1):
                message += f"{i}. {self.format_signal_message(signal)}\n"
                if i < len(signals):
                    message += "\n"
            
            if self.send_notification(message):
                sent_count = 1
        else:
            # Отправляем каждое уведомление отдельно
            for signal in signals:
                message = self.format_signal_message(signal)
                if self.send_notification(message):
                    sent_count += 1
        
        return sent_count
    
    def send_test_message(self) -> bool:
        """
        Отправить тестовое сообщение для проверки подключения.
        
        Returns:
            bool: True если отправлено успешно
        """
        test_message = "✅ <b>Stock Analytics Bot</b>\n\nБот успешно подключён и готов к работе!"
        return self.send_notification(test_message)
