"""
Аналог stockFBO.txt (GAS loadStockFBO).

Загружает остатки FBO из Ozon API и записывает
результат на лист «Склад FBO» в Google Sheets.

Запуск:
  python run.py stock-fbo <spreadsheet_id>
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
    normalize_warehouse_name,
)
from src.utils.logger import setup_logger

logger = logging.getLogger(__name__)

STOCK_WAREHOUSES_URL = "https://api-seller.ozon.ru/v2/analytics/stock_on_warehouses"
ANALYTICS_STOCKS_URL = "https://api-seller.ozon.ru/v1/analytics/stocks"

HEADERS = [
    "Кабинет",
    "Дата",
    "SKU",
    "Артикул поставщика",
    "Количество товара, доступное к продаже на Ozon (остаток)",
    "Количество товара, указанное в подтверждённых будущих поставках",
    "Количество товара, зарезервированное для покупки, возврата и перевозки между складами",
    "Название склада, где находится",
    "На сколько дней хватит остатка товара с учётом среднесуточных продаж по кластеру",
    "Кластер",
]


def load_stock_fbo(spreadsheet_id: str, credentials: dict) -> bool:
    logger.info("=== loadStockFBO start ===")

    spreadsheet = open_spreadsheet(spreadsheet_id, credentials)
    settings = get_settings(spreadsheet)
    sheet = get_or_create_sheet(spreadsheet, "Склад FBO")
    sheet.clear()

    hdrs = ozon_headers(settings)

    # ---------- STOCK ON WAREHOUSES ----------
    payload = {
        "limit": 1000,
        "offset": 0,
    }

    with requests.Session() as session:
        resp = session.post(STOCK_WAREHOUSES_URL, json=payload, headers=hdrs, timeout=30)

    if resp.status_code != 200:
        raise RuntimeError(f"Stock FBO error {resp.status_code}: {resp.text[:200]}")

    rows_data = resp.json().get("result", {}).get("rows", [])
    logger.info(f"stock_on_warehouses вернул {len(rows_data)} строк")

    # ---------- ANALYTICS STOCKS ----------
    sku_list = list({str(r["sku"]) for r in rows_data if r.get("sku")})

    days_map = {}
    cluster_map = {}

    if sku_list:
        with requests.Session() as session:
            resp2 = session.post(
                ANALYTICS_STOCKS_URL,
                json={"skus": sku_list},
                headers=hdrs,
                timeout=30,
            )

        if resp2.status_code == 200:
            for item in resp2.json().get("items", []):
                wh = normalize_warehouse_name(item.get("warehouse_name", ""))
                key = f"{item['sku']}|{wh}"
                days_map[key] = item.get("idc_cluster", "")
                cluster_map[key] = item.get("cluster_name", "")
        else:
            logger.warning(f"Analytics stocks error: {resp2.text[:200]}")

    # ---------- OUTPUT ----------
    all_rows = [HEADERS]

    for row in rows_data:
        wh = normalize_warehouse_name(row.get("warehouse_name", ""))
        key = f"{row['sku']}|{wh}"

        days_on_hand = days_map.get(key, "")
        cluster_name = cluster_map.get(key, "")

        # fallback: ищем по SKU без привязки к складу
        if days_on_hand == "" and cluster_name == "":
            prefix = f"{row['sku']}|"
            fallback = next((k for k in days_map if k.startswith(prefix)), None)
            if fallback:
                days_on_hand = days_map.get(fallback, "")
                cluster_name = cluster_map.get(fallback, "")

        all_rows.append([
            settings["cabinet_name"],
            settings["date_to"],
            row.get("sku", ""),
            row.get("item_code", ""),
            row.get("free_to_sell_amount", ""),
            row.get("promised_amount", ""),
            row.get("reserved_amount", ""),
            row.get("warehouse_name", ""),
            days_on_hand,
            cluster_name,
        ])

    if len(all_rows) > 1:
        sheet.update(all_rows, value_input_option="USER_ENTERED")
        logger.info(f"Записано строк: {len(all_rows) - 1}")
    else:
        logger.info("Нет данных для записи.")

    logger.info(f"=== loadStockFBO done. Rows: {len(all_rows) - 1} ===")
    return True


def main():
    parser = argparse.ArgumentParser(description="Загрузка остатков FBO из Ozon в Google Sheets")
    parser.add_argument("--spreadsheet-id", required=True, help="ID таблицы Google Sheets")
    parser.add_argument("--credentials-file", default="credentials.json")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    setup_logger(level=args.log_level)

    credentials = load_credentials()
    success = load_stock_fbo(args.spreadsheet_id, credentials)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
