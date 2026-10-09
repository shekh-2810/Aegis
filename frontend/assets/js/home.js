function formatDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" });
  } catch (e) {
    return iso;
  }
}

function renderFeatured(story) {
  if (!story) return;
  document.getElementById("featured-title").textContent = story.title;
  document.getElementById("featured-excerpt").textContent = story.description;
  document.getElementById("featured-meta").textContent = `${formatDate(story.date)} • ${story.category || ""}`;
}

function renderBreaking(items) {
  if (!items || !items.length) return;
  document.getElementById("breaking-text").textContent = items[0].title;
}

function renderTrending(items) {
  const container = document.getElementById("trending-list");
  if (!items || !items.length) return;
  container.innerHTML = items
    .map(
      (item, index) => `
        <a class="trending__card" href="#">
          <span class="trending__rank">${String(index + 1).padStart(2, "0")}</span>
          <h3 class="trending__title">${item.title}</h3>
        </a>`
    )
    .join("");
}

function renderArticles(items) {
  const container = document.getElementById("article-list");
  if (!items) return;
  if (!items.length) {
    container.innerHTML = `<p>No articles found for this category yet.</p>`;
    return;
  }
  container.innerHTML = items
    .map(
      (item) => `
        <a class="article" href="#">
          <span class="tag">${(item.category || "").toUpperCase()}</span>
          <h3 class="article__title">${item.title}</h3>
          <p class="article__excerpt">${item.description || ""}</p>
          <p class="article__meta">${formatDate(item.date)}</p>
        </a>`
    )
    .join("");
}

function renderAlerts(items) {
  const container = document.getElementById("alert-list");
  if (!items || !items.length) return;
  container.innerHTML = items
    .map(
      (item) => `
        <div class="alert-item">
          <i class="fa-solid fa-triangle-exclamation"></i>
          <p>${item.title}</p>
        </div>`
    )
    .join("");
}

async function loadHomepage() {
  try {
    const data = await apiFetch("/api/homepage");
    renderBreaking(data.breaking_news);
    renderFeatured(data.featured_story);
    renderTrending(data.trending);
    renderArticles(data.latest_articles);
    renderAlerts(data.alerts);
  } catch (err) {
    console.error("Failed to load homepage data:", err);
  }
}

async function loadArticlesByCategory(category) {
  document.getElementById("feed-heading").textContent = category === "All" ? "Latest Articles" : category;
  try {
    const data = await apiFetch(`/api/articles?category=${encodeURIComponent(category)}`);
    renderArticles(data.articles);
  } catch (err) {
    console.error("Failed to load articles:", err);
  }
}

function setupCategoryNav() {
  const nav = document.getElementById("category-nav");
  if (!nav) return;
  nav.addEventListener("click", (event) => {
    const link = event.target.closest("[data-category]");
    if (!link) return;
    event.preventDefault();

    nav.querySelectorAll(".categories__item").forEach((el) => el.classList.remove("is-active"));
    link.classList.add("is-active");

    loadArticlesByCategory(link.dataset.category);
  });
}

function setupNewsletterForm() {
  const form = document.getElementById("newsletter-form");
  const message = document.getElementById("newsletter-message");
  if (!form) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = document.getElementById("newsletter-email").value.trim();
    if (!email) return;

    try {
      const result = await apiFetch("/api/subscribe", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      message.textContent = result.message;
      form.reset();
    } catch (err) {
      message.textContent = err.message || "Something went wrong. Please try again.";
    }
  });
}

async function loadThreatFeed() {
  const section = document.getElementById("threat-feed-section");
  const list = document.getElementById("threat-feed-list");
  if (!section || !list) return;

  try {
    const data = await apiFetch("/api/detect/threat-feed?limit=8");
    const results = data.results || [];
    if (!results.length) return; // crawler hasn't been run yet — stay hidden

    list.innerHTML = results
      .map((r) => {
        const isHigh = r.verdict === "malicious";
        const color = isHigh ? "#DC2626" : "#F59E0B";
        return `
          <li style="padding:10px 0; border-bottom:1px solid var(--border);">
            <strong style="color:${color}; text-transform:uppercase; font-size:12px;">${r.verdict}</strong>
            &nbsp;<code>${r.domain}</code>
            <span style="color:var(--text-muted); font-size:13px;"> — mimicking "${r.target_brand || "a known brand"}" (risk ${r.risk_score}/100)</span>
          </li>`;
      })
      .join("");
    section.style.display = "";
  } catch (err) {
    console.error("Failed to load threat feed:", err);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadHomepage();
  loadThreatFeed();
  setupCategoryNav();
  setupNewsletterForm();
});
