
from backend.app.db.db_model.model import Base
from backend.app.db.tools.engine_pool import db
from termcolor import cprint


def create_tables():
    cprint("Getting engine session ...", "blue")
    engine = db.engine
    if not engine.dialect.has_table(engine.connect(), "flyer_items"):
        session = db.get_session()
        cprint("Table does not exist. Creating tables...", "yellow")
        Base.metadata.create_all(session.bind)
        cprint("Tables created successfully.", "green")
    else:
        cprint("Table already exists.", "green")


if __name__ == "__main__":

    create_tables()