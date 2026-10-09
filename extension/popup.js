// ---------------------------------------------------------------
// Aiges popup logic — wired to the real backend at /api/detect.
// Falls back to the background worker's cached result when
// available (instant), otherwise fetches fresh.
// ---------------------------------------------------------------

const API_BASE = "http://127.0.0.1:8000";

let lastResult = null;
let currentTabId = null;

function showPage(name) {
  document.querySelectorAll(".page").forEach((p) => p.classList.remove("active"));
  const page = document.querySelector(`[data-page="${name}"]`);
  if (page) page.classList.add("active");
}

function getDomain(url) {
  try {
    return new URL(url).hostname;
  } catch {
    return "unknown site";
  }
}

async function getCachedResultFromBackground(tabId) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ type: "getCachedResult", tabId }, (response) => {
      resolve(response?.result || null);
    });
  });
}

async function scanUrl(url) {
  const response = await fetch(`${API_BASE}/api/detect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.json();
}

function formatDate(iso) {
  if (!iso) return "Not available";
  try {
    return new Date(iso).toLocaleString(undefined, {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function renderSafePage(result, domain) {
  document.getElementById("currentDomainSafe").textContent = domain;

  const title = document.getElementById("safeTitle");
  const sub = document.getElementById("safeSub");
  const threatLine = document.getElementById("safeThreatLine");

  if (result.verdict === "unknown") {
    title.textContent = "Couldn't verify this site";
    sub.textContent = "Aiges couldn't parse a domain to check for this page.";
    threatLine.innerHTML = "Not checked";
  } else {
    title.textContent = "You're protected";
    sub.textContent = "This website looks safe.";
    threatLine.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6L9 17l-5-5"/></svg>
      No threats detected
    `;
  }
  showPage("safe");
}

function renderRiskPage(result, domain) {
  const title = document.getElementById("riskTitle");
  const sub = document.getElementById("riskSub");
  const alertRows = document.getElementById("alertRows");

  const isMalicious = result.verdict === "malicious";
  title.textContent = isMalicious ? "Warning: risky site" : "Caution: suspicious site";
  sub.textContent = isMalicious
    ? "This site shows strong signs of phishing or fraud. Proceeding is not recommended."
    : "This site shows some warning signs. Double-check before entering any details.";

  const reasons = result.reasons && result.reasons.length
    ? result.reasons
    : ["Multiple risk signals detected."];

  alertRows.innerHTML = reasons
    .slice(0, 4)
    .map(
      (reason) => `
        <div class="alert-row">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.3 3.9L1.8 18a2 2 0 001.7 3h17a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z"/><path d="M12 9v4M12 17h.01"/></svg>
          <span>${reason}</span>
        </div>`
    )
    .join("");

  showPage("risk");
}

function renderInsightPage(result, domain) {
  document.getElementById("currentDomainInsight").textContent = domain;

  const score = result.risk_score ?? 0;
  const isHigh = result.verdict === "malicious";
  const isMedium = result.verdict === "suspicious";

  document.getElementById("insightBadge").textContent = isHigh
    ? "High risk"
    : isMedium
    ? "Medium risk"
    : "Low risk";
  document.getElementById("insightBadge").className = isHigh || isMedium ? "badge-risk" : "badge-risk";
  document.getElementById("insightBadge").style.background = isHigh
    ? ""
    : isMedium
    ? "#FFF6DF"
    : "#E9FBF0";
  document.getElementById("insightBadge").style.color = isHigh ? "" : isMedium ? "#92400E" : "#159A4A";

  document.getElementById("insightBanner").textContent = isHigh
    ? "This site has been flagged as risky by Aiges's detection engine."
    : isMedium
    ? "This site shows some warning signs worth a closer look."
    : "No significant risk signals were found for this site.";

  document.getElementById("detailRiskScore").textContent = `${score}/100`;
  document.getElementById("detailVerdict").textContent =
    result.verdict.charAt(0).toUpperCase() + result.verdict.slice(1);
  document.getElementById("detailTyposquat").textContent = result.is_typosquat_suspect
    ? "Yes"
    : "No";
  document.getElementById("detailScanned").textContent = formatDate(result.checked_at);
  document.getElementById("detailCached").textContent = result.cached
    ? "Cached (checked within 24h)"
    : "Fresh scan";

  const reasonsList = document.getElementById("detailReasons");
  reasonsList.innerHTML = (result.reasons || [])
    .map((reason) => `<li>${reason}</li>`)
    .join("");
}

function setProtectionUI(on) {
  const toggle = document.getElementById("protectionToggle");
  const label = document.getElementById("protectionState");
  toggle.classList.toggle("on", on);
  toggle.setAttribute("aria-pressed", String(on));
  label.textContent = on ? "ON" : "OFF";
}

async function renderResult(result, url) {
  lastResult = result;
  const domain = result.domain || getDomain(url);

  if (result.verdict === "malicious" || result.verdict === "suspicious") {
    renderRiskPage(result, domain);
  } else {
    renderSafePage(result, domain);
  }
  renderInsightPage(result, domain);
}

async function runCheck() {
  showPage("checking");

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const url = tab?.url || "";
  currentTabId = tab?.id ?? null;

  if (!/^https?:\/\//i.test(url)) {
    // Browser-internal pages (chrome://, about:, etc.) can't be scanned.
    document.getElementById("currentDomainSafe").textContent = "this page";
    document.getElementById("safeTitle").textContent = "Nothing to check here";
    document.getElementById("safeSub").textContent = "Aiges only checks http(s) pages.";
    document.getElementById("safeThreatLine").innerHTML = "Not applicable";
    showPage("safe");
    return;
  }

  try {
    let result = currentTabId != null ? await getCachedResultFromBackground(currentTabId) : null;
    if (!result) {
      result = await scanUrl(url);
    }
    await renderResult(result, url);
  } catch (err) {
    showPage("offline");
  }
}

async function init() {
  const { protectionOn = true } = await chrome.storage.local.get("protectionOn");
  setProtectionUI(protectionOn);
  await runCheck();
}

document.addEventListener("click", (event) => {
  if (event.target.closest("#protectionToggle")) {
    (async () => {
      const { protectionOn = true } = await chrome.storage.local.get("protectionOn");
      const next = !protectionOn;
      await chrome.storage.local.set({ protectionOn: next });
      setProtectionUI(next);
    })();
  }

  if (event.target.closest("#viewReportBtn")) {
    showPage("insight");
  }

  if (event.target.closest("#closeReportBtn")) {
    showPage(lastResult && (lastResult.verdict === "malicious" || lastResult.verdict === "suspicious") ? "risk" : "safe");
  }

  if (event.target.closest("#goBackBtn")) {
    (async () => {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab?.id != null) chrome.tabs.update(tab.id, { url: "chrome://newtab" });
      window.close();
    })();
  }

  if (event.target.closest("#proceedBtn")) {
    window.close();
  }

  if (event.target.closest("#settingsBtn")) {
    chrome.runtime.openOptionsPage?.();
  }

  if (event.target.closest("#retryBtn")) {
    runCheck();
  }
});

init();
