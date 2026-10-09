import json
import os
from datetime import datetime, timezone

import httpx

REPORT_TYPE_LABELS = {
    "standard": "Standard Report",
    "detailed": "Detailed Report",
    "legal": "Legal Support Report",
    "multilingual": "Multilingual Report",
}


def _yes_no(value):
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return "Not specified"


def _readable_datetime(value):
    """Turn an ISO timestamp into prose-friendly text, leaving other input as-is."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime("%d %b %Y at %H:%M")
    except (ValueError, TypeError):
        return str(value)


def build_report(incident: dict, report_type: str = "standard", report_language: str = "English") -> dict:
    """Build a structured, template-based report from the collected incident data.

    This is a deterministic placeholder generator — no external AI/LLM call is made.
    """
    incident_type = incident.get("incident_type") or "Unspecified incident"
    location = incident.get("location") or "an unspecified location/platform"
    description = incident.get("description") or "No description was provided."
    occurred_at = incident.get("occurred_at")
    occurred_readable = _readable_datetime(occurred_at) or "an unspecified date/time"

    summary = (
        f"On {occurred_readable}, the reporting user experienced a {incident_type.lower()} "
        f"incident involving {location}. {description}"
    )

    timeline = [
        {"label": "Incident occurred", "detail": occurred_at or "Not specified"},
        {"label": "Report started", "detail": incident.get("created_at")},
        {"label": "Report generated", "detail": datetime.now(timezone.utc).isoformat()},
    ]

    technical_details = {
        "incident_type": incident_type,
        "location_or_platform": location,
        "evidence_files_count": len(incident.get("evidence_files", [])),
    }

    financial_loss = incident.get("financial_loss")
    amount_lost = incident.get("amount_lost")
    impact_assessment = {
        "financial_loss": _yes_no(financial_loss),
        "amount_lost": amount_lost if financial_loss else None,
        "platform_contacted": _yes_no(incident.get("contacted_platform")),
        "platform_response": incident.get("platform_response") or "No response recorded.",
    }

    evidence_summary = (
        f"{len(incident.get('evidence_files', []))} piece(s) of evidence were attached to this report."
        if incident.get("evidence_files")
        else "No evidence files were attached."
    )

    recommendations = [
        "Change passwords for any accounts that may have been compromised.",
        "Enable two-factor authentication wherever available.",
        "Do not click links or share OTPs from unsolicited messages.",
        "Monitor bank/payment statements for unauthorized transactions.",
    ]
    if financial_loss:
        recommendations.insert(0, "Contact your bank/payment provider immediately to report the fraudulent transaction.")

    next_steps = [
        "Download this report and keep a copy for your records.",
        "Submit this report to the relevant authority if you wish to pursue formal action.",
        "Use the tracking code to check the status of this report at any time.",
    ]

    return {
        "report_type": report_type,
        "report_type_label": REPORT_TYPE_LABELS.get(report_type, "Standard Report"),
        "report_language": report_language,
        "summary": summary,
        "timeline": timeline,
        "technical_details": technical_details,
        "impact_assessment": impact_assessment,
        "evidence_summary": evidence_summary,
        "recommendations": recommendations,
        "next_steps": next_steps,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ai_enhanced": False,
    }


# --------------------------------------------------------------------------
# Stage 2 (optional): LLM-polished summary and recommendations.
#
# `build_report()` above always runs first and is what gets returned if this
# fails or no API key is set — this only *replaces* the summary and
# recommendations fields of an already-complete, valid report. It never
# invents facts: the model is given the same structured incident data the
# template used and asked to rewrite it more naturally, not to add new
# claims.
# --------------------------------------------------------------------------

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-6"
LLM_TIMEOUT_SECONDS = 15.0


def enhance_report_with_llm(incident: dict, report: dict, report_language: str = "English") -> dict:
    """Try to rewrite `report["summary"]` and `report["recommendations"]`
    using Claude, grounded strictly in the same incident data. Returns the
    report unchanged (with `ai_enhanced` left False) if ANTHROPIC_API_KEY
    isn't set or the call fails for any reason — this is a best-effort
    polish step, not a required one.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return report

    prompt = f"""You are helping finalize a cyber-fraud incident report for a victim.
Here is the structured data already collected (do not invent anything beyond this):

{json.dumps({
    "incident_type": incident.get("incident_type"),
    "location_or_platform": incident.get("location"),
    "description": incident.get("description"),
    "occurred_at": incident.get("occurred_at"),
    "financial_loss": incident.get("financial_loss"),
    "amount_lost": incident.get("amount_lost"),
    "contacted_platform": incident.get("contacted_platform"),
    "platform_response": incident.get("platform_response"),
    "evidence_file_count": len(incident.get("evidence_files", [])),
}, default=str)}

Write in {report_language}. Respond with ONLY a JSON object, no other text, in this exact shape:
{{"summary": "a clear 2-4 sentence narrative summary of what happened, written for the victim to read back",
  "recommendations": ["list", "of", "4-6", "concrete", "next steps", "most urgent first"]}}
"""

    try:
        response = httpx.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": ANTHROPIC_MODEL,
                "max_tokens": 600,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=LLM_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        text = "".join(
            block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
        ).strip()
        # Models sometimes wrap JSON in a code fence despite instructions — strip it defensively.
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed = json.loads(text)

        if parsed.get("summary"):
            report["summary"] = parsed["summary"]
        if parsed.get("recommendations"):
            report["recommendations"] = parsed["recommendations"]
        report["ai_enhanced"] = True
    except Exception:
        # Any failure (no network, bad key, rate limit, bad JSON back) just
        # means we keep the deterministic version already in `report`.
        pass

    return report
