# api/crud.py
from sqlalchemy.orm import Session
from .models import Influencer

def get_influencer(db: Session, id: str):
    return db.query(Influencer).filter(Influencer.id == id).first()

def create_influencer(db: Session, data: dict):
    """
    data should include keys:
      id, title, description, published_at,
      subscriber_count, view_count, video_count
    """
    if get_influencer(db, data["id"]):
        return  # already exists

    inst = Influencer(**data)
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst
