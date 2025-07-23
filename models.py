from sqlalchemy import Column, String, Integer, DateTime
from database import Base  # use the shared Base from database.py

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    userName = Column(String, index=True)
    email = Column(String, index=True, unique=True)
    hashed_password = Column(String, index=True)
    datetime = Column(DateTime, index=True, nullable=False)
    image = Column(String, nullable=True)
