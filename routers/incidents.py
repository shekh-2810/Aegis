import os
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import Response

from auth_utils import get_current_user, get_optional_user
from database import incidents_collection
from models import IncidentAdditionalUpdate, IncidentDetailsUpdate, IncidentGenerateReportRequest
from pdf_generator import build_pdf
from report_generator import build_report, enhance_report_with_llm

router = APIRouter(prefix="/api/incidents", tags=["incidents"])

UPLOAD_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_tracking_code() -> str:
    return "AIG-" + secrets.token_hex(4).upper()


def _to_object_id(incident_id: str) -> ObjectId:
    try:
        return ObjectId(incident_id)
    except InvalidId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")


def _get_incident_or_404(incident_id: str) -> dict:
    incident = incidents_collection.find_one({"_id": _to_object_id(incident_id)})
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")
    return incident


def _verify_access(incident: dict, user: Optional[dict], tracking_code: Optional[str]):
    owner_id = incident.get("user_id")

    if owner_id:
        if user and str(user["_id"]) == owner_id:
            return
        if tracking_code and tracking_code == incident.get("tracking_code"):
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this report.")

    # Anonymous incident: correct tracking code is required.
    if tracking_code and tracking_code == incident.get("tracking_code"):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this report.")


def _clean(incident: dict) -> dict:
    incident = dict(incident)
    incident["id"] = str(incident.pop("_id"))
    if incident.get("user_id"):
        incident["user_id"] = str(incident["user_id"])
    return incident


@router.post("", status_code=status.HTTP_201_CREATED)
def create_incident(current_user: Optional[dict] = Depends(get_optional_user)):
    now = _now()
    doc = {
        "tracking_code": _new_tracking_code(),
        "user_id": str(current_user["_id"]) if current_user else None,
        "status": "draft",
        "incident_type": None,
        "location": None,
        "occurred_at": None,
        "description": None,
        "financial_loss": None,
        "amount_lost": None,
        "evidence_files": [],
        "contacted_platform": None,
        "platform_response": None,
        "notes": None,
        "report_type": None,
        "report_language": None,
        "generated_report": None,
        "created_at": now,
        "updated_at": now,
    }
    result = incidents_collection.insert_one(doc)
    return _clean(incidents_collection.find_one({"_id": result.inserted_id}))


@router.get("")
def list_my_incidents(current_user: dict = Depends(get_current_user)):
    docs = incidents_collection.find({"user_id": str(current_user["_id"])}).sort("created_at", -1)
    return {"incidents": [_clean(doc) for doc in docs]}


@router.delete("/{incident_id}")
def delete_incident(
    incident_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete one of the current user's own reports. Requires login —
    anonymous (tracking-code-only) reports can't be deleted this way, since
    there's no account to prove ownership against.
    """
    incident = _get_incident_or_404(incident_id)
    if incident.get("user_id") != str(current_user["_id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this report.")

    incidents_collection.delete_one({"_id": incident["_id"]})

    incident_dir = os.path.join(UPLOAD_ROOT, incident_id)
    if os.path.isdir(incident_dir):
        import shutil
        shutil.rmtree(incident_dir, ignore_errors=True)

    return {"deleted": True, "id": incident_id}


@router.get("/track")
def track_incident(code: str = Query(...)):
    incident = incidents_collection.find_one({"tracking_code": code.strip()})
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No report found for that tracking code.")
    return _clean(incident)


@router.get("/{incident_id}")
def get_incident(
    incident_id: str,
    tracking_code: Optional[str] = Query(default=None),
    current_user: Optional[dict] = Depends(get_optional_user),
):
    incident = _get_incident_or_404(incident_id)
    _verify_access(incident, current_user, tracking_code)
    return _clean(incident)


@router.patch("/{incident_id}/details")
def update_details(
    incident_id: str,
    request: IncidentDetailsUpdate,
    tracking_code: Optional[str] = Query(default=None),
    current_user: Optional[dict] = Depends(get_optional_user),
):
    incident = _get_incident_or_404(incident_id)
    _verify_access(incident, current_user, tracking_code)

    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    updates["updated_at"] = _now()

    incidents_collection.update_one({"_id": incident["_id"]}, {"$set": updates})
    return _clean(incidents_collection.find_one({"_id": incident["_id"]}))


@router.patch("/{incident_id}/additional")
def update_additional(
    incident_id: str,
    request: IncidentAdditionalUpdate,
    tracking_code: Optional[str] = Query(default=None),
    current_user: Optional[dict] = Depends(get_optional_user),
):
    incident = _get_incident_or_404(incident_id)
    _verify_access(incident, current_user, tracking_code)

    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    updates["updated_at"] = _now()

    incidents_collection.update_one({"_id": incident["_id"]}, {"$set": updates})
    return _clean(incidents_collection.find_one({"_id": incident["_id"]}))


@router.post("/{incident_id}/evidence")
async def upload_evidence(
    incident_id: str,
    file: UploadFile,
    tracking_code: Optional[str] = Query(default=None),
    current_user: Optional[dict] = Depends(get_optional_user),
):
    incident = _get_incident_or_404(incident_id)
    _verify_access(incident, current_user, tracking_code)

    original_name = file.filename or "upload"
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}.",
        )

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File exceeds the 10 MB limit.")

    incident_dir = os.path.join(UPLOAD_ROOT, incident_id)
    os.makedirs(incident_dir, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(incident_dir, stored_name), "wb") as f:
        f.write(contents)

    evidence_entry = {
        "filename": stored_name,
        "original_name": original_name,
        "content_type": file.content_type,
        "size": len(contents),
        "uploaded_at": _now(),
    }

    incidents_collection.update_one(
        {"_id": incident["_id"]},
        {"$push": {"evidence_files": evidence_entry}, "$set": {"updated_at": _now()}},
    )
    return _clean(incidents_collection.find_one({"_id": incident["_id"]}))


@router.delete("/{incident_id}/evidence/{filename}")
def delete_evidence(
    incident_id: str,
    filename: str,
    tracking_code: Optional[str] = Query(default=None),
    current_user: Optional[dict] = Depends(get_optional_user),
):
    incident = _get_incident_or_404(incident_id)
    _verify_access(incident, current_user, tracking_code)

    safe_filename = os.path.basename(filename)
    incidents_collection.update_one(
        {"_id": incident["_id"]},
        {"$pull": {"evidence_files": {"filename": safe_filename}}, "$set": {"updated_at": _now()}},
    )

    file_path = os.path.join(UPLOAD_ROOT, incident_id, safe_filename)
    if os.path.isfile(file_path) and os.path.commonpath([UPLOAD_ROOT, file_path]) == UPLOAD_ROOT:
        os.remove(file_path)

    return _clean(incidents_collection.find_one({"_id": incident["_id"]}))


@router.post("/{incident_id}/generate-report")
def generate_report(
    incident_id: str,
    request: IncidentGenerateReportRequest,
    tracking_code: Optional[str] = Query(default=None),
    current_user: Optional[dict] = Depends(get_optional_user),
):
    incident = _get_incident_or_404(incident_id)
    _verify_access(incident, current_user, tracking_code)

    report = build_report(incident, request.report_type, request.report_language)
    # Best-effort Stage 2 polish — silently no-ops if ANTHROPIC_API_KEY isn't
    # set, so this is safe to leave on by default.
    report = enhance_report_with_llm(incident, report, request.report_language)

    incidents_collection.update_one(
        {"_id": incident["_id"]},
        {
            "$set": {
                "report_type": request.report_type,
                "report_language": request.report_language,
                "generated_report": report,
                "status": "generated",
                "updated_at": _now(),
            }
        },
    )
    return _clean(incidents_collection.find_one({"_id": incident["_id"]}))


@router.get("/{incident_id}/report/pdf")
def download_report_pdf(
    incident_id: str,
    tracking_code: Optional[str] = Query(default=None),
    current_user: Optional[dict] = Depends(get_optional_user),
):
    incident = _get_incident_or_404(incident_id)
    _verify_access(incident, current_user, tracking_code)

    if not incident.get("generated_report"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Generate the report before downloading it.")

    pdf_bytes = build_pdf(incident)
    headers = {"Content-Disposition": f'attachment; filename="aiges-report-{incident["tracking_code"]}.pdf"'}
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@router.patch("/{incident_id}/submit")
def submit_incident(
    incident_id: str,
    tracking_code: Optional[str] = Query(default=None),
    current_user: Optional[dict] = Depends(get_optional_user),
):
    incident = _get_incident_or_404(incident_id)
    _verify_access(incident, current_user, tracking_code)

    incidents_collection.update_one(
        {"_id": incident["_id"]},
        {"$set": {"status": "submitted", "updated_at": _now()}},
    )
    return _clean(incidents_collection.find_one({"_id": incident["_id"]}))
