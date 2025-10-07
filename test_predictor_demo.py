"""
Демонстрационный скрипт для тестирования модуля предсказаний.
Запуск: python test_predictor_demo.py
"""
import asyncio
import json
from app.predictor import generate_event_signals
from app.predictor.config import PredictorConfig


async def main():
    """Основная функция демонстрации."""
    print("=" * 70)
    print("  ДЕМОНСТРАЦИЯ МОДУЛЯ ПРЕДСКАЗАНИЙ НОВОСТНЫХ ВСПЛЕСКОВ")
    print("=" * 70)
    print()
    
    # Загружаем конфигурацию
    config = PredictorConfig.load()
    print(f"✓ Конфигурация загружена")
    print(f"  - Источников новостей: {len(config.news_sources)}")
    print(f"  - Позитивных ключевых слов: {len(config.positive_keywords)}")
    print(f"  - Негативных ключевых слов: {len(config.negative_keywords)}")
    print(f"  - Использование вакансий: {config.use_vacancies}")
    print()
    
    # Тестируем с несколькими компаниями
    test_companies = [
        ['SBER', 'Сбербанк'],
        ['GAZP', 'Газпром'],
        ['YNDX', 'Яндекс'],
    ]
    
    for companies in test_companies:
        print("-" * 70)
        print(f"📊 Анализ для: {', '.join(companies)}")
        print("-" * 70)
        
        try:
            # Генерируем сигнал
            signal = await generate_event_signals(target_companies=companies)
            
            # Выводим результаты
            print(f"\n🔮 СИГНАЛ: {signal['signal_level']}")
            print(f"\n📝 Обоснование:")
            print(f"   {signal['reason']}")
            
            print(f"\n📈 Статистика:")
            stats = signal.get('stats', {})
            print(f"   - Всего проанализировано: {stats.get('total', 0)}")
            print(f"   - HIGH_PROBABILITY: {stats.get('HIGH_PROBABILITY', 0)}")
            print(f"   - MEDIUM_PROBABILITY: {stats.get('MEDIUM_PROBABILITY', 0)}")
            print(f"   - NEGATIVE: {stats.get('NEGATIVE', 0)}")
            print(f"   - Средний балл: {stats.get('avg_score', 0.0):.2f}")
            
            # Показываем топ новостей
            top_items = signal.get('top_items', [])
            if top_items:
                print(f"\n🔥 Топ-3 релевантные новости:")
                for i, item in enumerate(top_items[:3], 1):
                    print(f"\n   {i}. {item.get('title', 'Без заголовка')}")
                    print(f"      Категория: {item.get('category', 'N/A')}")
                    print(f"      Балл: {item.get('score', 0.0):.2f}")
                    keywords = item.get('matched_keywords', [])
                    if keywords:
                        print(f"      Ключевые слова: {', '.join(keywords[:5])}")
            
            print()
            
        except Exception as e:
            print(f"❌ Ошибка при анализе: {e}")
            import traceback
            traceback.print_exc()
        
        print()
        
        # Небольшая пауза между запросами
        await asyncio.sleep(2)
    
    # Показываем пример интеграции с системой рекомендаций
    print("=" * 70)
    print("  ПРИМЕР ИНТЕГРАЦИИ С СИСТЕМОЙ РЕКОМЕНДАЦИЙ")
    print("=" * 70)
    print()
    
    from app.reco.engine import make_reco
    from app.reco.models import TickerSnapshot, RecoConfig
    
    # Создаём тестовый snapshot
    snapshot = TickerSnapshot(
        symbol="SBER",
        price=270.0,
        sma200=280.0,
        dy_pct=9.5,
        trend_pct_20d=1.2,
        high_52w=320.0,
        low_52w=240.0
    )
    
    reco_config = RecoConfig()
    
    # Без сигнала предсказаний
    reco_without = make_reco(snapshot, reco_config)
    print("📊 Рекомендация БЕЗ модуля предсказаний:")
    print(f"   Действие: {reco_without.action}")
    print(f"   Score: {reco_without.score}")
    print()
    
    # Получаем сигнал
    signal = await generate_event_signals(['SBER'])
    
    # С сигналом предсказаний
    reco_with = make_reco(snapshot, reco_config, event_signal=signal)
    print("📊 Рекомендация С модулем предсказаний:")
    print(f"   Действие: {reco_with.action}")
    print(f"   Score: {reco_with.score}")
    print(f"   Разница в score: {reco_with.score - reco_without.score:+.2f}")
    print()
    
    if reco_with.reasons:
        print("   Обоснование:")
        for reason in reco_with.reasons:
            print(f"   - {reason}")
    
    print()
    print("=" * 70)
    print("  ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

