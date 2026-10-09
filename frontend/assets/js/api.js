const API_BASE = "http://127.0.0.1:8000";
const TOKEN_KEY = "aiges_token";
const USER_KEY = "aiges_user";

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setSession(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

function getCurrentUser() {
  const raw = localStorage.getItem(USER_KEY);
  return raw ? JSON.parse(raw) : null;
}

async function apiFetch(path, options = {}) {
  const headers = Object.assign({}, options.headers || {});
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const isFormData = options.body instanceof FormData;
  if (!isFormData && options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, Object.assign({}, options, { headers }));
  } catch (networkErr) {
    // fetch() throws (not a normal HTTP error) when the backend can't be
    // reached at all — wrong port, server not running, or this page was
    // opened directly as a file:// URL instead of via a local server.
    if (window.location.protocol === "file:") {
      throw new Error(
        "This page was opened directly as a file. Serve the frontend with " +
        "'python -m http.server' and open it via http://127.0.0.1 instead."
      );
    }
    throw new Error(
      `Can't reach the Aiges backend at ${API_BASE}. Make sure it's running ` +
      `('uvicorn main:app --reload').`
    );
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const data = await response.json();
      if (typeof data.detail === "string") {
        detail = data.detail;
      } else if (Array.isArray(data.detail)) {
        detail = data.detail.map(e => e.msg || "").join(" ");
      }
    } catch (e) {
      // ignore non-JSON error bodies
    }
    throw new Error(detail);
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response;
}
