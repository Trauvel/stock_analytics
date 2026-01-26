"""Пример использования DDD архитектуры."""

import asyncio
from app.application.dependencies import container
from app.application.stock_analysis.generate_report_use_case import GenerateReportUseCase


async def main():
    """Пример генерации отчёта через DDD use case."""
    
    # Получаем use case из контейнера зависимостей
    use_case: GenerateReportUseCase = container.generate_report_use_case()
    
    # Генерируем отчёт для нескольких тикеров
    symbols = ["SBER", "VTBR", "MOEX"]
    
    print(f"Генерация отчёта для {len(symbols)} тикеров...")
    report = await use_case.execute(symbols=symbols)
    
    print(f"\n✅ Отчёт сгенерирован!")
    print(f"Дата: {report['generated_at']}")
    print(f"Тикеров обработано: {len(report['universe'])}")
    
    # Показываем результаты по каждому тикеру
    print("\n📊 Результаты:")
    for symbol, data in report['by_symbol'].items():
        price = data.get('price')
        dy = data.get('dy_pct')
        signals_count = len(data.get('signals', []))
        
        print(f"\n{symbol}:")
        print(f"  Цена: {price}₽" if price else "  Цена: N/A")
        print(f"  Дивидендная доходность: {dy}%" if dy else "  DY: N/A")
        print(f"  Сигналов: {signals_count}")
        if signals_count > 0:
            print(f"  Сигналы: {', '.join(data['signals'])}")


if __name__ == "__main__":
    asyncio.run(main())
