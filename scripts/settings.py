"""
Shared settings and utilities for FBO/FBS scripts.

Настройки читаются из листа «Настройки» Google-таблицы (как в остальных скриптах).
Аутентификация — через credentials.json (сервисный аккаунт).
"""

import os
import json
import logging
from datetime import datetime, timedelta

import gspread
from oauth2client.service_account import ServiceAccountCredentials

logger = logging.getLogger(__name__)

_SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def load_credentials() -> dict:
    """Загружает credentials из переменной окружения или файла (аналог run_ads_report.py)."""
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        return json.loads(creds_json)

    creds_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    if os.path.exists(creds_file):
        with open(creds_file, "r") as f:
            return json.load(f)

    raise ValueError(
        "Не найдены credentials. Установите GOOGLE_CREDENTIALS_JSON или создайте credentials.json"
    )


def open_spreadsheet(spreadsheet_id: str, credentials: dict) -> gspread.Spreadsheet:
    """Открывает Google-таблицу по ID."""
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials, _SCOPES)
    gc = gspread.authorize(creds)
    spreadsheet = gc.open_by_key(spreadsheet_id)
    logger.info(f"Открыта таблица: {spreadsheet.title}")
    return spreadsheet


def get_settings(spreadsheet: gspread.Spreadsheet, days_back: int = 30) -> dict:
    """
    Читает настройки из листа «Настройки» таблицы.
    Структура листа такая же, как SettingsSheet:
      B1 - Client ID
      B2 - API Key
      B3 - Performance Client ID
      B4 - Performance Client Secret
      B5 - Название кабинета
      B9 - DAYS_BACK (опционально, приоритет у аргумента days_back)
    """
    ws = spreadsheet.worksheet("Настройки")

    def cell(addr, default=""):
        val = ws.acell(addr).value
        return str(val).strip() if val is not None else default

    days_from_sheet = ws.acell("B9").value
    if days_from_sheet:
        try:
            days_back = int(days_from_sheet)
        except (ValueError, TypeError):
            pass

    date_to = datetime.now()
    date_from = date_to - timedelta(days=days_back)
    date_from_str = date_from.strftime("%Y-%m-%d")
    date_to_str = date_to.strftime("%Y-%m-%d")

    logger.info(f"Период отчёта: {date_from_str} — {date_to_str}")

    return {
        "client_id": cell("B1"),
        "api_key": cell("B2"),
        "performance_client_id": cell("B3"),
        "performance_client_secret": cell("B4"),
        "cabinet_name": cell("B5", "Основной кабинет"),
        "date_from": date_from_str,
        "date_to": date_to_str,
    }


def get_or_create_sheet(spreadsheet: gspread.Spreadsheet, name: str) -> gspread.Worksheet:
    """Возвращает лист по имени, создаёт если не существует."""
    try:
        return spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=name, rows=5000, cols=20)


def to_iso(date_str: str) -> str:
    """'YYYY-MM-DD' → 'YYYY-MM-DDT00:00:00.000Z'"""
    return f"{date_str}T00:00:00.000Z"


def format_date(iso_date_string: str) -> str:
    """ISO-дата → 'DD.MM.YYYY HH:MM:SS'"""
    if not iso_date_string:
        return ""
    try:
        dt = datetime.fromisoformat(iso_date_string.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y %H:%M:%S")
    except Exception as e:
        logger.warning(f"Ошибка форматирования даты: {iso_date_string} - {e}")
        return iso_date_string


def normalize_warehouse_name(name: str) -> str:
    """Нормализует название склада."""
    if not name:
        return ""
    n = str(name).strip().upper().replace("_", " ")
    n = " ".join(n.split()).replace("Ё", "Е")
    aliases = {
        "НОВОРОССИЙСК МРФЦ": "НОВОРОССИЙСК",
        "НОВОРОССИЙСК МРФЦ СКЛАД": "НОВОРОССИЙСК",
    }
    return aliases.get(n, n)


def ozon_headers(settings: dict) -> dict:
    return {
        "Client-Id": str(settings["client_id"]),
        "Api-Key": settings["api_key"],
        "Content-Type": "application/json",
    }
