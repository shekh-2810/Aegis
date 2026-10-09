from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from database import detections_collection
from detector import score_url_async

router = APIRouter(prefix="/api/detect", tags=["detection"])

CACHE_TTL_SECONDS = 86400  # 24 hours, matches the Mongo TTL index


class DetectRequest(BaseModel):
    url: str = Field(min_length=3, max_length=2048)


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    checked_at = doc.get("checked_at")
    if isinstance(checked_at, datetime):
        doc["checked_at"] = checked_at.isoformat()
    return doc


@router.post("")
async def detect_url(request: DetectRequest):
    """Score a URL and cache the result per-domain for 24 hours.

    Combines local heuristics with Google Safe Browsing / VirusTotal when
    their API keys are configured (see .env.example) — if neither key is
    set, this runs on heuristics alone.
    """
    result = await score_url_async(request.url)
    domain = result.get("domain")

    if not domain:
        return {**result, "cached": False, "checked_at": None}

    now = datetime.now(timezone.utc)
    cached = detections_collection.find_one({"domain": domain})

    if cached:
        age_seconds = (now - cached["checked_at"].replace(tzinfo=timezone.utc)).total_seconds()
        if age_seconds < CACHE_TTL_SECONDS:
            response = _serialize(cached)
            response["cached"] = True
            response["url"] = request.url
            return response

    record = {**result, "checked_at": now}
    detections_collection.update_one(
        {"domain": domain},
        {"$set": record},
        upsert=True,
    )

    response = _serialize(record)
    response["cached"] = False
    return response


@router.get("/history")
def detect_history(limit: int = Query(default=20, le=100)):
    """Return the most recently scanned domains (for a simple dashboard/feed)."""
    docs = detections_collection.find().sort("checked_at", -1).limit(limit)
    return {"results": [_serialize(doc) for doc in docs]}


@router.get("/threat-feed")
def threat_feed(limit: int = Query(default=20, le=100)):
    """Proactive threat intel: flagged domains found by the crawler (not
    user-submitted scans). Run `python crawler.py` to populate this.
    """
    docs = (
        detections_collection.find({"source": "crawler"})
        .sort("checked_at", -1)
        .limit(limit)
    )
    return {"results": [_serialize(doc) for doc in docs]}
