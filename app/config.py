import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

BROWSER_HEADLESS: bool = os.getenv("BROWSER_HEADLESS", "false").lower() == "true"
BROWSER_SLOW_MO: int = int(os.getenv("BROWSER_SLOW_MO", "50"))

DB_PATH: Path = BASE_DIR / os.getenv("DB_PATH", "data/cita_previa.db")
DISCOVERY_DIR: Path = BASE_DIR / os.getenv("DISCOVERY_DIR", "data/discovery")

ICPPLUS_URL = "https://sede.administracionespublicas.gob.es/pagina/index/directorio/icpplus"

# Checker settings — pre-filled with the Alicante / Ukraine TIE flow from discovery
PROVINCE_URL_PATH: str = os.getenv("PROVINCE_URL_PATH", "/icpco/citar?p=3&locale=es")
SEDE_VALUE: str = os.getenv("SEDE_VALUE", "99")           # 99 = any office
TRAMITE_GROUP_INDEX: int = int(os.getenv("TRAMITE_GROUP_INDEX", "1"))
TRAMITE_VALUE: str = os.getenv("TRAMITE_VALUE", "4112")   # Tarjeta Ucrania TIE
SUBTRAMITE_VALUE: str = os.getenv("SUBTRAMITE_VALUE", "")

NIE: str = os.getenv("NIE", "")
NOMBRE: str = os.getenv("NOMBRE", "")

CHECK_INTERVAL_SECONDS: int = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))
# How long to wait before re-alerting when slots remain open (default 1 hour)
ALERT_COOLDOWN_SECONDS: int = int(os.getenv("ALERT_COOLDOWN_SECONDS", "3600"))
