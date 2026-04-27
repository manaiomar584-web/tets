const state = {
  jobs: [],
  currentUser: null,
  theme: localStorage.getItem("theme") || "light",
};

const deviceTypeLabels = {
  Computer: "Ordinateur",
  Laptop: "Portable",
  Desktop: "Bureau",
  PDA: "PDA",
  Phone: "Telephone",
  Tablet: "Tablette",
  "Smart Watch": "Montre connectee",
  Camera: "Camera",
  CCTV: "CCTV",
  Monitor: "Moniteur",
  Television: "Television",
  Printer: "Imprimante",
  Scanner: "Scanner",
  Projector: "Projecteur",
  "Game Console": "Console",
  Speaker: "Haut-parleur",
  Amplifier: "Amplificateur",
  Router: "Routeur",
  Modem: "Modem",
  "POS Terminal": "Terminal POS",
  UPS: "UPS",
  Inverter: "Onduleur",
  "Power Supply": "Alimentation",
  Keyboard: "Clavier",
  Mouse: "Souris",
  "External Drive": "Disque externe",
  Other: "Autre",
};

const statusLabels = {
  Received: "Recu",
  Diagnosis: "Diagnostic",
  Repairing: "Reparation",
  Ready: "Pret",
  Delivered: "Livre",
};

const statusOrder = {
  Received: 1,
  Diagnosis: 2,
  Repairing: 3,
  Ready: 4,
  Delivered: 5,
};

const subcontractReturnLabels = {
  Pending: "Envoye, pas encore revenu",
  Returned: "Revenu",
};

// UI Elements
const authShell = document.getElementById("authShell");
const appShell = document.getElementById("appShell");
const loginForm = document.getElementById("loginForm");
const repairForm = document.getElementById("repairForm");
const scanForm = document.getElementById("scanForm");
const jobsList = document.getElementById("jobsList");
const searchInput = document.getElementById("searchInput");
const filterStatus = document.getElementById("filterStatus");
const formTitle = document.getElementById("formTitle");
const saveButton = document.getElementById("saveButton");
const scanResult = document.getElementById("scanResult");
const logoutButton = document.getElementById("logoutButton");
const resetButton = document.getElementById("resetButton");
const printFormButton = document.getElementById("printFormButton");
const printPickupFormButton = document.getElementById("printPickupFormButton");
const exportButton = document.getElementById("exportButton");
const importButton = document.getElementById("importButton");
const clearAllButton = document.getElementById("clearAllButton");
const themeToggle = document.getElementById("themeToggle");
const themeIcon = document.getElementById("themeIcon");
const toastContainer = document.getElementById("toast-container");

const importInput = document.createElement("input");
importInput.type = "file";
importInput.accept = ".xlsx,.xls";

// Notification System
function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${message}</span>`;
  toastContainer.appendChild(toast);
  setTimeout(() => toast.classList.add("show"), 10);
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// Theme Logic
function applyTheme() {
  document.body.setAttribute("data-theme", state.theme);
  const icon = document.getElementById("themeIcon");
  if (state.theme === "dark") {
    icon.innerHTML = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>';
  } else {
    icon.innerHTML = '<circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>';
  }
  localStorage.setItem("theme", state.theme);
}

themeToggle.addEventListener("click", () => {
  state.theme = state.theme === "light" ? "dark" : "light";
  applyTheme();
});

// API Helper
async function api(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    let message = "Erreur";
    try {
      const errorPayload = await response.json();
      message = errorPayload.detail || errorPayload.error || message;
    } catch (e) {}
    throw new Error(message);
  }
  if (response.status === 204) return null;
  return response.json();
}

function getStatusClass(status) {
  return `status-${String(status || "").toLowerCase()}`;
}

function formatMoney(value) {
  const num = Number(value);
  if (isNaN(num) || value === "" || value === null) return "-";
  return num.toLocaleString("fr-FR", { minimumFractionDigits: 2 }) + " TND";
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  return isNaN(date.getTime()) ? value : date.toLocaleDateString("fr-FR");
}

function getCheckedValues(name) {
  return Array.from(document.querySelectorAll(`input[name="${name}"]:checked`)).map(i => i.value);
}

function setCheckedValues(name, values) {
  const set = new Set(values || []);
  document.querySelectorAll(`input[name="${name}"]`).forEach(i => i.checked = set.has(i.value));
}

function renderTimeline(currentStatus) {
  const steps = ["Received", "Diagnosis", "Repairing", "Ready", "Delivered"];
  const currentIndex = steps.indexOf(currentStatus);
  return `
    <div class="timeline">
      ${steps.map((s, i) => `
        <div class="step ${i <= currentIndex ? 'done' : ''} ${i === currentIndex ? 'active' : ''}" title="${statusLabels[s]}"></div>
      `).join("")}
    </div>
  `;
}

function renderRevenueChart() {
  const svg = document.getElementById("revenueSvg");
  if (!svg) return;
  const delivered = state.jobs.filter(j => j.status === "Delivered" && j.delivered_date);
  const now = new Date();
  const last7Days = [...Array(7)].map((_, i) => {
    const d = new Date();
    d.setDate(now.getDate() - (6 - i));
    return d.toISOString().split("T")[0];
  });

  const totals = last7Days.map(day => {
    return delivered
      .filter(j => (j.delivered_date || "").startsWith(day))
      .reduce((sum, j) => sum + Number(j.amount || 0), 0);
  });

  const max = Math.max(...totals, 100);
  const barWidth = 30;
  const gap = 12;

  svg.innerHTML = totals.map((val, i) => {
    const h = (val / max) * 120;
    const x = i * (barWidth + gap) + 10;
    const y = 130 - h;
    return `<rect class="bar-rect" x="${x}" y="${y}" width="${barWidth}" height="${h}" title="${val} TND">
              <title>${last7Days[i]}: ${val} TND</title>
            </rect>`;
  }).join("");
}

function renderJobs() {
  const totalJobs = document.getElementById("totalJobs");
  const waitingJobs = document.getElementById("waitingJobs");
  const readyJobs = document.getElementById("readyJobs");
  const deliveredJobs = document.getElementById("deliveredJobs");

  if (totalJobs) totalJobs.textContent = state.jobs.length;
  if (waitingJobs) waitingJobs.textContent = state.jobs.filter(j => !["Ready", "Delivered"].includes(j.status)).length;
  if (readyJobs) readyJobs.textContent = state.jobs.filter(j => j.status === "Ready").length;
  if (deliveredJobs) deliveredJobs.textContent = state.jobs.filter(j => j.status === "Delivered").length;

  renderRevenueChart();

  const query = searchInput.value.toLowerCase();
  const status = filterStatus.value;
  
  const filtered = state.jobs.filter(j => {
    const haystack = `${j.customer_name} ${j.phone_number} ${j.product_number} ${j.job_id} ${j.brand_model} ${j.scan_reference}`.toLowerCase();
    return haystack.includes(query) && (status === "All" || j.status === status);
  });

  if (!filtered.length) {
    jobsList.innerHTML = '<div class="empty">Aucun dossier trouve.</div>';
    return;
  }

  jobsList.innerHTML = filtered.map(j => `
    <div class="table-row">
      <div data-label="Code"><strong>${j.product_number}</strong><div class="muted">${j.scan_reference || "N/A"}</div></div>
      <div data-label="Interne"><strong>${j.job_id}</strong><div class="muted">${j.serial_number || "N/A"}</div></div>
      <div data-label="Type">${deviceTypeLabels[j.device_type] || j.device_type}</div>
      <div data-label="Client">
        <div style="display:flex; align-items:center; gap:0.5rem;">
          <strong>${j.customer_name}</strong>
          <button class="icon-button" style="padding:2px 4px; font-size:10px;" onclick="filterByCustomer('${j.phone_number}')" title="Historique client">📜</button>
        </div>
        <div class="muted">${j.brand_model || "Sans modele"}</div>
      </div>
      <div data-label="Statut">
        <span class="status-pill ${getStatusClass(j.status)}">${statusLabels[j.status]}</span>
        ${renderTimeline(j.status)}
      </div>
      <div data-label="Depot">${formatDate(j.received_date)}</div>
      <div data-label="Montant">${formatMoney(j.amount)}</div>
      <div data-label="SN/PN">${j.scan_reference || "-"}</div>
      <div data-label="Tel">${j.phone_number || "-"}</div>
      <div data-label="Atelier">${j.is_subcontracted === "Yes" ? (j.subcontract_company || "Externe") : "Interne"}</div>
      <div class="row-actions">
        <button class="icon-button" onclick="printJob('${j.id}')" title="Bon Depot (Impression)">📥</button>
        <button class="icon-button" onclick="downloadJobPDF('${j.id}')" title="Bon Depot (PDF)">📄</button>
        <button class="icon-button" onclick="printPickupSlip('${j.id}')" title="Bon Retrait (Impression)">📤</button>
        <button class="icon-button" onclick="downloadPickupPDF('${j.id}')" title="Bon Retrait (PDF)">📑</button>
        <button class="icon-button" onclick="editJob('${j.id}')" title="Modifier">✏️</button>
        ${state.currentUser.role === 'admin' ? `<button class="icon-button" onclick="deleteJob('${j.id}')" title="Supprimer">🗑️</button>` : ''}
      </div>
    </div>
  `).join("");
}

window.downloadJobPDF = (id) => {
  window.open(`/api/jobs/${id}/pdf?type=depot`, "_blank");
  showToast("Telechargement du PDF (Depot)...", "info");
};

window.downloadPickupPDF = (id) => {
  window.open(`/api/jobs/${id}/pdf?type=retrait`, "_blank");
  showToast("Telechargement du PDF (Retrait)...", "info");
};

window.filterByCustomer = (phone) => {
  if (!phone) return;
  searchInput.value = phone;
  renderJobs();
  showToast(`Affichage de l'historique pour ${phone}`, "info");
};

async function loadJobs() {
  try {
    const res = await api("/api/jobs");
    state.jobs = res.jobs || [];
    renderJobs();
  } catch (e) {
    showToast(e.message, "error");
  }
}

function resetForm() {
  repairForm.reset();
  document.getElementById("editingId").value = "";
  document.getElementById("receivedDate").value = new Date().toISOString().split("T")[0];
  formTitle.textContent = "Nouveau dossier";
  saveButton.textContent = "Enregistrer";
}

function populateForm(j) {
  resetForm();

  document.getElementById("editingId").value = j.id || "";
  document.getElementById("customerName").value = j.customer_name || "";
  document.getElementById("phoneNumber").value = j.phone_number || "";
  document.getElementById("deviceType").value = j.device_type || "Computer";
  document.getElementById("status").value = j.status || "Received";
  document.getElementById("brandModel").value = j.brand_model || "";
  document.getElementById("serialNumber").value = j.serial_number || "";
  document.getElementById("scanReference").value = j.scan_reference || "";
  document.getElementById("receivedDate").value = (j.received_date || "").split('T')[0];
  document.getElementById("deliveryDecision").value = j.delivery_decision || "Pending";
  document.getElementById("deliveredDate").value = (j.delivered_date || "").split('T')[0];
  document.getElementById("amount").value = j.amount || "";
  document.getElementById("paidStatus").value = j.paid_status || "No";
  document.getElementById("problem").value = j.problem || "";
  document.getElementById("repairDone").value = j.repair_done || "";
  document.getElementById("notes").value = j.notes || "";
  document.getElementById("otherAccessory").value = j.other_accessory || "";
  document.getElementById("conditionRemarks").value = j.condition_remarks || "";
  document.getElementById("technicianName").value = j.technician_name || "";
  document.getElementById("isSubcontracted").value = j.is_subcontracted || "No";
  document.getElementById("subcontractCompany").value = j.subcontract_company || "";
  document.getElementById("subcontractSentDate").value = (j.subcontract_sent_date || "").split('T')[0];
  document.getElementById("subcontractReturnStatus").value = j.subcontract_return_status || "Pending";
  document.getElementById("subcontractReturnedDate").value = (j.subcontract_returned_date || "").split('T')[0];
  document.getElementById("subcontractNotes").value = j.subcontract_notes || "";
  
  const accessories = Array.isArray(j.accessories) ? j.accessories : (typeof j.accessories === 'string' ? JSON.parse(j.accessories) : []);
  const condition = Array.isArray(j.device_condition) ? j.device_condition : (typeof j.device_condition === 'string' ? JSON.parse(j.device_condition) : []);
  const returnCond = Array.isArray(j.return_condition) ? j.return_condition : (typeof j.return_condition === 'string' ? JSON.parse(j.return_condition) : []);
  
  setCheckedValues("accessories", accessories);
  setCheckedValues("deviceCondition", condition);
  setCheckedValues("returnCondition", returnCond);
  
  formTitle.textContent = "Modifier dossier";
  saveButton.textContent = "Mettre a jour";
  window.scrollTo({ top: 0, behavior: "smooth" });
  showToast(`Edition du dossier ${j.product_number}`, "info");
}

window.editJob = (id) => {
  const j = state.jobs.find(i => i.id === id);
  if (j) populateForm(j);
};

window.deleteJob = async (id) => {
  if (!confirm("Supprimer ce dossier ?")) return;
  try {
    await api(`/api/jobs/${id}`, { method: "DELETE" });
    showToast("Dossier supprime", "success");
    await loadJobs();
  } catch (e) {
    showToast(e.message, "error");
  }
};

function fillPrintSlip(job) {
  document.getElementById("slipProductNumber").textContent = job.product_number || "-";
  document.getElementById("slipCustomerName").textContent = job.customer_name || "-";
  document.getElementById("slipPhoneNumber").textContent = job.phone_number || "-";
  document.getElementById("slipDeviceType").textContent = deviceTypeLabels[job.device_type] || job.device_type || "-";
  document.getElementById("slipBrandModel").textContent = job.brand_model || "-";
  document.getElementById("slipSerialNumber").textContent = job.serial_number || "-";
  document.getElementById("slipScanReference").textContent = job.scan_reference || "-";
  document.getElementById("slipJobId").textContent = job.job_id || "-";
  document.getElementById("slipReceivedDate").textContent = formatDate(job.received_date);
  document.getElementById("slipProblem").textContent = job.problem || "-";
  
  const accList = document.getElementById("slipAccessories");
  const accessories = Array.isArray(job.accessories) ? job.accessories : (job.accessories ? JSON.parse(job.accessories) : []);
  accList.innerHTML = ["Chargeur", "Cable d'alimentation", "Batterie", "Sac / Housse"].map(a =>
    `<div>[${accessories.includes(a) ? 'x' : ' '}] ${a}</div>`
  ).join("");

  const condList = document.getElementById("slipCondition");
  const condition = Array.isArray(job.device_condition) ? job.device_condition : (job.device_condition ? JSON.parse(job.device_condition) : []);
  condList.innerHTML = ["Bon etat", "Rayures", "Pieces cassees", "Ecran endommage", "Pieces manquantes"].map(c =>
    `<div>[${condition.includes(c) ? 'x' : ' '}] ${c}</div>`
  ).join("");
  
  document.getElementById("slipOtherAccessory").textContent = job.other_accessory || "-";
  document.getElementById("slipConditionRemarks").textContent = job.condition_remarks || "-";
  document.getElementById("slipTechnicianName").textContent = job.technician_name || "Signature du technicien";
}

function fillPickupSlip(job) {
  document.getElementById("pickupProductNumber").textContent = job.product_number || "-";
  document.getElementById("pickupDate").textContent = formatDate(job.delivered_date || new Date().toISOString());
  document.getElementById("pickupCustomerName").textContent = job.customer_name || "-";
  document.getElementById("pickupDeviceType").textContent = deviceTypeLabels[job.device_type] || job.device_type || "-";
  document.getElementById("pickupBrandModel").textContent = job.brand_model || "-";
  document.getElementById("pickupRepairDone").textContent = job.repair_done || "-";
  document.getElementById("pickupAmount").textContent = job.amount || "0.00";
  document.getElementById("pickupPaidStatus").textContent = String(job.paid_status || "").toLowerCase() === "yes" ? "☒ Oui ☐ Non" : "☐ Oui ☒ Non";
  document.getElementById("pickupTechnicianName").textContent = job.technician_name || "Signature du technicien";
  const returnState = document.getElementById("pickupReturnState");
  const selected = Array.isArray(job.return_condition) ? job.return_condition : (job.return_condition ? JSON.parse(job.return_condition) : []);
  returnState.innerHTML = ["Teste et fonctionnel", "Restitue en bon etat", "Client satisfait"].map(item =>
    `<div>[${selected.includes(item) ? 'x' : ' '}] ${item}</div>`
  ).join("");
}

function setPrintMode(mode) {
  document.body.classList.remove("print-mode-deposit", "print-mode-pickup");
  if (mode === "deposit") document.body.classList.add("print-mode-deposit");
  if (mode === "pickup") document.body.classList.add("print-mode-pickup");
}

window.printJob = (id) => {
  const j = state.jobs.find(i => i.id === id);
  if (!j) return;
  fillPrintSlip(j);
  setPrintMode("deposit");
  window.print();
};

window.printPickupSlip = (id) => {
  const j = state.jobs.find(i => i.id === id);
  if (!j) return;
  fillPickupSlip(j);
  setPrintMode("pickup");
  window.print();
};

if (printFormButton) {
  printFormButton.addEventListener("click", () => {
    const id = document.getElementById("editingId").value;
    if (id) {
      window.printJob(id);
    } else {
      showToast("Veuillez d'abord enregistrer ou selectionner un dossier", "warning");
    }
  });
}

if (printPickupFormButton) {
  printPickupFormButton.addEventListener("click", () => {
    const id = document.getElementById("editingId").value;
    if (id) {
      window.printPickupSlip(id);
    } else {
      showToast("Veuillez d'abord enregistrer ou selectionner un dossier", "warning");
    }
  });
}

// Event Listeners
loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const res = await api("/api/login", {
      method: "POST",
      body: JSON.stringify({
        username: loginForm.loginUsername.value.trim(),
        password: loginForm.loginPassword.value
      })
    });
    state.currentUser = res.user;
    authShell.style.display = "none";
    appShell.classList.remove("app-hidden");
    showToast(`Bienvenue ${res.user.full_name}`, "success");
    await loadJobs();
  } catch (e) {
    document.getElementById("authMessage").textContent = e.message;
  }
});

repairForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("editingId").value;
  const payload = {
    customerName: document.getElementById("customerName").value.trim(),
    phoneNumber: document.getElementById("phoneNumber").value.trim(),
    deviceType: document.getElementById("deviceType").value,
    status: document.getElementById("status").value,
    brandModel: document.getElementById("brandModel").value.trim(),
    serialNumber: document.getElementById("serialNumber").value.trim(),
    productNumber: "", // Usually server-side, but keep field
    scanReference: document.getElementById("scanReference").value.trim(),
    receivedDate: document.getElementById("receivedDate").value,
    deliveryDecision: document.getElementById("deliveryDecision").value,
    deliveredDate: document.getElementById("deliveredDate").value,
    amount: document.getElementById("amount").value,
    paidStatus: document.getElementById("paidStatus").value,
    problem: document.getElementById("problem").value.trim(),
    repairDone: document.getElementById("repairDone").value.trim(),
    notes: document.getElementById("notes").value.trim(),
    accessories: getCheckedValues("accessories"),
    otherAccessory: document.getElementById("otherAccessory").value.trim(),
    deviceCondition: getCheckedValues("deviceCondition"),
    conditionRemarks: document.getElementById("conditionRemarks").value.trim(),
    technicianName: document.getElementById("technicianName").value.trim(),
    returnCondition: getCheckedValues("returnCondition"),
    isSubcontracted: document.getElementById("isSubcontracted").value,
    subcontractCompany: document.getElementById("subcontractCompany").value.trim(),
    subcontractSentDate: document.getElementById("subcontractSentDate").value,
    subcontractReturnStatus: document.getElementById("subcontractReturnStatus").value,
    subcontractReturnedDate: document.getElementById("subcontractReturnedDate").value,
    subcontractNotes: document.getElementById("subcontractNotes").value.trim(),
  };

  try {
    if (id) {
      await api(`/api/jobs/${id}`, { method: "PUT", body: JSON.stringify(payload) });
      showToast("Dossier mis a jour", "success");
    } else {
      await api("/api/jobs", { method: "POST", body: JSON.stringify(payload) });
      showToast("Dossier cree", "success");
    }
    await loadJobs();
    resetForm();
  } catch (e) {
    showToast(e.message, "error");
  }
});

scanForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const scanCode = document.getElementById("scanCode").value.trim();
  try {
    await api("/api/jobs/scan", {
      method: "POST",
      body: JSON.stringify({
        scanCode,
        customerName: document.getElementById("scanCustomerName").value.trim(),
        deviceType: document.getElementById("scanDeviceType").value,
        brandModel: document.getElementById("scanBrandModel").value.trim(),
      })
    });
    showToast("Enregistrement rapide reussi", "success");
    scanForm.reset();
    await loadJobs();
  } catch (e) {
    showToast(e.message, "error");
  }
});

logoutButton.addEventListener("click", async () => {
  await api("/api/logout", { method: "POST" });
  location.reload();
});

[searchInput, filterStatus].forEach(el => {
  if (el) el.addEventListener("input", renderJobs);
});

async function init() {
  applyTheme();
  try {
    const res = await api("/api/session");
    if (res.user) {
      state.currentUser = res.user;
      authShell.style.display = "none";
      appShell.classList.remove("app-hidden");
      document.getElementById("sessionName").textContent = res.user.full_name;
      document.getElementById("sessionRole").textContent = res.user.username;
      document.getElementById("roleBadge").textContent = res.user.role === "admin" ? "Administrateur" : "Utilisateur";
      await loadJobs();
    }
  } catch (e) {}
}

// Autocomplete Logic
async function handleAutocomplete(input, listId, otherInputId) {
  const query = input.value.trim();
  if (query.length < 2) return;

  try {
    const res = await api(`/api/customers/search?q=${encodeURIComponent(query)}`);
    const customers = res.customers || [];
    const list = document.getElementById(listId);
    list.innerHTML = customers
      .map(c => `<option value="${listId === 'customerNamesList' ? c.name : c.phone}">${c.name} - ${c.phone}</option>`)
      .join("");
    
    const match = customers.find(c => c.name === query || c.phone === query);
    if (match) {
      const otherInput = document.getElementById(otherInputId);
      if (otherInput && !otherInput.value) {
        otherInput.value = (otherInputId === 'phoneNumber') ? match.phone : match.name;
        showToast("Client reconnu, informations recuperees", "info");
      }
    }
  } catch (e) {}
}

const nameInput = document.getElementById("customerName");
if (nameInput) {
  nameInput.addEventListener("input", (e) => {
    handleAutocomplete(e.target, "customerNamesList", "phoneNumber");
  });
}

const phoneInput = document.getElementById("phoneNumber");
if (phoneInput) {
  phoneInput.addEventListener("input", (e) => {
    handleAutocomplete(e.target, "customerPhonesList", "customerName");
  });
}

if (exportButton) {
  exportButton.addEventListener("click", () => {
    window.open("/api/export", "_blank");
  });
}

if (importButton) {
  importButton.addEventListener("click", () => {
    importInput.click();
  });
}

importInput.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async (event) => {
    const base64 = event.target.result.split(",")[1];
    try {
      const res = await api("/api/import", {
        method: "POST",
        body: JSON.stringify({ content_base64: base64 })
      });
      showToast(`${res.imported} dossiers importes`, "success");
      await loadJobs();
    } catch (err) {
      showToast(err.message, "error");
    }
  };
  reader.readAsDataURL(file);
});

if (clearAllButton) {
  clearAllButton.addEventListener("click", async () => {
    if (!confirm("Voulez-vous vraiment supprimer TOUS les dossiers ? Cette action est irreversible.")) return;
    try {
      await api("/api/jobs", { method: "DELETE" });
      showToast("Base de donnees videe", "success");
      await loadJobs();
    } catch (e) {
      showToast(e.message, "error");
    }
  });
}

if (resetButton) {
  resetButton.addEventListener("click", resetForm);
}

init();
