# scripts/run_all_reports.py
#!/usr/bin/env python3
"""
Скрипт для запуска всех отчетов сразу
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime

# Добавляем путь к модулям
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.google_sheets.client import GoogleSheetsClient
from src.google_sheets.sheets.settings_sheet import SettingsSheet
from src.reports.report_runner import ReportRunner
from src.utils.logger import setup_logger

def load_credentials():
    """Загрузить credentials"""
    creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
    
    if creds_json:
        return json.loads(creds_json)
    
    creds_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
    
    if os.path.exists(creds_file):
        with open(creds_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    raise ValueError("Не найдены credentials")

def run_all_reports(spreadsheet_id: str, credentials: dict, reports_to_run: list = None):
    """Запустить все отчеты"""
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
        
        # 3. Создаем ReportRunner
        runner = ReportRunner(settings, spreadsheet)
        
        # 4. Запускаем отчеты
        if reports_to_run:
            logger.info(f"Запускаю отчеты: {', '.join(reports_to_run)}")
            for report in reports_to_run:
                try:
                    logger.info(f"=== Запуск отчета: {report} ===")
                    if report == 'prices':
                        result = runner.run_prices(overwrite=False)
                    else:
                        result = runner.run_report(report)
                    
                    if result.get('success'):
                        logger.info(f"✅ Отчет '{report}' выполнен успешно")
                    else:
                        logger.error(f"❌ Отчет '{report}' завершился с ошибкой: {result.get('error')}")
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка выполнения отчета '{report}': {e}")
        else:
            # Запускаем все отчеты
            logger.info("Запускаю все отчеты...")
            runner.run_all_reports()
        
        logger.info("🎉 Все отчеты завершены!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        return False

def main():
    parser = argparse.ArgumentParser(description='Запуск всех отчетов Ozon')
    parser.add_argument(
        '--spreadsheet-id',
        required=True,
        help='ID таблицы Google Sheets'
    )
    parser.add_argument(
        '--reports',
        nargs='+',
        choices=['products', 'prices', 'orders', 'stock', 'sales', 'ads', 'detalization'],
        help='Какие отчеты запускать (по умолчанию все)'
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
        
        # Запускаем отчеты
        success = run_all_reports(args.spreadsheet_id, credentials, args.reports)
        
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