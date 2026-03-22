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
from src.google_sheets.sheets.ads_sheet import AdsSheet
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

def create_ads_sheet(spreadsheet_id: str, credentials: dict) -> bool:
    """Основная функция создания листа с рекламной статистикой"""
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
        
        # 3. Проверка настроек Performance API
        if not settings.get('performance_client_id') or not settings.get('performance_client_secret'):
            logger.error("❌ Не указаны данные Performance API (client_id и client_secret)")
            logger.error("Укажите их в листе 'Настройки':")
            logger.error("  - B3: Performance Client ID")
            logger.error("  - B4: Performance Client Secret")
            logger.error("Без этих данных загрузка рекламной статистики невозможна.")
            return False
        
        # 4. Рекламная статистика
        logger.info("Начинаю загрузку рекламной статистики...")
        ads_sheet = AdsSheet(spreadsheet, settings)
        success = ads_sheet.execute()
        
        if success:
            logger.info("✅ Рекламная статистика успешно загружена!")
            return True
        else:
            logger.error("❌ Ошибка при загрузке рекламной статистики")
            return False
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        return False

def main():
    parser = argparse.ArgumentParser(
        description='Загрузка рекламной статистики из Ozon Performance в Google Sheets',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python run_ads_report.py --spreadsheet-id 1A2B3C4D5E6F7G8H9I0J
  python run_ads_report.py --spreadsheet-id 1A2B3C4D5E6F7G8H9I0J --log-level DEBUG
  
Функционал:
  • Получает ВСЕ кампании из Ozon Performance
  • Фильтрует кампании по статусам (RUNNING, STOPPED, INACTIVE, ARCHIVED, FINISHED)
  • Разбивает кампании на пачки по 10 штук
  • Для каждой пачки запрашивает отчет за указанный период
  • Ожидает готовности отчета
  • Сохраняет данные в лист "Реклама"
  • Обрабатывает все кампании, а не только первые 10

Настройки в листе "Настройки":
  B3: Performance Client ID
  B4: Performance Client Secret
  B9: Дней назад для отчета (по умолчанию: 30)
  B12: Макс. кампаний в одном запросе (по умолчанию: 10)
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
    logger.info("Загрузка рекламной статистики Ozon Performance")
    logger.info("=" * 60)
    
    try:
        # Загружаем credentials
        credentials = load_credentials()
        
        # Запускаем
        success = create_ads_sheet(args.spreadsheet_id, credentials)
        
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