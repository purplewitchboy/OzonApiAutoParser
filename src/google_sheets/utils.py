import logging
import time
import gspread

logger = logging.getLogger(__name__)


def with_retry(func, *args, max_retries: int = 5, base_delay: float = 20, **kwargs):
    """Выполняет вызов gspread с ретраями при 429 (Quota exceeded).

    Квота Google Sheets API ('Read/Write requests per minute per user') общая
    на весь service account — её могут исчерпать любые другие скрипты/таблицы,
    выполняющиеся в это же время в рамках одного workflow. Поэтому 429 стоит
    ретраить с задержкой практически при любом обращении к Sheets API, а не
    только чинить конкретное место, где он вылез в логах.
    """
    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except gspread.exceptions.APIError as e:
            status_code = None
            try:
                status_code = e.response.status_code
            except Exception:
                pass

            is_quota_error = status_code == 429 or 'Quota exceeded' in str(e) or '429' in str(e)

            if not is_quota_error or attempt == max_retries:
                raise

            delay = base_delay * attempt  # 20s, 40s, 60s, 80s, 100s...
            logger.warning(
                f"Google Sheets API 429 (попытка {attempt}/{max_retries}), "
                f"жду {delay} сек. перед повтором..."
            )
            time.sleep(delay)


def ensure_sheet_size(worksheet, required_rows: int, required_cols: int):
    """
    Гарантирует, что лист имеет нужное количество строк и столбцов.
    При необходимости расширяет его.
    """
    try:
        current_rows = worksheet.row_count
        current_cols = worksheet.col_count

        new_rows = max(current_rows, required_rows)
        new_cols = max(current_cols, required_cols)

        if new_rows != current_rows or new_cols != current_cols:
            worksheet.resize(rows=new_rows, cols=new_cols)
            logger.info(
                f"Лист '{worksheet.title}' расширен до "
                f"{new_rows} строк и {new_cols} столбцов"
            )

    except Exception as e:
        logger.error(f"Ошибка расширения листа '{worksheet.title}': {e}")
        raise
