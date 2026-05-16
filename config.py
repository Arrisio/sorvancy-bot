from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN: str = os.environ["BOT_TOKEN"]

DB_HOST: str = os.environ["DB_HOST"]
DB_PORT: int = int(os.environ.get("DB_PORT", 5432))
DB_NAME: str = os.environ["DB_NAME"]
DB_USER: str = os.environ["DB_USER"]
DB_PASSWORD: str = os.environ["DB_PASSWORD"]

DISCOUNT_PERCENT: int = int(os.environ.get("DISCOUNT_PERCENT", 10))
