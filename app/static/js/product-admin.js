let settings = null;
let products = [];
let kits = [];

const categoryOptions = [
  "frequently_used",
  "product",
  "fluid_exchange",
  "pmp_kit_product",
];

const statusEl = document.getElementById("status");

async function init() {
  const [settingsRes, productsRes, kitsRes] = await Promise.all([
    fetch("/api/menu-admin/settings"),
    fetch("/api/menu-admin/products"),
    fetch("/api/menu-admin/pmp-kits"),
  ]);
  settings = await settingsRes.json();
  products = await productsRes.json();
  kits = await kitsRes.json();
  renderSettings();
  renderProducts();
  renderKits();
}

function renderSettings() {
  document.getElementById("setting-elr").value = settings.target_elr;
  document.getElementById("setting-labor").value = settings.avg_labor_cost_per_hour;
  document.getElementById("setting-gross").value = settings.parts_gross_pct;
  document.getElementById("setting-spiff").value = settings.spiff_amount;
}

function renderProducts() {
  const body = document.getElementById("products-body");
  body.innerHTML = products.map(product => `
    <tr data-id="${product.id}">
      <td><input data-field="name" value="${escapeAttr(product.name)}" /></td>
      <td>
        <select data-field="category">
          ${categoryOptions.map(opt => `<option value="${opt}" ${product.category === opt ? "selected" : ""}>${label(opt)}</option>`).join("")}
        </select>
      </td>
      <td class="num"><input data-field="parts_cost" type="number" step="0.01" value="${product.parts_cost ?? ""}" /></td>
      <td class="num"><input data-field="parts_sale" type="number" step="0.01" value="${product.parts_sale ?? ""}" /></td>
      <td class="num"><input data-field="labor_hours" type="number" step="0.01" value="${product.labor_hours ?? ""}" /></td>
      <td class="num"><input data-field="current_sales_price" type="number" step="0.01" value="${product.current_sales_price ?? ""}" /></td>
      <td><input data-field="op_code" value="${escapeAttr(product.op_code || "")}" /></td>
      <td><input data-field="vin_specific" type="checkbox" ${product.vin_specific ? "checked" : ""} /></td>
      <td><input data-field="active" type="checkbox" ${product.active ? "checked" : ""} /></td>
      <td><button class="btn-secondary btn-danger" data-delete-product="${product.id}">Delete</button></td>
    </tr>
  `).join("");
  body.querySelectorAll("input, select").forEach(input => input.addEventListener("input", onProductInput));
  body.querySelectorAll("[data-delete-product]").forEach(btn => btn.addEventListener("click", onDeleteProduct));
}

function renderKits() {
  const list = document.getElementById("kit-list");
  const activeProducts = products.filter(p => p.active);
  list.innerHTML = kits.map(kit => {
    const summary = kitSummary(kit);
    return `
    <div class="kit-card" data-id="${kit.id}">
      <div class="kit-card-header">
        <div class="kit-card-title">
          <strong>${escapeHtml(kit.group_name || "Untitled kit")}</strong>
          <span>${kit.product_items.length} products selected · ${summary.partsCostText} component cost</span>
        </div>
        <div class="kit-summary-strip">
          <div><span>Component cost</span><strong>${summary.partsCostText}</strong></div>
          <button class="btn-secondary btn-danger" data-delete-kit="${kit.id}">Delete kit</button>
        </div>
      </div>
      <div class="kit-builder">
        <div class="kit-panel kit-details-panel">
          <div class="kit-panel-heading">
            <h3>Kit details</h3>
          </div>
          <div class="kit-details-layout">
            <div class="kit-name-fields">
              <div class="admin-field kit-name-field"><label>Group name</label><input data-field="group_name" value="${escapeAttr(kit.group_name)}" /></div>
              <div class="admin-field kit-name-field"><label>Kit name</label><input data-field="kit_name" value="${escapeAttr(kit.kit_name)}" /></div>
            </div>
            <div class="kit-number-fields">
              <div class="admin-field"><label>Labor hours</label><input data-field="labor_hours" type="number" step="0.01" value="${kit.labor_hours}" /></div>
              <div class="admin-field"><label>Pretty price</label><input data-field="pretty_price" type="number" step="0.01" value="${kit.pretty_price}" /></div>
              <div class="admin-field"><label>Projected sales</label><input data-field="projected_monthly_sales" type="number" step="1" value="${kit.projected_monthly_sales}" /></div>
              <label class="kit-active-toggle">
                <input data-field="active" type="checkbox" ${kit.active ? "checked" : ""} />
                <span>Active</span>
              </label>
            </div>
          </div>
        </div>
        <div class="kit-compose">
          <div class="kit-panel">
            <div class="kit-panel-heading">
              <h3>Available products</h3>
              <span>${activeProducts.length - kit.product_items.length} available</span>
            </div>
            <input class="product-picker-search" data-kit-search="${kit.id}" placeholder="Search products..." />
            <div class="product-picker-list">
              ${activeProducts
                .filter(product => !kit.product_items.some(item => item.product_id === product.id))
                .map(product => productPickerButton(product, kit.id))
                .join("") || '<p class="kit-empty">All active products are already in this kit.</p>'}
            </div>
          </div>
          <div class="kit-panel selected-products-panel">
            <div class="kit-panel-heading">
              <h3>Selected products</h3>
              <span>${summary.partsCostText}</span>
            </div>
            <div class="kit-items-editor">
              ${kit.product_items.map(item => kitItemRow(item)).join("") || '<p class="kit-empty">No products selected yet. Add products from the available list.</p>'}
            </div>
          </div>
        </div>
      </div>
    </div>
  `}).join("");
  list.querySelectorAll("input, select").forEach(input => input.addEventListener("input", onKitInput));
  list.querySelectorAll("[data-add-product]").forEach(btn => btn.addEventListener("click", onAddProductToKit));
  list.querySelectorAll("[data-quantity-product]").forEach(input => input.addEventListener("input", onKitQuantityInput));
  list.querySelectorAll("[data-remove-product]").forEach(btn => btn.addEventListener("click", onRemoveProductFromKit));
  list.querySelectorAll("[data-kit-search]").forEach(input => input.addEventListener("input", onKitSearch));
  list.querySelectorAll("[data-delete-kit]").forEach(btn => btn.addEventListener("click", onDeleteKit));
}

function productPickerButton(product, kitId) {
  return `
    <button class="product-picker-item" data-add-product="${product.id}" data-kit-id="${kitId}">
      <span>
        <strong>${escapeHtml(product.name)}</strong>
        <span>${label(product.category)}</span>
      </span>
      <em>${product.parts_cost != null ? `$${Number(product.parts_cost).toFixed(2)}` : "No cost"} · Add</em>
    </button>
  `;
}

function kitItemRow(item) {
  const product = products.find(p => p.id === item.product_id);
  const cost = product?.parts_cost != null ? Number(product.parts_cost) * Number(item.quantity || 0) : null;
  return `<div class="kit-item-row">
    <span>
      <strong>${escapeHtml(product?.name || item.product_id)}</strong>
      <span>${product ? label(product.category) : "Missing product"}${cost != null ? ` · ${money(cost)}` : ""}</span>
    </span>
    <input type="number" step="0.01" min="0" data-quantity-product="${item.product_id}" value="${item.quantity}" />
    <button class="kit-remove-item" data-remove-product="${item.product_id}">Remove</button>
  </div>`;
}

function kitSummary(kit) {
  const productById = new Map(products.map(product => [product.id, product]));
  const partsCost = kit.product_items.reduce((total, item) => {
    const product = productById.get(item.product_id);
    if (product?.parts_cost == null) return total;
    return total + Number(product.parts_cost) * Number(item.quantity || 0);
  }, 0);
  return {
    partsCost,
    partsCostText: money(partsCost),
  };
}

function onProductInput(event) {
  const row = event.target.closest("tr");
  const product = products.find(item => item.id === row.dataset.id);
  if (!product) return;
  const field = event.target.dataset.field;
  product[field] = readInputValue(event.target);
  renderKits();
}

function onKitInput(event) {
  const card = event.target.closest(".kit-card");
  const kit = kits.find(item => item.id === card.dataset.id);
  if (!kit) return;
  const field = event.target.dataset.field;
  if (field) {
    kit[field] = readInputValue(event.target);
  }
}

function onAddProductToKit(event) {
  const kit = kits.find(item => item.id === event.currentTarget.dataset.kitId);
  if (!kit) return;
  const productId = event.currentTarget.dataset.addProduct;
  if (!kit.product_items.some(item => item.product_id === productId)) {
    kit.product_items.push({ product_id: productId, quantity: 1 });
  }
  renderKits();
}

function onKitQuantityInput(event) {
  const card = event.target.closest(".kit-card");
  const kit = kits.find(item => item.id === card.dataset.id);
  if (!kit) return;
  const productId = event.target.dataset.quantityProduct;
  const item = kit.product_items.find(productItem => productItem.product_id === productId);
  if (item) item.quantity = parseFloat(event.target.value) || 0;
}

function onRemoveProductFromKit(event) {
  const card = event.target.closest(".kit-card");
  const kit = kits.find(item => item.id === card.dataset.id);
  if (!kit) return;
  kit.product_items = kit.product_items.filter(item => item.product_id !== event.target.dataset.removeProduct);
  renderKits();
}

function onKitSearch(event) {
  const query = event.target.value.trim().toLowerCase();
  const panel = event.target.closest(".kit-panel");
  panel.querySelectorAll(".product-picker-item").forEach(item => {
    item.style.display = item.textContent.toLowerCase().includes(query) ? "" : "none";
  });
}

function readInputValue(input) {
  if (input.type === "checkbox") return input.checked;
  if (input.type === "number") return input.value === "" ? null : parseFloat(input.value);
  return input.value;
}

function onDeleteProduct(event) {
  products = products.filter(product => product.id !== event.target.dataset.deleteProduct);
  kits.forEach(kit => {
    kit.product_items = kit.product_items.filter(item => products.some(product => product.id === item.product_id));
  });
  renderProducts();
  renderKits();
}

function onDeleteKit(event) {
  kits = kits.filter(kit => kit.id !== event.target.dataset.deleteKit);
  renderKits();
}

document.getElementById("add-product").addEventListener("click", () => {
  products.push({
    id: crypto.randomUUID(),
    name: "New Product",
    category: "product",
    parts_cost: null,
    parts_sale: null,
    labor_hours: null,
    current_sales_price: null,
    op_code: "",
    vin_specific: false,
    active: true,
  });
  renderProducts();
  renderKits();
});

document.getElementById("add-kit").addEventListener("click", () => {
  kits.push({
    id: crypto.randomUUID(),
    group_name: "New Service Kit",
    kit_name: "New Kit",
    product_items: [],
    labor_hours: 1,
    parts_cost: 0,
    pretty_price: 0,
    projected_monthly_sales: 30,
    active: true,
  });
  renderKits();
});

document.querySelectorAll(".settings-tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".settings-tab").forEach(item => item.classList.remove("active"));
    document.querySelectorAll(".settings-section").forEach(section => section.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(tab.dataset.section).classList.add("active");
  });
});

document.getElementById("save-all").addEventListener("click", async () => {
  statusEl.textContent = "Saving...";
  settings = {
    target_elr: parseFloat(document.getElementById("setting-elr").value) || 0,
    avg_labor_cost_per_hour: parseFloat(document.getElementById("setting-labor").value) || 0,
    parts_gross_pct: parseFloat(document.getElementById("setting-gross").value) || 0,
    spiff_amount: parseFloat(document.getElementById("setting-spiff").value) || 0,
  };

  await fetch("/api/menu-admin/settings", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });

  await fetch("/api/menu-admin/products", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(products),
  });

  await fetch("/api/menu-admin/pmp-kits", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(kits),
  });

  statusEl.textContent = "Saved. New dealership projects will inherit these values; existing projects keep any edited overrides.";
});

function label(value) {
  return value.replace(/_/g, " ").replace(/\b\w/g, char => char.toUpperCase());
}

function money(value) {
  const num = Number(value || 0);
  return `$${num.toFixed(2)}`;
}

function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

function escapeAttr(str) {
  return String(str ?? "").replace(/"/g, "&quot;");
}

init();
