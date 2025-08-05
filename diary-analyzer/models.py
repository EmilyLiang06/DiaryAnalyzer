from sqlalchemy import Column, Integer, String, Date, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Diary(Base):
    __tablename__ = "diaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    text = Column(Text, nullable=False)
    mood = Column(String(32))
    keywords = Column(String(256))  # 可以用逗号分隔关键词

    def __repr__(self):
        return f"<Diary(id={self.id}, date={self.date}, mood={self.mood})>"