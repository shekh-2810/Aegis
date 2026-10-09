const params = new URLSearchParams(window.location.search);
const blockedUrl = params.get("url") || "";
const reasons = (params.get("reasons") || "").split("|||").filter(Boolean);

document.getElementById("blockedUrl").textContent = blockedUrl || "Unknown URL";
document.getElementById("reasonsList").innerHTML = reasons.length
  ? reasons.map((r) => `<li>${r}</li>`).join("")
  : "<li>Multiple risk signals detected.</li>";

document.getElementById("backBtn").addEventListener("click", () => {
  window.location.href = "chrome://newtab";
});

document.getElementById("proceedBtn").addEventListener("click", () => {
  if (blockedUrl) {
    // Remember the user's choice for this exact URL so we don't
    // immediately re-block it on the very next navigation.
    chrome.runtime.sendMessage({ type: "allowOnce", url: blockedUrl }, () => {
      window.location.href = blockedUrl;
    });
  }
});
