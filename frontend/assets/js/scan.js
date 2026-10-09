const VERDICT_ICONS = {
  safe: "fa-solid fa-circle-check",
  suspicious: "fa-solid fa-triangle-exclamation",
  malicious: "fa-solid fa-circle-xmark",
  unknown: "fa-solid fa-circle-question",
};

const VERDICT_LABELS = {
  safe: "Looks safe",
  suspicious: "Suspicious",
  malicious: "Likely malicious",
  unknown: "Could not check",
};

function renderScanResult(data) {
  const box = document.getElementById("scanner-result");
  if (!box) return;

  const verdict = data.verdict || "unknown";
  box.className = `scanner__result is-visible scanner__result--${verdict}`;

  const icon = VERDICT_ICONS[verdict] || VERDICT_ICONS.unknown;
  const label = VERDICT_LABELS[verdict] || "Unknown";
  const reasons = (data.reasons || [])
    .map((reason) => `<li>${reason}</li>`)
    .join("");

  box.innerHTML = `
    <p class="scanner__verdict"><i class="${icon}"></i> ${label}</p>
    <p class="scanner__score">
      Risk score: ${data.risk_score ?? 0}/100
      ${data.domain ? ` &bull; Domain: ${data.domain}` : ""}
      ${data.cached ? " &bull; (cached result)" : ""}
    </p>
    <ul class="scanner__reasons">${reasons}</ul>
  `;
}

function renderScanError(message) {
  const box = document.getElementById("scanner-result");
  if (!box) return;
  box.className = "scanner__result is-visible scanner__result--unknown";
  box.innerHTML = `<p class="scanner__error">${message}</p>`;
}

function setupScanner() {
  const form = document.getElementById("scanner-form");
  if (!form) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = document.getElementById("scanner-input");
    const button = form.querySelector("button[type='submit']");
    const url = input.value.trim();
    if (!url) return;

    const originalLabel = button.innerHTML;
    button.disabled = true;
    button.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Checking...`;

    try {
      const data = await apiFetch("/api/detect", {
        method: "POST",
        body: JSON.stringify({ url }),
      });
      renderScanResult(data);
    } catch (err) {
      renderScanError(err.message || "Could not check this link. Please try again.");
    } finally {
      button.disabled = false;
      button.innerHTML = originalLabel;
    }
  });
}

document.addEventListener("DOMContentLoaded", setupScanner);
