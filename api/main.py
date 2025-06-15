# api/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .recommendations import router as rec_router

app = FastAPI(
    title="Influencer AI Platform",
    description="POST /api/recommend with { brief_text, top_n, method } → returns recommendations[]",
)

# Allow cross‐origin requests from your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # or ["https://your-frontend-domain.com"]
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# All recommendation calls live under /api
app.include_router(rec_router, prefix="/api")
