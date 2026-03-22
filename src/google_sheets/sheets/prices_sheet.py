# src/google_sheets/sheets/prices_sheet.py

import gspread
from datetime import datetime
from typing import List, Dict, Any
import time
import logging
from src.ozon_api.seller_api import OzonSellerAPI
from src.google_sheets.utils import ensure_sheet_size  # <-- функция авторасширения

logger = logging.getLogger(__name__)


class PricesSheet:
    """Класс для работы с листом 'Цены'"""

    def __init__(self, spreadsheet, settings: Dict[str, str]):
        self.spreadsheet = spreadsheet
        self.settings = settings
        self.ozon_api = OzonSellerAPI(
            client_id=settings['client_id'],
            api_key=settings['api_key']
        )
        self.sheet_name = 'Цены'

    def get_or_create_sheet(self):
        """Получить существующий лист или создать новый"""
        try:
            worksheet = self.spreadsheet.worksheet(self.sheet_name)
            logger.info(f"Лист '{self.sheet_name}' найден")
            return worksheet
        except gspread.exceptions.WorksheetNotFound:
            logger.info(f"Лист '{self.sheet_name}' не найден, создаю...")
            worksheet = self.spreadsheet.add_worksheet(
                title=self.sheet_name,
                rows=1000,
                cols=8
            )
            self.write_headers(worksheet)
            return worksheet

    def write_headers(self, worksheet):
        """Записать заголовки в лист"""
        headers = [
            'Кабинет',
            'Дата',
            'SKU',
            'Артикул продавца',
            'Цена до учёта скидок. На карточке товара отображается зачёркнутой',
            'Минимальная цена товара после применения всех скидок',
            'Цена товара с учётом скидок — это значение показывается на карточке товара',
            'Цена на товар с учетом акций продавца'
        ]
        worksheet.update('A1', [headers])

    def format_date_for_sheet(self, date_obj: datetime = None) -> str:
        """Форматировать дату в дд.мм.гггг"""
        if date_obj is None:
            date_obj = datetime.now()
        return date_obj.strftime('%d.%m.%Y')

    def fetch_prices_data(self) -> Dict[str, Any]:
        """Получить данные о ценах из Ozon API"""
        endpoint = "/v5/product/info/prices"
        payload = {
            "filter": {"visibility": "ALL"},
            "limit": 1000
        }

        response = self.ozon_api._make_request("POST", endpoint, payload)

        if response.success:
            return response.data
        else:
            raise Exception(f"Ошибка API: {response.error}")

    def process_prices_data(self, api_data: Dict[str, Any]) -> List[List]:
        """Обработать данные и подготовить к записи"""
        today_date = self.format_date_for_sheet()
        new_rows = []

        items = api_data.get('items', [])
        logger.info(f"Обрабатываю {len(items)} товаров из API")

        for item in items:
            try:
                price = item.get('price', {})
                row_data = [
                    self.settings.get('cabinet_name', ''),
                    today_date,
                    str(item.get('product_id', '')),
                    item.get('offer_id', ''),
                    price.get('old_price', ''),
                    price.get('min_price', ''),
                    price.get('price', ''),
                    price.get('marketing_seller_price', '')
                ]
                new_rows.append(row_data)
            except Exception as e:
                logger.error(f"Ошибка обработки товара: {item}. Ошибка: {e}")
                continue

        logger.info(f"Найдено {len(new_rows)} новых записей для добавления")
        return new_rows

    def write_new_rows(self, worksheet, new_rows: List[List]):
        """Записать новые строки в лист"""
        if not new_rows:
            logger.info("Нет новых данных для добавления")
            return

        try:
            all_values = worksheet.get_all_values()
            start_row = len(all_values) + 1  # после существующих данных

            batch_size = 100
            for i in range(0, len(new_rows), batch_size):
                batch = new_rows[i:i + batch_size]
                end_row = start_row + len(batch) - 1

                # АВТОРАСШИРЕНИЕ листа
                ensure_sheet_size(worksheet, end_row, 8)

                cell_range = f"A{start_row}:H{end_row}"
                worksheet.update(cell_range, batch)

                logger.info(f"Записано {len(batch)} строк в строки {start_row}-{end_row}")

                start_row += len(batch)

                if i + batch_size < len(new_rows):
                    time.sleep(1)

        except Exception as e:
            logger.error(f"Ошибка записи данных: {e}")
            raise

    def execute(self, overwrite: bool = False):
        """Основной метод выполнения загрузки цен"""
        logger.info("=== СТАРТ ЗАГРУЗКИ ЦЕН ===")

        try:
            # 1. Получаем или создаем лист
            worksheet = self.get_or_create_sheet()

            # 2. Режим перезаписи
            if overwrite:
                logger.info("Режим перезаписи: очищаю старые данные...")
                worksheet.clear()
                self.write_headers(worksheet)
                existing_data = []
            else:
                existing_data = worksheet.get_all_values()

            # 3. Получаем данные из API
            logger.info("Получаю данные о ценах из Ozon API...")
            api_data = self.fetch_prices_data()

            # 4. Обрабатываем
            new_rows = self.process_prices_data(api_data)

            # 5. Записываем
            if new_rows:
                self.write_new_rows(worksheet, new_rows)
                logger.info(f"✅ Добавлено {len(new_rows)} записей")
            else:
                logger.info("ℹ️ Нет новых данных")

            total_items = len(api_data.get('items', []))
            logger.info(f"=== ЗАВЕРШЕНО. Обработано товаров: {total_items} ===")

            return {
                'success': True,
                'total_items': total_items,
                'new_rows_added': len(new_rows),
            }

        except Exception as e:
            logger.error(f"❌ Ошибка выполнения: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
