import os, pathlib, logging
from dotenv import load_dotenv

def setup_logging():
    pathlib.Path('logs').mkdir(exist_ok=True)
    logging.basicConfig(
        filename='logs/run.log',
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logging.getLogger().addHandler(console)

def load_env():
    load_dotenv()
    return {
        "APCA_API_KEY_ID": os.getenv("APCA_API_KEY_ID", ""),
        "APCA_API_SECRET_KEY": os.getenv("APCA_API_SECRET_KEY", ""),
        "APCA_API_BASE_URL": os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets"),
        "MODE": os.getenv("MODE","paper"),
        "DISCORD_WEBHOOK_URL": os.getenv("DISCORD_WEBHOOK_URL",""),
    }
