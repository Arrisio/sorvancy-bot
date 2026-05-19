from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN: str = os.environ["BOT_TOKEN"]

DB_HOST: str = os.environ["DB_HOST"]
DB_PORT: int = int(os.environ.get("DB_PORT", 5432))
DB_NAME: str = os.environ["DB_NAME"]
DB_USER: str = os.environ["DB_USER"]
DB_PASSWORD: str = os.environ["DB_PASSWORD"]

OWNER_ID: int | None = (
    int(os.environ["OWNER_ID"]) if os.environ.get("OWNER_ID") else None
)

SUPPORT_ID: int | None = (
    int(os.environ["SUPPORT_ID"]) if os.environ.get("SUPPORT_ID") else None
)

BROADCAST_SEND_DELAY_SECONDS: float = float(os.environ.get("BROADCAST_SEND_DELAY_SECONDS", 15))
BROADCAST_WINDOW_START_HOUR: int = int(os.environ.get("BROADCAST_WINDOW_START_HOUR", 10))
BROADCAST_WINDOW_END_HOUR: int = int(os.environ.get("BROADCAST_WINDOW_END_HOUR", 17))

# Bot URL for deeplinks embedded in customer QR codes.
# Format: https://max.ru/<botName>
# Code appends ?start=show_profile_<customer_id>
DEEPLINK_BASE: str = os.environ.get("DEEPLINK_BASE", "")

INVITE_SECRET: str = os.environ.get("INVITE_SECRET", "")

