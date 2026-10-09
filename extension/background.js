// Aiges background service worker.
//
// Two jobs:
//  1. Scan every page the user navigates to and set a toolbar badge
//     (none = safe, amber "?" = suspicious, red "!" = malicious).
//  2. For a "malicious" verdict, redirect the tab to a local warning page
//     before the page finishes loading, instead of just badging it.
//
// Honest limitation: Manifest V3 removed synchronous/blocking webRequest
// for regular extensions, so there is no way to truly stop the network
// request itself. This redirects the tab as soon as the scan result comes
// back (triggered on `onBeforeNavigate`, which fires before the page
// commits), which in practice blocks the page before it's visible most of
// the time — but it is a best-effort redirect, not a network-level block.
//
// MV3 service workers can also be terminated by Chrome when idle, so the
// in-memory caches below are a performance nice-to-have, not a guarantee.

const API_BASE = "http://127.0.0.1:8000";
const ALLOW_ONCE_TTL_MS = 5 * 60 * 1000; // 5 minutes

// tabId -> last detection result (for the popup to read instantly)
const tabResults = new Map();
// url -> timestamp the user chose "proceed anyway" for it
const allowedOnce = new Map();

async function scanUrl(url) {
  const response = await fetch(`${API_BASE}/api/detect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.json();
}

function isScannableUrl(url) {
  return typeof url === "string" && /^https?:\/\//i.test(url);
}

function isAllowedOnce(url) {
  const ts = allowedOnce.get(url);
  if (!ts) return false;
  if (Date.now() - ts > ALLOW_ONCE_TTL_MS) {
    allowedOnce.delete(url);
    return false;
  }
  return true;
}

function updateBadgeForTab(tabId, result) {
  if (!result || result.verdict === "unknown" || result.verdict === "safe") {
    chrome.action.setBadgeText({ text: "", tabId });
    return;
  }
  if (result.verdict === "malicious") {
    chrome.action.setBadgeText({ text: "!", tabId });
    chrome.action.setBadgeBackgroundColor({ color: "#DC2626", tabId });
  } else if (result.verdict === "suspicious") {
    chrome.action.setBadgeText({ text: "?", tabId });
    chrome.action.setBadgeBackgroundColor({ color: "#F59E0B", tabId });
  }
}

function redirectToWarning(tabId, url, reasons) {
  const warningUrl =
    chrome.runtime.getURL("warning.html") +
    `?url=${encodeURIComponent(url)}&reasons=${encodeURIComponent((reasons || []).join("|||"))}`;
  chrome.tabs.update(tabId, { url: warningUrl });
}

async function handleNavigation(tabId, url, { blockIfMalicious }) {
  if (!isScannableUrl(url)) {
    tabResults.delete(tabId);
    chrome.action.setBadgeText({ text: "", tabId });
    return;
  }

  const { protectionOn = true } = await chrome.storage.local.get("protectionOn");
  if (!protectionOn) {
    chrome.action.setBadgeText({ text: "", tabId });
    return;
  }

  try {
    const result = await scanUrl(url);
    tabResults.set(tabId, { ...result, url });
    updateBadgeForTab(tabId, result);

    if (blockIfMalicious && result.verdict === "malicious" && !isAllowedOnce(url)) {
      redirectToWarning(tabId, url, result.reasons);
    }
  } catch (err) {
    // Backend unreachable — clear any stale badge rather than show wrong info.
    tabResults.delete(tabId);
    chrome.action.setBadgeText({ text: "", tabId });
  }
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({ protectionOn: true });
});

// Fires before the page commits — our best chance to redirect away from a
// malicious page before the user sees it.
chrome.webNavigation.onBeforeNavigate.addListener((details) => {
  if (details.frameId !== 0) return;
  handleNavigation(details.tabId, details.url, { blockIfMalicious: true });
});

// Fires once the navigation has committed — a fallback (e.g. for
// history/SPA navigations that don't always fire onBeforeNavigate) and to
// make sure the badge is correct even if onBeforeNavigate was missed.
chrome.webNavigation.onCommitted.addListener((details) => {
  if (details.frameId !== 0) return;
  if (tabResults.get(details.tabId)?.url === details.url) return; // already scanned
  handleNavigation(details.tabId, details.url, { blockIfMalicious: false });
});

chrome.tabs.onRemoved.addListener((tabId) => {
  tabResults.delete(tabId);
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "getCachedResult") {
    const result = tabResults.get(message.tabId) || null;
    sendResponse({ result });
    return true;
  }
  if (message?.type === "allowOnce" && message.url) {
    allowedOnce.set(message.url, Date.now());
    sendResponse({ ok: true });
    return true;
  }
  return true; // keep the message channel open for the async sendResponse
});
