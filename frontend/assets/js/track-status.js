(function () {
  const form = document.getElementById("track-form");
  const input = document.getElementById("tracking-code");
  const message = document.getElementById("track-message");
  const resultBox = document.getElementById("track-result");

  const STATUS_LABELS = {
    draft: "In progress",
    generated: "Report generated",
    submitted: "Submitted",
  };

  function formatDate(value) {
    if (!value) return "—";
    try {
      return new Date(value).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" });
    } catch (e) {
      return value;
    }
  }

  function renderResult(incident) {
    document.getElementById("result-status").textContent = STATUS_LABELS[incident.status] || incident.status;
    document.getElementById("result-type").textContent = incident.incident_type || "Not specified";
    document.getElementById("result-created").textContent = formatDate(incident.created_at);
    document.getElementById("result-location").textContent = incident.location || "Not specified";
    resultBox.hidden = false;
  }

  async function trackByCode(code) {
    message.textContent = "Looking up your report...";
    resultBox.hidden = true;
    try {
      const incident = await apiFetch(`/api/incidents/track?code=${encodeURIComponent(code)}`);
      message.textContent = "";
      renderResult(incident);
    } catch (err) {
      message.textContent = err.message || "No report found for that tracking code.";
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const code = input.value.trim();
    if (code) trackByCode(code);
  });

  async function loadMyReports() {
    const user = getCurrentUser();
    if (!user) return;

    try {
      const data = await apiFetch("/api/incidents");
      if (!data.incidents.length) return;

      const section = document.getElementById("my-reports-section");
      const list = document.getElementById("my-reports-list");
      section.hidden = false;
      list.innerHTML = data.incidents
        .map(
          (incident) => `
            <div class="alert-item">
              <i class="fa-solid fa-file-lines"></i>
              <p>
                <strong>${incident.tracking_code}</strong> — ${incident.incident_type || "Untitled"} —
                ${STATUS_LABELS[incident.status] || incident.status}
              </p>
            </div>`
        )
        .join("");
    } catch (err) {
      console.error("Could not load your reports:", err);
    }
  }

  const params = new URLSearchParams(window.location.search);
  const prefillCode = params.get("code");
  if (prefillCode) {
    input.value = prefillCode;
    trackByCode(prefillCode);
  }

  loadMyReports();
})();
