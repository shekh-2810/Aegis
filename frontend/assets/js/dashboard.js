(function () {
  const listEl = document.getElementById("dash-list");
  const emptyEl = document.getElementById("dash-empty");
  const messageEl = document.getElementById("dash-message");

  const STATUS_LABEL = { draft: "Draft", generated: "Report ready", submitted: "Submitted" };

  function formatDate(value) {
    if (!value) return "—";
    try {
      return new Date(value).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" });
    } catch (e) {
      return value;
    }
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str || "";
    return div.innerHTML;
  }

  function rowTemplate(incident) {
    const status = incident.status || "draft";
    const title = incident.incident_type || "Untitled report";
    return `
      <div class="report-row" data-id="${incident.id}">
        <div class="report-row__top">
          <div>
            <div class="report-row__title">${escapeHtml(title)}
              <span class="status-pill status-pill--${status}">${STATUS_LABEL[status] || status}</span>
            </div>
            <div class="report-row__meta">
              Tracking code: <strong>${incident.tracking_code}</strong>
              &nbsp;&middot;&nbsp; Reported ${formatDate(incident.created_at)}
              ${incident.location ? `&nbsp;&middot;&nbsp; ${escapeHtml(incident.location)}` : ""}
            </div>
          </div>
          <div class="report-row__actions">
            <a class="btn btn--ghost" href="track-status.html?code=${encodeURIComponent(incident.tracking_code)}">
              <i class="fa-regular fa-eye"></i> View
            </a>
            <button type="button" class="btn btn--ghost" data-action="edit">
              <i class="fa-solid fa-pen"></i> Edit
            </button>
            <button type="button" class="btn btn--ghost" data-action="delete" style="color:#DC2626;">
              <i class="fa-solid fa-trash"></i> Delete
            </button>
          </div>
        </div>

        <div class="edit-panel" id="edit-${incident.id}">
          <div class="field">
            <label class="field__label">Incident type</label>
            <select class="select" data-field="incident_type">
              <option value="">Select incident type</option>
              <option ${title === "Phishing" ? "selected" : ""}>Phishing</option>
              <option ${title === "Fraud" ? "selected" : ""}>Fraud</option>
              <option ${title === "Scam" ? "selected" : ""}>Scam</option>
            </select>
          </div>
          <div class="field">
            <label class="field__label">Where did it happen?</label>
            <input class="input" type="text" data-field="location" value="${escapeHtml(incident.location || "")}">
          </div>
          <div class="field">
            <label class="field__label">Description</label>
            <textarea class="input" rows="3" data-field="description" maxlength="1000">${escapeHtml(incident.description || "")}</textarea>
          </div>
          <div class="action-bar">
            <button type="button" class="btn btn--ghost" data-action="cancel-edit">Cancel</button>
            <button type="button" class="btn btn--primary" data-action="save-edit">Save changes</button>
          </div>
        </div>
      </div>
    `;
  }

  async function loadIncidents() {
    messageEl.textContent = "";
    try {
      const data = await apiFetch("/api/incidents");
      const incidents = data.incidents || [];

      if (!incidents.length) {
        emptyEl.style.display = "";
        listEl.innerHTML = "";
        return;
      }

      emptyEl.style.display = "none";
      listEl.innerHTML = incidents.map(rowTemplate).join("");
    } catch (err) {
      messageEl.textContent = err.message || "Could not load your reports.";
    }
  }

  listEl.addEventListener("click", async (event) => {
    const row = event.target.closest(".report-row");
    if (!row) return;
    const incidentId = row.dataset.id;
    const action = event.target.closest("button")?.dataset.action;
    if (!action) return;

    if (action === "edit") {
      document.getElementById(`edit-${incidentId}`).classList.add("is-open");
    }

    if (action === "cancel-edit") {
      document.getElementById(`edit-${incidentId}`).classList.remove("is-open");
    }

    if (action === "save-edit") {
      const panel = document.getElementById(`edit-${incidentId}`);
      const payload = {
        incident_type: panel.querySelector('[data-field="incident_type"]').value || null,
        location: panel.querySelector('[data-field="location"]').value || null,
        description: panel.querySelector('[data-field="description"]').value || null,
      };
      try {
        await apiFetch(`/api/incidents/${incidentId}/details`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
        messageEl.textContent = "Report updated.";
        await loadIncidents();
      } catch (err) {
        messageEl.textContent = err.message || "Could not save changes.";
      }
    }

    if (action === "delete") {
      if (!window.confirm("Delete this report? This cannot be undone.")) return;
      try {
        await apiFetch(`/api/incidents/${incidentId}`, { method: "DELETE" });
        messageEl.textContent = "Report deleted.";
        await loadIncidents();
      } catch (err) {
        messageEl.textContent = err.message || "Could not delete this report.";
      }
    }
  });

  // Dashboard requires login — anonymous tracking-code reports aren't
  // listed here since there's no account to list them against.
  if (!getCurrentUser()) {
    window.location.href = "login.html";
  } else {
    loadIncidents();
  }
})();
