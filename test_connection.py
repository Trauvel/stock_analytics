#!/usr/bin/env python3
"""Тест подключения к серверу."""

import requests
import socket
import sys
import os

# Устанавливаем кодировку для Windows
os.environ['PYTHONIOENCODING'] = 'utf-8'

def test_connection():
    """Тестируем различные способы подключения к серверу."""
    
    print("=" * 60)
    print("ТЕСТ ПОДКЛЮЧЕНИЯ К СЕРВЕРУ")
    print("=" * 60)
    
    # Тестируем различные адреса
    addresses = [
        "http://localhost:8000",
        "http://127.0.0.1:8000", 
        "http://0.0.0.0:8000",
        "http://192.168.31.36:8000"
    ]
    
    for addr in addresses:
        try:
            print(f"\nТестируем: {addr}")
            response = requests.get(addr, timeout=5)
            print(f"[OK] Успешно! Статус: {response.status_code}")
            print(f"   Заголовки: {dict(response.headers)}")
            
            # Проверяем содержимое
            if "Stock Analytics" in response.text:
                print("   [OK] Содержимое корректное")
            else:
                print("   [WARN] Содержимое неожиданное")
                
        except requests.exceptions.ConnectionError as e:
            print(f"[ERROR] Ошибка подключения: {e}")
        except requests.exceptions.Timeout as e:
            print(f"[TIMEOUT] Таймаут: {e}")
        except Exception as e:
            print(f"[ERROR] Ошибка: {e}")
    
    # Тестируем сокет
    print(f"\n{'='*60}")
    print("ТЕСТ СОКЕТА")
    print("=" * 60)
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('127.0.0.1', 8000))
        sock.close()
        
        if result == 0:
            print("[OK] Сокет подключение успешно")
        else:
            print(f"[ERROR] Сокет подключение не удалось: {result}")
    except Exception as e:
        print(f"[ERROR] Ошибка сокета: {e}")
    
    print(f"\n{'='*60}")
    print("РЕКОМЕНДАЦИИ")
    print("=" * 60)
    print("1. Попробуйте в браузере:")
    print("   - http://localhost:8000")
    print("   - http://127.0.0.1:8000")
    print("   - http://192.168.31.36:8000")
    print("\n2. Если не работает, проверьте:")
    print("   - Антивирус/файрвол не блокирует порт 8000")
    print("   - Другие приложения не используют порт 8000")
    print("   - Браузер не использует прокси")
    print("\n3. Попробуйте другой браузер или режим инкогнито")

if __name__ == "__main__":
    test_connection()
