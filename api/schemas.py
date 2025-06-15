# api/schemas.py

from pydantic import BaseModel

class RecommendRequest(BaseModel):
    brief_text: str
    top_n: int = 5
