import gspread
import time
from typing import List, Dict
import logging
from src.ozon_api.seller_api import OzonSellerAPI
from src.utils.converters import calculate_volume_liters, convert_weight_to_kg
from src.google_sheets.utils import ensure_sheet_size  # <-- ДОБАВЛЕНО

logger = logging.getLogger(__name__)


class ProductsSheet:
    def __init__(self, spreadsheet, settings: dict):
        self.spreadsheet = spreadsheet
        self.settings = settings
        self.ozon_api = OzonSellerAPI(
            client_id=settings['client_id'],
            api_key=settings['api_key']
        )

    def create_or_clear_sheet(self):
        try:
            worksheet = self.spreadsheet.worksheet('Товары')
            logger.info("Лист 'Товары' найден, очищаем...")
            worksheet.clear()
            return worksheet
        except gspread.exceptions.WorksheetNotFound:
            logger.info("Создаю лист 'Товары'...")
            worksheet = self.spreadsheet.add_worksheet(
                title='Товары',
                rows=1000,
                cols=21
            )
            return worksheet

    def write_headers(self, worksheet):
        headers = [
            "Кабинет", "SKU", "Артикул продавца", "Название", "Баркод",
            "Цена до учёта скидок. На карточке товара отображается зачёркнутой",
            "Минимальная цена товара после применения всех скидок",
            "Цена товара с учётом скидок — это значение показывается на карточке товара",
            "Цена на товар с учетом всех акций. Это значение будет указано на витрине Ozon",
            "Объёмный вес", "Ширина", "Высота", "Глубина",
            "Вес", "Объём, л", "Ссылка на изображение", "Стоимость доставки",
            "Процент комиссии", "Стоимость возврата", "Схема продажи", "Сумма комиссии"
        ]
        worksheet.update('A1', [headers])

    def get_all_products(self) -> List[Dict]:
        all_products = []
        last_id = ""
        limit = 1000

        logger.info("Загрузка товаров с Ozon...")

        while True:
            response = self.ozon_api.get_product_list(last_id, limit)

            if not response.success:
                logger.error(f"Ошибка: {response.error}")
                break

            result = response.data.get('result', {})
            items = result.get('items', [])

            if not items:
                break

            product_ids = [str(p['product_id']) for p in items if p.get('product_id')]

            if product_ids:
                detailed_products = self._get_detailed_products_info(product_ids)
                all_products.extend(detailed_products)

            last_id = result.get('last_id', '')

            logger.info(f"Загружено: {len(all_products)} товаров")

            if not last_id or len(items) < limit:
                break

            time.sleep(1)

            if len(all_products) >= 10000:
                logger.warning("Достигнут лимит 10000 товаров")
                break

        logger.info(f"Всего загружено: {len(all_products)} товаров")
        return all_products

    def _get_detailed_products_info(self, product_ids: List[str]) -> List[Dict]:
        all_detailed = []
        chunk_size = 1000

        for i in range(0, len(product_ids), chunk_size):
            chunk = product_ids[i:i + chunk_size]

            response = self.ozon_api.get_products_detailed_info(chunk)

            if response.success and response.data:
                items = response.data.get('items', [])
                all_detailed.extend(items)

            if i + chunk_size < len(product_ids):
                time.sleep(0.5)

        return all_detailed

    def _get_product_dimensions(self, product_id: str) -> Dict:
        response = self.ozon_api.get_product_dimensions(product_id)

        if response.success and response.data:
            result = response.data.get('result', [])
            if result:
                product = result[0]
                return {
                    'width': product.get('width'),
                    'height': product.get('height'),
                    'depth': product.get('depth'),
                    'weight': product.get('weight'),
                    'dimension_unit': product.get('dimension_unit', ''),
                    'weight_unit': product.get('weight_unit', '')
                }

        return {
            'width': '', 'height': '', 'depth': '',
            'weight': '', 'dimension_unit': '', 'weight_unit': ''
        }

    def process_product_data(self, product: Dict) -> List:
        main_image = product.get('primary_image', [''])[0] if product.get('primary_image') else ''
        barcode = product.get('barcodes', [''])[0] if product.get('barcodes') else ''

        delivery_amount = percent = return_amount = sale_schema = commission_value = ""
        if product.get('commissions'):
            commission = product['commissions'][0]
            delivery_amount = commission.get('delivery_amount', '')
            percent = commission.get('percent', '')
            return_amount = commission.get('return_amount', '')
            sale_schema = commission.get('sale_schema', '')
            commission_value = commission.get('value', '')

        dimensions = self._get_product_dimensions(product.get('id', ''))

        volume_liters = calculate_volume_liters(
            dimensions['width'],
            dimensions['height'],
            dimensions['depth'],
            dimensions['dimension_unit']
        )

        weight_in_kg = convert_weight_to_kg(
            dimensions['weight'],
            dimensions['weight_unit']
        )

        return [
            self.settings.get('cabinet_name', ''),
            product.get('sku', ''),
            product.get('offer_id', ''),
            product.get('name', ''),
            barcode,
            product.get('old_price', ''),
            product.get('min_price', ''),
            product.get('price', ''),
            "",
            product.get('volume_weight', ''),
            dimensions['width'],
            dimensions['height'],
            dimensions['depth'],
            weight_in_kg,
            volume_liters,
            main_image,
            delivery_amount,
            percent,
            return_amount,
            sale_schema,
            commission_value
        ]

    def write_products_data(self, worksheet, products_data: List[Dict]):
        if not products_data:
            logger.info("Нет данных для записи")
            return

        rows_to_write = []

        for product in products_data:
            try:
                rows_to_write.append(self.process_product_data(product))
            except Exception as e:
                logger.error(f"Ошибка товара: {e}")
                continue

        if rows_to_write:
            batch_size = 100
            start_row = 2

            for i in range(0, len(rows_to_write), batch_size):
                batch = rows_to_write[i:i + batch_size]
                end_row = start_row + len(batch) - 1

                # АВТОРАСШИРЕНИЕ
                ensure_sheet_size(worksheet, end_row, 21)

                cell_range = f"A{start_row}:U{end_row}"
                worksheet.update(cell_range, batch)

                start_row += len(batch)

                if i + batch_size < len(rows_to_write):
                    time.sleep(1)

    def execute(self):
        logger.info("=== ЗАГРУЗКА ТОВАРОВ ===")

        try:
            worksheet = self.create_or_clear_sheet()
            self.write_headers(worksheet)

            all_products = self.get_all_products()

            if all_products:
                self.write_products_data(worksheet, all_products)
                logger.info(f"✅ Загружено {len(all_products)} товаров")
                return True
            else:
                logger.info("Товары не найдены")
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return False
