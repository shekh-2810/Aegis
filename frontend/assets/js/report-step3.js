(function () {
  const optionsContainer = document.getElementById("report-options");
  const continueBtn = document.getElementById("continue-btn");
  const generateMessage = document.getElementById("generate-message");
  let selectedType = "standard";

  function formatDate(value) {
    if (!value) return "Not specified";
    try {
      return new Date(value).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" });
    } catch (e) {
      return value;
    }
  }

  function renderSummary(incident) {
    document.getElementById("summary-type").textContent = incident.incident_type || "Not specified";
    document.getElementById("summary-date").textContent = formatDate(incident.occurred_at);
    document.getElementById("summary-platform").textContent = incident.location || "Not specified";
    document.getElementById("summary-impact").textContent =
      incident.financial_loss === true ? "Financial Loss" : incident.financial_loss === false ? "No financial loss" : "Not specified";
    document.getElementById("summary-description").textContent = incident.description || "Not specified";
    document.getElementById("summary-actions").textContent =
      incident.contacted_platform === true ? "Contacted platform" : incident.contacted_platform === false ? "No action taken yet" : "Not specified";
    document.getElementById("summary-evidence").textContent = `${(incident.evidence_files || []).length} file(s) uploaded`;
    document.getElementById("summary-context").textContent = incident.amount_lost != null ? `Loss around ₹${incident.amount_lost}` : incident.notes || "None provided";
  }

  optionsContainer.addEventListener("click", (event) => {
    const option = event.target.closest(".option");
    if (!option) return;
    optionsContainer.querySelectorAll(".option").forEach((el) => el.classList.remove("is-selected"));
    option.classList.add("is-selected");
    selectedType = option.dataset.reportType;
  });

  continueBtn.addEventListener("click", async () => {
    const session = redirectIfNoIncident();
    if (!session) return;

    continueBtn.disabled = true;
    generateMessage.textContent = "Generating your report...";

    try {
      await apiFetch(`/api/incidents/${session.id}/generate-report${incidentQuerySuffix()}`, {
        method: "POST",
        body: JSON.stringify({ report_type: selectedType, report_language: "English" }),
      });
      window.location.href = "step-4-download.html";
    } catch (err) {
      generateMessage.textContent = err.message || "Could not generate the report. Please try again.";
      continueBtn.disabled = false;
    }
  });

  async function load() {
    const session = redirectIfNoIncident();
    if (!session) return;
    try {
      const incident = await fetchCurrentIncident();
      if (incident) renderSummary(incident);
    } catch (err) {
      console.error("Could not load incident summary:", err);
    }
  }

  load();
})();
