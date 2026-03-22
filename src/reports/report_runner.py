# src/reports/report_runner.py
import time
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class ReportRunner:
    """Запуск отчетов для конкретного магазина"""
    
    def __init__(self, shop_settings: Dict, spreadsheet):
        self.shop = shop_settings
        self.spreadsheet = spreadsheet
        self.reports = {
            'orders_fbo': self.run_orders_fbo,
            'stock_fbo': self.run_stock_fbo,
            'sales_fbo': self.run_sales_fbo,
            'prices': self.run_prices,
            'products': self.run_products,
            'ads': self.run_ads,
            'detalization': self.run_detalization
        }
    
    def run_all_reports(self):
        """Запустить все отчеты для магазина"""
        logger.info(f"Запуск всех отчетов для {self.shop.get('cabinet_name', '')}")
        
        for report_name, report_func in self.reports.items():
            try:
                logger.info(f"Запуск отчета: {report_name}")
                report_func()
                time.sleep(2)  # Пауза между отчетами
            except Exception as e:
                logger.error(f"Ошибка в отчете {report_name}: {e}")
                # Продолжаем выполнение других отчетов
    
    def run_report(self, report_name: str, **kwargs):
        """Запустить конкретный отчет"""
        if report_name not in self.reports:
            raise ValueError(f"Неизвестный отчет: {report_name}")
        
        return self.reports[report_name](**kwargs)
    
    def run_prices(self, overwrite: bool = False):
        """Отчет Цены"""
        from src.google_sheets.sheets.prices_sheet import PricesSheet
        prices_sheet = PricesSheet(self.spreadsheet, self.shop)
        return prices_sheet.execute(overwrite=overwrite)
    
    def run_products(self):
        """Отчет Товары"""
        from src.google_sheets.sheets.products_sheet import ProductsSheet
        products_sheet = ProductsSheet(self.spreadsheet, self.shop)
        return products_sheet.execute()
    
    def run_orders_fbo(self):
        """Отчет Заказы FBO (в разработке)"""
        logger.info("Отчет 'Заказы FBO' пока не реализован")
        return {'success': False, 'error': 'Not implemented'}
    
    def run_stock_fbo(self):
        """Отчет Склад FBO (в разработке)"""
        logger.info("Отчет 'Склад FBO' пока не реализован")
        return {'success': False, 'error': 'Not implemented'}
    
    def run_sales_fbo(self):
        """Отчет Продажи FBO (в разработке)"""
        logger.info("Отчет 'Продажи FBO' пока не реализован")
        return {'success': False, 'error': 'Not implemented'}
    
    def run_ads(self):
        """Отчет Реклама (в разработке)"""
        logger.info("Отчет 'Реклама' пока не реализован")
        return {'success': False, 'error': 'Not implemented'}
    
    def run_detalization(self):
        """Отчет Детализация (в разработке)"""
        logger.info("Отчет 'Детализация' пока не реализован")
        return {'success': False, 'error': 'Not implemented'}