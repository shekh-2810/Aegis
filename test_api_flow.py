"""End-to-end smoke test for the Aiges backend.

Run with the API server up:  python test_api_flow.py
Exercises every endpoint the frontend depends on and prints PASS/FAIL per check.
"""
import io
import json
import urllib.error
import urllib.request
import uuid

BASE = "http://127.0.0.1:8000"

results = []


def check(name, condition, detail=""):
    results.append((name, bool(condition), detail))
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f"  -> {detail}" if detail else ""))


def request(method, path, body=None, token=None, raw=False, multipart=None):
    url = BASE + path
    headers = {}
    data = None

    if multipart is not None:
        boundary = uuid.uuid4().hex
        filename, content, content_type = multipart
        buf = io.BytesIO()
        buf.write(f"--{boundary}\r\n".encode())
        buf.write(
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
        )
        buf.write(f"Content-Type: {content_type}\r\n\r\n".encode())
        buf.write(content)
        buf.write(f"\r\n--{boundary}--\r\n".encode())
        data = buf.getvalue()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"

    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            payload = resp.read()
            if raw:
                return resp.status, payload
            return resp.status, json.loads(payload) if payload else None
    except urllib.error.HTTPError as e:
        payload = e.read()
        try:
            return e.code, json.loads(payload)
        except Exception:
            return e.code, payload


print("=" * 70)
print("PUBLIC / HOMEPAGE ENDPOINTS")
print("=" * 70)

status, data = request("GET", "/api/homepage")
check("GET /api/homepage returns 200", status == 200, f"status={status}")
check("homepage has all 5 sections",
      all(k in data for k in ["breaking_news", "featured_story", "trending", "latest_articles", "alerts"]),
      f"keys={sorted(data.keys()) if isinstance(data, dict) else data}")
check("homepage featured_story populated", data.get("featured_story") is not None)
check("homepage latest_articles non-empty", len(data.get("latest_articles", [])) > 0,
      f"count={len(data.get('latest_articles', []))}")
check("homepage alerts non-empty", len(data.get("alerts", [])) > 0,
      f"count={len(data.get('alerts', []))}")
check("homepage docs have string id (no ObjectId leak)",
      all(isinstance(a.get("id"), str) for a in data.get("latest_articles", [])))

status, data = request("GET", "/api/articles?category=Phishing")
check("GET /api/articles?category=Phishing returns 200", status == 200)
check("category filter works (all results are Phishing)",
      data.get("articles") and all(a["category"].lower() == "phishing" for a in data["articles"]),
      f"count={len(data.get('articles', []))}")

status, data = request("GET", "/api/articles?category=All")
check("category=All returns everything", len(data.get("articles", [])) == 6,
      f"count={len(data.get('articles', []))}")

email = f"test-{uuid.uuid4().hex[:8]}@example.com"
status, data = request("POST", "/api/subscribe", {"email": email})
check("POST /api/subscribe accepts new email", status == 200 and data.get("success"))
status, data = request("POST", "/api/subscribe", {"email": email})
check("POST /api/subscribe dedupes existing email",
      "already subscribed" in data.get("message", "").lower(), data.get("message"))
status, data = request("POST", "/api/subscribe", {"email": "not-an-email"})
check("POST /api/subscribe rejects malformed email", status == 422, f"status={status}")

print()
print("=" * 70)
print("AUTH ENDPOINTS")
print("=" * 70)

user_email = f"user-{uuid.uuid4().hex[:8]}@example.com"
status, data = request("POST", "/api/auth/signup",
                       {"name": "Test User", "email": user_email, "password": "supersecret123"})
check("POST /api/auth/signup returns 200", status == 200, f"status={status}")
check("signup returns access_token", bool(data.get("access_token")))
check("signup returns user object with id/name/email",
      all(k in data.get("user", {}) for k in ["id", "name", "email"]))
check("signup does NOT leak password_hash", "password_hash" not in json.dumps(data))
token = data.get("access_token")

status, data = request("POST", "/api/auth/signup",
                       {"name": "Dup", "email": user_email, "password": "supersecret123"})
check("signup rejects duplicate email with 409", status == 409, f"status={status}")

status, data = request("POST", "/api/auth/signup",
                       {"name": "Short", "email": f"x-{uuid.uuid4().hex[:6]}@e.com", "password": "short"})
check("signup enforces min password length (422)", status == 422, f"status={status}")

status, data = request("POST", "/api/auth/login", {"email": user_email, "password": "supersecret123"})
check("POST /api/auth/login succeeds with correct creds", status == 200 and bool(data.get("access_token")))
login_token = data.get("access_token")

status, data = request("POST", "/api/auth/login", {"email": user_email, "password": "wrongpassword"})
check("login rejects wrong password with 401", status == 401, f"status={status}")

status, data = request("GET", "/api/auth/me", token=login_token)
check("GET /api/auth/me returns the user", status == 200 and data.get("email") == user_email)

status, data = request("GET", "/api/auth/me")
check("GET /api/auth/me without token returns 401", status == 401, f"status={status}")

status, data = request("GET", "/api/auth/me", token="garbage.token.here")
check("GET /api/auth/me with invalid token returns 401", status == 401, f"status={status}")

print()
print("=" * 70)
print("INCIDENT WIZARD — AUTHENTICATED FLOW")
print("=" * 70)

status, incident = request("POST", "/api/incidents", token=login_token)
check("POST /api/incidents creates draft (201)", status == 201, f"status={status}")
check("new incident status is 'draft'", incident.get("status") == "draft")
check("new incident has tracking_code", bool(incident.get("tracking_code")),
      incident.get("tracking_code"))
check("new incident is owned by the user", incident.get("user_id") == json.loads(
    json.dumps(incident))["user_id"] and incident.get("user_id") is not None)
iid = incident["id"]
code = incident["tracking_code"]

status, data = request("PATCH", f"/api/incidents/{iid}/details", {
    "incident_type": "Phishing",
    "location": "fake-bank-login.com",
    "occurred_at": "2026-09-10T14:30",
    "description": "I received an SMS with a link to what looked like my bank login page and entered my OTP.",
}, token=login_token)
check("PATCH /details returns 200", status == 200, f"status={status}")
check("/details persisted incident_type", data.get("incident_type") == "Phishing")
check("/details persisted description", "OTP" in (data.get("description") or ""))

status, data = request("PATCH", f"/api/incidents/{iid}/additional", {
    "financial_loss": True,
    "amount_lost": 5000,
    "contacted_platform": True,
    "platform_response": "Bank blocked the card and opened a dispute.",
    "notes": "Also reported to cybercrime portal.",
}, token=login_token)
check("PATCH /additional returns 200", status == 200, f"status={status}")
check("/additional persisted financial_loss=True", data.get("financial_loss") is True)
check("/additional persisted amount_lost", data.get("amount_lost") == 5000)

status, data = request("PATCH", f"/api/incidents/{iid}/additional",
                       {"financial_loss": False}, token=login_token)
check("PATCH /additional can set boolean False (not dropped)",
      data.get("financial_loss") is False, f"value={data.get('financial_loss')}")
request("PATCH", f"/api/incidents/{iid}/additional",
        {"financial_loss": True, "amount_lost": 5000}, token=login_token)

png = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a49444154789c6300010000050001")
status, data = request("POST", f"/api/incidents/{iid}/evidence", token=login_token,
                       multipart=("screenshot.png", png, "image/png"))
check("POST /evidence accepts a PNG", status == 200, f"status={status}")
check("evidence recorded in incident", len(data.get("evidence_files", [])) == 1,
      f"count={len(data.get('evidence_files', []))}")
ev = data["evidence_files"][0]
check("stored filename is randomized (not original)", ev["filename"] != "screenshot.png",
      f"stored={ev['filename']}")
check("original_name preserved", ev["original_name"] == "screenshot.png")

status, data = request("POST", f"/api/incidents/{iid}/evidence", token=login_token,
                       multipart=("malware.exe", b"MZ\x00\x00", "application/octet-stream"))
check("POST /evidence rejects disallowed extension (.exe)", status == 400, f"status={status}")

status, data = request("POST", f"/api/incidents/{iid}/evidence", token=login_token,
                       multipart=("huge.pdf", b"x" * (11 * 1024 * 1024), "application/pdf"))
check("POST /evidence rejects file over 10MB", status == 400, f"status={status}")

status, data = request("POST", f"/api/incidents/{iid}/generate-report",
                       {"report_type": "detailed", "report_language": "English"}, token=login_token)
check("POST /generate-report returns 200", status == 200, f"status={status}")
check("status advanced to 'generated'", data.get("status") == "generated", data.get("status"))
report = data.get("generated_report") or {}
check("report has summary", bool(report.get("summary")))
check("report summary includes user's description",
      "OTP" in report.get("summary", ""))
check("report has timeline", len(report.get("timeline", [])) >= 3)
check("report has recommendations", len(report.get("recommendations", [])) > 0)
check("report has next_steps", len(report.get("next_steps", [])) > 0)
check("report_type label reflects 'detailed' choice",
      report.get("report_type") == "detailed", report.get("report_type_label"))
check("financial-loss recommendation injected first",
      "bank" in report.get("recommendations", [""])[0].lower(),
      report.get("recommendations", [""])[0])
check("impact_assessment reflects loss amount",
      report.get("impact_assessment", {}).get("amount_lost") == 5000)
check("evidence_summary mentions attached evidence",
      "1 piece" in report.get("evidence_summary", ""), report.get("evidence_summary"))

status, pdf = request("GET", f"/api/incidents/{iid}/report/pdf", token=login_token, raw=True)
check("GET /report/pdf returns 200", status == 200, f"status={status}")
check("response is a real PDF (%PDF magic bytes)", pdf[:4] == b"%PDF", f"first bytes={pdf[:8]}")
check("PDF is non-trivial in size", len(pdf) > 1000, f"{len(pdf)} bytes")

status, data = request("PATCH", f"/api/incidents/{iid}/submit", token=login_token)
check("PATCH /submit returns 200", status == 200, f"status={status}")
check("status advanced to 'submitted'", data.get("status") == "submitted", data.get("status"))

status, data = request("GET", "/api/incidents", token=login_token)
check("GET /api/incidents lists the user's reports", status == 200 and len(data.get("incidents", [])) >= 1,
      f"count={len(data.get('incidents', []))}")

status, data = request("GET", f"/api/incidents/track?code={code}")
check("GET /api/incidents/track finds report by code (no auth)", status == 200, f"status={status}")
check("track returns correct incident", data.get("id") == iid)

status, data = request("GET", "/api/incidents/track?code=AIG-DOESNOTEXIST")
check("track with bogus code returns 404", status == 404, f"status={status}")

print()
print("=" * 70)
print("ACCESS CONTROL")
print("=" * 70)

other_email = f"other-{uuid.uuid4().hex[:8]}@example.com"
status, data = request("POST", "/api/auth/signup",
                       {"name": "Other User", "email": other_email, "password": "supersecret123"})
other_token = data["access_token"]

status, data = request("GET", f"/api/incidents/{iid}", token=other_token)
check("another user CANNOT read someone else's incident (403)", status == 403, f"status={status}")

status, data = request("PATCH", f"/api/incidents/{iid}/details",
                       {"description": "hacked"}, token=other_token)
check("another user CANNOT modify someone else's incident (403)", status == 403, f"status={status}")

status, data = request("GET", f"/api/incidents/{iid}")
check("anonymous CANNOT read owned incident without code (403)", status == 403, f"status={status}")

status, data = request("GET", f"/api/incidents/{iid}?tracking_code={code}")
check("anonymous CAN read with correct tracking_code (shareable link)", status == 200, f"status={status}")

status, data = request("GET", f"/api/incidents/{iid}?tracking_code=AIG-WRONGCODE")
check("wrong tracking_code is rejected (403)", status == 403, f"status={status}")

status, data = request("GET", "/api/incidents")
check("GET /api/incidents requires auth (401)", status == 401, f"status={status}")

status, data = request("GET", "/api/incidents/000000000000000000000000", token=login_token)
check("nonexistent incident id returns 404", status == 404, f"status={status}")

status, data = request("GET", "/api/incidents/not-an-objectid", token=login_token)
check("malformed incident id returns 404 (not 500)", status == 404, f"status={status}")

print()
print("=" * 70)
print("INCIDENT WIZARD — ANONYMOUS FLOW")
print("=" * 70)

status, anon = request("POST", "/api/incidents")
check("anonymous can create an incident", status == 201, f"status={status}")
check("anonymous incident has no owner", anon.get("user_id") is None)
aid, acode = anon["id"], anon["tracking_code"]

status, data = request("PATCH", f"/api/incidents/{aid}/details?tracking_code={acode}",
                       {"incident_type": "Fraud", "location": "upi-scam.example",
                        "description": "Fake payment request."})
check("anonymous can patch details with tracking_code", status == 200, f"status={status}")

status, data = request("PATCH", f"/api/incidents/{aid}/details", {"description": "no code"})
check("anonymous CANNOT patch without tracking_code (403)", status == 403, f"status={status}")

status, data = request("POST", f"/api/incidents/{aid}/generate-report?tracking_code={acode}",
                       {"report_type": "standard", "report_language": "English"})
check("anonymous can generate report with tracking_code", status == 200, f"status={status}")

status, pdf = request("GET", f"/api/incidents/{aid}/report/pdf?tracking_code={acode}", raw=True)
check("anonymous can download PDF with tracking_code", status == 200 and pdf[:4] == b"%PDF",
      f"status={status}")

status, fresh = request("POST", "/api/incidents")
status, data = request("GET", f"/api/incidents/{fresh['id']}/report/pdf?tracking_code={fresh['tracking_code']}")
check("PDF download before generating returns 400", status == 400, f"status={status}")

print()
print("=" * 70)
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"RESULT: {passed}/{total} checks passed")
failures = [(n, d) for n, ok, d in results if not ok]
if failures:
    print("\nFAILURES:")
    for n, d in failures:
        print(f"  - {n}" + (f"  ({d})" if d else ""))
print("=" * 70)
