#!/usr/bin/env python3
import os
import sys
import json
import logging
import argparse

# Добавляем путь к модулям
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.google_sheets.client import GoogleSheetsClient
from src.google_sheets.sheets.settings_sheet import SettingsSheet
from src.google_sheets.sheets.details_sheet import DetailsSheet
from src.utils.logger import setup_logger

def load_credentials():
    """Загрузить credentials из переменной окружения или файла"""
    creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
    
    if creds_json:
        return json.loads(creds_json)
    
    creds_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
    
    if os.path.exists(creds_file):
        with open(creds_file, 'r') as f:
            return json.load(f)
    
    raise ValueError("Не найдены credentials. Установите GOOGLE_CREDENTIALS_JSON или создайте credentials.json")

def create_details_sheet(spreadsheet_id: str, credentials: dict) -> bool:
    """Основная функция создания листа с детализацией транзакций"""
    logger = logging.getLogger(__name__)
    
    try:
        # 1. Google Sheets клиент
        logger.info(f"Открываю таблицу {spreadsheet_id}")
        gs_client = GoogleSheetsClient(credentials_json=credentials)
        spreadsheet = gs_client.open_spreadsheet(spreadsheet_id)
        
        # 2. Настройки
        logger.info("Загружаю настройки...")
        settings_sheet = SettingsSheet(spreadsheet)
        settings = settings_sheet.load_settings()
        
        # 3. Проверка настроек Seller API
        if not settings.get('client_id') or not settings.get('api_key'):
            logger.error("❌ Не указаны данные Seller API (client_id и api_key)")
            logger.error("Укажите их в листе 'Настройки':")
            logger.error("  - B1: Client ID")
            logger.error("  - B2: API Key")
            return False
        
        # 4. Детализация транзакций
        logger.info("Начинаю загрузку детализации транзакций...")
        details_sheet = DetailsSheet(spreadsheet, settings)
        success = details_sheet.execute()
        
        if success:
            logger.info("✅ Лист 'Детализация' успешно создан!")
            return True
        else:
            logger.error("❌ Ошибка при создании листа")
            return False
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Загрузка детализации транзакций из Ozon в Google Sheets',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python run_details_report.py --spreadsheet-id 1A2B3C4D5E6F7G8H9I0J
  python run_details_report.py --spreadsheet-id 1A2B3C4D5E6F7G8H9I0J --log-level DEBUG
  
Функционал:
  • Автоматический расчет периода: вчера 23:59:59 и 30 дней назад от вчера 00:00:00
  • Загрузка всех транзакций за период
  • Загрузка данных отправлений пачками
  • Детализация по товарам и услугам
  • Создание листа "Детализация" с полным набором данных

Период расчета:
  • Дата ПО: вчера 23:59:59 UTC
  • Дата С: 30 дней назад от вчера 00:00:00 UTC
        """
    )
    
    parser.add_argument(
        '--spreadsheet-id',
        required=True,
        help='ID таблицы Google Sheets'
    )
    parser.add_argument(
        '--credentials-file',
        default='credentials.json',
        help='Путь к файлу с credentials (по умолчанию: credentials.json)'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Уровень логирования (по умолчанию: INFO)'
    )
    
    args = parser.parse_args()
    
    # Логирование
    setup_logger(level=args.log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("Загрузка детализации транзакций Ozon")
    logger.info("=" * 60)
    
    try:
        # Загружаем credentials
        credentials = load_credentials()
        
        # Запускаем
        success = create_details_sheet(args.spreadsheet_id, credentials)
        
        if success:
            logger.info("=" * 60)
            logger.info("🎉 Скрипт успешно завершен!")
            logger.info("=" * 60)
            sys.exit(0)
        else:
            logger.info("=" * 60)
            logger.error("💥 Скрипт завершился с ошибками")
            logger.info("=" * 60)
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"💥 Необработанная ошибка: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()