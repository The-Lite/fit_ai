from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,Session


class Database:

    _instance = None
    _intialized = False

    def __new__(cls,db_url:str):
        if cls._instance is None:
            cls._instance = super(Database,cls).__new__(cls)
        return cls._instance
    def __init__(self,db_url:str):
        if self._intialized:
            return
        self.engine = create_engine(db_url,echo=False)
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False
        )
        self._intialized = True
    
    def get_session(self) -> Session:
        return self.SessionLocal()