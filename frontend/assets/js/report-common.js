const INCIDENT_KEY = "aiges_incident";

function getIncidentSession() {
  const raw = sessionStorage.getItem(INCIDENT_KEY);
  return raw ? JSON.parse(raw) : null;
}

function setIncidentSession(id, trackingCode) {
  sessionStorage.setItem(INCIDENT_KEY, JSON.stringify({ id, tracking_code: trackingCode }));
}

function incidentQuerySuffix() {
  const session = getIncidentSession();
  if (!session) return "";

  // Always send the tracking code, even when logged in. A report started
  // anonymously has no owner, so if the user signs in part-way through the
  // wizard the owner check cannot match and only the code grants access.
  return `?tracking_code=${encodeURIComponent(session.tracking_code)}`;
}

async function ensureIncident() {
  let session = getIncidentSession();
  if (session) return session;

  const incident = await apiFetch("/api/incidents", { method: "POST" });
  session = { id: incident.id, tracking_code: incident.tracking_code };
  setIncidentSession(session.id, session.tracking_code);
  return session;
}

async function fetchCurrentIncident() {
  const session = getIncidentSession();
  if (!session) return null;
  return apiFetch(`/api/incidents/${session.id}${incidentQuerySuffix()}`);
}

function redirectIfNoIncident() {
  const session = getIncidentSession();
  if (!session) {
    window.location.href = "step-1-details.html";
    return null;
  }
  return session;
}

// Shows the tracking code at the top of every report-wizard page as soon as
// a draft exists, so a user who leaves partway through (not just at the
// final download step) still has it saved/visible somewhere.
function renderTrackingBanner() {
  const session = getIncidentSession();
  const main = document.querySelector("main.page");
  if (!session || !main || document.getElementById("tracking-banner")) return;

  const banner = document.createElement("div");
  banner.id = "tracking-banner";
  banner.style.cssText =
    "display:flex; align-items:center; justify-content:space-between; gap:12px; " +
    "background:var(--brand-tint, #EEF1FA); border:1px solid var(--border, #D7DCEE); " +
    "border-radius:10px; padding:10px 16px; margin-bottom:16px; font-size:14px; flex-wrap:wrap;";
  banner.innerHTML = `
    <span>Your tracking code: <strong style="letter-spacing:0.03em;">${session.tracking_code}</strong>
      — save this to check your report status anytime.</span>
    <button type="button" id="tracking-banner-copy" class="btn btn--ghost" style="padding:4px 12px; font-size:12px;">
      <i class="fa-regular fa-copy"></i> Copy
    </button>
  `;
  main.prepend(banner);

  document.getElementById("tracking-banner-copy").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(session.tracking_code);
      const btn = document.getElementById("tracking-banner-copy");
      btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied';
      setTimeout(() => { btn.innerHTML = '<i class="fa-regular fa-copy"></i> Copy'; }, 1500);
    } catch (e) {
      // clipboard API unavailable — the code is already visible in the banner text
    }
  });
}

document.addEventListener("DOMContentLoaded", renderTrackingBanner);
