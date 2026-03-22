#!/usr/bin/env python3
import os
import json
import sys

def setup_environment():
    print("=" * 60)
    print("🛠️  НАСТРОЙКА ОКРУЖЕНИЯ OZON REPORTS")
    print("=" * 60)
    
    # 1. Проверяем Python
    print("\n1. Проверка Python...")
    print(f"   Версия Python: {sys.version}")
    
    if sys.version_info < (3, 8):
        print("   ⚠️  Рекомендуется Python 3.8 или выше")
    else:
        print("   ✅ Python версия подходит")
    
    # 2. Проверяем файл credentials
    print("\n2. Проверка credentials...")
    if os.path.exists('credentials.json'):
        print("   ✅ Файл credentials.json найден")
        try:
            with open('credentials.json', 'r') as f:
                data = json.load(f)
                email = data.get('client_email', 'не указан')
                print(f"   📧 Сервисный аккаунт: {email}")
        except:
            print("   ❌ Ошибка чтения credentials.json")
    else:
        print("   ❌ Файл credentials.json не найден")
        print("   Создайте его из Google Cloud Console")
    
    # 3. Создаем .env файл если нет
    print("\n3. Проверка .env файла...")
    if os.path.exists('.env'):
        print("   ✅ Файл .env найден")
    else:
        print("   ⚠️  Файл .env не найден, создаю .env.example...")
        with open('.env.example', 'w') as f:
            f.write('# Ключ сервисного аккаунта Google\n')
            f.write('GOOGLE_CREDENTIALS_JSON={"type": "service_account", ...}\n\n')
            f.write('# Или путь к файлу\n')
            f.write('# GOOGLE_CREDENTIALS_FILE=credentials.json\n\n')
            f.write('# ID таблицы для тестов\n')
            f.write('# TEST_SPREADSHEET_ID=your-id-here\n\n')
            f.write('# Логирование\n')
            f.write('LOG_LEVEL=INFO\n')
        print("   ✅ Создан .env.example. Скопируйте в .env и заполните")
    
    # 4. Проверяем зависимости
    print("\n4. Проверка зависимостей...")
    try:
        import gspread
        print(f"   ✅ gspread установлен: {gspread.__version__}")
    except ImportError:
        print("   ❌ gspread не установлен")
        print("   Установите: pip install -r requirements.txt")
    
    try:
        import requests
        print(f"   ✅ requests установлен: {requests.__version__}")
    except ImportError:
        print("   ❌ requests не установлен")
    
    print("\n" + "=" * 60)
    print("📝 ИНСТРУКЦИЯ:")
    print("1. Установите зависимости: pip install -r requirements.txt")
    print("2. Скопируйте .env.example в .env и заполните")
    print("3. Дайте доступ сервисному аккаунту к таблице")
    print("4. Запустите: python run.py products <spreadsheet_id>")
    print("=" * 60)

if __name__ == "__main__":
    setup_environment()