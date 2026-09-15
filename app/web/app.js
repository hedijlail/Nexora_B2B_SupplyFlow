const state = { token: sessionStorage.getItem("b2b_token"), currentView: "dashboard" };
const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value ?? "—").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);

function showError(message) {
  const element = $("#app-error");
  element.textContent = message;
  element.hidden = !message;
}

async function api(path) {
  const response = await fetch(path, { headers: { Authorization: `Bearer ${state.token}` } });
  if (response.status === 401) return signOut();
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Request failed");
  }
  return response.json();
}

async function apiWrite(path, body) {
  const response = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${state.token}` }, body: JSON.stringify(body) });
  if (!response.ok) { const payload = await response.json().catch(() => ({})); throw new Error(payload.detail || "Could not save record"); }
  return response.json();
}

function money(value) {
  return new Intl.NumberFormat(undefined, { style: "currency", currency: "USD" }).format(value || 0);
}

function table(headers, rows) {
  if (!rows.length) return '<div class="empty">No records yet.</div>';
  return `<div class="table-wrap"><table><thead><tr>${headers.map((header) => `<th>${header}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
}

async function renderDashboard() {
  const data = await api("/dashboard/summary");
  $("#dashboard").innerHTML = `<div class="cards">
    <article class="card"><p>Fulfilled sales</p><strong>${money(data.fulfilled_sales_total)}</strong></article>
    <article class="card"><p>Open orders</p><strong>${money(data.open_orders_total)}</strong></article>
    <article class="card"><p>Outstanding invoices</p><strong>${money(data.invoices_outstanding_total)}</strong></article>
    <article class="card"><p>Stock units</p><strong>${data.stock_units_total}</strong></article>
    <article class="card"><p>Stock cost value</p><strong>${money(data.stock_cost_value)}</strong></article>
    <article class="card"><p>Overdue invoices</p><strong>${data.overdue_invoices_count}</strong></article>
  </div>`;
}

async function renderCustomers() {
  const rows = await api("/customers");
  $("#customers").innerHTML = quickForm("customer-form", "Add customer", '<input name="code" required placeholder="Customer code"><input name="name" required placeholder="Customer name"><input name="email" type="email" placeholder="Email"><input name="credit_limit" type="number" min="0" value="0" placeholder="Credit limit">') + table(["Code", "Customer", "Email", "Credit limit", "Status"], rows.map((row) => `<tr><td>${escapeHtml(row.code)}</td><td>${escapeHtml(row.name)}</td><td>${escapeHtml(row.email)}</td><td>${money(row.credit_limit)}</td><td><span class="status">${row.is_active ? "Active" : "Inactive"}</span></td></tr>`));
  bindCreate("customer-form", "/customers", (data) => ({ code: data.code, name: data.name, email: data.email || null, credit_limit: Number(data.credit_limit || 0) }));
}

async function renderProducts() {
  const rows = await api("/products");
  $("#products").innerHTML = quickForm("product-form", "Add product", '<input name="sku" required placeholder="SKU"><input name="name" required placeholder="Product name"><input name="sale_price" type="number" min="0" step="0.01" value="0" placeholder="Sale price"><input name="cost_price" type="number" min="0" step="0.01" value="0" placeholder="Cost price">') + table(["SKU", "Product", "Unit", "Sale price", "Status"], rows.map((row) => `<tr><td>${escapeHtml(row.sku)}</td><td>${escapeHtml(row.name)}</td><td>${escapeHtml(row.unit)}</td><td>${money(row.sale_price)}</td><td><span class="status">${row.is_active ? "Active" : "Inactive"}</span></td></tr>`));
  bindCreate("product-form", "/products", (data) => ({ sku: data.sku, name: data.name, sale_price: Number(data.sale_price || 0), cost_price: Number(data.cost_price || 0) }));
}

async function renderWarehouses() {
  const rows = await api("/warehouses");
  $("#warehouses").innerHTML = quickForm("warehouse-form", "Add warehouse", '<input name="code" required placeholder="Warehouse code"><input name="name" required placeholder="Warehouse name">') + table(["Code", "Warehouse", "Status"], rows.map((row) => `<tr><td>${escapeHtml(row.code)}</td><td>${escapeHtml(row.name)}</td><td><span class="status">${row.is_active ? "Active" : "Inactive"}</span></td></tr>`));
  bindCreate("warehouse-form", "/warehouses", (data) => ({ code: data.code, name: data.name }));
}

function quickForm(id, title, fields) { return `<form id="${id}" class="quick-form"><strong>${title}</strong><div>${fields}<button class="primary" type="submit">Save</button></div><p class="form-error" hidden></p></form>`; }
function bindCreate(formId, path, toPayload) {
  $(`#${formId}`).addEventListener("submit", async (event) => {
    event.preventDefault(); const form = event.currentTarget; const error = form.querySelector(".form-error");
    try { await apiWrite(path, toPayload(Object.fromEntries(new FormData(form)))); await selectView(state.currentView); }
    catch (exception) { error.textContent = exception.message; error.hidden = false; }
  });
}

async function renderStocks() {
  const rows = await api("/stocks");
  $("#stocks").innerHTML = table(["SKU", "Product", "Quantity", "Reserved"], rows.map((row) => `<tr><td>${escapeHtml(row.sku)}</td><td>${escapeHtml(row.product_name)}</td><td>${row.quantity}</td><td>${row.reserved_quantity}</td></tr>`));
}

async function renderOrders() {
  const rows = await api("/orders");
  $("#orders").innerHTML = table(["Order", "Status", "Total"], rows.map((row) => `<tr><td>${escapeHtml(row.order_number)}</td><td><span class="status">${escapeHtml(row.status)}</span></td><td>${money(row.grand_total)}</td></tr>`));
}

async function renderInvoices() {
  const rows = await api("/invoices");
  $("#invoices").innerHTML = table(["Invoice", "Issue date", "Due date", "Status", "Total"], rows.map((row) => `<tr><td>${escapeHtml(row.invoice_number)}</td><td>${escapeHtml(row.issue_date)}</td><td>${escapeHtml(row.due_date)}</td><td><span class="status">${escapeHtml(row.status)}</span></td><td>${money(row.grand_total)}</td></tr>`));
}

const renderers = { dashboard: renderDashboard, customers: renderCustomers, products: renderProducts, warehouses: renderWarehouses, stocks: renderStocks, orders: renderOrders, invoices: renderInvoices };

async function selectView(view) {
  state.currentView = view;
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.view === view));
  document.querySelectorAll(".view").forEach((item) => item.classList.toggle("active", item.id === view));
  $("#section-title").textContent = view[0].toUpperCase() + view.slice(1);
  $("#section-kicker").textContent = view === "dashboard" ? "OVERVIEW" : "MANAGEMENT";
  showError("");
  try { await renderers[view](); } catch (error) { showError(error.message); }
}

function signOut() {
  sessionStorage.removeItem("b2b_token");
  state.token = null;
  $("#app-view").hidden = true;
  $("#login-view").hidden = false;
}

$("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const error = $("#login-error");
  error.hidden = true;
  try {
    const response = await fetch("/auth/token", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ company_slug: $("#company-slug").value, email: $("#email").value, password: $("#password").value }) });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Sign in failed");
    state.token = payload.access_token;
    sessionStorage.setItem("b2b_token", state.token);
    $("#login-view").hidden = true;
    $("#app-view").hidden = false;
    selectView("dashboard");
  } catch (exception) { error.textContent = exception.message; error.hidden = false; }
});
document.querySelectorAll(".nav-item").forEach((item) => item.addEventListener("click", () => selectView(item.dataset.view)));
$("#refresh").addEventListener("click", () => selectView(state.currentView));
$("#logout").addEventListener("click", signOut);
if (state.token) { $("#login-view").hidden = true; $("#app-view").hidden = false; selectView("dashboard"); }
