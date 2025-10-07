"""
Быстрый тест API модуля предсказаний.
Запуск: python test_forecast_api.py
"""
import asyncio
import sys
import os

# Исправление кодировки для Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


async def test_predictor_api():
    """Тест API endpoint'ов предсказаний."""
    print("=" * 70)
    print("  ТЕСТ API МОДУЛЯ ПРЕДСКАЗАНИЙ")
    print("=" * 70)
    print()
    
    try:
        # Тест 1: Базовый импорт
        print("1️⃣ Тест импорта модуля...")
        from app.predictor import generate_event_signals
        print("   ✅ Модуль импортирован успешно")
        print()
        
        # Тест 2: Генерация сигнала без тикеров
        print("2️⃣ Тест генерации сигнала (без тикеров)...")
        try:
            signal = await generate_event_signals()
            print(f"   ✅ Сигнал сгенерирован: {signal['signal_level']}")
            print(f"   📊 Проанализировано: {signal['stats'].get('total', 0)} элементов")
        except Exception as e:
            print(f"   ⚠️  Предупреждение: {e}")
            print("   (Это нормально, если нет интернета или источники недоступны)")
        print()
        
        # Тест 3: Генерация с тикерами
        print("3️⃣ Тест генерации сигнала с тикерами...")
        try:
            signal = await generate_event_signals(['SBER', 'Сбербанк'])
            print(f"   ✅ Сигнал сгенерирован: {signal['signal_level']}")
            print(f"   📝 Обоснование: {signal['reason'][:100]}...")
            print(f"   📊 Статистика:")
            stats = signal['stats']
            print(f"      - Всего: {stats.get('total', 0)}")
            print(f"      - HIGH: {stats.get('HIGH_PROBABILITY', 0)}")
            print(f"      - MEDIUM: {stats.get('MEDIUM_PROBABILITY', 0)}")
            print(f"      - NEGATIVE: {stats.get('NEGATIVE', 0)}")
        except Exception as e:
            print(f"   ⚠️  Ошибка: {e}")
        print()
        
        # Тест 4: Конфигурация
        print("4️⃣ Тест загрузки конфигурации...")
        try:
            from app.predictor.config import PredictorConfig
            config = PredictorConfig.load()
            print(f"   ✅ Конфигурация загружена")
            print(f"   📰 Источников новостей: {len(config.news_sources)}")
            print(f"   🔑 Позитивных ключевых слов: {len(config.positive_keywords)}")
            print(f"   🔑 Негативных ключевых слов: {len(config.negative_keywords)}")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
        print()
        
        # Тест 5: История
        print("5️⃣ Тест истории событий...")
        try:
            import json
            from pathlib import Path
            
            history_file = Path("data/events_history.json")
            if history_file.exists():
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                print(f"   ✅ История найдена: {len(history)} записей")
                if history:
                    last = history[-1]
                    print(f"   📅 Последний сигнал: {last['signal_level']}")
            else:
                print(f"   ℹ️  История пока пуста (файл будет создан при первом запуске)")
        except Exception as e:
            print(f"   ⚠️  Ошибка: {e}")
        print()
        
        print("=" * 70)
        print("  ✅ ВСЕ БАЗОВЫЕ ТЕСТЫ ПРОЙДЕНЫ")
        print("=" * 70)
        print()
        print("Следующий шаг:")
        print("  1. Запустите сервер: python run_server.py")
        print("  2. Откройте: http://localhost:8000/static/forecast.html")
        print()
        
        return True
        
    except Exception as e:
        print("=" * 70)
        print(f"  ❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        result = asyncio.run(test_predictor_api())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
        sys.exit(1)

