import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

BIRTHDAY_HINT = "ДД.ММ.ГГ или ДД.ММ.ГГГГ, разделитель любой — например 12.05.90"


def _infer_year(yy: int) -> int:
    threshold = datetime.now().year % 100
    return 2000 + yy if yy <= threshold else 1900 + yy


def parse_birthday(text: str) -> tuple[date | None, str | None]:
    """Parse user birthday string. Returns (date, None) or (None, user-facing error)."""
    parts = [p for p in re.split(r"\D+", text.strip()) if p]
    if len(parts) != 3:
        return None, f"Не понял дату. Введите в формате {BIRTHDAY_HINT}:"
    d_str, m_str, y_str = parts
    try:
        d, m, y_raw = int(d_str), int(m_str), int(y_str)
        y = _infer_year(y_raw) if y_raw < 100 else y_raw
        bd = date(y, m, d)
    except ValueError:
        return None, "Такой даты не существует (например, 31 февраля). Попробуйте ещё раз:"
    if bd > date.today():
        return None, "День рождения не может быть в будущем. Введите корректную дату:"
    return bd, None


def parse_broadcast_dt(text: str, tz: ZoneInfo, default_hour: int) -> tuple[datetime | None, str | None]:
    """Parse broadcast schedule string. Returns (datetime, None) or (None, user-facing error).

    Accepts DD.MM or DD.MM HH:MM. Auto-advances to next year if date already passed.
    """
    text = text.strip()
    m = re.match(r"(\d{1,2})\.(\d{1,2})(?:\s+(\d{1,2}):(\d{2}))?$", text)
    if not m:
        return None, "Не понял дату. Укажите «ДД.ММ» или «ДД.ММ ЧЧ:ММ»"
    d, mo = int(m[1]), int(m[2])
    h = int(m[3]) if m[3] else default_hour
    mi = int(m[4]) if m[4] else 0
    now = datetime.now(tz)
    try:
        dt = datetime(now.year, mo, d, h, mi, tzinfo=tz)
    except ValueError:
        return None, "Такой даты не существует. Проверьте число и месяц"
    if dt <= now:
        try:
            dt = datetime(now.year + 1, mo, d, h, mi, tzinfo=tz)
        except ValueError:
            return None, "Такой даты не существует. Проверьте число и месяц"
    return dt, None
