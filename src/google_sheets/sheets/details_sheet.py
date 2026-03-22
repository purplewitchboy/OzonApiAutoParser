import gspread
import logging
import time
from typing import List, Dict, Any, Set
from datetime import datetime, timedelta
from src.ozon_api.seller_api import OzonSellerAPI
from src.google_sheets.utils import ensure_sheet_size

logger = logging.getLogger(__name__)

# Маппинг услуг на столбцы (аналогично GAS скрипту)
SERVICE_TO_COLUMN = {
    'MarketplaceServiceItemRedistributionLastMileCourier': 'Последняя миля',
    'MarketplaceServiceItemDirectFlowTrans': 'Магистраль',
    'MarketplaceServiceItemDropoffFF': 'Обработка отправления',
    'MarketplaceServiceItemDropoffPVZ': 'Обработка отправления',
    'MarketplaceServiceItemDropoffFS': 'Обработка отправления',
    'MarketplaceServiceItemDropoffPPZ': 'Обработка отправления',
    'MarketplaceServiceItemPickup': 'Обработка отправления',
    'MarketplaceServiceItemFulfillment': 'Сборка',
    'MarketplaceServiceItemReturnFromTrans': 'Обратная магистраль',
    'MarketplaceServiceItemReturnNotDelivToCustomer': 'Отмены',
    'MarketplaceServiceItemReturnPartGoodsCustomer': 'Невыкуп',
    'MarketplaceServiceItemDirectFlowLogistic': 'Логистика',
    'MarketplaceServiceItemDirectFlowLogisticVDC': 'Логистика',
    'MarketplaceServiceItemReturnFlowLogistic': 'Обратная логистика',
    'MarketplaceRedistributionOfAcquiringOperation': 'Комиссия',
    'MarketplaceNotDeliveredCostItem': 'Отмены',
    'MarketplaceServiceItemRedistributionReturnsPVZ': 'Обработка возврата',
    'MarketplaceDeliveryCostItem': 'Логистика',
    'ItemAdvertisementForSupplierLogistic': 'Логистика',
    'ItemAdvertisementForSupplierLogisticSeller': 'Логистика',
    'MarketplaceServiceItemDeliveryKGT': 'Логистика',
    'MarketplaceSaleReviewsItem': 'Прочие',
    'MarketplaceMarketingActionCostItem': 'Прочие',
    'MarketplaceServiceItemInstallment': 'Прочие',
    'MarketplaceServiceItemMarkingItems': 'Прочие',
    'MarketplaceServiceItemFlexiblePaymentSchedule': 'Прочие',
    'MarketplaceServiceItemReturnFromStock': 'Прочие',
    'MarketplaceServicePremiumCashbackIndividualPoints': 'Прочие',
    'MarketplaceServicePremiumPromotion': 'Прочие',
    'ItemAgentServiceStarsMembership': 'Прочие',
    'OperationMarketplaceWithHoldingForUndeliverableGoods': 'Прочие',
    'OperationMarketplaceAgencyFeeAggregator3PLGlobal': 'Прочие',
    'OperationMarketplaceServiceStorage': 'Прочие',
    'MarketplaceReturnStorageServiceAtThePickupPointFbsItem': 'Прочие',
    'MarketplaceReturnStorageServiceInTheWarehouseFbsItem': 'Прочие'
}

class DetailsSheet:
    """Класс для работы с листом детализации транзакций"""
    
    def __init__(self, spreadsheet, settings: dict):
        self.spreadsheet = spreadsheet
        self.settings = settings
        self.seller_api = OzonSellerAPI(
            client_id=settings['client_id'],
            api_key=settings['api_key']
        )
        self.cabinet = settings.get('cabinet_name', '')
    
    def create_or_clear_sheet(self):
        """Создание или очистка листа Детализация"""
        try:
            worksheet = self.spreadsheet.worksheet('Детализация')
            logger.info("Лист 'Детализация' найден, очищаем...")
            worksheet.clear()
            return worksheet
        except gspread.exceptions.WorksheetNotFound:
            logger.info("Создаю лист 'Детализация'...")
            worksheet = self.spreadsheet.add_worksheet(
                title='Детализация',
                rows=1000,
                cols=23
            )
            return worksheet
    
    def write_headers(self, worksheet):
        """Запись заголовков"""
        headers = [
            "Кабинет", "Дата начисления", "Тип начисления",
            "Номер отправления или услуги", "Дата принятия",
            "SKU", "Артикул", "Количество",
            "За продажу до вычета", "Ставка комиссии", "Комиссия",
            "Сборка", "Обработка отправления",
            "Магистраль", "Последняя миля",
            "Обратная магистраль", "Обработка возврата",
            "Отмены", "Невыкуп", "Логистика",
            "Индекс локализации", "Обратная логистика", "Итого"
        ]
        
        # Записываем заголовки
        worksheet.update('A1', [headers])
        
        # Форматируем заголовки (жирный шрифт и серый фон)
        try:
            worksheet.format('A1:W1', {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.94, 'green': 0.94, 'blue': 0.94}
            })
        except Exception as e:
            logger.warning(f"Не удалось применить форматирование: {e}")
    
    def get_period(self):
        """Получение периода: день ПО - вчера 23:59:59, день С - 30 дней назад от вчера 00:00:00"""
        now = datetime.utcnow()
        
        # Вчера 23:59:59 UTC
        yesterday = now - timedelta(days=1)
        date_to = datetime(
            yesterday.year, yesterday.month, yesterday.day,
            23, 59, 59
        )
        
        # 30 дней назад от вчера 00:00:00 UTC
        date_from = date_to - timedelta(days=30)
        date_from = datetime(
            date_from.year, date_from.month, date_from.day,
            0, 0, 0
        )
        
        # Форматируем в RFC3339
        formatted_from = date_from.isoformat() + 'Z'
        formatted_to = date_to.isoformat() + 'Z'
        
        logger.info(f"Период отчета: {date_from.strftime('%Y-%m-%d %H:%M:%S')} — {date_to.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return formatted_from, formatted_to
    
    def get_all_transactions(self, date_from: str, date_to: str):
        """Получение ВСЕХ транзакций за период (исправленная версия)"""
        result = []
        page = 1
        page_size = 1000
        total_operations = 0
        max_pages = 50  # Ограничение на 50 страниц (50,000 операций)
        
        try:
            logger.info("Начинаю загрузку транзакций...")
            
            while True:
                response = self.seller_api.get_transaction_list(
                    date_from=date_from,
                    date_to=date_to,
                    page=page,
                    page_size=page_size
                )
                
                if not response.success:
                    logger.error(f"Ошибка при загрузке транзакций: {response.error}")
                    break
                
                data = response.data
                
                # Проверяем структуру ответа
                if not data or not data.get('result'):
                    logger.warning("Некорректная структура ответа или отсутствуют данные")
                    break
                
                # Получаем операции из результата
                operations = data['result'].get('operations', [])
                
                if not operations:
                    logger.info("Больше нет операций для загрузки")
                    break
                
                # Добавляем операции в результат
                result.extend(operations)
                total_operations += len(operations)
                
                # Логируем прогресс для первой страницы
                if page == 1:
                    logger.info(f"Первая страница: {len(operations)} операций")
                    
                    # Проверяем наличие page_count в ответе
                    if 'page_count' in data:
                        total_pages = data['page_count']
                        logger.info(f"Всего страниц согласно API: {total_pages}")
                    else:
                        logger.warning("Поле 'page_count' отсутствует в ответе API")
                
                # Проверяем, нужно ли загружать следующую страницу
                # 1. Если в ответе есть page_count, проверяем его
                if 'page_count' in data:
                    total_pages = data['page_count']
                    if page >= total_pages:
                        logger.info(f"Достигнута последняя страница ({page}/{total_pages})")
                        break
                # 2. Если page_count нет, проверяем количество операций
                elif len(operations) < page_size:
                    logger.info(f"Последняя страница ({page}), операций меньше чем {page_size}")
                    break
                # 3. Если достигнут лимит страниц
                elif page >= max_pages:
                    logger.warning(f"Достигнут лимит страниц ({max_pages}). Загрузка прервана.")
                    break
                
                # Увеличиваем номер страницы для следующего запроса
                page += 1
                
                # Пауза для соблюдения лимитов API
                if page % 10 == 0:
                    time.sleep(1)  # Большая пауза каждые 10 страниц
                else:
                    time.sleep(0.2)  # Короткая пауза между запросами
                
                # Прогресс каждые 10 страниц
                if page % 10 == 0 or (page == 2 and total_operations >= 1000):
                    logger.info(f"Загружено страниц: {page}, операций: {total_operations}")
            
            logger.info(f"Загружено всего операций: {total_operations} за {page} страниц")
            return result
            
        except Exception as error:
            logger.error(f"Ошибка при загрузке транзакций: {error}", exc_info=True)
            return []
    
    def get_postings_data_batch(self, posting_numbers: List[str]):
        """Массовый запрос данных отправлений"""
        try:
            if not posting_numbers:
                logger.info("Нет номеров отправлений для загрузки")
                return {}
            
            # Разбиваем на группы по 100 номеров (лимит Ozon API)
            chunk_size = 100
            chunks = []
            for i in range(0, len(posting_numbers), chunk_size):
                chunks.append(posting_numbers[i:i + chunk_size])
            
            all_postings_data = {}
            
            logger.info(f"Загрузка данных для {len(posting_numbers)} отправлений ({len(chunks)} пачек)...")
            
            # Обрабатываем каждую группу
            for chunk_index, chunk in enumerate(chunks, 1):
                response = self.seller_api.get_postings_fbo_list(
                    posting_numbers=chunk,
                    limit=1000
                )
                
                if response.success and response.data and response.data.get('result'):
                    for posting in response.data['result']:
                        if posting.get('posting_number'):
                            all_postings_data[posting['posting_number']] = posting
                else:
                    logger.warning(f"Не удалось загрузить данные для пачки {chunk_index}: {response.error}")
                
                # Пауза между запросами
                if chunk_index < len(chunks):
                    time.sleep(0.3)
                
                # Прогресс каждые 5 чанков
                if chunk_index % 5 == 0 or chunk_index == len(chunks):
                    logger.info(f"Загружено данных отправлений: {len(all_postings_data)} из {len(posting_numbers)}")
            
            logger.info(f"Загружено данных отправлений: {len(all_postings_data)} из {len(posting_numbers)}")
            return all_postings_data
            
        except Exception as error:
            logger.error(f"Ошибка при массовой загрузке отправлений: {error}", exc_info=True)
            return {}
    
    @staticmethod
    def format_date_dmy(value):
        """Форматирование даты в dd.MM.yyyy"""
        if not value:
            return ""
        
        try:
            if isinstance(value, str):
                # Пытаемся распарсить дату из строки
                date_formats = [
                    '%Y-%m-%dT%H:%M:%S.%fZ',
                    '%Y-%m-%dT%H:%M:%SZ',
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d'
                ]
                
                for fmt in date_formats:
                    try:
                        date_obj = datetime.strptime(value, fmt)
                        return date_obj.strftime('%d.%m.%Y')
                    except ValueError:
                        continue
                
                # Если не удалось распарсить, возвращаем как есть
                return value
            
            elif isinstance(value, datetime):
                return value.strftime('%d.%m.%Y')
            
            return str(value)
            
        except Exception:
            return ""
    
    @staticmethod
    def collect_services_by_column(services):
        """Агрегация услуг по столбцам"""
        column_sums = {
            'Сборка': 0,
            'Обработка отправления': 0,
            'Магистраль': 0,
            'Последняя миля': 0,
            'Обратная магистраль': 0,
            'Обработка возврата': 0,
            'Отмены': 0,
            'Невыкуп': 0,
            'Логистика': 0,
            'Обратная логистика': 0,
            'Комиссия': 0,
            'Прочие': 0
        }
        
        if not services or not isinstance(services, list):
            return column_sums
        
        for service in services:
            name = service.get('name')
            amount = 0
            
            # Извлечение суммы из услуги
            price = service.get('price')
            if price:
                if isinstance(price, dict):
                    amount = price.get('total') or price.get('amount') or price.get('value') or 0
                else:
                    try:
                        amount = float(price)
                    except (ValueError, TypeError):
                        amount = 0
            
            # Определение целевого столбца
            target_column = SERVICE_TO_COLUMN.get(name)
            
            if target_column and target_column in column_sums:
                column_sums[target_column] += amount
            elif name and 'Прочие' in column_sums:
                column_sums['Прочие'] += amount
        
        return column_sums
    
    def process_transactions_to_rows(self, operations, posting_data_cache):
        """Обработка операций и формирование строк (исправленная логика с группировкой)"""
        rows = []
        processed_count = 0
        total_operations = len(operations)
        
        logger.info(f"Начинаю обработку {total_operations} операций...")
        
        for op in operations:
            # Агрегация услуг
            services = op.get('services', [])
            service_sums = self.collect_services_by_column(services)
            
            # Получение items
            items = op.get('items', [])
            if not items:
                items = [{'sku': "", 'offer_id': "", 'quantity': 1}]
            
            # Получение данных отправления
            posting_data = None
            posting_number = op.get('posting', {}).get('posting_number')
            if posting_number:
                posting_data = posting_data_cache.get(posting_number)
            
            # ГРУППИРОВКА ТОВАРОВ ПО SKU (решение проблемы с дублированием)
            # Создаем словарь для группировки товаров по SKU
            grouped_items = {}
            
            for item in items:
                sku = item.get('sku', '')
                offer_id = item.get('offer_id', '')
                quantity = item.get('quantity', 0)
                
                # Если у товара нет SKU, оставляем как есть
                if not sku:
                    # Для товаров без SKU не группируем, оставляем как есть
                    grouped_items[f"unique_{len(grouped_items)}"] = {
                        'sku': sku,
                        'offer_id': offer_id,
                        'quantity': quantity,
                        'original_item': item
                    }
                else:
                    # Группируем товары с одинаковым SKU
                    if sku not in grouped_items:
                        grouped_items[sku] = {
                            'sku': sku,
                            'offer_id': offer_id,
                            'quantity': quantity,
                            'original_item': item
                        }
                    else:
                        # Если товар с таким SKU уже есть, суммируем количество
                        grouped_items[sku]['quantity'] += quantity
            
            # Обработка сгруппированных товаров
            for item_key, grouped_item in grouped_items.items():
                # Инициализация переменных для строки (ТОЧНО как в GAS)
                offer_id = ""  # По умолчанию - пустая строка
                quantity = 0   # По умолчанию - 0
                
                # ЛОГИКА ЗАПОЛНЕНИЯ ПО ДАННЫМ ОТПРАВЛЕНИЯ (как в GAS)
                if posting_data and posting_data.get('products') and posting_data['products']:
                    # 1. АРТИКУЛ: Берем всегда из ПЕРВОГО товара в отправлении.
                    first_product = posting_data['products'][0]
                    offer_id = first_product.get('offer_id', '')
                    
                    # 2. КОЛИЧЕСТВО: Заполняем ТОЛЬКО если в транзакции (item) есть SKU.
                    item_sku = grouped_item['sku']
                    if item_sku:
                        # Ищем товар в отправлении, у которого sku точно совпадает с sku из транзакции.
                        matched_product = None
                        for product in posting_data['products']:
                            if product.get('sku') == item_sku:
                                matched_product = product
                                break
                        
                        if matched_product and matched_product.get('quantity') is not None:
                            # Если нашли - берем его количество.
                            quantity = matched_product['quantity']
                        # Если не нашли, quantity останется 0 (как в GAS)
                else:
                    # Если данных отправления нет, но в item есть SKU, то это, вероятно, услуга (например, эквайринг).
                    # В таком случае в количество ставим 1.
                    if grouped_item['sku']:
                        quantity = 1
                    # Если данных об отправлении нет и в item нет SKU, то оба поля останутся пустыми.
                
                # Расчет комиссии
                sale_amount = op.get('accruals_for_sale', 0)
                commission = op.get('sale_commission', 0) or service_sums.get('Комиссия', 0)
                commission_rate = ""
                
                if sale_amount and commission:
                    try:
                        commission_rate = abs(commission / sale_amount)
                    except ZeroDivisionError:
                        commission_rate = ""
                
                # Формирование строки
                rows.append([
                    self.cabinet,                                       # Кабинет
                    self.format_date_dmy(op.get('operation_date')),    # Дата начисления
                    op.get('operation_type_name', ''),                  # Тип начисления
                    posting_number or op.get('operation_id', ''),       # Номер отправления или услуги
                    self.format_date_dmy(op.get('posting', {}).get('order_date')),  # Дата принятия
                    grouped_item['sku'],                                # SKU (из сгруппированных данных)
                    offer_id,                                           # Артикул
                    quantity,                                           # Количество
                    sale_amount,                                        # За продажу до вычета
                    commission_rate,                                    # Ставка комиссии
                    commission,                                         # Комиссия
                    service_sums.get('Сборка', 0),                      # Сборка
                    service_sums.get('Обработка отправления', 0),       # Обработка отправления
                    service_sums.get('Магистраль', 0),                  # Магистраль
                    service_sums.get('Последняя миля', 0),              # Последняя миля
                    service_sums.get('Обратная магистраль', 0),         # Обратная магистраль
                    service_sums.get('Обработка возврата', 0),          # Обработка возврата
                    service_sums.get('Отмены', 0),                      # Отмены
                    service_sums.get('Невыкуп', 0),                     # Невыкуп
                    service_sums.get('Логистика', 0),                   # Логистика
                    "",                                                 # Индекс локализации
                    service_sums.get('Обратная логистика', 0),          # Обратная логистика
                    op.get('amount', 0)                                 # Итого
                ])
            
            # Логируем прогресс
            processed_count += 1
            if processed_count % 100 == 0:
                logger.info(f"Обработано операций: {processed_count} из {total_operations}")
                
                # Дополнительное логирование для отладки
                if logger.level <= logging.DEBUG:
                    logger.debug(f"Пример операции #{processed_count}:")
                    logger.debug(f"  Тип: {op.get('operation_type_name')}")
                    logger.debug(f"  ID: {op.get('operation_id')}")
                    logger.debug(f"  Всего items: {len(items)}")
                    logger.debug(f"  Сгруппировано: {len(grouped_items)}")
                    logger.debug(f"  Услуги: {[s.get('name') for s in services]}")
        
        logger.info(f"Всего обработано строк: {len(rows)}")
        
        # Дополнительная статистика для отладки
        logger.info(f"Статистика: {total_operations} операций -> {len(rows)} строк")
        
        return rows
    
    def execute(self) -> bool:
        """Основная логика выполнения"""
        logger.info("=== СТАРТ СКРИПТА ДЕТАЛИЗАЦИИ ТРАНЗАКЦИЙ ===")
        
        try:
            # 1. Получение периода (автоматически)
            date_from, date_to = self.get_period()
            
            # 2. Загрузка всех транзакций за период
            operations = self.get_all_transactions(date_from, date_to)
            
            if not operations:
                logger.info("За выбранный период транзакций не найдено.")
                return False
            
            # 3. Сбор уникальных номеров отправлений
            unique_posting_numbers = []
            posting_numbers_set = set()
            
            for op in operations:
                posting_number = op.get('posting', {}).get('posting_number')
                if posting_number and posting_number not in posting_numbers_set:
                    posting_numbers_set.add(posting_number)
                    unique_posting_numbers.append(posting_number)
            
            logger.info(f"Найдено уникальных номеров отправлений: {len(unique_posting_numbers)}")
            
            # 4. Загрузка данных отправлений пачкой
            posting_data_cache = self.get_postings_data_batch(unique_posting_numbers)
            
            # 5. Подготовка листа
            worksheet = self.create_or_clear_sheet()
            self.write_headers(worksheet)
            
            # 6. Обработка транзакций и формирование строк
            rows = self.process_transactions_to_rows(operations, posting_data_cache)
            
            if not rows:
                logger.info("Нет данных для записи")
                return False
            
            # 7. Запись данных в таблицу
            if rows:
                chunk_size = 5000  # Разбиваем на части для больших данных
                
                for i in range(0, len(rows), chunk_size):
                    chunk = rows[i:i + chunk_size]
                    start_row = i + 2  # +2 потому что заголовки в первой строке
                    
                    # Авторасширение листа
                    ensure_sheet_size(worksheet, start_row + len(chunk), 23)
                    
                    # Записываем данные
                    cell_range = f"A{start_row}:W{start_row + len(chunk) - 1}"
                    worksheet.update(cell_range, chunk, value_input_option='USER_ENTERED')
                    
                    logger.info(f"Записано строк {start_row}-{start_row + len(chunk) - 1}")
                    
                    # Пауза между записами
                    if i + chunk_size < len(rows):
                        time.sleep(1)
                
                # Автоматическое выравнивание столбцов
                try:
                    worksheet.columns_auto_resize(0, 22)  # От A до W
                    logger.info("Столбцы автоматически выровнены")
                except Exception as e:
                    logger.warning(f"Не удалось выровнять столбцы: {e}")
            
            logger.info("✅ Детализация транзакций успешно загружена!")
            return True
                
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
            return False