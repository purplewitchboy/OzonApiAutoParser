"""
Аналог OrdersFBS.txt (GAS loadOrdersFBS).

Загружает заказы FBS из Ozon API и записывает
результат на лист «Заказы FBS» в Google Sheets.

Запуск:
  python run.py orders-fbs <spreadsheet_id>
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

LIST_URL = "https://api-seller.ozon.ru/v3/posting/fbs/list"

HEADERS = [
    "Кабинет",
    "Номер заказа",
    "Номер отправления",
    "Принят в обработку",
    "Статус",
    "Сумма отправления",
    "Код валюты отправления",
    "OZON id",
    "Артикул",
    "Итоговая стоимость товара",
    "Код валюты товара",
    "Стоимость товара для покупателя",
    "Код валюты покупателя",
    "Количество",
]


def load_orders_fbs(spreadsheet_id: str, credentials: dict) -> bool:
    logger.info("=== loadOrdersFBS start ===")

    spreadsheet = open_spreadsheet(spreadsheet_id, credentials)
    settings = get_settings(spreadsheet)
    sheet = get_or_create_sheet(spreadsheet, "Заказы FBS_TEST")
    sheet.clear()

    hdrs = ozon_headers(settings)

    payload = {
        "filter": {
            "since": to_iso(settings["date_from"]),
            "to": to_iso(settings["date_to"]),
        },
        "limit": 1000,
        "offset": 0,
    }

    with requests.Session() as session:
        resp = session.post(LIST_URL, json=payload, headers=hdrs, timeout=30)

    logger.info(f"Orders FBS HTTP CODE: {resp.status_code}")

    if resp.status_code != 200:
        raise RuntimeError(f"Orders FBS error {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    postings = (data.get("result") or {}).get("postings", [])
    logger.info(f"FBS postings count: {len(postings)}")

    all_rows = [HEADERS]

    for posting in postings:
        financial = posting.get("financial_data") or {}
        posting_services = financial.get("posting_services") or {}

        for product in posting.get("products", []):
            price = float(product.get("price") or 0)
            quantity = int(product.get("quantity") or 0)
            currency = product.get("currency_code", "")

            all_rows.append([
                settings["cabinet_name"],
                posting.get("order_number", ""),
                posting.get("posting_number", ""),
                posting.get("in_process_at", ""),
                posting.get("status", ""),
                posting_services.get("marketplace_service_item_fulfillment", ""),
                posting_services.get("currency", ""),
                product.get("ozon_id", ""),
                product.get("offer_id", ""),
                price * quantity or "",
                currency,
                price or "",
                currency,
                quantity,
            ])

    if len(all_rows) > 1:
        sheet.update(all_rows, value_input_option="USER_ENTERED")
        logger.info(f"Записано строк: {len(all_rows) - 1}")
    else:
        logger.info("Нет данных для записи.")

    logger.info(f"=== loadOrdersFBS done. Rows: {len(all_rows) - 1} ===")
    return True


def main():
    parser = argparse.ArgumentParser(description="Загрузка заказов FBS из Ozon в Google Sheets")
    parser.add_argument("--spreadsheet-id", required=True, help="ID таблицы Google Sheets")
    parser.add_argument("--credentials-file", default="credentials.json")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    setup_logger(level=args.log_level)

    credentials = load_credentials()
    success = load_orders_fbs(args.spreadsheet_id, credentials)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
