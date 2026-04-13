const USER_STORAGE_KEY = "restock-console-session";
const CONFIG_PATH = "../../app_config.yml";

const state = {
  config: null,
  session: loadStoredSession(),
  challenge: null,
  selectedUserItemId: "",
  selectedAdminItemId: "",
  products: [],
};

const authScreen = document.getElementById("authScreen");
const userScreen = document.getElementById("userScreen");
const adminScreen = document.getElementById("adminScreen");

const loginView = document.getElementById("loginView");
const signupView = document.getElementById("signupView");
const confirmView = document.getElementById("confirmView");

const loginEmail = document.getElementById("loginEmail");
const loginPassword = document.getElementById("loginPassword");
const signInBtn = document.getElementById("signInBtn");
const goSignUpBtn = document.getElementById("goSignUpBtn");
const authOutput = document.getElementById("authOutput");
const loginChallengeBlock = document.getElementById("loginChallengeBlock");
const loginNewPassword = document.getElementById("loginNewPassword");
const loginChallengeBtn = document.getElementById("loginChallengeBtn");

const signupEmail = document.getElementById("signupEmail");
const signupPassword = document.getElementById("signupPassword");
const signUpBtn = document.getElementById("signUpBtn");
const backToSignInBtn = document.getElementById("backToSignInBtn");
const signupOutput = document.getElementById("signupOutput");

const confirmEmail = document.getElementById("confirmEmail");
const confirmCode = document.getElementById("confirmCode");
const confirmBtn = document.getElementById("confirmBtn");
const confirmBackBtn = document.getElementById("confirmBackBtn");
const confirmOutput = document.getElementById("confirmOutput");

const apiBaseInput = document.getElementById("apiBase");
const adminApiBaseMirror = document.getElementById("adminApiBaseMirror");
const userRefreshBtn = document.getElementById("userRefreshBtn");
const adminRefreshBtn = document.getElementById("adminRefreshBtn");
const heroStatus = document.getElementById("heroStatus");

const userSummary = document.getElementById("userSummary");
const userProductsGrid = document.getElementById("userProductsGrid");
const userSelectedItemInput = document.getElementById("userSelectedItemInput");
const userSubscribeBtn = document.getElementById("userSubscribeBtn");
const userActionMessage = document.getElementById("userActionMessage");
const logoutBtn = document.getElementById("logoutBtn");

const adminSummary = document.getElementById("adminSummary");
const adminProductsGrid = document.getElementById("adminProductsGrid");
const adminSelectedItemInput = document.getElementById("adminSelectedItemInput");
const adminRestockCount = document.getElementById("adminRestockCount");
const adminRestockBtn = document.getElementById("adminRestockBtn");
const adminActionMessage = document.getElementById("adminActionMessage");
const adminNewItemId = document.getElementById("adminNewItemId");
const adminNewItemStock = document.getElementById("adminNewItemStock");
const adminCreateItemBtn = document.getElementById("adminCreateItemBtn");
const adminCreateItemMessage = document.getElementById("adminCreateItemMessage");
const adminLogoutBtn = document.getElementById("adminLogoutBtn");

function loadStoredSession() {
  try {
    const raw = localStorage.getItem(USER_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function persistSession(session) {
  if (session) {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(session));
  } else {
    localStorage.removeItem(USER_STORAGE_KEY);
  }
}

function decodeJwt(token) {
  const [, payload] = token.split(".");
  const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
  return JSON.parse(atob(normalized));
}

function buildUrl(path) {
  const base = apiBaseInput.value.trim().replace(/\/+$/, "");
  return `${base}/${path.replace(/^\/+/, "")}`;
}

function parseSimpleYaml(yamlText) {
  const root = {};
  const stack = [{ indent: -1, value: root }];

  for (const rawLine of yamlText.split(/\r?\n/)) {
    if (!rawLine.trim() || rawLine.trim().startsWith("#")) continue;

    const indent = rawLine.length - rawLine.trimStart().length;
    const line = rawLine.trim();

    while (stack.length && indent <= stack[stack.length - 1].indent) {
      stack.pop();
    }

    const parent = stack[stack.length - 1].value;

    if (line.startsWith("- ")) {
      if (!Array.isArray(parent)) {
        throw new Error(`Invalid YAML list placement: ${line}`);
      }
      parent.push(line.slice(2).trim());
      continue;
    }

    const separatorIndex = line.indexOf(":");
    if (separatorIndex === -1) {
      throw new Error(`Unsupported YAML line: ${line}`);
    }

    const key = line.slice(0, separatorIndex).trim();
    const rawValue = line.slice(separatorIndex + 1).trim();

    if (rawValue === "") {
      const nextValue = key === "notes" ? [] : {};
      parent[key] = nextValue;
      stack.push({ indent, value: nextValue });
    } else {
      parent[key] = rawValue.replace(/^['"]|['"]$/g, "");
    }
  }

  return root;
}

async function loadConfig() {
  const response = await fetch(CONFIG_PATH, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Failed to load app_config.yml");
  }

  const yamlText = await response.text();
  state.config = parseSimpleYaml(yamlText);
  apiBaseInput.value = state.config.frontend.api_base_url;
  syncApiBase();
}

function cognitoRequest(target, body) {
  return fetch(`https://cognito-idp.${state.config.frontend.cognito_region}.amazonaws.com/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-amz-json-1.1",
      "X-Amz-Target": target,
    },
    body: JSON.stringify(body),
  });
}

function setOutput(element, payload) {
  if (!element) return;
  element.textContent = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
}

function clearOutput(element) {
  if (!element) return;
  element.textContent = "";
}

function clearAuthOutputs() {
  clearOutput(authOutput);
  clearOutput(signupOutput);
  clearOutput(confirmOutput);
}

function setHeroStatus(message) {
  if (!heroStatus) return;
  heroStatus.textContent = message;
}

function setActiveView(view) {
  [loginView, signupView, confirmView].forEach((node) => node.classList.remove("active"));
  view.classList.add("active");
}

function isAdminSession(session) {
  const groups = session?.claims?.["cognito:groups"] || [];
  return Array.isArray(groups) && groups.includes("admin");
}

function routeSession() {
  authScreen.classList.add("hidden");
  userScreen.classList.add("hidden");
  adminScreen.classList.add("hidden");

  if (!state.session) {
    authScreen.classList.remove("hidden");
    return;
  }

  if (isAdminSession(state.session)) {
    adminScreen.classList.remove("hidden");
    adminSummary.textContent = `${state.session.claims.email || "Admin"} can restock inventory and trigger notifications.`;
  } else {
    userScreen.classList.remove("hidden");
    userSummary.textContent = `${state.session.claims.email || "User"} can subscribe to out-of-stock products.`;
  }
}

function storeSession(idToken) {
  state.session = {
    idToken,
    claims: decodeJwt(idToken),
  };
  persistSession(state.session);
  routeSession();
}

function logout() {
  state.session = null;
  state.challenge = null;
  persistSession(null);
  clearAuthOutputs();
  loginChallengeBlock.classList.add("hidden");
  routeSession();
}

function syncApiBase() {
  adminApiBaseMirror.value = apiBaseInput.value.trim();
}

function renderProducts(target, mode) {
  if (!state.products.length) {
    target.innerHTML = '<p class="muted">No products returned.</p>';
    return;
  }

  const selectedItemId = mode === "user" ? state.selectedUserItemId : state.selectedAdminItemId;

  target.innerHTML = state.products
    .map((product) => {
      const stockCount = Number(product.stockCount ?? 0);
      const emailCount = Array.isArray(product.subscriberEmails) ? product.subscriberEmails.length : 0;
      const badgeClass = stockCount > 0 ? "in-stock" : "out-stock";
      const badgeText = stockCount > 0 ? "In stock" : "Out of stock";
      const selectedClass = product.itemId === selectedItemId ? "selected" : "";
      const outClass = stockCount > 0 ? "" : "out";

      return `
        <article class="product-card ${selectedClass} ${outClass}" data-item-id="${product.itemId}" data-mode="${mode}">
          <div class="product-top">
            <h3 class="product-id">${product.itemId ?? "unknown-item"}</h3>
            <span class="badge ${badgeClass}">${badgeText}</span>
          </div>
          <p class="product-meta">
            Stock Count: <strong>${stockCount}</strong><br>
            Subscriber Emails: <strong>${emailCount}</strong>
          </p>
        </article>
      `;
    })
    .join("");

  target.querySelectorAll(".product-card").forEach((card) => {
    card.addEventListener("click", () => {
      const itemId = card.dataset.itemId;
      if (mode === "user") {
        state.selectedUserItemId = itemId;
        userSelectedItemInput.value = itemId;
        userActionMessage.textContent = `Ready to subscribe to ${itemId}.`;
        renderProducts(userProductsGrid, "user");
      } else {
        state.selectedAdminItemId = itemId;
        adminSelectedItemInput.value = itemId;
        adminActionMessage.textContent = `Ready to restock ${itemId}.`;
        renderProducts(adminProductsGrid, "admin");
      }
    });
  });
}

async function loadProducts() {
  syncApiBase();
  setHeroStatus("Loading products...");
  try {
    const response = await fetch(buildUrl("/products"));
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Failed to load products");
    }

    state.products = payload.products || [];
    renderProducts(userProductsGrid, "user");
    renderProducts(adminProductsGrid, "admin");
    setHeroStatus(`Loaded ${payload.count ?? 0} products.`);
  } catch (error) {
    setHeroStatus(error.message);
  }
}

async function registerUser() {
  setOutput(signupOutput, "Creating user...");
  const email = signupEmail.value.trim();
  const password = signupPassword.value;

  try {
    const response = await cognitoRequest("AWSCognitoIdentityProviderService.SignUp", {
      ClientId: state.config.frontend.cognito_app_client_id,
      Username: email,
      Password: password,
      UserAttributes: [{ Name: "email", Value: email }],
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.message || "User registration failed");
    }

    confirmEmail.value = email;
    setActiveView(confirmView);
    clearOutput(signupOutput);
  } catch (error) {
    setOutput(signupOutput, error.message);
  }
}

async function confirmUser() {
  setOutput(confirmOutput, "Confirming account...");
  try {
    const response = await cognitoRequest("AWSCognitoIdentityProviderService.ConfirmSignUp", {
      ClientId: state.config.frontend.cognito_app_client_id,
      Username: confirmEmail.value.trim(),
      ConfirmationCode: confirmCode.value.trim(),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.message || "Account confirmation failed");
    }

    loginEmail.value = confirmEmail.value.trim();
    setActiveView(loginView);
    clearOutput(confirmOutput);
  } catch (error) {
    setOutput(confirmOutput, error.message);
  }
}

async function signIn() {
  setOutput(authOutput, "Signing in...");
  try {
    const response = await cognitoRequest("AWSCognitoIdentityProviderService.InitiateAuth", {
      ClientId: state.config.frontend.cognito_app_client_id,
      AuthFlow: "USER_PASSWORD_AUTH",
      AuthParameters: {
        USERNAME: loginEmail.value.trim(),
        PASSWORD: loginPassword.value,
      },
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.message || "Sign in failed");
    }

    if (payload.ChallengeName === "NEW_PASSWORD_REQUIRED") {
      state.challenge = {
        username: loginEmail.value.trim(),
        session: payload.Session,
      };
      loginChallengeBlock.classList.remove("hidden");
      setOutput(authOutput, payload);
      return;
    }

    state.challenge = null;
    loginChallengeBlock.classList.add("hidden");
    storeSession(payload.AuthenticationResult.IdToken);
    clearOutput(authOutput);
    loadProducts();
  } catch (error) {
    setOutput(authOutput, error.message);
  }
}

async function submitNewPassword() {
  if (!state.challenge) {
    setOutput(authOutput, "No active challenge.");
    return;
  }

  setOutput(authOutput, "Submitting new password...");
  try {
    const response = await cognitoRequest("AWSCognitoIdentityProviderService.RespondToAuthChallenge", {
      ClientId: state.config.frontend.cognito_app_client_id,
      ChallengeName: "NEW_PASSWORD_REQUIRED",
      Session: state.challenge.session,
      ChallengeResponses: {
        USERNAME: state.challenge.username,
        NEW_PASSWORD: loginNewPassword.value,
      },
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.message || "Password update failed");
    }

    const challengeUsername = state.challenge.username;
    state.challenge = null;
    loginChallengeBlock.classList.add("hidden");
    storeSession(payload.AuthenticationResult.IdToken);
    clearOutput(authOutput);
    loadProducts();
  } catch (error) {
    setOutput(authOutput, error.message);
  }
}

async function subscribeSelectedItem() {
  if (!state.session?.idToken || !state.selectedUserItemId) {
    userActionMessage.textContent = "Select an item first.";
    return;
  }

  userActionMessage.textContent = "Submitting subscription...";
  try {
    const response = await fetch(buildUrl("/subscriptions"), {
      method: "POST",
      headers: {
        Authorization: state.session.idToken,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ itemId: state.selectedUserItemId }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Subscription failed");
    }

    userActionMessage.textContent = payload.message || `Subscribed to ${state.selectedUserItemId}.`;
    loadProducts();
  } catch (error) {
    userActionMessage.textContent = error.message;
  }
}

async function restockSelectedItem() {
  if (!state.session?.idToken || !state.selectedAdminItemId) {
    adminActionMessage.textContent = "Select an item first.";
    return;
  }

  adminActionMessage.textContent = "Submitting restock...";
  try {
    const response = await fetch(buildUrl("/restock"), {
      method: "POST",
      headers: {
        Authorization: state.session.idToken,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        itemId: state.selectedAdminItemId,
        stockCount: Number(adminRestockCount.value),
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Restock failed");
    }

    adminActionMessage.textContent = payload.message || `Restocked ${state.selectedAdminItemId}.`;
    loadProducts();
  } catch (error) {
    adminActionMessage.textContent = error.message;
  }
}

async function createProduct() {
  const itemId = adminNewItemId.value.trim();
  const stockCount = Number(adminNewItemStock.value);

  if (!state.session?.idToken) {
    adminCreateItemMessage.textContent = "Admin session is missing.";
    return;
  }

  if (!itemId) {
    adminCreateItemMessage.textContent = "Enter a new item ID first.";
    return;
  }

  if (!Number.isInteger(stockCount) || stockCount < 0) {
    adminCreateItemMessage.textContent = "Initial stock must be a non-negative integer.";
    return;
  }

  adminCreateItemMessage.textContent = "Creating product...";
  try {
    const response = await fetch(buildUrl("/products"), {
      method: "POST",
      headers: {
        Authorization: state.session.idToken,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        itemId,
        stockCount,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "Create product failed");
    }

    adminCreateItemMessage.textContent = payload.message || `Created item ${itemId}.`;
    adminNewItemId.value = "";
    adminNewItemStock.value = "0";
    await loadProducts();
  } catch (error) {
    adminCreateItemMessage.textContent = error.message;
  }
}

signInBtn.addEventListener("click", signIn);
goSignUpBtn.addEventListener("click", () => setActiveView(signupView));
signUpBtn.addEventListener("click", registerUser);
backToSignInBtn.addEventListener("click", () => setActiveView(loginView));
confirmBtn.addEventListener("click", confirmUser);
confirmBackBtn.addEventListener("click", () => setActiveView(loginView));
loginChallengeBtn.addEventListener("click", submitNewPassword);

userRefreshBtn.addEventListener("click", loadProducts);
adminRefreshBtn.addEventListener("click", loadProducts);
logoutBtn.addEventListener("click", logout);
adminLogoutBtn.addEventListener("click", logout);
userSubscribeBtn.addEventListener("click", subscribeSelectedItem);
adminRestockBtn.addEventListener("click", restockSelectedItem);
adminCreateItemBtn.addEventListener("click", createProduct);
apiBaseInput.addEventListener("input", syncApiBase);

async function init() {
  setActiveView(loginView);
  try {
    await loadConfig();
    routeSession();
    if (state.session) {
      await loadProducts();
    }
  } catch (error) {
    setOutput(authOutput, error.message);
  }
}

init();
