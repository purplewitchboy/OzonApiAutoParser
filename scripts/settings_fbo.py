import logging
from datetime import datetime, timedelta

# Переиспользуем общие утилиты
from scripts.settings import (
    load_credentials,
    open_spreadsheet,
    get_or_create_sheet,
    ozon_headers,
    normalize_warehouse_name,
)

logger = logging.getLogger(__name__)


def get_settings(spreadsheet, days_back: int = 30) -> dict:
    """
    Читает настройки из листа «Настройки» таблицы.
    Период: от 30 дней назад (00:00:00 МСК) до вчера (23:59:59 МСК).
    Даты передаются в Ozon в формате московского времени с суффиксом .000Z.
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

    MSK = timedelta(hours=3)
    now_msk = datetime.utcnow() + MSK
    yesterday_msk = datetime(now_msk.year, now_msk.month, now_msk.day) - timedelta(days=1)

    date_to_msk = datetime(yesterday_msk.year, yesterday_msk.month, yesterday_msk.day, 23, 59, 59)
    date_from_msk = datetime(yesterday_msk.year, yesterday_msk.month, yesterday_msk.day) - timedelta(days=days_back)

    date_from_iso = date_from_msk.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    date_to_iso = date_to_msk.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    logger.info(
        f"Период отчёта (МСК): {date_from_msk.strftime('%Y-%m-%d %H:%M:%S')} — "
        f"{date_to_msk.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    return {
        "client_id": cell("B1"),
        "api_key": cell("B2"),
        "performance_client_id": cell("B3"),
        "performance_client_secret": cell("B4"),
        "cabinet_name": cell("B5", "Основной кабинет"),
        "date_from": date_from_iso,
        "date_to": date_to_iso,
    }


def to_iso(date_str: str) -> str:
    """Даты уже в ISO-формате — возвращаем как есть."""
    return date_str


def format_date(iso_date_string: str) -> str:
    """ISO-дата → 'DD.MM.YYYY' (только дата, без времени)."""
    if not iso_date_string:
        return ""
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f+00:00",
        "%Y-%m-%dT%H:%M:%S+00:00",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(iso_date_string, fmt).strftime("%d.%m.%Y")
        except ValueError:
            continue
    logger.warning(f"Не удалось распарсить дату: {iso_date_string}")
    return iso_date_string
