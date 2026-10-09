from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone

from database import (
    articles_collection,
    alerts_collection,
    subscribers_collection,
)
from models import SubscribeRequest
from routers.auth import router as auth_router
from routers.incidents import router as incidents_router
from routers.detect import router as detect_router

app = FastAPI(
    title="Aiges Backend",
    description="Minimal backend API for the Aiges homepage.",
    version="1.0.0",
)

# Allows the local HTML frontend to call the API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(incidents_router)
app.include_router(detect_router)


def clean_document(doc):
    """Convert MongoDB _id into a JSON-friendly string id."""
    if not doc:
        return None
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


@app.get("/api/homepage")
def get_homepage():
    """Return all data needed to render the homepage in one request."""

    latest = list(
        articles_collection.find().sort("date", -1).limit(6)
    )

    trending = list(
        articles_collection.find({"trending": True}).sort("date", -1).limit(5)
    )

    featured = articles_collection.find_one({"featured": True})

    alerts = list(
        alerts_collection.find().sort("date", -1).limit(5)
    )

    # The newest article is used as the breaking-news item.
    breaking = latest[:1]

    return {
        "breaking_news": [clean_document(item) for item in breaking],
        "featured_story": clean_document(featured),
        "trending": [clean_document(item) for item in trending],
        "latest_articles": [clean_document(item) for item in latest],
        "alerts": [clean_document(item) for item in alerts],
    }


@app.get("/api/articles")
def get_articles(
    category: str | None = Query(default=None)
):
    """Return articles, optionally filtered by category."""
    query = {}

    if category and category.lower() != "all":
        query["category"] = {
            "$regex": f"^{category}$",
            "$options": "i",
        }

    articles = list(
        articles_collection.find(query).sort("date", -1)
    )

    return {
        "category": category or "All",
        "articles": [clean_document(item) for item in articles],
    }


@app.post("/api/subscribe")
def subscribe(request: SubscribeRequest):
    """Save a newsletter subscriber if the email is not already present."""
    email = request.email.lower().strip()

    existing = subscribers_collection.find_one({"email": email})
    if existing:
        return {
            "success": True,
            "message": "This email is already subscribed.",
        }

    subscribers_collection.insert_one(
        {
            "email": email,
            "subscribed_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    return {
        "success": True,
        "message": "Successfully subscribed to the Aiges newsletter.",
    }


## Note: the old `/api/generate-report` placeholder (unrelated to incident
## reports) has been removed — real report generation now lives at
## `POST /api/incidents/{id}/generate-report`, with an optional Claude-
## powered Stage 2 polish (see report_generator.enhance_report_with_llm).
