"""
Aiges detection engine.

Given a URL, this module produces a risk score (0-100) and a verdict
(safe / suspicious / malicious / unknown) by combining:

  1. Local heuristics (always run, no network needed):
     - HTTPS presence
     - IP address used instead of a domain name
     - Excessive subdomain depth
     - Suspicious / commonly-abused TLDs
     - Brand typosquatting (edit-distance against a known brand list)
     - Suspicious keywords in the URL (e.g. "login", "verify") combined
       with another risk signal

  2. Optional external threat-intel signals (only run if the corresponding
     API key is set in the environment):
     - Google Safe Browsing (GOOGLE_SAFE_BROWSING_API_KEY)
     - VirusTotal (VIRUSTOTAL_API_KEY)

External signals are combined with the heuristic score using the same
"ensemble aggregation with graceful degradation" approach used elsewhere in
this project: each external check runs independently, a failed/missing/
timed-out check is simply skipped (not treated as an error), and whatever
signals *did* respond are weighted together. This means the detector always
returns a usable verdict — it's just more confident when the API keys are
configured than when it's running on heuristics alone.

`score_url_async()` is the full pipeline (heuristics + external APIs) and is
what the `/api/detect` endpoint uses. `score_url()` is the heuristics-only,
synchronous version — used by the crawler for fast bulk scanning without
burning external API rate limits on hundreds of candidate domains.
"""

import asyncio
import ipaddress
import os
import re
from urllib.parse import urlparse

import httpx

# A small seed list of commonly-impersonated brands. In production this
# would be expanded / loaded from the crawler's seed list.
KNOWN_BRANDS = [
    "google", "facebook", "amazon", "paypal", "apple", "microsoft",
    "netflix", "instagram", "whatsapp", "twitter", "linkedin", "flipkart",
    "sbi", "hdfcbank", "icicibank", "axisbank", "paytm", "phonepe", "upi",
    "airtel", "jio", "irctc",
]

SUSPICIOUS_TLDS = {
    "tk", "ml", "ga", "cf", "gq", "xyz", "top", "work", "click", "link",
    "loan", "win", "review", "country", "kim", "gdn", "biz",
}

SUSPICIOUS_KEYWORDS = [
    "login", "verify", "secure", "account", "update", "confirm",
    "signin", "bank", "otp", "reward", "gift", "prize", "free",
]


def _levenshtein(a: str, b: str) -> int:
    """Plain-Python edit distance (no external dependency needed)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    previous_row = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current_row = [i]
        for j, cb in enumerate(b, start=1):
            insert_cost = current_row[j - 1] + 1
            delete_cost = previous_row[j] + 1
            replace_cost = previous_row[j - 1] + (ca != cb)
            current_row.append(min(insert_cost, delete_cost, replace_cost))
        previous_row = current_row
    return previous_row[-1]


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _registrable_root(domain: str) -> str:
    """Best-effort extraction of the 'brand-looking' label from a domain.

    Not a full public-suffix-list implementation - good enough for a
    heuristic MVP (e.g. "secure-login.paypal-verify.com" -> "paypal-verify").
    """
    parts = domain.split(".")
    if len(parts) >= 2:
        return parts[-2]
    return domain


def _closest_brand(label: str):
    """Return (brand, distance) for the closest known brand to `label`.

    Checks the whole label plus each hyphen/digit-separated token inside it,
    so "paypa1-secure-login" is compared against "paypal" as well as the
    label as a whole, not just an exact-length match.
    """
    tokens = {label.lower()} | set(re.split(r"[^a-z]+", label.lower()))
    tokens.discard("")

    best_brand, best_distance = None, None
    for brand in KNOWN_BRANDS:
        for token in tokens:
            distance = _levenshtein(token, brand)
            if best_distance is None or distance < best_distance:
                best_brand, best_distance = brand, distance
    return best_brand, best_distance


def _verdict_for_score(score: int) -> str:
    if score >= 60:
        return "malicious"
    if score >= 30:
        return "suspicious"
    return "safe"


def score_url(raw_url: str) -> dict:
    """Heuristics-only scan (no network calls). Synchronous and fast —
    used by the crawler for bulk scanning, and as the base signal inside
    `score_url_async()`.

    Returns a dict with: url, domain, verdict, risk_score, reasons,
    is_typosquat_suspect.
    """
    url = raw_url.strip()
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        url = "http://" + url

    parsed = urlparse(url)
    domain = (parsed.hostname or "").lower()

    if not domain:
        return {
            "url": raw_url,
            "domain": None,
            "verdict": "unknown",
            "risk_score": 0,
            "reasons": ["Could not parse a valid domain from the input."],
            "is_typosquat_suspect": False,
        }

    reasons = []
    score = 0

    # 1. HTTPS check
    if parsed.scheme != "https":
        score += 15
        reasons.append("Site does not use HTTPS.")

    # 2. IP address instead of domain name
    if _is_ip(domain):
        score += 25
        reasons.append("URL uses a raw IP address instead of a domain name.")

    # 3. Subdomain depth (not meaningful for raw IPs)
    if not _is_ip(domain):
        label_count = domain.count(".")
        if label_count >= 3:
            score += 15
            reasons.append("Domain has an unusually deep subdomain chain.")

    # 4. Suspicious TLD
    tld = domain.rsplit(".", 1)[-1] if "." in domain else ""
    if tld in SUSPICIOUS_TLDS:
        score += 20
        reasons.append(f"Uses a TLD commonly abused for scams (.{tld}).")

    # 5. Brand typosquat check
    is_typosquat_suspect = False
    if not _is_ip(domain):
        root_label = _registrable_root(domain)
        brand, distance = _closest_brand(root_label)
        if brand and 0 < distance <= 2 and root_label.lower() != brand:
            is_typosquat_suspect = True
            score += 30
            reasons.append(
                f"Domain closely resembles the brand '{brand}' "
                f"(edit distance {distance}) but is not an exact match."
            )

    # 6. Suspicious keywords combined with a non-root domain
    full_url_lower = url.lower()
    keyword_hits = [kw for kw in SUSPICIOUS_KEYWORDS if kw in full_url_lower]
    if keyword_hits and (is_typosquat_suspect or tld in SUSPICIOUS_TLDS):
        score += 10
        reasons.append(
            "Contains sensitive keywords (" + ", ".join(keyword_hits[:3]) + ") "
            "alongside other risk signals."
        )

    score = min(score, 100)
    verdict = _verdict_for_score(score)

    if not reasons:
        reasons.append("No known risk indicators found.")

    return {
        "url": raw_url,
        "domain": domain,
        "verdict": verdict,
        "risk_score": score,
        "reasons": reasons,
        "is_typosquat_suspect": is_typosquat_suspect,
    }


# --------------------------------------------------------------------------
# Optional external threat-intel signals.
#
# Each function below returns None if its API key isn't set, the request
# fails, or it times out — callers treat None as "no opinion", never as an
# error, which is what makes the ensemble degrade gracefully.
# --------------------------------------------------------------------------

GOOGLE_SAFE_BROWSING_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
VIRUSTOTAL_URL = "https://www.virustotal.com/api/v3/urls"
EXTERNAL_TIMEOUT_SECONDS = 4.0


async def _check_google_safe_browsing(client: httpx.AsyncClient, url: str):
    api_key = os.environ.get("GOOGLE_SAFE_BROWSING_API_KEY")
    if not api_key:
        return None

    body = {
        "client": {"clientId": "aiges", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes": [
                "MALWARE", "SOCIAL_ENGINEERING",
                "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION",
            ],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}],
        },
    }
    try:
        response = await client.post(
            GOOGLE_SAFE_BROWSING_URL,
            params={"key": api_key},
            json=body,
            timeout=EXTERNAL_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        matches = data.get("matches", [])
        if matches:
            threat_types = sorted({m.get("threatType", "THREAT") for m in matches})
            return {
                "source": "Google Safe Browsing",
                "score": 50,
                "reason": f"Google Safe Browsing flagged this URL ({', '.join(threat_types)}).",
            }
        return {"source": "Google Safe Browsing", "score": 0, "reason": None}
    except Exception:
        return None


async def _check_virustotal(client: httpx.AsyncClient, url: str):
    api_key = os.environ.get("VIRUSTOTAL_API_KEY")
    if not api_key:
        return None

    try:
        # VirusTotal's v3 API identifies a URL by the base64 (unpadded) of
        # the URL string itself.
        import base64
        url_id = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")

        response = await client.get(
            f"{VIRUSTOTAL_URL}/{url_id}",
            headers={"x-apikey": api_key},
            timeout=EXTERNAL_TIMEOUT_SECONDS,
        )
        if response.status_code == 404:
            # VirusTotal has never seen this URL before — not a risk signal
            # either way, just unknown to them.
            return {"source": "VirusTotal", "score": 0, "reason": None}
        response.raise_for_status()
        data = response.json()
        stats = (
            data.get("data", {})
            .get("attributes", {})
            .get("last_analysis_stats", {})
        )
        malicious = stats.get("malicious", 0)
        suspicious = stats.get("suspicious", 0)
        if malicious > 0:
            return {
                "source": "VirusTotal",
                "score": 50,
                "reason": f"VirusTotal: {malicious} security vendor(s) flagged this URL as malicious.",
            }
        if suspicious > 0:
            return {
                "source": "VirusTotal",
                "score": 25,
                "reason": f"VirusTotal: {suspicious} security vendor(s) flagged this URL as suspicious.",
            }
        return {"source": "VirusTotal", "score": 0, "reason": None}
    except Exception:
        return None


async def score_url_async(raw_url: str) -> dict:
    """Full ensemble pipeline: local heuristics + optional external APIs.

    If neither GOOGLE_SAFE_BROWSING_API_KEY nor VIRUSTOTAL_API_KEY is set,
    this is equivalent to `score_url()` — the external calls are simply
    skipped. This is what `/api/detect` calls.
    """
    base = score_url(raw_url)
    if base["domain"] is None:
        return base

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            _check_google_safe_browsing(client, base["url"]),
            _check_virustotal(client, base["url"]),
            return_exceptions=True,
        )

    external_score = 0
    for result in results:
        if not result or isinstance(result, Exception):
            continue
        external_score += result["score"]
        if result["reason"]:
            base["reasons"].append(result["reason"])

    if external_score:
        base["risk_score"] = min(base["risk_score"] + external_score, 100)
        base["verdict"] = _verdict_for_score(base["risk_score"])

    return base
