import gspread
import logging
import time
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from src.ozon_api.performance_api import OzonPerformanceAPI
from src.google_sheets.utils import with_retry

logger = logging.getLogger(__name__)

class AdsSheet:
    """Класс для работы с листом рекламной статистики"""
    
    def __init__(self, spreadsheet, settings: dict):
        self.spreadsheet = spreadsheet
        self.settings = settings
        self.performance_api = OzonPerformanceAPI(
            client_id=settings.get('performance_client_id', ''),
            client_secret=settings.get('performance_client_secret', '')
        )
        
        # Конфигурация ТОЧНО как в GAS-скрипте
        self.config = {
            'DAYS_BACK': 30,               # Глубина сбора данных в днях
            'POLLING_RETRY': 40,           # Макс. количество проверок готовности отчета (40 x 15с = 10 мин)
            'POLLING_SLEEP': 15,           # Пауза между проверками (15 секунд)
            'CHUNK_SIZE': 10,              # Размер пачки (10 кампаний)
            'REPORT_REQUEST_MAX_RETRIES': 20,  # Ретраи запроса отчёта при "лимит активных запросов"
            'REPORT_REQUEST_RETRY_DELAY': 30,  # Пауза (сек) между такими ретраями
        }
    
    def create_or_clear_sheet(self):
        """Создание или очистка листа Реклама"""
        try:
            worksheet = with_retry(self.spreadsheet.worksheet, 'Реклама')
            logger.info("Лист 'Реклама' найден, очищаем...")
            with_retry(worksheet.clear)
            return worksheet
        except gspread.exceptions.WorksheetNotFound:
            logger.info("Создаю лист 'Реклама'...")
            worksheet = with_retry(
                self.spreadsheet.add_worksheet,
                title='Реклама',
                rows=1000,
                cols=15
            )
            return worksheet
    
    def write_headers(self, worksheet):
        """Запись заголовков"""
        headers = [
            "ID Кампании", "Название кампании", "SKU/ID товара", "Дата",
            "Показы", "Клики", "CTR (%)", "Расход (руб)", "Ср. ставка (руб)",
            "Заказы", "Выручка с заказов", "Заказы (модели)", "Выручка (модели)",
            "Название товара", "Цена товара"
        ]
        
        # Записываем заголовки
        with_retry(worksheet.update, 'A1', [headers])
        
        # Форматируем заголовки (жирный шрифт и серый фон)
        try:
            with_retry(worksheet.format, 'A1:O1', {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.94, 'green': 0.94, 'blue': 0.94}
            })
        except Exception as e:
            logger.warning(f"Не удалось применить форматирование: {e}")
    
    def get_all_campaigns(self) -> List[str]:
        """Получение ВСЕХ кампаний"""
        response = self.performance_api.get_campaigns()
        
        if not response.success:
            logger.error("Ошибка при получении кампаний: %s", response.error)
            return []
        
        campaigns = response.data.get('list', [])
        
        if not campaigns:
            logger.info("Не найдено ни одной кампании")
            return []
        
        # Фильтруем по статусам ТОЧНО как в GAS-скрипте
        active_states = [
            'CAMPAIGN_STATE_RUNNING',
            'CAMPAIGN_STATE_STOPPED', 
            'CAMPAIGN_STATE_INACTIVE',
            'CAMPAIGN_STATE_ARCHIVED',
            'CAMPAIGN_STATE_FINISHED'
        ]
        
        filtered_campaigns = [
            c for c in campaigns 
            if c.get('state') in active_states
        ]
        
        # Получаем ID всех отфильтрованных кампаний
        campaign_ids = [str(c['id']) for c in filtered_campaigns]
        
        logger.info("Найдено кампаний: %s", len(campaign_ids))
        
        return campaign_ids
    
    def chunk_array(self, array: List[str], size: int) -> List[List[str]]:
        """Разделение массива на части заданного размера"""
        result = []
        for i in range(0, len(array), size):
            result.append(array[i:i + size])
        return result
    
    def get_report_period(self) -> Tuple[str, str]:
        """Получение периода для отчета в формате UTC"""
        now = datetime.utcnow()
        
        # Конец периода - сегодня 23:59:59 UTC
        date_to = datetime(
            now.year, now.month, now.day,
            23, 59, 59
        )
        
        # Начало периода - DAYS_BACK дней назад 00:00:00 UTC
        date_from = date_to - timedelta(days=self.config['DAYS_BACK'])
        date_from = datetime(
            date_from.year, date_from.month, date_from.day,
            0, 0, 0
        )
        
        # Форматируем в ISO с Z (UTC)
        formatted_from = date_from.isoformat() + 'Z'
        formatted_to = date_to.isoformat() + 'Z'
        
        logger.info("Период отчета: %s — %s", formatted_from, formatted_to)
        
        return formatted_from, formatted_to
    
    def request_report_uuid(self, campaign_ids: List[str], date_from: str, date_to: str) -> Optional[str]:
        """Запрос отчета и получение UUID"""
        max_retries = self.config['REPORT_REQUEST_MAX_RETRIES']
        retry_delay = self.config['REPORT_REQUEST_RETRY_DELAY']

        for attempt in range(1, max_retries + 1):
            response = self.performance_api.request_statistics_report(
                campaigns=campaign_ids,
                date_from=date_from,
                date_to=date_to
            )

            if response.success and response.data:
                return response.data.get('UUID')

            error_text = (response.error or '').lower()
            is_capacity_limit = '429' in error_text and 'лимит' in error_text and 'запрос' in error_text

            if is_capacity_limit and attempt < max_retries:
                logger.warning(
                    "Лимит активных отчётов Ozon (1 одновременно) — попытка %s/%s, "
                    "жду %s сек. и повторяю запрос...",
                    attempt, max_retries, retry_delay
                )
                time.sleep(retry_delay)
                continue

            logger.error("Ошибка при запросе отчета: %s", response.error)
            return None

        return None
    
    def _convert_to_correct_type(self, value, field_name: str = ""):
        """Конвертирует значение в правильный тип для Google Sheets"""
        if value is None:
            # В зависимости от поля возвращаем соответствующее значение по умолчанию
            if field_name in ["views", "clicks", "orders", "models"]:
                return 0  # int
            elif field_name in ["ctr", "moneySpent", "avgBid", "ordersMoney", "modelsMoney", "price"]:
                return 0.0  # float
            else:
                return ""  # str
        
        # Если уже правильный тип
        if isinstance(value, (int, float, str)):
            return value
        
        # Если строка
        if isinstance(value, str):
            value = value.strip()
            if value == "":
                # Пустая строка
                return self._convert_to_correct_type(None, field_name)
            
            # Проверяем, является ли значение числом
            # Убираем возможные разделители
            test_value = value.replace(',', '.').replace(' ', '')
            
            # Убираем символ процента для CTR
            if field_name == "ctr":
                test_value = test_value.replace('%', '')
            
            # Пробуем преобразовать в число
            try:
                # Пробуем как float
                num_value = float(test_value)
                
                # Для целочисленных полей возвращаем int
                if field_name in ["views", "clicks", "orders", "models"]:
                    return int(num_value)
                else:
                    # Для остальных числовых полей возвращаем float
                    return num_value
            except (ValueError, TypeError):
                # Не число, оставляем как строку
                return value
        
        # Для других типов преобразуем в строку
        return str(value)
    
    def poll_and_save_report(self, uuid: str, worksheet) -> bool:
        """Ожидание и получение готового отчета"""
        attempts = 0
        
        while attempts < self.config['POLLING_RETRY']:
            time.sleep(self.config['POLLING_SLEEP'])
            attempts += 1
            
            logger.info("Проверка готовности отчета (%s/%s)...", 
                       attempts, self.config['POLLING_RETRY'])
            
            response = self.performance_api.get_report_status(uuid)
            
            if response.success:
                if response.data:
                    self.save_report_to_sheet(response.data, worksheet)
                    return True
                # Если отчет еще не готов (204)
                continue
            elif response.error and ("204" in response.error or "404" in response.error):
                continue
            else:
                logger.error("Ошибка при проверке отчета: %s", response.error)
                break
        
        logger.error("Не удалось дождаться отчета за %s попыток", attempts)
        return False
    
    def save_report_to_sheet(self, report_data: Dict, worksheet):
        """Запись данных отчета в таблицу

        ВАЖНО: worksheet передаётся уже открытым из execute(), чтобы не делать
        лишний read-запрос ss.worksheet(sheet_name) на каждый чанк кампаний
        """
        sheet = worksheet
        
        rows_to_append = []
        
        for campaign_id, campaign in report_data.items():
            campaign_title = campaign.get('title', '')
            rows = (campaign.get('report', {}) and campaign['report'].get('rows')) or []
            
            for row in rows:
                # Преобразуем каждое поле к правильному типу
                # Текстовые поля
                campaign_id_str = str(campaign_id)
                campaign_title_str = str(campaign_title) if campaign_title else ""
                sku_product_id = str(row.get('sku') or row.get('product_id') or "")
                date_value = row.get('date') or ""
                title = str(row.get('title') or "")
                
                # Числовые поля с приведением типов
                views = self._convert_to_correct_type(row.get('views'), "views")
                clicks = self._convert_to_correct_type(row.get('clicks'), "clicks")
                ctr = self._convert_to_correct_type(row.get('ctr'), "ctr")
                money_spent = self._convert_to_correct_type(row.get('moneySpent'), "moneySpent")
                avg_bid = self._convert_to_correct_type(row.get('avgBid'), "avgBid")
                orders = self._convert_to_correct_type(row.get('orders'), "orders")
                orders_money = self._convert_to_correct_type(row.get('ordersMoney'), "ordersMoney")
                models = self._convert_to_correct_type(row.get('models'), "models")
                models_money = self._convert_to_correct_type(row.get('modelsMoney'), "modelsMoney")
                price = self._convert_to_correct_type(row.get('price'), "price")
                
                # Для отладки: проверим типы
                if logger.level <= logging.DEBUG:
                    debug_row = [
                        campaign_id_str,
                        campaign_title_str,
                        sku_product_id,
                        date_value,
                        views,
                        clicks,
                        ctr,
                        money_spent,
                        avg_bid,
                        orders,
                        orders_money,
                        models,
                        models_money,
                        title,
                        price
                    ]
                    logger.debug("Типы данных в строке:")
                    for i, val in enumerate(debug_row):
                        logger.debug(f"  Колонка {i+1}: {type(val).__name__} = {val}")
                
                rows_to_append.append([
                    campaign_id_str,        # ID Кампании (строка)
                    campaign_title_str,     # Название кампании (строка)
                    sku_product_id,         # SKU/ID товара (строка)
                    date_value,             # Дата (строка RFC3339)
                    views,                  # Показы (int)
                    clicks,                 # Клики (int)
                    ctr,                    # CTR (%) (float)
                    money_spent,            # Расход (руб) (float)
                    avg_bid,                # Ср. ставка (руб) (float)
                    orders,                 # Заказы (int)
                    orders_money,           # Выручка с заказов (float)
                    models,                 # Заказы (модели) (int)
                    models_money,           # Выручка (модели) (float)
                    title,                  # Название товара (строка)
                    price                   # Цена товара (float)
                ])
        
        if rows_to_append:
            # append_rows сам находит первую свободную строку и дописывает данные —
            # это ОДИН write-запрос без предварительного чтения листа.
            with_retry(
                sheet.append_rows,
                rows_to_append,
                value_input_option='USER_ENTERED',
                table_range='A1'
            )
            
            logger.info("Добавлено строк: %s", len(rows_to_append))
    
    def execute(self) -> bool:
        """Основная логика выполнения (аналог loadADS)"""
        logger.info("--- СТАРТ OZON PERFORMANCE SCRIPT ---")
        
        try:
            # 1. Получение токена (делается автоматически в performance_api)
            
            # 2. Получение всех кампаний
            campaign_ids = self.get_all_campaigns()
            logger.info("Найдено кампаний: %s", len(campaign_ids))
            
            if not campaign_ids:
                logger.info("ИНФО: Активные рекламные кампании не найдены.")
                return False
            
            # 3. Подготовка листа
            worksheet = self.create_or_clear_sheet()
            self.write_headers(worksheet)
            
            # 4. Получение периода
            date_from, date_to = self.get_report_period()
            
            # 5. Разделение на пачки по 10 кампаний
            chunks = self.chunk_array(campaign_ids, self.config['CHUNK_SIZE'])
            
            # 6. Обработка каждой пачки
            for i, batch in enumerate(chunks, 1):
                logger.info("Обработка %s активных кампаний: %s", len(batch), batch)
                
                uuid = self.request_report_uuid(batch, date_from, date_to)
                if not uuid:
                    continue
                
                success = self.poll_and_save_report(uuid, worksheet)
                
                if success:
                    logger.info("--- ЗАВЕРШЕНО УСПЕШНО: Данные обновлены в таблице ---")
                else:
                    logger.info("--- ОШИБКА: Не удалось дождаться отчета от Ozon ---")
                
                # Важная пауза между запросами
                if i < len(chunks):
                    time.sleep(2)
            
            logger.info("--- СКРИПТ ВЫПОЛНЕН ---")
            return True
                
        except Exception as e:
            logger.error("❌ Критическая ошибка: %s", e, exc_info=True)
            return False
