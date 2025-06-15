# api/recommendations.py

from fastapi import APIRouter
from sqlalchemy.orm import Session

from .models                    import SessionLocal, Influencer
from .schemas                   import RecommendRequest
from ai.brief_parser            import parse_brief
from etl.youtube_scraper        import search_channels_by_video  # <– changed import
from api.crud                   import create_influencer

router = APIRouter()

@router.post("/recommend")
def recommend(req: RecommendRequest):
    brief_text, top_n = req.brief_text, req.top_n
    prefs = parse_brief(brief_text)

    db: Session = SessionLocal()
    try:
        # 1) Hard-filter by subscriber count
        candidates = (
            db.query(Influencer)
              .filter(Influencer.subscriber_count >= prefs["min_subs"])
              .all()
        )

        # 2) If too few in DB, video-based fallback & ingest
        live_ids = None
        if len(candidates) < 10:
            live = search_channels_by_video(brief_text, max_results=30)
            for ch in live:
                create_influencer(db, ch)
            live_ids = [ch["id"] for ch in live]

        # 3) Build ranking query
        q = db.query(Influencer).order_by(Influencer.subscriber_count.desc())
        if live_ids is not None:
            # only rank the freshly scraped bike channels
            q = q.filter(Influencer.id.in_(live_ids))
        else:
            # rank existing DB matches
            q = q.filter(Influencer.subscriber_count >= prefs["min_subs"])

        influencers = q.limit(top_n).all()

        # 4) Return results
        return {"recommendations": [
            {"id": inf.id, "title": inf.title, "subs": inf.subscriber_count}
            for inf in influencers
        ]}
    finally:
        db.close()
