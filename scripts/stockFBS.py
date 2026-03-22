"""
Аналог StockFBS.txt (GAS loadStockFBS).

Загружает остатки FBS из Ozon API и записывает
результат на лист «Склад FBS» в Google Sheets.

Запуск:
  python run.py stock-fbs <spreadsheet_id>
"""

import sys
import os
import logging
import argparse

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.settings import (
    load_credentials,
    open_spreadsheet,
    get_settings,
    get_or_create_sheet,
    ozon_headers,
    to_iso,
)
from src.utils.logger import setup_logger

logger = logging.getLogger(__name__)

STOCK_WAREHOUSES_URL = "https://api-seller.ozon.ru/v2/analytics/stock_on_warehouses"

HEADERS = [
    "Кабинет",
    "Дата",
    "Количество",
    "Зарезервировано",
    "sku",
    "Название склада",
]


def load_stock_fbs(spreadsheet_id: str, credentials: dict) -> bool:
    logger.info("=== loadStockFBS start ===")

    spreadsheet = open_spreadsheet(spreadsheet_id, credentials)
    settings = get_settings(spreadsheet)
    sheet = get_or_create_sheet(spreadsheet, "Склад FBS_TEST")
    sheet.clear()

    hdrs = ozon_headers(settings)

    payload = {
        "filter": {
            "since": to_iso(settings["date_from"]),
            "to": to_iso(settings["date_to"]),
        },
        "warehouse_type": "fbs",
        "limit": 1000,
        "offset": 0,
    }

    with requests.Session() as session:
        resp = session.post(STOCK_WAREHOUSES_URL, json=payload, headers=hdrs, timeout=30)

    logger.info(f"Stock FBS HTTP CODE: {resp.status_code}")

    if resp.status_code != 200:
        raise RuntimeError(f"Stock FBS error {resp.status_code}: {resp.text[:200]}")

    rows_data = resp.json().get("result", {}).get("rows", [])

    all_rows = [HEADERS]

    for row in rows_data:
        all_rows.append([
            settings["cabinet_name"],
            settings["date_to"],
            row.get("total", 0),
            row.get("reserved", 0),
            row.get("sku", ""),
            row.get("warehouse_name", ""),
        ])

    if len(all_rows) > 1:
        sheet.update(all_rows, value_input_option="USER_ENTERED")
        logger.info(f"Записано строк: {len(all_rows) - 1}")
    else:
        logger.info("Нет данных для записи.")

    logger.info(f"=== loadStockFBS done. Rows: {len(all_rows) - 1} ===")
    return True


def main():
    parser = argparse.ArgumentParser(description="Загрузка остатков FBS из Ozon в Google Sheets")
    parser.add_argument("--spreadsheet-id", required=True, help="ID таблицы Google Sheets")
    parser.add_argument("--credentials-file", default="credentials.json")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    setup_logger(level=args.log_level)

    credentials = load_credentials()
    success = load_stock_fbs(args.spreadsheet_id, credentials)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
