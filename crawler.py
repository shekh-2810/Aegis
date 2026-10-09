"""
Aiges typosquat crawler.

Proactively generates plausible lookalike domains for a seed list of brands
(character substitution, insertion, hyphenation, alternate TLDs) and runs
each candidate through the same heuristic detector used by `/api/detect`.
Anything that comes back suspicious/malicious is stored in the `detections`
collection tagged with source="crawler", so it shows up in
`GET /api/detect/history` and can be surfaced as proactive threat intel on
the homepage/alerts feed — separate from on-demand user scans.

This intentionally reuses `score_url()` (the heuristics-only, synchronous
path) rather than the full external-API ensemble: a single run generates
hundreds of candidate domains, and burning Google Safe Browsing / VirusTotal
rate limits on every one of them isn't a good trade for a routine background
job. If you want the crawler to also use the external APIs, swap in
`score_url_async()` and run it in batches with a delay between them.

Usage:
    python crawler.py                  # scan the full default brand list
    python crawler.py paypal hdfcbank  # scan just these brands
"""

import sys
from datetime import datetime, timezone

from database import detections_collection
from detector import KNOWN_BRANDS, score_url

# Common typosquat techniques, applied to each brand name.
SUBSTITUTIONS = {
    "o": ["0"], "i": ["1", "l"], "l": ["1", "i"], "e": ["3"],
    "a": ["4", "@"], "s": ["5", "$"],
}
ALT_TLDS = ["com", "net", "info", "xyz", "top", "tk", "online", "site"]
PREFIXES = ["secure-", "login-", "verify-", "my-", "www-"]
SUFFIXES = ["-login", "-verify", "-secure", "-support", "-account"]


def _character_substitutions(brand: str):
    candidates = set()
    for i, ch in enumerate(brand):
        for replacement in SUBSTITUTIONS.get(ch, []):
            candidates.add(brand[:i] + replacement + brand[i + 1:])
    return candidates


def _generate_candidates(brand: str):
    """Yield plausible lookalike domains for a single brand."""
    candidates = set()

    candidates |= _character_substitutions(brand)
    candidates |= {f"{p}{brand}" for p in PREFIXES}
    candidates |= {f"{brand}{s}" for s in SUFFIXES}
    # Simple adjacent-letter doubling, e.g. "paypal" -> "payypal"
    for i in range(1, len(brand)):
        candidates.add(brand[:i] + brand[i] + brand[i:])

    domains = set()
    for name in candidates:
        for tld in ALT_TLDS:
            domains.add(f"{name}.{tld}")
    return domains


def run_crawl(brands=None, verbose=True):
    """Scan generated candidate domains for the given brands (default: all
    known brands). Stores only flagged (non-"safe") results. Returns the
    list of flagged results.
    """
    brands = brands or KNOWN_BRANDS
    flagged = []
    scanned = 0

    for brand in brands:
        for domain in _generate_candidates(brand):
            scanned += 1
            result = score_url(f"https://{domain}")
            if result["verdict"] == "safe":
                continue

            record = {
                **result,
                "checked_at": datetime.now(timezone.utc),
                "source": "crawler",
                "target_brand": brand,
            }
            detections_collection.update_one(
                {"domain": result["domain"]},
                {"$set": record},
                upsert=True,
            )
            flagged.append(record)
            if verbose:
                print(f"  [{result['verdict'].upper()}] {domain}  (score {result['risk_score']}, brand: {brand})")

    if verbose:
        print(f"\nScanned {scanned} candidate domains across {len(brands)} brand(s).")
        print(f"Flagged {len(flagged)} as suspicious/malicious and cached them.")

    return flagged


if __name__ == "__main__":
    target_brands = sys.argv[1:] or None
    if target_brands:
        unknown = [b for b in target_brands if b not in KNOWN_BRANDS]
        if unknown:
            print(f"Note: {unknown} aren't in detector.KNOWN_BRANDS — add them there first for typosquat matching to work.")
    run_crawl(target_brands)
