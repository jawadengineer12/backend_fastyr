from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()


user = os.getenv("POSTGRES_USER")

password = os.getenv("POSTGRES_PASSWORD")

host = os.getenv("POSTGRES_HOST")

port = os.getenv("POSTGRES_PORT")

database = os.getenv("POSTGRES_DB")

SQLALCHEMY_DATABASE_URL = f"postgresql://{user}:{password}@{host}/{database}"
# SQLALCHEMY_DATABASE_URL = f"postgresql://{user}:{password}@{host}/{database}-test" #test database

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
