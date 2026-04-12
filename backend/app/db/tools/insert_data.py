from termcolor import cprint

from backend.app.db.tools.engine_pool import db 
from backend.app.db.tools.db_manager import Database
from backend.app.db.db_model.model import FlyerItem
from datetime import date, timedelta
from decimal import Decimal
import json

def insert_data(db:Database,data:json,store_name:str):
    db_session = db.get_session()

    today = date.today()
    # Flyer week: Thursday (weekday=3) → Wednesday (weekday=2)
    days_since_thursday = (today.weekday() - 3) % 7
    flyer_date_start = today - timedelta(days=days_since_thursday)
    flyer_date_end = flyer_date_start + timedelta(days=6)
    items = data.get("items", [])
    for item_data in items:
        price_value = item_data["price"].replace("$", "").strip()
        item = FlyerItem(
            item_name=item_data["item_name"],
            price_value=Decimal(str(price_value)),
            category=item_data["category"],
            description=item_data["description"],
            store_name=store_name,
            flyer_date_start=flyer_date_start,
            flyer_date_end=flyer_date_end,
        )
        cprint(f"Inserting item: {item.item_name}, price: {item.price_value}, category: {item.category}, description: {item.description}", "green")
        db_session.add(item)
    cprint(f"Committing {len(items)} items to the database for store: {store_name}", "blue")
    db_session.commit()

if __name__ == "__main__":
    with open("backend/data/data_test/flayers/provigo/json/result.json", "r") as f:
        data = json.load(f)
    insert_data(db, data, "PROVIGO")