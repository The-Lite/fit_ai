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
    if items:
        item_name = items["item_name"]
        price_text = items["price_text"]
        price_value = items["price_value"]
        category = items["category"]
    item = FlyerItem(
            item_name=item_name,
            price_value=Decimal(str(price_value)),
            category=category,
            store=store_name,
            flyer_date_start=flyer_date_start,
            flyer_date_end=flyer_date_end,
        )
    db_session.add(item)
    db_session.commit()