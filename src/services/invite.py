import base64
import hashlib
import hmac
from datetime import date

import config


def _sign(owner_id: int, date_str: str) -> str:
    raw = f"{owner_id}:{date_str}"
    return hmac.new(config.INVITE_SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()


def make_invite_token(owner_id: int) -> str:
    date_str = date.today().isoformat()
    sig = _sign(owner_id, date_str)
    payload = f"{owner_id}:{date_str}:{sig}"
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def verify_invite_token(token: str) -> tuple[int | None, str | None]:
    """Returns (owner_id, None) on success, (None, 'expired'), or (None, 'invalid')."""
    try:
        padding = 4 - len(token) % 4
        if padding != 4:
            token = token + "=" * padding
        payload = base64.urlsafe_b64decode(token.encode()).decode()
        owner_id_str, date_str, sig = payload.split(":", 2)
        owner_id = int(owner_id_str)
    except Exception:
        return None, "invalid"

    expected = _sign(owner_id, date_str)
    if not hmac.compare_digest(sig, expected):
        return None, "invalid"

    try:
        token_date = date.fromisoformat(date_str)
    except ValueError:
        return None, "invalid"

    if (date.today() - token_date).days > 1:
        return None, "expired"

    return owner_id, None


def staff_invite_deeplink(token: str) -> str:
    return f"{config.DEEPLINK_BASE}?start={token}"
