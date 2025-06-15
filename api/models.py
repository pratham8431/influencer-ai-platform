# api/models.py
from sqlalchemy import Column, String, DateTime, create_engine, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Influencer(Base):
    __tablename__ = "influencers"

    id               = Column(String,   primary_key=True, index=True)
    title            = Column(String,   nullable=False)
    description      = Column(String)
    published_at     = Column(DateTime)
    subscriber_count = Column(BigInteger)
    view_count       = Column(BigInteger)
    video_count      = Column(BigInteger)

SQLALCHEMY_DATABASE_URL = "postgresql://ai_user:ai_pass@localhost:5432/influencer_ai"
engine   = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
