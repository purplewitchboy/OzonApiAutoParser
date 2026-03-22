import logging

logger = logging.getLogger(__name__)


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
