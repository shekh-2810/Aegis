(function () {
  const form = document.getElementById("details-form");
  const description = document.getElementById("description");
  const count = document.getElementById("description-count");
  const message = document.getElementById("details-message");
  const continueBtn = document.getElementById("continue-btn");

  description.addEventListener("input", () => {
    count.textContent = `${description.value.length} / 1000`;
  });

  async function prefill() {
    const session = getIncidentSession();
    if (!session) return;
    try {
      const incident = await fetchCurrentIncident();
      if (!incident) return;
      document.getElementById("incident-type").value = incident.incident_type || "";
      document.getElementById("location").value = incident.location || "";
      document.getElementById("when").value = incident.occurred_at || "";
      description.value = incident.description || "";
      count.textContent = `${description.value.length} / 1000`;
    } catch (err) {
      console.error("Could not load saved incident details:", err);
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    continueBtn.disabled = true;
    message.textContent = "";

    const payload = {
      incident_type: document.getElementById("incident-type").value || null,
      location: document.getElementById("location").value || null,
      occurred_at: document.getElementById("when").value || null,
      description: description.value || null,
    };

    try {
      const session = await ensureIncident();
      await apiFetch(`/api/incidents/${session.id}/details${incidentQuerySuffix()}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      window.location.href = "step-2-additional.html";
    } catch (err) {
      message.textContent = err.message || "Could not save your details. Please try again.";
      continueBtn.disabled = false;
    }
  });

  prefill();
})();
