import gspread
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SettingsSheet:
    def __init__(self, spreadsheet):
        self.spreadsheet = spreadsheet
        self.settings_sheet = None
    
    def _get_cell_value(self, cell: str, default: Any = None) -> Any:
        """Получение значения ячейки с обработкой ошибок"""
        try:
            value = self.settings_sheet.acell(cell).value
            return value if value is not None else default
        except Exception:
            return default
    
    def _get_numeric_value(self, cell: str, default: int = 0) -> int:
        """Получение числового значения с обработкой ошибок"""
        try:
            value = self._get_cell_value(cell, default)
            return int(value) if value else default
        except (ValueError, TypeError):
            return default
    
    def load_settings(self) -> Dict[str, Any]:
        """Загрузка всех настроек из листа 'Настройки'"""
        try:
            self.settings_sheet = self.spreadsheet.worksheet('Настройки')
            
            if not self.settings_sheet:
                raise Exception("Лист 'Настройки' не найден!")
            
            # Основные настройки Seller API
            client_id = self._get_cell_value('B1', '').strip()
            api_key = self._get_cell_value('B2', '').strip()
            
            # Настройки Performance API
            performance_client_id = self._get_cell_value('B3', '').strip()
            performance_client_secret = self._get_cell_value('B4', '').strip()
            
            # Общие настройки
            cabinet_name = self._get_cell_value('B5', 'Основной кабинет')
            
            # Конфигурация рекламной статистики
            days_back = self._get_numeric_value('B9', 30)
            polling_retry = self._get_numeric_value('B10', 20)
            polling_sleep = self._get_numeric_value('B11', 15)
            max_campaigns = self._get_numeric_value('B12', 10)
            
            settings = {
                # Основные настройки Seller API
                'client_id': client_id,
                'api_key': api_key,
                'cabinet_name': cabinet_name,
                
                # Настройки Performance API
                'performance_client_id': performance_client_id,
                'performance_client_secret': performance_client_secret,
                
                # Конфигурация рекламной статистики
                'DAYS_BACK': days_back,
                'POLLING_RETRY': polling_retry,
                'POLLING_SLEEP': polling_sleep,
                'MAX_CAMPAIGNS_PER_REQUEST': max_campaigns
            }
            
            # Валидация обязательных настроек Seller API
            if not settings['client_id'] or not settings['api_key']:
                logger.warning("Client ID и/или API Key для Seller API не заполнены")
            
            # Валидация Client ID как числа (если указан)
            if settings['client_id']:
                try:
                    int(settings['client_id'])
                except ValueError:
                    logger.warning(f"Client ID должен быть числом: {settings['client_id']}")
            
            # Валидация настроек Performance API
            if not settings['performance_client_id'] or not settings['performance_client_secret']:
                logger.warning("Client ID и/или Client Secret для Performance API не заполнены")
                logger.warning("Для работы с рекламной статистикой заполните ячейки B3 и B4")
            
            logger.info(f"Настройки загружены для: {settings['cabinet_name']}")
                        
            return settings
            
        except gspread.exceptions.WorksheetNotFound:
            raise Exception("Лист 'Настройки' не найден! Создайте лист с названием 'Настройки'")
        except Exception as e:
            logger.error(f"Ошибка загрузки настроек: {e}", exc_info=True)
            raise