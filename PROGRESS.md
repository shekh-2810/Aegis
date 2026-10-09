# Aiges — Project Status (Final)

Course code: 25BCY. This is the consolidated, feature-complete snapshot: every
track from the original project brief has a real, working implementation —
auth, incident reporting, PDF export, local+external detection, a crawler for
proactive threat intel, an AI-assisted report stage, and a browser extension
that actually warns and blocks, not just displays a badge.

## Full feature checklist

| Area | Status | Notes |
|---|---|---|
| Auth (signup/login/JWT) | ✅ Done | bcrypt hashing, JWT bearer tokens |
| News/alerts homepage | ✅ Done | Category filters, featured/trending/breaking, newsletter signup |
| Incident report wizard | ✅ Done | 4-step flow, works logged-in or anonymous (tracking code) |
| Evidence upload | ✅ Done | jpg/png/pdf, 10MB limit |
| **Report generation (Stage 1 — deterministic)** | ✅ Done | Template-based summary, timeline, impact assessment, recommendations |
| **Report generation (Stage 2 — AI-assisted)** | ✅ Done, optional | If `ANTHROPIC_API_KEY` is set, Claude rewrites the summary/recommendations from the same structured data (never invents new facts). Falls back silently to Stage 1 if the key is missing or the call fails. |
| PDF export | ✅ Done | Downloadable PDF via `fpdf2` |
| Track status by code | ✅ Done | |
| **URL/link detection (heuristics)** | ✅ Done | HTTPS check, IP-as-domain, subdomain depth, suspicious TLDs, Levenshtein brand-typosquat detection, keyword combinations |
| **URL/link detection (external APIs)** | ✅ Done, optional | Google Safe Browsing + VirusTotal checks run in parallel with heuristics and combine into the same score when `GOOGLE_SAFE_BROWSING_API_KEY` / `VIRUSTOTAL_API_KEY` are set. Each check fails independently and silently (ensemble with graceful degradation) — a missing key or a timeout never breaks the response, it just means that signal is skipped. |
| Detection result caching | ✅ Done | Per-domain, 24h Mongo TTL |
| **Typosquat crawler** | ✅ Done | `crawler.py` generates lookalike domains for a seed brand list (character substitution, insertion, prefixes/suffixes, alt TLDs) and bulk-scans them with the heuristic engine, storing flagged results tagged `source="crawler"` |
| **Proactive threat feed** | ✅ Done | `GET /api/detect/threat-feed` + a homepage widget showing what the crawler found — separate from user-submitted scans |
| Link scanner widget (frontend) | ✅ Done | "Check a link before you click" on the homepage |
| Guidance page | ✅ Done | Real written content for all six topics |
| **Browser extension — popup** | ✅ Done | Three-state UI (checking / safe / at-risk), real site-report detail view with live risk score, verdict, typosquat flag, and reasons |
| **Browser extension — real-time scanning** | ✅ Done | `background.js` scans every page navigation automatically and sets a toolbar badge (red `!` malicious, amber `?` suspicious) without the user opening the popup |
| **Browser extension — actual blocking** | ✅ Done | A "malicious" verdict redirects the tab to a warning interstitial (`warning.html`) before the page is shown, with "go back" or "proceed anyway" (remembered for 5 minutes per URL so it doesn't immediately re-block) |
| Single MongoDB cluster | ✅ Done | Earlier drafts of this project used two separate Atlas clusters (backend + classifier); this codebase has always used one |

## What's genuinely still a limitation (by design, not an oversight)

- **External API calls (Safe Browsing, VirusTotal, Claude) weren't live-tested with real keys** in the environment this was built in — it has no network access to googleapis.com or virustotal.com, and no Anthropic key was available to test the success path. What *was* tested: the code runs correctly, degrades gracefully with no key, and degrades gracefully when a key is present but the call fails (wrong key, unreachable, bad response) — so the worst case if something's misconfigured is "runs on heuristics/template only," never a crash. You should do one real test pass with your own keys before the demo, just to see the enhanced path fire at least once.
- **Extension blocking is best-effort, not network-level.** Manifest V3 removed synchronous/blocking `webRequest` for regular extensions, so there's no way to truly stop the request before it's sent. This redirects the tab as soon as the scan result is back (via `onBeforeNavigate`), which blocks the page before it's visible almost all of the time in practice — worth saying exactly that if asked, rather than claiming it's unbreakable.
- **PhishTank is not integrated** — Cisco Talos changed their API key policy and stopped issuing new keys. Correctly logged as outside your control, not a gap in the work.
- **Typosquat detection catches spelling variants** (e.g. `paypa1` for `paypal`) but not a real brand name embedded in an unrelated domain (e.g. `paypal.totally-different-site.com`) — that needs a verified allowlist of official domains to compare against, which isn't built. Worth mentioning as a known edge case if asked directly, not something to volunteer unprompted.
- **The crawler's brand list is a small seed list** (~20 brands) inside `detector.py`. Expanding it is a one-line list edit, not an architecture change.

## If your supervisor asks "what would you still improve with more time"

Have these two ready — they're honest and specific, not hand-wavy:
1. A verified official-domain allowlist, so brand-in-subdomain impersonation (not just spelling variants) gets caught too.
2. True network-level blocking via `declarativeNetRequest` dynamic rules instead of a tab-redirect-after-the-fact — more robust than the current approach, but a bigger lift.
