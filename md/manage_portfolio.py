"""Скрипт для управления портфелем."""

import sys
import json
from datetime import datetime
from app.store.io import save_portfolio, load_portfolio

def show_portfolio():
    """Показать текущий портфель."""
    print("=" * 80)
    print("ТЕКУЩИЙ ПОРТФЕЛЬ")
    print("=" * 80)
    
    portfolio = load_portfolio()
    
    if not portfolio:
        print("\n[INFO] Портфель не найден. Создайте новый командой:")
        print("  python manage_portfolio.py create")
        return
    
    print(f"\nНазвание: {portfolio.get('name', 'Без названия')}")
    print(f"Валюта: {portfolio.get('currency', 'RUB')}")
    print(f"Свободные средства: {portfolio.get('cash', 0):,.2f} {portfolio.get('currency', 'RUB')}")
    
    positions = portfolio.get('positions', [])
    print(f"\nПозиций: {len(positions)}")
    
    if positions:
        print("\n" + "-" * 80)
        print(f"{'Тикер':<10} {'Количество':<12} {'Ср. цена':<12} {'Сумма':<15} {'Заметки'}")
        print("-" * 80)
        
        total_value = 0
        for pos in positions:
            symbol = pos['symbol']
            qty = pos['quantity']
            avg_price = pos.get('avg_price', 0)
            value = qty * avg_price if avg_price else 0
            notes = pos.get('notes', '')
            
            print(f"{symbol:<10} {qty:<12} {avg_price:<12.2f} {value:<15,.2f} {notes or '-'}")
            total_value += value
        
        print("-" * 80)
        print(f"Общая стоимость позиций: {total_value:,.2f} {portfolio.get('currency', 'RUB')}")
        print(f"Всего с кешем: {total_value + portfolio.get('cash', 0):,.2f} {portfolio.get('currency', 'RUB')}")
    
    print(f"\nСоздан: {portfolio.get('created_at', 'N/A')}")
    print(f"Обновлён: {portfolio.get('updated_at', 'N/A')}")


def create_portfolio():
    """Создать новый портфель интерактивно."""
    print("=" * 80)
    print("СОЗДАНИЕ НОВОГО ПОРТФЕЛЯ")
    print("=" * 80)
    
    name = input("\nНазвание портфеля [Мой портфель]: ").strip() or "Мой портфель"
    currency = input("Валюта [RUB]: ").strip() or "RUB"
    
    try:
        cash = float(input("Свободные средства [0]: ").strip() or "0")
    except ValueError:
        cash = 0
    
    positions = []
    
    print("\nДобавьте позиции (пустой тикер для завершения):")
    
    while True:
        print(f"\nПозиция #{len(positions) + 1}")
        symbol = input("  Тикер (например SBER): ").strip().upper()
        
        if not symbol:
            break
        
        try:
            quantity = int(input("  Количество: ").strip())
            avg_price = float(input("  Средняя цена покупки: ").strip())
            notes = input("  Заметки (необязательно): ").strip()
            
            position = {
                "symbol": symbol,
                "quantity": quantity,
                "avg_price": avg_price,
                "market": "moex",
                "type": "stock"
            }
            
            if notes:
                position["notes"] = notes
            
            positions.append(position)
            print(f"  [OK] Добавлено: {symbol} x {quantity} @ {avg_price}")
            
        except ValueError as e:
            print(f"  [ERROR] Неверный формат данных: {e}")
            continue
    
    # Формируем портфель
    portfolio_data = {
        "name": name,
        "currency": currency,
        "cash": cash,
        "positions": positions,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # Сохраняем
    save_portfolio(portfolio_data)
    
    print("\n" + "=" * 80)
    print("[SUCCESS] Портфель создан и сохранён в data/portfolio.json")
    print("=" * 80)
    
    # Показываем что получилось
    show_portfolio()


def update_from_template():
    """Обновить портфель из шаблона."""
    print("=" * 80)
    print("ОБНОВЛЕНИЕ ПОРТФЕЛЯ ИЗ ШАБЛОНА")
    print("=" * 80)
    
    # Шаблон портфеля
    portfolio_data = {
        "name": "Основной портфель",
        "currency": "RUB",
        "cash": 50000.0,
        "positions": [
            {
                "symbol": "SBER",
                "quantity": 100,
                "avg_price": 265.30,
                "market": "moex",
                "type": "stock",
                "notes": "Голубые фишки, дивидендная стратегия"
            },
            {
                "symbol": "GAZP",
                "quantity": 50,
                "avg_price": 120.00,
                "market": "moex",
                "type": "stock",
                "notes": "Высокая дивидендная доходность"
            },
            {
                "symbol": "LKOH",
                "quantity": 10,
                "avg_price": 6000.00,
                "market": "moex",
                "type": "stock"
            }
        ],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    print("\nШаблон портфеля:")
    print(json.dumps(portfolio_data, indent=2, ensure_ascii=False))
    
    confirm = input("\nСохранить этот портфель? [y/N]: ").strip().lower()
    
    if confirm == 'y':
        save_portfolio(portfolio_data)
        print("\n[SUCCESS] Портфель сохранён!")
    else:
        print("\n[CANCELLED] Отменено")


def edit_portfolio():
    """Редактировать существующий портфель."""
    print("=" * 80)
    print("РЕДАКТИРОВАНИЕ ПОРТФЕЛЯ")
    print("=" * 80)
    
    portfolio = load_portfolio()
    
    if not portfolio:
        print("\n[ERROR] Портфель не найден. Создайте новый:")
        print("  python manage_portfolio.py create")
        return
    
    print("\nТекущий портфель:")
    show_portfolio()
    
    print("\n" + "=" * 80)
    print("Что хотите изменить?")
    print("  1. Название")
    print("  2. Добавить позицию")
    print("  3. Удалить позицию")
    print("  4. Изменить cash")
    print("  0. Отмена")
    
    choice = input("\nВыбор: ").strip()
    
    if choice == '1':
        new_name = input("Новое название: ").strip()
        portfolio['name'] = new_name
        portfolio['updated_at'] = datetime.now().isoformat()
        save_portfolio(portfolio)
        print("[OK] Название обновлено")
        
    elif choice == '2':
        symbol = input("Тикер: ").strip().upper()
        quantity = int(input("Количество: "))
        avg_price = float(input("Средняя цена: "))
        notes = input("Заметки (необязательно): ").strip()
        
        new_position = {
            "symbol": symbol,
            "quantity": quantity,
            "avg_price": avg_price,
            "market": "moex",
            "type": "stock"
        }
        if notes:
            new_position["notes"] = notes
        
        portfolio['positions'].append(new_position)
        portfolio['updated_at'] = datetime.now().isoformat()
        save_portfolio(portfolio)
        print(f"[OK] Позиция {symbol} добавлена")
        
    elif choice == '3':
        if not portfolio['positions']:
            print("[INFO] Нет позиций для удаления")
            return
        
        print("\nТекущие позиции:")
        for i, pos in enumerate(portfolio['positions']):
            print(f"  {i+1}. {pos['symbol']} x {pos['quantity']}")
        
        idx = int(input("Номер для удаления: ")) - 1
        if 0 <= idx < len(portfolio['positions']):
            removed = portfolio['positions'].pop(idx)
            portfolio['updated_at'] = datetime.now().isoformat()
            save_portfolio(portfolio)
            print(f"[OK] Позиция {removed['symbol']} удалена")
        else:
            print("[ERROR] Неверный номер")
            
    elif choice == '4':
        new_cash = float(input("Новая сумма cash: "))
        portfolio['cash'] = new_cash
        portfolio['updated_at'] = datetime.now().isoformat()
        save_portfolio(portfolio)
        print("[OK] Cash обновлён")


def main():
    """Главная функция."""
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python manage_portfolio.py show      - Показать портфель")
        print("  python manage_portfolio.py create    - Создать новый")
        print("  python manage_portfolio.py template  - Из шаблона")
        print("  python manage_portfolio.py edit      - Редактировать")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'show':
        show_portfolio()
    elif command == 'create':
        create_portfolio()
    elif command == 'template':
        update_from_template()
    elif command == 'edit':
        edit_portfolio()
    else:
        print(f"[ERROR] Неизвестная команда: {command}")


if __name__ == "__main__":
    main()

