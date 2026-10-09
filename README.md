# Aiges

**Cyber fraud detection and incident reporting platform.**

Aiges helps people spot online fraud before it hurts them and know what to do when it already has. It has two parts that work together:

- **Browser extension:** checks the sites you visit in real time and warns you about phishing, scams, and malware.
- **Web portal:** lets victims report incidents, get step-by-step recovery guidance, track the status of their report, and read proactively gathered threat intelligence.

---

## Features

**Detection**
- URL risk scoring that combines Google Safe Browsing, VirusTotal, and local heuristics (HTTPS check, IP-as-domain, subdomain depth, suspicious TLDs, brand typosquatting via edit distance)
- Verdicts: `safe`, `suspicious`, `malicious`, `unknown`
- Per-domain result caching to cut API calls and latency
- Crawler that generates lookalike domains for a list of seed brands and runs them through the detector

**Incident reporting**
- Four-step report wizard: details, additional info, generate, download
- PDF report generation for filing with banks or cybercrime authorities
- Tracking ID and a status page to follow a report after submission

**Portal**
- User authentication
- Dashboard, scan page, recovery guidance, and a threat news feed

---

## Project structure

```
Aiges/
├── main.py                # FastAPI app entry point
├── routers/               # API routes
│   ├── auth.py            #   login / registration
│   ├── detect.py          #   URL detection endpoint
│   └── incidents.py       #   incident submission and tracking
├── detector.py            # Detection logic and risk scoring
├── crawler.py             # Lookalike-domain crawler
├── report_generator.py    # Incident report content
├── pdf_generator.py       # PDF output
├── auth_utils.py          # Auth helpers
├── database.py            # Database connection
├── models.py              # Data models
├── seed_data.py           # Sample data for development
├── create_test_user.py    # Creates a test account
├── test_api_flow.py       # End-to-end API test
├── extension/             # Browser extension (Manifest V3)
├── frontend/              # Static HTML/CSS/JS site
│   ├── assets/{css,js}/
│   └── report/            #   report wizard steps
├── requirements.txt
└── .env.example
```

---

## Getting started

### Prerequisites

- Python 3.10+
- A database connection string (see `.env.example`)
- API keys for Google Safe Browsing and VirusTotal (free tiers work)
- Chrome or any Chromium-based browser for the extension

### 1. Clone and install

```bash
git clone https://github.com/shekh-2810/Aegis.git
cd Aegis
python3 -m venv python-env
source python-env/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Open `.env` and fill in the values. **Never commit `.env`.**

### 3. Run the backend

```bash
uvicorn main:app --reload --port 8000
```

The API will be at `http://localhost:8000`, with interactive docs at `http://localhost:8000/docs`.

### 4. (Optional) Seed data and a test user

```bash
python seed_data.py
python create_test_user.py
```

### 5. Serve the frontend

In a second terminal:

```bash
cd frontend
python -m http.server 5500
```

Open `http://localhost:5500`.

### 6. Load the extension

1. Go to `chrome://extensions`
2. Turn on **Developer mode**
3. Click **Load unpacked** and select the `extension/` folder
4. Pin Aiges and visit any site. The popup shows the verdict, and dangerous pages trigger a warning screen

The extension talks to the backend at `http://localhost:8000`, so keep it running.

---

## API overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/detect` | Check a URL and return a verdict and risk score |
| POST | `/api/incidents` | Submit an incident report and receive a tracking ID |
| GET | `/api/incidents/{id}` | Look up the status of a report |
| POST | `/api/auth/...` | Register and log in |

Full, current request and response schemas are at `/docs` when the server is running.

---

## Testing

With the backend running:

```bash
python test_api_flow.py
```

---

## Roadmap

- LLM-assisted incident report writing
- Larger crawler seed list and wider detection coverage
- Consolidating data stores into a single database
- Renaming the misleading `confidence` field in detection output to `risk_score`

---

## Team

Built as a college project (25BCY) by a five-person student team covering backend/API, detection logic, frontend, extension, and documentation/QA.

---

## Disclaimer

Aiges is an educational project. Its verdicts are heuristic and should not be treated as a guarantee that a site is safe or malicious. If you are a victim of fraud, contact your bank and your local cybercrime authority immediately (in India: **1930** or [cybercrime.gov.in](https://cybercrime.gov.in)).
