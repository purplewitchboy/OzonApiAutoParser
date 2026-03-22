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
from src.google_sheets.sheets.products_sheet import ProductsSheet
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

def create_products_sheet(spreadsheet_id: str, credentials: dict):
    """Основная функция создания листа с товарами"""
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
        
        # 3. Товары
        logger.info("Создаю лист 'Товары'...")
        products_sheet = ProductsSheet(spreadsheet, settings)
        success = products_sheet.execute()
        
        if success:
            logger.info("✅ Лист 'Товары' успешно создан!")
            return True
        else:
            logger.error("❌ Ошибка при создании листа")
            return False
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        return False

def main():
    parser = argparse.ArgumentParser(description='Загрузка товаров из Ozon в Google Sheets')
    parser.add_argument(
        '--spreadsheet-id',
        required=True,
        help='ID таблицы Google Sheets'
    )
    parser.add_argument(
        '--credentials-file',
        default='credentials.json',
        help='Путь к файлу с credentials'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Уровень логирования'
    )
    
    args = parser.parse_args()
    
    # Логирование
    setup_logger(level=args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Загружаем credentials
        credentials = load_credentials()
        
        # Запускаем
        success = create_products_sheet(args.spreadsheet_id, credentials)
        
        if success:
            logger.info("🎉 Скрипт успешно завершен!")
            sys.exit(0)
        else:
            logger.error("💥 Скрипт завершился с ошибками")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"💥 Необработанная ошибка: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()