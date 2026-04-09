
from backend.app.db.tools.db_manager import Database
from backend.utils.load_config import load_config
config = load_config("config.json")


db = Database(config["database"]["url"])