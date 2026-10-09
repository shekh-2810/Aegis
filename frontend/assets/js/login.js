(function () {
  const form = document.getElementById("auth-form");
  const nameField = document.getElementById("name-field");
  const nameInput = document.getElementById("name");
  const heading = document.getElementById("auth-heading");
  const lede = document.getElementById("auth-lede");
  const submitBtn = document.getElementById("auth-submit");
  const switchText = document.getElementById("auth-switch");
  const toggleLink = document.getElementById("auth-toggle-link");
  const message = document.getElementById("auth-message");
  const passwordToggle = document.getElementById("password-toggle");
  const passwordInput = document.getElementById("password");

  let mode = "login";

  function applyMode() {
    if (mode === "login") {
      nameField.hidden = true;
      nameInput.required = false;
      heading.textContent = "Welcome back";
      lede.textContent = "Log in to your Aiges account to access your reports, guidance and more.";
      submitBtn.textContent = "Log in";
      switchText.innerHTML = 'Don\'t have an account? <a href="#" id="auth-toggle-link">Create one</a>';
    } else {
      nameField.hidden = false;
      nameInput.required = true;
      heading.textContent = "Create your account";
      lede.textContent = "Sign up for Aiges to report incidents, get guidance and track your reports.";
      submitBtn.textContent = "Sign up";
      switchText.innerHTML = 'Already have an account? <a href="#" id="auth-toggle-link">Log in</a>';
    }
    message.textContent = "";
    message.className = "field__hint";
    document.getElementById("auth-toggle-link").addEventListener("click", onToggle);
  }

  function onToggle(event) {
    event.preventDefault();
    mode = mode === "login" ? "signup" : "login";
    applyMode();
  }

  toggleLink.addEventListener("click", onToggle);

  passwordToggle.addEventListener("click", () => {
    const isPassword = passwordInput.type === "password";
    passwordInput.type = isPassword ? "text" : "password";
    passwordToggle.innerHTML = isPassword
      ? '<i class="fa-regular fa-eye-slash"></i>'
      : '<i class="fa-regular fa-eye"></i>';
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    message.className = "field__hint";
    message.textContent = mode === "login" ? "Logging in..." : "Creating your account...";
    submitBtn.disabled = true;

    const email = document.getElementById("email").value.trim();
    const password = passwordInput.value;

    try {
      let result;
      if (mode === "login") {
        result = await apiFetch("/api/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        });
      } else {
        result = await apiFetch("/api/auth/signup", {
          method: "POST",
          body: JSON.stringify({ name: nameInput.value.trim(), email, password }),
        });
      }

      setSession(result.access_token, result.user);
      message.className = "field__hint is-success";
      message.textContent = `Welcome${result.user?.name ? ", " + result.user.name : ""}! Redirecting...`;
      window.location.href = "index.html";
    } catch (err) {
      message.className = "field__hint is-error";
      message.textContent = err.message || "Something went wrong. Please try again.";
      submitBtn.disabled = false;
    }
  });

  applyMode();
})();
