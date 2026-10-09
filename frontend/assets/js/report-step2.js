(function () {
  const form = document.getElementById("additional-form");
  const lossSelect = document.getElementById("loss");
  const amountInput = document.getElementById("amount");
  const evidenceInput = document.getElementById("evidence");
  const evidenceList = document.getElementById("evidence-list");
  const evidenceMessage = document.getElementById("evidence-message");
  const contactedSelect = document.getElementById("contacted");
  const responseInput = document.getElementById("response");
  const notesInput = document.getElementById("notes");
  const message = document.getElementById("additional-message");
  const continueBtn = document.getElementById("continue-btn");

  function renderEvidence(files) {
    evidenceList.innerHTML = (files || [])
      .map((f) => `<li><i class="fa-regular fa-file"></i> ${f.original_name}</li>`)
      .join("");
  }

  async function prefill() {
    const session = redirectIfNoIncident();
    if (!session) return;

    try {
      const incident = await fetchCurrentIncident();
      if (!incident) return;
      if (incident.financial_loss === true) lossSelect.value = "Yes";
      else if (incident.financial_loss === false) lossSelect.value = "No";
      if (incident.amount_lost != null) amountInput.value = incident.amount_lost;
      if (incident.contacted_platform === true) contactedSelect.value = "Yes";
      else if (incident.contacted_platform === false) contactedSelect.value = "No";
      responseInput.value = incident.platform_response || "";
      notesInput.value = incident.notes || "";
      renderEvidence(incident.evidence_files);
    } catch (err) {
      console.error("Could not load saved incident:", err);
    }
  }

  evidenceInput.addEventListener("change", async () => {
    const session = getIncidentSession();
    if (!session) return;

    evidenceMessage.textContent = "Uploading...";
    for (const file of evidenceInput.files) {
      const body = new FormData();
      body.append("file", file);
      try {
        const incident = await apiFetch(`/api/incidents/${session.id}/evidence${incidentQuerySuffix()}`, {
          method: "POST",
          body,
        });
        renderEvidence(incident.evidence_files);
      } catch (err) {
        evidenceMessage.textContent = err.message || `Could not upload ${file.name}.`;
        return;
      }
    }
    evidenceMessage.textContent = "Files uploaded.";
    evidenceInput.value = "";
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    continueBtn.disabled = true;
    message.textContent = "";

    const session = redirectIfNoIncident();
    if (!session) return;

    const payload = {
      financial_loss: lossSelect.value === "" ? null : lossSelect.value === "Yes",
      amount_lost: amountInput.value === "" ? null : Number(amountInput.value),
      contacted_platform: contactedSelect.value === "" ? null : contactedSelect.value === "Yes",
      platform_response: responseInput.value || null,
      notes: notesInput.value || null,
    };

    try {
      await apiFetch(`/api/incidents/${session.id}/additional${incidentQuerySuffix()}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      window.location.href = "step-3-generate.html";
    } catch (err) {
      message.textContent = err.message || "Could not save this step. Please try again.";
      continueBtn.disabled = false;
    }
  });

  prefill();
})();
