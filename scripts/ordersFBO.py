"""
Аналог loadOrdersFBO.txt (GAS loadOrdersFBO).

Загружает заказы FBO из Ozon API и записывает
результат на лист «Заказы FBO» в Google Sheets.

Запуск:
  python run.py orders-fbo <spreadsheet_id>
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
    format_date,
)
from src.utils.logger import setup_logger

logger = logging.getLogger(__name__)

LIST_URL = "https://api-seller.ozon.ru/v2/posting/fbo/list"
LIMIT = 1000

HEADERS = [
    "Кабинет",
    "Номер заказа",
    "Номер отправления",
    "Принят в обработку",
    "Статус",
    "Сумма отправления",
    "Код валюты отправления",
    "SKU",
    "Артикул",
    "Итоговая стоимость",
    "Код валюты товара",
    "Стоимость товара для покупателя",
    "Код валюты покупателя",
    "Количество",
]


def load_orders_fbo(spreadsheet_id: str, credentials: dict) -> bool:
    logger.info("=== loadOrdersFBO start ===")

    spreadsheet = open_spreadsheet(spreadsheet_id, credentials)
    settings = get_settings(spreadsheet)
    sheet = get_or_create_sheet(spreadsheet, "Заказы FBO")
    sheet.clear()

    all_rows = [HEADERS]
    hdrs = ozon_headers(settings)
    offset = 0

    with requests.Session() as session:
        while True:
            payload = {
                "filter": {
                    "since": to_iso(settings["date_from"]),
                    "to": to_iso(settings["date_to"]),
                },
                "limit": LIMIT,
                "offset": offset,
            }

            logger.info(f"Orders FBO: запрос с offset={offset}...")
            resp = session.post(LIST_URL, json=payload, headers=hdrs, timeout=30)

            if resp.status_code != 200:
                raise RuntimeError(f"Orders FBO error {resp.status_code}: {resp.text[:200]}")

            result = resp.json().get("result", [])

            if not result:
                break

            for posting in result:
                formatted_date = format_date(posting.get("in_process_at", ""))

                for product in posting.get("products", []):
                    price = float(product.get("price") or 0)
                    quantity = int(product.get("quantity") or 0)
                    currency = product.get("currency_code", "")

                    all_rows.append([
                        settings["cabinet_name"],
                        posting.get("order_number", ""),
                        posting.get("posting_number", ""),
                        formatted_date,
                        posting.get("status", ""),
                        quantity * price,
                        currency,
                        product.get("sku", ""),
                        product.get("offer_id", ""),
                        price,
                        currency,
                        "",   # Стоимость товара для покупателя
                        "",   # Код валюты покупателя
                        quantity,
                    ])

            logger.info(f"  получено {len(result)} отправлений, строк накоплено: {len(all_rows) - 1}")

            if len(result) < LIMIT:
                break

            offset += LIMIT

    if len(all_rows) > 1:
        sheet.update(all_rows, value_input_option="USER_ENTERED")
        logger.info(f"Записано строк: {len(all_rows) - 1}")
    else:
        logger.info("Нет данных для записи.")

    logger.info("=== loadOrdersFBO done ===")
    return True


def main():
    parser = argparse.ArgumentParser(description="Загрузка заказов FBO из Ozon в Google Sheets")
    parser.add_argument("--spreadsheet-id", required=True, help="ID таблицы Google Sheets")
    parser.add_argument("--credentials-file", default="credentials.json")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    setup_logger(level=args.log_level)

    credentials = load_credentials()
    success = load_orders_fbo(args.spreadsheet_id, credentials)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
