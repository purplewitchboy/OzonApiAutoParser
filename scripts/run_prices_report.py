# scripts/run_prices_report.py
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
from src.google_sheets.sheets.prices_sheet import PricesSheet
from src.utils.logger import setup_logger

def load_credentials():
    """Загрузить credentials из переменной окружения или файла"""
    creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
    
    if creds_json:
        return json.loads(creds_json)
    
    creds_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
    
    if os.path.exists(creds_file):
        with open(creds_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    raise ValueError(
        f"Не найдены credentials. Создайте файл {creds_file} "
        f"или установите переменную GOOGLE_CREDENTIALS_JSON"
    )

def load_prices(spreadsheet_id: str, credentials: dict, overwrite: bool = False):
    """Загрузить цены в таблицу"""
    logger = logging.getLogger(__name__)
    
    try:
        # 1. Инициализируем клиент Google Sheets
        logger.info(f"Открываю таблицу {spreadsheet_id}")
        gs_client = GoogleSheetsClient(credentials_json=credentials)
        spreadsheet = gs_client.open_spreadsheet(spreadsheet_id)
        
        # 2. Загружаем настройки
        logger.info("Загружаю настройки из листа 'Настройки'")
        settings_sheet = SettingsSheet(spreadsheet)
        settings = settings_sheet.load_settings()
        
        # 3. Загружаем цены
        logger.info("Загружаю цены...")
        prices_sheet = PricesSheet(spreadsheet, settings)
        result = prices_sheet.execute(overwrite=overwrite)
        
        if result.get('success'):
            logger.info(f"✅ Цены успешно загружены!")
            logger.info(f"   Всего товаров: {result.get('total_items', 0)}")
            logger.info(f"   Добавлено новых записей: {result.get('new_rows_added', 0)}")
            logger.info(f"   Уже было записей: {result.get('existing_rows', 0)}")
            return True
        else:
            logger.error(f"❌ Ошибка при загрузке цен: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        return False

def main():
    """Точка входа"""
    parser = argparse.ArgumentParser(description='Загрузка цен из Ozon в Google Sheets')
    parser.add_argument(
        '--spreadsheet-id',
        required=True,
        help='ID таблицы Google Sheets'
    )
    parser.add_argument(
        '--credentials-file',
        default='credentials.json',
        help='Путь к файлу с credentials сервисного аккаунта'
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Перезаписать существующие данные (по умолчанию только добавление новых)'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Уровень логирования'
    )
    
    args = parser.parse_args()
    
    # Настраиваем логирование
    setup_logger(level=args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Загружаем credentials
        credentials = load_credentials()
        
        # Запускаем загрузку цен
        success = load_prices(
            args.spreadsheet_id, 
            credentials, 
            overwrite=args.overwrite
        )
        
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