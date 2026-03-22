"""
Аналог salesFBO.txt (GAS loadSalesFBO).

Загружает список отправлений FBO из Ozon API и записывает
результат на лист «Продажи FBO» в Google Sheets.

Запуск:
  python run.py sales-fbo <spreadsheet_id>
"""

import sys
import os
import time
import logging
import argparse

import requests

# Путь к общим модулям
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
MAX_RETRIES = 3

HEADERS = [
    "Кабинет",
    "Идентификатор заказа",
    "Номер заказа",
    "Статус отправления",
    "Дата и время создания отправления",
    "SKU",
    "Количество",
    "Цена",
    "Кластер отправления",
    "Кластер доставки",
    "Название склада",
]


def _fetch_with_retry(session: requests.Session, payload: dict, hdrs: dict) -> dict:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.post(LIST_URL, json=payload, headers=hdrs, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                logger.warning(f"Attempt {attempt}: Rate limit (429). Waiting...")
                if attempt == MAX_RETRIES:
                    resp.raise_for_status()
                time.sleep(2 ** attempt + 1)
            else:
                resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt} failed: {e}")
            if attempt == MAX_RETRIES:
                raise
            time.sleep(2)
    return {}


def load_sales_fbo(spreadsheet_id: str, credentials: dict) -> bool:
    logger.info("=== loadSalesFBO start ===")

    spreadsheet = open_spreadsheet(spreadsheet_id, credentials)
    settings = get_settings(spreadsheet)
    sheet = get_or_create_sheet(spreadsheet, "Продажи FBO")
    sheet.clear()

    all_rows = [HEADERS]
    hdrs = ozon_headers(settings)

    payload = {
        "filter": {
            "since": to_iso(settings["date_from"]),
            "to": to_iso(settings["date_to"]),
        },
        "with": {"analytics_data": True, "financial_data": True},
        "limit": LIMIT,
        "offset": 0,
    }

    with requests.Session() as session:
        offset = 0
        while True:
            payload["offset"] = offset
            logger.info(f"Fetching page with offset {offset}...")

            data = _fetch_with_retry(session, payload, hdrs)
            postings = data.get("result", [])

            if not postings:
                break

            for posting in postings:
                financial = posting.get("financial_data") or {}
                cluster_from = financial.get("cluster_from", "")
                cluster_to = financial.get("cluster_to", "")

                analytics = posting.get("analytics_data") or {}
                delivery = posting.get("delivery_method") or {}
                warehouse_name = (
                    analytics.get("warehouse_name")
                    or analytics.get("warehouse")
                    or delivery.get("warehouse_name")
                    or delivery.get("warehouse")
                    or ""
                )

                formatted_date = format_date(posting.get("created_at", ""))

                for product in posting.get("products", []):
                    all_rows.append([
                        settings["cabinet_name"],
                        posting.get("posting_number", ""),
                        posting.get("order_number", ""),
                        posting.get("status", ""),
                        formatted_date,
                        product.get("sku", ""),
                        product.get("quantity", 0),
                        product.get("price", ""),
                        cluster_from,
                        cluster_to,
                        warehouse_name,
                    ])

            offset += len(postings)
            logger.info(f"Processed {len(postings)} postings. Total rows: {len(all_rows) - 1}")

            if len(postings) < LIMIT:
                break

            time.sleep(0.3)

    if len(all_rows) > 1:
        sheet.update(all_rows, value_input_option="USER_ENTERED")
        logger.info(f"Записано строк: {len(all_rows) - 1}")
    else:
        logger.info("Нет данных для записи.")

    logger.info("=== loadSalesFBO done ===")
    return True


def main():
    parser = argparse.ArgumentParser(description="Загрузка продаж FBO из Ozon в Google Sheets")
    parser.add_argument("--spreadsheet-id", required=True, help="ID таблицы Google Sheets")
    parser.add_argument("--credentials-file", default="credentials.json")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    setup_logger(level=args.log_level)

    credentials = load_credentials()
    success = load_sales_fbo(args.spreadsheet_id, credentials)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
