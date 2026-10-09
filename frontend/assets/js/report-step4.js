(function () {
  const actionMessage = document.getElementById("action-message");

  function formatDate(value) {
    if (!value) return "—";
    try {
      return new Date(value).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" });
    } catch (e) {
      return value;
    }
  }

  function trackingUrl(trackingCode) {
    return new URL(`../track-status.html?code=${encodeURIComponent(trackingCode)}`, window.location.href).href;
  }

  async function load() {
    const session = redirectIfNoIncident();
    if (!session) return null;

    const incident = await fetchCurrentIncident();
    if (!incident || !incident.generated_report) {
      window.location.href = "step-3-generate.html";
      return null;
    }

    document.getElementById("paper-ref").innerHTML =
      `Report ID: ${incident.tracking_code}<br>Generated: ${formatDate(incident.generated_report.generated_at)}`;
    document.getElementById("paper-type").textContent = incident.incident_type || "Not specified";
    document.getElementById("paper-date").textContent = formatDate(incident.occurred_at);
    document.getElementById("paper-platform").textContent = incident.location || "Not specified";
    document.getElementById("paper-generated-on").textContent = formatDate(incident.generated_report.generated_at);
    document.getElementById("paper-summary").textContent = incident.generated_report.summary || "";

    return incident;
  }

  const incidentPromise = load();

  document.getElementById("download-pdf-btn").addEventListener("click", async (event) => {
    event.preventDefault();
    const session = getIncidentSession();
    if (!session) return;

    actionMessage.textContent = "Preparing your PDF...";
    try {
      const response = await apiFetch(`/api/incidents/${session.id}/report/pdf${incidentQuerySuffix()}`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `aiges-report-${session.tracking_code}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      actionMessage.textContent = "PDF downloaded.";
    } catch (err) {
      actionMessage.textContent = err.message || "Could not download the PDF.";
    }
  });

  document.getElementById("shareable-link-btn").addEventListener("click", async (event) => {
    event.preventDefault();
    const session = getIncidentSession();
    if (!session) return;

    const url = trackingUrl(session.tracking_code);
    try {
      await navigator.clipboard.writeText(url);
      actionMessage.textContent = "Shareable link copied to clipboard.";
    } catch (err) {
      actionMessage.textContent = `Shareable link: ${url}`;
    }
  });

  document.getElementById("share-email-btn").addEventListener("click", (event) => {
    event.preventDefault();
    const session = getIncidentSession();
    if (!session) return;

    const url = trackingUrl(session.tracking_code);
    const subject = encodeURIComponent(`Aiges Cyber Incident Report — ${session.tracking_code}`);
    const body = encodeURIComponent(`View my incident report status here: ${url}`);
    window.location.href = `mailto:?subject=${subject}&body=${body}`;
  });

  document.getElementById("submit-authorities-btn").addEventListener("click", async (event) => {
    event.preventDefault();
    const session = getIncidentSession();
    if (!session) return;

    actionMessage.textContent = "Submitting...";
    try {
      await apiFetch(`/api/incidents/${session.id}/submit${incidentQuerySuffix()}`, { method: "PATCH" });
      actionMessage.textContent = "Your report has been marked as submitted.";
    } catch (err) {
      actionMessage.textContent = err.message || "Could not submit the report.";
    }
  });
})();
