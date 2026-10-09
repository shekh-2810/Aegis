(function () {
  const actions = document.getElementById("header-actions");
  if (!actions) return;

  const user = getCurrentUser();
  if (!user) return;

  // The report wizard pages live one folder deeper (frontend/report/), so
  // links to root-level pages need a "../" prefix there.
  const inSubfolder = window.location.pathname.includes("/report/");
  const dashboardHref = inSubfolder ? "../dashboard.html" : "dashboard.html";

  actions.innerHTML = `
    <a class="btn btn--ghost" href="${dashboardHref}">
      <i class="fa-solid fa-table-list"></i> My Reports
    </a>
    <span class="btn btn--ghost" style="pointer-events:none;">
      <i class="fa-regular fa-user"></i> ${user.name}
    </span>
    <button class="btn btn--primary" id="logout-btn" type="button">Log out</button>
  `;

  document.getElementById("logout-btn").addEventListener("click", () => {
    clearSession();
    window.location.reload();
  });
})();
