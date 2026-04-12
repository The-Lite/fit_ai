from backend.app.db.tools.engine_pool import db
from backend.app.db.db_model.model import FlyerItem

def compute_weekly_needs(weight_kg: float, height_cm: float, budget: float):
    protein_g = round(weight_kg * 2.0)

    return {
        "daily_protein_g": protein_g,
        "weekly_food_needs": [
            {"item": "chicken breast", "qty": 2.5, "unit": "kg"},
            {"item": "eggs", "qty": 24, "unit": "unit"},
            {"item": "rice", "qty": 2.0, "unit": "kg"},
            {"item": "oats", "qty": 1.0, "unit": "kg"},
        ],
        "budget": budget,
    }

def get_products(store_name: str) -> dict:
    session = db.get_session()
    items = session.query(FlyerItem).filter(FlyerItem.store_name == store_name).all()
    return {
        store_name: [
            {
                "item_name": item.item_name,
                "price_value": float(item.price_value) if item.price_value is not None else None,
                "category": item.category,
                "flyer_date_start": item.flyer_date_start.isoformat(),
                "flyer_date_end": item.flyer_date_end.isoformat(),
            }
            for item in items
        ]
    }
    

def comparison_engine():
    # later: replace this with actual comparison logic
    pass



def cart_optimizer():
    # later: replace this with actual optimization logic
    pass


if __name__ == "__main__":
    print(get_products("MAXI"))
