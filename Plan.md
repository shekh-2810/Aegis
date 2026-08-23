# Aiges — Updated Plan (Post-Supervisor Review)

**For the team — read this before our next sync**

---

## TL;DR

We're pivoting. Instead of *only* a browser extension that warns you when you visit a sketchy site, we're now building a **website that actively goes out, finds cyber fraud/scam activity on its own, detects it, and displays it** — like a live dashboard of "here's what's happening out there right now."

The extension isn't dead — it becomes one *input* into a bigger system instead of being the whole product.

---

## Why the change?

Our supervisor's feedback: a browser extension that only reacts when a user visits a site doesn't feel different enough from "just ask ChatGPT if this site is safe." She wants Aiges to have its own independent value — something that exists and updates *without* a user needing to ask it anything.

So the new pitch is: **Aiges actively hunts for fraud/scam activity across the web and shows it to you**, instead of waiting for you to bring it a URL.

---

## What actually changes

| Old Plan | New Plan |
|---|---|
| Extension checks a site *when user visits it* | Crawler checks sites *on its own, continuously* |
| Detection engine runs on-demand | Detection engine runs on a schedule, at scale |
| Website = report + recovery guidance for users | Website = live dashboard of detected fraud + report/recovery guidance |
| Data source = whatever URL the user is currently on | Data source = URLs/domains the crawler discovers itself |

---

## What stays exactly the same (good news — this is most of our work)

Our **Stage 1 detection engine already works** and doesn't need to be rebuilt:

- `detectionService.js` — combines signals into a risk score
- `urlHeuristics.js` — the 5 local checks (HTTPS, IP-as-domain, subdomain depth, suspicious TLD, brand typosquat)
- Google Safe Browsing + VirusTotal integration
- MongoDB caching layer (`DetectionCache.js`)
- The verdict system (safe / suspicious / malicious / unknown)

**This is the core engine. We're not throwing it away — we're pointing it at a new source of URLs.**

Right now, the engine gets one URL at a time (from the extension, when a user visits a page). In the new plan, the engine gets a *stream* of URLs from our own crawler instead.

---

## What's new — the pieces we have to build

### 1. The Crawler
A background service that goes out and finds candidate URLs/domains to check — instead of waiting for a user to hand us one.

Sources it can pull from (we'll pick a manageable subset, not all of these):
- Newly registered domains (there are public feeds for this)
- Typosquat variants of well-known brands (e.g. `paypa1.com`, `arnaz0n.in`) — we can generate these ourselves using the same Levenshtein logic we already built for the extension
- Domains mentioned in public phishing/scam feed lists
- Links found on pages we've already flagged (basic link-following)

### 2. The "Case" Layer
Right now our system outputs a risk score for a URL. Now we also want to show *what it did* — some human-readable context, not just a number.

For each detected case, we'll try to capture:
- The domain/URL
- What it's impersonating (if it's a brand typosquat)
- Which signals flagged it (GSB / VirusTotal / heuristics)
- Risk score + verdict
- When it was first detected / last seen

### 3. The Public Dashboard (Website Frontend)
A page where anyone can browse recently detected fraud/scam domains — searchable, filterable by risk level, showing the "case" details above. This is the part that makes Aiges feel alive without needing user input, which is exactly what our supervisor wants to see.

### 4. Scheduler / Job Runner
Something that runs the crawler at intervals (e.g. every few hours) instead of on-demand. Keeps the dashboard fresh without us doing it manually.

---

## How this maps to our existing roles

| Role | Old focus | New focus |
|---|---|---|
| Extension Developer | Real-time site warning UI | Same, but now also feeds discovered URLs back into the crawler's queue |
| Backend/API Developer | `/api/detect` endpoint | Same endpoint + new crawler service + scheduler |
| Detection Logic Lead | Risk scoring, heuristics | Same, plus tuning heuristics to work well on batches instead of single URLs |
| Website Frontend Developer | Report + recovery guidance pages | Same, plus the new public dashboard/case-browsing UI |
| Documentation/QA/PM | Docs, testing, review prep | Same, plus documenting the new crawler flow for reviewers |

Nobody's role is being thrown out — everyone's scope just widens slightly in the direction of "the thing we built now runs proactively."

---

## High-level flow (new system)

```
Crawler finds candidate URLs
        ↓
Existing detection engine scores each one
        (GSB + VirusTotal + heuristics — unchanged)
        ↓
Result saved as a "case" in MongoDB
        ↓
Dashboard displays cases (searchable, filterable)
        ↓
Extension still works exactly as before for real-time
   user browsing, AND also feeds new URLs into the crawler
```

---

## What we're keeping tight (scope discipline, as always)

Given how close our next review is, we are **not** trying to build a general-purpose web crawler on day one. MVP target:

1. Crawler generates typosquat candidates for a small fixed list of well-known brands (reuse existing Levenshtein logic)
2. Existing detection engine scores them (already works)
3. Scheduler runs this every few hours
4. Dashboard shows the results in a simple table/card view

Anything beyond that (news-source ingestion, broader crawling, advanced case write-ups) is a stretch goal for later checkpoints, not the MVP.

---

## Questions to raise as a team

- Which brands should our typosquat generator target first? (Start with 5–10 well-known ones)
- Who owns the scheduler/job runner setup?
- Do we reuse the existing MongoDB collection or spin up a new one for "cases" vs raw detection cache?
- What does the dashboard's minimum viable UI look like — just a table is fine for now?

---

*Questions or disagreements with this plan — bring them to our next sync before we start building, not after.*
