# Aiges — Run Instructions

Aiges has three parts:
1. **Backend API** (FastAPI + MongoDB Atlas) — news/alerts, auth, incident
   reporting with PDF + AI-assisted report generation, and URL/link
   detection (heuristics + optional external threat-intel APIs).
2. **Frontend** (static HTML/CSS/JS) — the website.
3. **Browser extension** (`extension/`) — real-time scanning, a toolbar
   badge, and an actual block/warning page for malicious sites.

---

## 1. Install backend dependencies

```bash
pip install -r requirements.txt
```

## 2. Configure environment variables

```bash
cp .env.example .env
```

Required:
```
MONGO_URI=your_mongodb_atlas_connection_string
JWT_SECRET=change_me_to_a_long_random_value
JWT_EXPIRE_MINUTES=1440
```

Generate a JWT secret if needed:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**Optional** (the app works fully without these — see `.env.example` for
where to get each one):
```
GOOGLE_SAFE_BROWSING_API_KEY=   # adds a live threat-list check to /api/detect
VIRUSTOTAL_API_KEY=             # adds a multi-vendor reputation check to /api/detect
ANTHROPIC_API_KEY=              # polishes incident report text with Claude
```

> `.env` is **not** included in this package — never commit real credentials.

## 3. Seed sample news/alert data (run once)

```bash
python seed_data.py
```

## 4. Start the backend

```bash
uvicorn main:app --reload
```

API live at `http://127.0.0.1:8000`. Docs at `http://127.0.0.1:8000/docs`.
(`GET /` returning "Not Found" is expected — FastAPI doesn't serve a root
page by default.)

## 5. (Optional) Run the threat-intel crawler

```bash
python crawler.py                    # scans the full seed brand list
python crawler.py paypal hdfcbank    # scan just these brands
```

This generates lookalike domains (`paypa1.tk`, `secure-hdfcbank.xyz`, etc.)
for each brand, scans them, and stores anything flagged in MongoDB. Run this
before your demo so the homepage's "Recently flagged lookalike domains"
section and `GET /api/detect/threat-feed` have something to show — it starts
empty otherwise.

## 6. Serve the frontend

In a separate terminal:
```bash
cd frontend
python -m http.server 5500
```
Open `http://127.0.0.1:5500/index.html`.

> Firefox caches aggressively with `python -m http.server`. Hard-reload
> (`Ctrl+Shift+R`) after edits, or keep DevTools open with "Disable Cache" on.

## 7. Run the automated smoke test (optional)

With the backend running:
```bash
python test_api_flow.py
```

## 8. Load the browser extension

1. `chrome://extensions` → enable **Developer mode**
2. **Load unpacked** → select the `extension/` folder
3. The backend must be running — the extension calls `http://127.0.0.1:8000`

What it does now:
- **Auto-scans every page** you navigate to and sets a toolbar badge (red
  `!` = malicious, amber `?` = suspicious, nothing = safe/unknown)
- **Blocks malicious pages** by redirecting to a warning screen before the
  page loads, with "go back" or "proceed anyway" (remembered for 5 minutes)
- Click the icon any time for a full site report (risk score, verdict,
  typosquat flag, reasons)
- The protection toggle in the popup turns auto-scanning off entirely

If you edit anything in `extension/`, go back to `chrome://extensions` and
hit the reload icon on the Aiges card to pick up the change.

---

## Feature map

| Feature | Where |
|---|---|
| Browse news & alerts | Homepage |
| **Check a link for phishing/scam risk** | Homepage scanner widget, or the extension |
| **Real-time browsing protection + blocking** | Browser extension |
| **Proactively discovered lookalike domains** | Homepage "Recently flagged" section, `/api/detect/threat-feed` |
| Sign up / log in | `login.html` |
| Report an incident | "Report Incident" in the nav |
| Track a report | `track-status.html` |
| Download a PDF report | Last step of the report wizard |
| **AI-polished report text** (if `ANTHROPIC_API_KEY` set) | Automatic, part of report generation |
| Safety guidance | `guidance.html` |

### API endpoints

```
GET   /api/homepage
GET   /api/articles?category=...
POST  /api/subscribe

POST  /api/auth/signup
POST  /api/auth/login
GET   /api/auth/me

POST  /api/incidents
GET   /api/incidents
GET   /api/incidents/track?code=...
GET   /api/incidents/{id}
PATCH /api/incidents/{id}/details
PATCH /api/incidents/{id}/additional
POST  /api/incidents/{id}/evidence
DELETE /api/incidents/{id}/evidence/{filename}
POST  /api/incidents/{id}/generate-report   # Stage 1 + optional Stage 2 (AI)
GET   /api/incidents/{id}/report/pdf
PATCH /api/incidents/{id}/submit

POST  /api/detect                    # heuristics + optional Safe Browsing/VirusTotal
GET   /api/detect/history?limit=20   # recent user-submitted scans
GET   /api/detect/threat-feed?limit=20  # crawler-discovered lookalike domains
```

---

## Known limitations

See `PROGRESS.md` for the full, honest list — the short version:
- External APIs (Safe Browsing, VirusTotal, Claude) weren't live-tested with
  real keys in the build environment (no network access to test them there).
  Do one test pass with your own keys before presenting.
- Extension blocking is a best-effort tab redirect, not a true network-level
  block (Manifest V3 limitation, not something we missed).
- Typosquat detection catches spelling variants, not brand names embedded
  in unrelated domains — needs a verified-domain allowlist to go further.
