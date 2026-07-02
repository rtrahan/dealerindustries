let STEPS = [];
const projectId = window.location.pathname.split("/").pop();
let project = null;
let calculations = null;
let saveTimer = null;
let currentStep = 0;

const els = {
  name: document.getElementById("project-name"),
  breadcrumb: document.getElementById("breadcrumb-name"),
  meta: document.getElementById("project-meta"),
  readyBanner: document.getElementById("ready-banner"),
  progressText: document.getElementById("progress-text"),
  progressFill: document.getElementById("progress-fill"),
  stepNav: document.getElementById("step-nav"),
  stepTitle: document.getElementById("step-title"),
  stepSubtitle: document.getElementById("step-subtitle"),
  sheetBadge: document.getElementById("sheet-badge"),
  stepContent: document.getElementById("step-content"),
  btnPrev: document.getElementById("btn-prev"),
  btnNext: document.getElementById("btn-next"),
  btnComplete: document.getElementById("btn-complete"),
  saveStatus: document.getElementById("save-status"),
  deliverablesPanel: document.getElementById("deliverables-panel"),
  advisorOpsExport: document.getElementById("advisor-ops-export"),
  partsPullExport: document.getElementById("parts-pull-export"),
};

async function init() {
  const stepsRes = await fetch("/api/workflow-steps");
  STEPS = await stepsRes.json();

  const res = await fetch(`/api/menu-projects/${projectId}`);
  if (!res.ok) {
    els.name.textContent = "Project not found";
    return;
  }
  project = await res.json();
  currentStep = Math.min(project.current_step || 0, STEPS.length - 1);
  await loadCalculations();
  render();
}

async function loadCalculations() {
  const res = await fetch(`/api/menu-projects/${projectId}/calculations`);
  if (res.ok) calculations = await res.json();
}

function updateProgress() {
  const stepsDone = project.steps_completed.filter(Boolean).length;
  const total = STEPS.length;
  const pct = total ? (stepsDone / total) * 100 : 0;
  const ready = stepsDone === total;

  els.progressText.textContent = stepsDone;
  els.progressFill.style.width = `${pct}%`;
  els.readyBanner.classList.toggle("visible", ready);
  els.deliverablesPanel.classList.toggle("ready", ready);
  els.advisorOpsExport.href = ready ? `/api/menu-projects/${projectId}/advisor-ops.pdf` : "#";
  els.partsPullExport.href = ready ? `/api/menu-projects/${projectId}/parts-pull.pdf` : "#";
  els.advisorOpsExport.setAttribute("aria-disabled", String(!ready));
  els.partsPullExport.setAttribute("aria-disabled", String(!ready));
  els.meta.textContent = ready
    ? "All workflow steps complete — this dealership is ready for service."
    : `Step ${currentStep + 1} of ${total}: ${STEPS[currentStep]?.title || ""}`;
}

function render() {
  document.title = `${project.name} — Menu Builder`;
  els.name.textContent = project.name;
  els.breadcrumb.textContent = project.name;
  updateProgress();

  renderStepNav();
  renderStepContent();
  updateNavButtons();
}

function renderStepNav() {
  els.stepNav.innerHTML = STEPS.map((s, i) => `
    <button type="button" class="step-nav-item ${i === currentStep ? "active" : ""} ${project.steps_completed[i] ? "done" : ""}" data-step="${i}">
      <span class="step-num">${project.steps_completed[i] ? "✓" : i + 1}</span>
      <span class="step-nav-text">
        <strong>${s.title}</strong>
        <span>${s.subtitle}</span>
      </span>
    </button>
  `).join("");

  els.stepNav.querySelectorAll(".step-nav-item").forEach(btn => {
    btn.addEventListener("click", () => goToStep(parseInt(btn.dataset.step, 10)));
  });
}

function renderStepContent() {
  const step = STEPS[currentStep];
  els.stepTitle.textContent = step.title;
  els.stepSubtitle.textContent = step.subtitle;
  els.sheetBadge.textContent = step.sheet || `Step ${currentStep + 1}`;

  const renderers = [renderPricing, renderPmp, renderPvp, renderAdvisorOps, renderPartsPull];
  els.stepContent.innerHTML = "";
  renderers[currentStep]();
}

function panelSection(title, desc, count) {
  const section = el("div", "panel-section");
  section.innerHTML = `
    <div class="panel-section-header">
      <div>
        <h3>${title}</h3>
        ${desc ? `<p>${desc}</p>` : ""}
      </div>
      ${count != null ? `<span class="count">${count}</span>` : ""}
    </div>
  `;
  return section;
}

function renderPricing() {
  const p = project.pricing;
  const grossPct = Math.round(p.parts_gross_pct * 100);

  const assumptions = panelSection("Global assumptions", "These drive all profitability calculations across the workbook.");
  const metrics = el("div", "metric-grid");
  metrics.innerHTML = `
    <div class="metric-card">
      <label for="f-elr">Maintenance ELR</label>
      <input type="number" id="f-elr" step="0.01" value="${p.target_elr}" />
      <div class="unit">$/hr target rate</div>
    </div>
    <div class="metric-card">
      <label for="f-labor">Avg labor cost</label>
      <input type="number" id="f-labor" step="0.01" value="${p.avg_labor_cost_per_hour}" />
      <div class="unit">$/hr shop cost</div>
    </div>
    <div class="metric-card">
      <label for="f-gross">Parts gross</label>
      <input type="number" id="f-gross" step="0.01" min="0" max="1" value="${p.parts_gross_pct}" />
      <div class="unit">${grossPct}% margin target</div>
    </div>
    <div class="metric-card">
      <label for="f-spiff">Spiff amount</label>
      <input type="number" id="f-spiff" step="0.01" value="${p.spiff_amount}" />
      <div class="unit">$ per unit</div>
    </div>
  `;
  assumptions.appendChild(metrics);
  els.stepContent.appendChild(assumptions);

  const bindPricing = () => {
    ["target_elr", "avg_labor_cost_per_hour", "parts_gross_pct", "spiff_amount"].forEach(field => {
      if (!project.pricing.override_fields.includes(field)) project.pricing.override_fields.push(field);
    });
    project.pricing = {
      target_elr: parseFloat(document.getElementById("f-elr").value) || 0,
      avg_labor_cost_per_hour: parseFloat(document.getElementById("f-labor").value) || 0,
      parts_gross_pct: parseFloat(document.getElementById("f-gross").value) || 0,
      spiff_amount: parseFloat(document.getElementById("f-spiff").value) || 0,
      override_fields: project.pricing.override_fields,
    };
    const unit = metrics.querySelector(".metric-card:nth-child(3) .unit");
    if (unit) unit.textContent = `${Math.round(project.pricing.parts_gross_pct * 100)}% margin target`;
    scheduleSave(true);
  };
  metrics.querySelectorAll("input").forEach(inp => inp.addEventListener("input", bindPricing));

  const catalogProducts = getPricingCatalogProducts();
  const catalog = panelSection(
    "Product pricing",
    "Frequently used items are pinned at the top, followed by dealership-facing products and fluid exchanges.",
    `${catalogProducts.length} rows`
  );
  catalog.appendChild(renderPricingTable(catalogProducts, {
    title: "Product pricing",
    headers: ["Product", "Parts cost", "Parts sale", "Current labor rate", "Current sales price", "Current OP code"],
    fields: ["name", "parts_cost", "parts_sale", "labor_hours", "current_sales_price", "op_code"],
  }));
  els.stepContent.appendChild(catalog);
}

function renderPricingTable(products, config) {
  const wrap = el("div", "data-table-wrap pricing-table-wrap");
  const header = config.headers.map((header, index) => {
    const isNumeric = index > 0 && header !== "Current OP code";
    return `<th class="${isNumeric ? "num" : ""}">${header}</th>`;
  }).join("");
  let lastCategory = "";
  const rows = products.map(prod => {
    const divider = prod.category === "fluid_exchange" && lastCategory !== "fluid_exchange"
      ? `<tr class="pricing-divider-row"><td colspan="${config.fields.length}">Fluid Exchanges</td></tr>`
      : "";
    lastCategory = prod.category;
    return `${divider}
    <tr data-id="${prod.id}" class="${prod.category === "frequently_used" ? "frequently-used-row" : ""}">
      ${config.fields.map((field, index) => {
        const isName = field === "name";
        const isNumeric = ["parts_cost", "parts_sale", "labor_hours", "current_sales_price"].includes(field);
        const value = prod[field] ?? "";
        return `<td class="${isName ? "product-col" : ""} ${isNumeric ? "num" : ""}">
          <input ${isNumeric ? 'type="number" step="0.01"' : ""} value="${escapeAttr(value)}" data-field="${field}" placeholder="—" />
        </td>`;
      }).join("")}
    </tr>
  `}).join("");
  wrap.innerHTML = `<table class="data-table pricing-table">
    <thead><tr>${header}</tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
  wrap.querySelectorAll("input").forEach(input => input.addEventListener("input", onProductChange));
  return wrap;
}

function getPricingCatalogProducts() {
  const frequentlyUsed = project.products.filter(prod => prod.category === "frequently_used");
  const frequentlyUsedNames = new Set(frequentlyUsed.map(prod => normalizeName(prod.name)));
  const productRows = project.products.filter(prod =>
    prod.category === "product" && !frequentlyUsedNames.has(normalizeName(prod.name))
  );
  const fluidRows = project.products.filter(prod => prod.category === "fluid_exchange");
  return [...frequentlyUsed, ...productRows, ...fluidRows];
}

function normalizeName(name) {
  return String(name || "").trim().toLowerCase().replace(/\s+/g, " ");
}

function onProductChange(e) {
  const row = e.target.closest("tr");
  const prod = project.products.find(p => p.id === row.dataset.id);
  if (!prod) return;
  const field = e.target.dataset.field;
  const val = e.target.value;
  if (!prod.override_fields.includes(field)) prod.override_fields.push(field);
  if (["parts_cost", "parts_sale", "labor_hours", "current_sales_price"].includes(field)) {
    prod[field] = val === "" ? null : parseFloat(val);
  } else {
    prod[field] = val;
  }
  scheduleSave();
}

function renderPmp() {
  if (!calculations) {
    els.stepContent.innerHTML = '<p class="empty-hint">Loading profitability calculations…</p>';
    return;
  }

  const intro = panelSection(
    "Kit profitability",
    "Adjust inputs and pretty prices — ELR and gross update automatically."
  );
  const list = el("div", "pmp-list");
  intro.appendChild(list);

  project.pmp_services.forEach((svc, idx) => {
    const calc = calculations.pmp[idx] || {};
    const components = pmpComponentSummary(svc);
    const card = el("div", "pmp-card");
    card.innerHTML = `
      <div class="pmp-card-header">
        <div class="pmp-card-header-text">
          <h4>${escapeHtml(svc.group_name)}</h4>
          <p>${escapeHtml(svc.kit_name)}</p>
        </div>
        <span class="elr-badge ${calc.meets_target ? "good" : "warn"}">
          ELR $${fmt(calc.actual_elr)} ${calc.meets_target ? "✓" : "↓"}
        </span>
      </div>
      <div class="pmp-card-body">
        <div class="pmp-inputs-wrap">
          <h5 class="pmp-section-title">Inputs</h5>
          <div class="pmp-inputs">
            <div class="field"><label>Labor hours</label><input type="number" step="0.01" class="pmp-hours" value="${svc.labor_hours}" /></div>
            <div class="field"><label>Component cost</label><input type="number" step="0.01" value="${calc.total_parts_cost ?? svc.parts_cost}" disabled /></div>
            <div class="field"><label>Pretty price</label><input type="number" step="0.01" class="pmp-pretty" value="${svc.pretty_price}" /></div>
            <div class="field"><label>Monthly vol</label><input type="number" step="1" class="pmp-sales" value="${svc.projected_monthly_sales}" /></div>
          </div>
          <div class="pmp-components">${components}</div>
        </div>
        <div class="pmp-metrics-wrap">
          <h5 class="pmp-section-title">Calculations</h5>
          <div class="pmp-metrics">
            <div class="pmp-metric"><label>Parts sale</label><div class="value">$${fmt(calc.total_parts_sale)}</div></div>
            <div class="pmp-metric"><label>Labor sale</label><div class="value">$${fmt(calc.labor_sale)}</div></div>
            <div class="pmp-metric highlight"><label>Total gross</label><div class="value">$${fmt(calc.total_gross)}</div></div>
            <div class="pmp-metric"><label>Target price</label><div class="value">$${fmt(calc.target_price)}</div></div>
            <div class="pmp-metric"><label>Labor gross</label><div class="value">$${fmt(calc.labor_gross)}</div></div>
            <div class="pmp-metric"><label>Monthly gross</label><div class="value">$${fmt(calc.monthly_gross)}</div></div>
          </div>
        </div>
      </div>
    `;
    card.querySelector(".pmp-hours").addEventListener("input", e => { markPmpOverride(svc, "labor_hours"); svc.labor_hours = parseFloat(e.target.value) || 0; onPmpChange(); });
    card.querySelector(".pmp-pretty").addEventListener("input", e => { markPmpOverride(svc, "pretty_price"); svc.pretty_price = parseFloat(e.target.value) || 0; onPmpChange(); });
    card.querySelector(".pmp-sales").addEventListener("input", e => { markPmpOverride(svc, "projected_monthly_sales"); svc.projected_monthly_sales = parseInt(e.target.value, 10) || 0; onPmpChange(); });
    list.appendChild(card);
  });

  const total = el("div", "pmp-total-bar");
  total.innerHTML = `<span>Total projected monthly gross</span><span>$${fmt(calculations.pmp_monthly_total)}</span>`;
  intro.appendChild(total);
  els.stepContent.appendChild(intro);
}

function onPmpChange() { scheduleSave(true); }

function markPmpOverride(service, field) {
  if (!service.override_fields.includes(field)) service.override_fields.push(field);
}

function pmpComponentSummary(service) {
  if (!service.product_items?.length) return '<p class="pmp-components-empty">No linked products. Edit this kit in Product Admin.</p>';
  const productMap = new Map(project.products.map(product => [product.source_product_id || product.id, product]));
  return `
    <div class="pmp-components-label">Products in kit</div>
    <div class="pmp-component-list">
      ${service.product_items.map(item => {
        const product = productMap.get(item.product_id);
        return `<span>${escapeHtml(product?.name || item.product_id)}${item.quantity !== 1 ? ` × ${item.quantity}` : ""}</span>`;
      }).join("")}
    </div>
  `;
}

function renderPvp() {
  const pvp = project.pvp;
  const calc = calculations?.pvp || {};
  const under100 = calc.under_100;

  const inputs = panelSection("Program inputs", "Used-vehicle protection pricing per car.");
  const calculator = el("div", "pvp-calculator");
  const grid = el("div", "pvp-input-grid");
  grid.innerHTML = `
    <div class="pvp-input-card">
      <label>Parts cost</label>
      <input type="number" id="pvp-cost" step="0.01" value="${pvp.parts_cost}" />
      <span>Dealer Industries cost basis</span>
    </div>
    <div class="pvp-input-card">
      <label>Parts markup</label>
      <input type="number" id="pvp-markup" step="0.01" value="${pvp.parts_markup_pct}" />
      <span>${Math.round((pvp.parts_markup_pct || 0) * 100)}% markup</span>
    </div>
    <div class="pvp-input-card">
      <label>CP labor rate</label>
      <input type="number" id="pvp-rate" step="0.01" value="${pvp.cp_labor_rate}" />
      <span>Customer-pay labor rate</span>
    </div>
    <div class="pvp-input-card">
      <label>Labor hours</label>
      <input type="number" id="pvp-hours" step="0.01" value="${pvp.labor_hours}" />
      <span>Time billed per car</span>
    </div>
  `;
  calculator.appendChild(grid);

  const summary = el("div", "pvp-summary");
  summary.innerHTML = `
    <div class="pvp-result-card"><div class="label">Parts sale</div><div class="amount">$${fmt(calc.parts_sale)}</div><span>Cost + markup</span></div>
    <div class="pvp-result-card"><div class="label">Labor sale</div><div class="amount">$${fmt(calc.labor_sale)}</div><span>Rate × hours</span></div>
    <div class="pvp-result-card highlight ${under100 ? "pass" : "warn"}">
      <div class="label">Total per used car</div>
      <div class="amount">$${fmt(calc.total)}</div>
      <span>${under100 ? "Under $100 target" : "Above $100 target"}</span>
    </div>
  `;
  calculator.appendChild(summary);

  const note = el("div", `pvp-rule ${under100 ? "pass" : "warn"}`);
  note.innerHTML = `
    <strong>${under100 ? "Meets target" : "Needs review"}</strong>
    <span>Formula: parts cost + markup + labor sale. Keep total per used car under $100.</span>
  `;
  calculator.appendChild(note);
  inputs.appendChild(calculator);
  els.stepContent.appendChild(inputs);

  grid.querySelectorAll("input").forEach(input => {
    input.addEventListener("input", () => {
      project.pvp = {
        parts_cost: parseFloat(document.getElementById("pvp-cost").value) || 0,
        parts_markup_pct: parseFloat(document.getElementById("pvp-markup").value) || 0,
        cp_labor_rate: parseFloat(document.getElementById("pvp-rate").value) || 0,
        labor_hours: parseFloat(document.getElementById("pvp-hours").value) || 0,
      };
      scheduleSave(true);
    });
  });
}

function renderAdvisorOps() {
  const section = panelSection(
    "Advisor cheat sheet",
    "OP codes, descriptions, and pricing for service advisors.",
    `${project.advisor_packages.length} packages`
  );
  const wrap = el("div", "data-table-wrap");
  let lastSection = "";
  const rows = project.advisor_packages.map(pkg => {
    let sectionRow = "";
    if (pkg.section !== lastSection) {
      lastSection = pkg.section;
      sectionRow = `<tr class="section-row"><td colspan="6">${escapeHtml(pkg.section)}</td></tr>`;
    }
    return sectionRow + `
      <tr data-id="${pkg.id}">
        <td class="op-code-col"><input value="${escapeAttr(pkg.op_code)}" data-field="op_code" placeholder="—" /></td>
        <td class="desc-col"><textarea data-field="description" placeholder="—">${escapeHtml(pkg.description)}</textarea></td>
        <td class="num"><input type="number" step="0.01" value="${pkg.parts}" data-field="parts" placeholder="—" /></td>
        <td class="num"><input type="number" step="0.01" value="${pkg.time}" data-field="time" placeholder="—" /></td>
        <td class="num"><input type="number" step="0.01" value="${pkg.labor}" data-field="labor" placeholder="—" /></td>
        <td class="num"><input type="number" step="0.01" value="${pkg.total}" data-field="total" placeholder="—" /></td>
      </tr>`;
  }).join("");

  wrap.innerHTML = `<table class="data-table advisor-table">
    <colgroup>
      <col class="col-op-code" />
      <col class="col-description" />
      <col class="col-parts" />
      <col class="col-time" />
      <col class="col-labor" />
      <col class="col-total" />
    </colgroup>
    <thead><tr><th>OP code</th><th>Description</th><th class="num">Parts</th><th class="num">Time</th><th class="num">Labor</th><th class="num">Total</th></tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
  wrap.querySelectorAll("textarea").forEach(autoSizeTextarea);
  wrap.querySelectorAll("input, textarea").forEach(input => {
    input.addEventListener("input", e => {
      if (e.target.tagName === "TEXTAREA") autoSizeTextarea(e.target);
      const row = e.target.closest("tr");
      const pkg = project.advisor_packages.find(p => p.id === row.dataset.id);
      if (!pkg) return;
      const f = e.target.dataset.field;
      pkg[f] = ["parts", "time", "labor", "total"].includes(f) ? parseFloat(e.target.value) || 0 : e.target.value;
      scheduleSave();
    });
  });
  section.appendChild(wrap);
  els.stepContent.appendChild(section);
}

function renderPartsPull() {
  const section = panelSection(
    "Parts pull sheet",
    "Part numbers and sale prices for the parts department.",
    `${project.parts_pull.length} line items`
  );
  const wrap = el("div", "data-table-wrap");
  const rows = project.parts_pull.map(row => {
    const isPackageRow = row.op_code_or_part === row.section && !row.parts_sale;
    return `
    <tr data-id="${row.id}" class="${isPackageRow ? "parts-package-row" : "parts-line-row"}">
      <td class="op-code-col"><input value="${escapeAttr(row.op_code_or_part)}" data-field="op_code_or_part" placeholder="—" /></td>
      <td class="desc-col"><textarea data-field="description" placeholder="—">${escapeHtml(row.description)}</textarea></td>
      <td class="num"><input value="${escapeAttr(String(row.parts_sale))}" data-field="parts_sale" placeholder="${isPackageRow ? "" : "Vin Specific"}" /></td>
    </tr>
  `;
  }).join("");

  wrap.innerHTML = `<table class="data-table parts-pull-table">
    <colgroup>
      <col class="col-op-code" />
      <col class="col-description" />
      <col class="col-parts-sale" />
    </colgroup>
    <thead><tr><th>OP code / Part #</th><th>Description</th><th class="num">Parts sale</th></tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
  wrap.querySelectorAll("textarea").forEach(autoSizeTextarea);
  wrap.querySelectorAll("input, textarea").forEach(input => {
    input.addEventListener("input", e => {
      if (e.target.tagName === "TEXTAREA") autoSizeTextarea(e.target);
      const tr = e.target.closest("tr");
      const row = project.parts_pull.find(p => p.id === tr.dataset.id);
      if (!row) return;
      const f = e.target.dataset.field;
      const val = e.target.value;
      row[f] = f === "parts_sale" && val !== "" && !isNaN(val) ? parseFloat(val) : val;
      scheduleSave();
    });
  });
  section.appendChild(wrap);
  els.stepContent.appendChild(section);
}

function updateNavButtons() {
  els.btnPrev.disabled = currentStep === 0;
  els.btnNext.style.display = currentStep < STEPS.length - 1 ? "inline-flex" : "none";
  const done = project.steps_completed[currentStep];
  els.btnComplete.textContent = done ? "Completed ✓" : "Mark step complete";
  els.btnComplete.classList.toggle("success", !done);
  els.btnComplete.disabled = done;
}

function goToStep(step) {
  currentStep = step;
  project.current_step = step;
  scheduleSave();
  render();
}

els.btnPrev.addEventListener("click", () => goToStep(Math.max(0, currentStep - 1)));
els.btnNext.addEventListener("click", () => goToStep(Math.min(STEPS.length - 1, currentStep + 1)));
els.advisorOpsExport.addEventListener("click", preventDisabledExport);
els.partsPullExport.addEventListener("click", preventDisabledExport);

els.btnComplete.addEventListener("click", () => {
  project.steps_completed[currentStep] = true;
  if (currentStep < STEPS.length - 1) {
    currentStep += 1;
    project.current_step = currentStep;
  }
  scheduleSave();
  render();
});

function setSaveStatus(state, text) {
  els.saveStatus.textContent = text;
  els.saveStatus.className = "save-pill";
  if (state) els.saveStatus.classList.add(state);
}

function preventDisabledExport(event) {
  if (event.currentTarget.getAttribute("aria-disabled") === "true") {
    event.preventDefault();
  }
}

function scheduleSave(recalc = false) {
  clearTimeout(saveTimer);
  setSaveStatus("saving", "Saving…");
  saveTimer = setTimeout(async () => {
    await saveProject();
    if (recalc) {
      await loadCalculations();
      if (currentStep === 1 || currentStep === 2) renderStepContent();
    }
  }, 500);
}

async function saveProject() {
  try {
    const res = await fetch(`/api/menu-projects/${projectId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        current_step: project.current_step,
        steps_completed: project.steps_completed,
        pricing: project.pricing,
        products: project.products,
        pmp_services: project.pmp_services,
        pvp: project.pvp,
        advisor_packages: project.advisor_packages,
        parts_pull: project.parts_pull,
      }),
    });
    if (!res.ok) throw new Error();
    project = await res.json();
    setSaveStatus("saved", "Saved");
    updateProgress();
    renderStepNav();
    updateNavButtons();
  } catch {
    setSaveStatus("", "Save failed");
  }
}

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text) e.textContent = text;
  return e;
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

function escapeAttr(s) {
  return String(s).replace(/"/g, "&quot;");
}

function fmt(n) {
  if (n == null || isNaN(n)) return "0.00";
  return Number(n).toFixed(2);
}

function autoSizeTextarea(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = `${Math.max(textarea.scrollHeight, 44)}px`;
}

init();
