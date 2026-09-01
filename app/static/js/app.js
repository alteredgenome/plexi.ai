// Plexi Enterprise Client State
let currentToken = localStorage.getItem("plexi_token");
let currentUser = JSON.parse(localStorage.getItem("plexi_user") || "null");
let currentHouseholdId = 1;
let allUsersCache = [];

document.addEventListener("DOMContentLoaded", async () => {
  if (window.lucide) lucide.createIcons();
  await checkSetupOrAuth();
});

function showToast(msg) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.innerText = msg;
  toast.classList.remove("opacity-0", "pointer-events-none");
  toast.classList.add("opacity-100");
  setTimeout(() => {
    toast.classList.add("opacity-0", "pointer-events-none");
    toast.classList.remove("opacity-100");
  }, 4000);
}

// Modal Open/Close Utilities
function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove("hidden");
  if (window.lucide) lucide.createIcons();
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add("hidden");
}

function openAddUserModal() { openModal("modal-add-user"); }
function openAssignDeviceModal() {
  const select = document.getElementById("assign-device-user");
  if (select && allUsersCache.length > 0) {
    select.innerHTML = allUsersCache.map(u => `<option value="${u.id}">${u.full_name} (${u.email})</option>`).join("");
  }
  openModal("modal-assign-device");
}
function openPavlokConfigModal() { openModal("modal-pavlok-config"); }
function openRingConnConfigModal() { openModal("modal-ringconn-config"); }
function openHAConfigModal() { openModal("modal-ha-config"); }
function openSyncModal() { openModal("modal-sync"); }
function openImportModal() { openModal("modal-import"); }
function openNewTaskModal() { openModal("modal-task"); }
function openDecomposeModal() { openModal("modal-decompose"); }
function openNewExpenseModal() { openModal("modal-expense"); }

// 1. Setup Wizard & Auth Check
async function checkSetupOrAuth() {
  try {
    const resp = await fetch("/api/v1/setup/status");
    const status = await resp.json();

    if (!status.is_setup_completed) {
      const overlay = document.getElementById("setup-wizard-overlay");
      if (overlay) overlay.classList.remove("hidden");
      return;
    }

    if (!currentToken) {
      promptLoginModal();
    } else {
      await loadDashboardData();
    }
  } catch (e) {
    console.error("Error checking setup status:", e);
  }
}

// Setup Wizard Stepper
function goToWizardStep(stepNum) {
  document.querySelectorAll(".wizard-step").forEach(el => el.classList.add("hidden"));
  const targetStep = document.getElementById(`wizard-step-${stepNum}`);
  if (targetStep) targetStep.classList.remove("hidden");

  for (let i = 1; i <= 2; i++) {
    const ind = document.getElementById(`step-ind-${i}`);
    if (!ind) continue;
    if (i === stepNum) {
      ind.className = "text-indigo-400 font-semibold";
    } else if (i < stepNum) {
      ind.className = "text-emerald-400 font-medium";
    } else {
      ind.className = "text-slate-500 font-medium";
    }
  }
  if (window.lucide) lucide.createIcons();
}

async function submitSetupWizard() {
  const nameInput = document.getElementById("wiz-admin-name");
  const emailInput = document.getElementById("wiz-admin-email");
  const passInput = document.getElementById("wiz-admin-pass");
  const startInput = document.getElementById("wiz-work-start");
  const endInput = document.getElementById("wiz-work-end");

  const name = nameInput ? nameInput.value.trim() : "";
  const email = emailInput ? emailInput.value.trim() : "";
  const pass = passInput ? passInput.value : "";
  const startH = startInput ? (parseInt(startInput.value) || 9) : 9;
  const endH = endInput ? (parseInt(endInput.value) || 18) : 18;

  const openrouterKey = document.getElementById("wiz-openrouter-key") ? document.getElementById("wiz-openrouter-key").value.trim() : "";
  const openrouterModel = document.getElementById("wiz-openrouter-model") ? document.getElementById("wiz-openrouter-model").value : "google/gemma-2-9b-it:free";

  if (!name || !email || !pass) {
    showToast("Please provide administrator name, email, and master password.");
    goToWizardStep(1);
    return;
  }

  showToast("Initializing Plexi instance...");

  try {
    const resp = await fetch("/api/v1/setup/initialize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        admin_email: email,
        admin_password: pass,
        admin_name: name,
        work_start_hour: startH,
        work_end_hour: endH,
        openrouter_api_key: openrouterKey || null,
        openrouter_model: openrouterModel || "google/gemma-2-9b-it:free"
      })
    });

    if (!resp.ok) {
      const err = await resp.json();
      let errorMsg = "Setup initialization failed.";
      if (typeof err.detail === "string") {
        errorMsg = err.detail;
      } else if (Array.isArray(err.detail) && err.detail.length > 0) {
        errorMsg = err.detail[0].msg || err.detail[0].message || JSON.stringify(err.detail[0]);
      }
      showToast(`Error: ${errorMsg}`);
      return;
    }

    const data = await resp.json();
    currentToken = data.access_token;
    localStorage.setItem("plexi_token", currentToken);

    document.getElementById("setup-wizard-overlay").classList.add("hidden");
    showToast("Plexi successfully initialized! Welcome.");

    await loadDashboardData();
  } catch (e) {
    console.error("Setup error:", e);
    showToast("Network error connecting to setup API.");
  }
}

function promptLoginModal() {
  const email = prompt("Plexi Enterprise Login\nEnter email:") || "admin@plexi.fyi";
  const pass = prompt("Enter password:") || "";
  
  if (!pass) return;

  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", pass);

  fetch("/api/v1/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: formData
  }).then(r => r.json()).then(data => {
    if (data.access_token) {
      currentToken = data.access_token;
      localStorage.setItem("plexi_token", currentToken);
      showToast("Logged in successfully!");
      loadDashboardData();
    } else {
      showToast("Authentication failed.");
    }
  }).catch(() => showToast("Login failed."));
}

async function loadDashboardData() {
  await Promise.all([
    loadAgenda(),
    loadProjects(),
    loadFinance(),
    loadBiometrics(),
    loadAdminData()
  ]);
}

// Navigation Tabs
function switchTab(tabName) {
  document.querySelectorAll(".tab-pane").forEach(el => el.classList.add("hidden"));
  document.querySelectorAll(".nav-tab").forEach(el => {
    el.classList.remove("bg-indigo-600/20", "text-indigo-400", "border-indigo-500/30");
    el.classList.add("text-slate-400");
  });

  const activePane = document.getElementById(`pane-${tabName}`);
  const activeBtn = document.getElementById(`tab-${tabName}`);
  if (activePane) activePane.classList.remove("hidden");
  if (activeBtn) {
    activeBtn.classList.add("bg-indigo-600/20", "text-indigo-400", "border-indigo-500/30");
    activeBtn.classList.remove("text-slate-400");
  }

  if (tabName === "admin") {
    loadAdminData();
  }

  if (window.lucide) lucide.createIcons();
}

// TAB 1: Load Agenda
async function loadAgenda() {
  if (!currentToken) return;
  const headers = { "Authorization": `Bearer ${currentToken}` };
  const todayStr = new Date().toISOString().split("T")[0];

  try {
    const [evResp, taskResp] = await Promise.all([
      fetch(`/api/v1/calendars/events?start_date=${todayStr}T00:00:00&end_date=${todayStr}T23:59:59`, { headers }),
      fetch(`/api/v1/tasks/`, { headers })
    ]);

    const events = await evResp.json();
    const tasks = await taskResp.json();

    const container = document.getElementById("timeline-container");
    if (!container) return;
    container.innerHTML = "";

    let timelineItems = [];

    if (Array.isArray(events)) {
      events.forEach(ev => {
        const s = new Date(ev.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const e = new Date(ev.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        if (ev.travel_buffer_before_minutes > 0) {
          timelineItems.push({
            time: `${s} (-${ev.travel_buffer_before_minutes}m)`,
            title: `Buffer: Travel & Preparation (${ev.title})`,
            badge: 'Travel Buffer',
            badgeColor: 'amber'
          });
        }

        timelineItems.push({
          time: `${s} - ${e}`,
          title: ev.title,
          badge: 'Fixed Event',
          badgeColor: 'indigo'
        });

        if (ev.recovery_buffer_after_minutes > 0) {
          timelineItems.push({
            time: `${e} (+${ev.recovery_buffer_after_minutes}m)`,
            title: `Buffer: Mental Recovery & Reset (${ev.title})`,
            badge: 'Recovery Window',
            badgeColor: 'amber'
          });
        }
      });
    }

    if (Array.isArray(tasks)) {
      tasks.forEach(t => {
        if (t.scheduled_start) {
          const s = new Date(t.scheduled_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          const e = new Date(t.scheduled_end).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          timelineItems.push({
            time: `${s} - ${e}`,
            title: `Task: ${t.title}`,
            badge: `Auto-Scheduled [${t.priority}]`,
            badgeColor: t.momentum_critical ? 'rose' : 'emerald'
          });
        }
      });
    }

    if (timelineItems.length === 0) {
      container.innerHTML = `<div class="text-xs text-slate-500 py-4">No scheduled events for today. Click 'Import / Sync' or 'Auto-Schedule Day' to optimize.</div>`;
      return;
    }

    timelineItems.forEach(item => {
      const colorClasses = {
        indigo: 'border-indigo-500 bg-indigo-950/40 text-indigo-300',
        amber: 'border-amber-500 bg-amber-950/40 text-amber-300',
        emerald: 'border-emerald-500 bg-emerald-950/40 text-emerald-300',
        rose: 'border-rose-500 bg-rose-950/40 text-rose-300'
      }[item.badgeColor] || 'border-indigo-500 bg-indigo-950/40 text-indigo-300';

      const dotColor = {
        indigo: 'bg-indigo-400',
        amber: 'bg-amber-400',
        emerald: 'bg-emerald-400',
        rose: 'bg-rose-400'
      }[item.badgeColor] || 'bg-indigo-400';

      const div = document.createElement("div");
      div.className = "relative group";
      div.innerHTML = `
        <span class="absolute -left-[31px] top-3.5 w-3 h-3 rounded-full ${dotColor} border-2 border-slate-900 shadow"></span>
        <div class="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition flex items-center justify-between">
          <div>
            <div class="flex items-center space-x-2">
              <span class="text-xs font-semibold text-slate-300 mono">${item.time}</span>
              <span class="text-[10px] px-2 py-0.5 rounded-full border ${colorClasses}">${item.badge}</span>
            </div>
            <h4 class="text-sm font-medium text-slate-200 mt-1">${item.title}</h4>
          </div>
        </div>
      `;
      container.appendChild(div);
    });

    if (window.lucide) lucide.createIcons();
  } catch (e) {
    console.log("Agenda fetch error:", e);
  }
}

async function triggerAutoSchedule() {
  const headers = { "Authorization": `Bearer ${currentToken}` };
  const todayStr = new Date().toISOString().split("T")[0];

  showToast("Running Plexi Dynamic Scheduling Engine...");
  const resp = await fetch(`/api/v1/tasks/auto-schedule?target_date=${todayStr}`, {
    method: "POST",
    headers
  });
  const data = await resp.json();
  showToast(`Auto-scheduled ${data.tasks_scheduled_count} tasks!`);
  await loadAgenda();
  await loadProjects();
}

// Calendar Sync & Import Handlers
async function submitFeedSync() {
  const name = document.getElementById("sync-feed-name").value.trim();
  const url = document.getElementById("sync-feed-url").value.trim();

  if (!url) {
    showToast("Please provide an iCal feed URL.");
    return;
  }

  showToast("Fetching and syncing calendar feed...");
  const headers = {
    "Authorization": `Bearer ${currentToken}`,
    "Content-Type": "application/json"
  };

  try {
    const resp = await fetch("/api/v1/calendars/sync/feed", {
      method: "POST",
      headers,
      body: JSON.stringify({ name: name || "Synced Calendar", feed_url: url })
    });

    if (!resp.ok) {
      const err = await resp.json();
      showToast(`Sync error: ${err.detail || 'Failed to sync feed'}`);
      return;
    }

    const data = await resp.json();
    closeModal("modal-sync");
    showToast(`Successfully synced ${data.events_imported_count} events!`);
    await loadAgenda();
  } catch (e) {
    showToast("Network error syncing feed.");
  }
}

async function submitICSImport() {
  const fileInput = document.getElementById("import-file-input");
  const calName = document.getElementById("import-cal-name").value.trim();

  if (!fileInput.files || fileInput.files.length === 0) {
    showToast("Please select a .ics file.");
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  if (calName) formData.append("calendar_name", calName);

  showToast("Uploading and parsing .ics file...");

  try {
    const resp = await fetch("/api/v1/calendars/import/ics", {
      method: "POST",
      headers: { "Authorization": `Bearer ${currentToken}` },
      body: formData
    });

    if (!resp.ok) {
      const err = await resp.json();
      showToast(`Import error: ${err.detail || 'Failed to import'}`);
      return;
    }

    const data = await resp.json();
    closeModal("modal-import");
    showToast(`Successfully imported ${data.events_imported_count} events!`);
    await loadAgenda();
  } catch (e) {
    showToast("Failed to upload .ics file.");
  }
}

// TAB 2: Projects & Kanban
async function loadProjects() {
  if (!currentToken) return;
  const headers = { "Authorization": `Bearer ${currentToken}` };
  const resp = await fetch("/api/v1/tasks/", { headers });
  const tasks = await resp.json();

  const p1List = document.getElementById("p1-task-list");
  const p3List = document.getElementById("p3-task-list");
  const p4List = document.getElementById("p4-task-list");

  if (!p1List || !p3List || !p4List) return;

  p1List.innerHTML = "";
  p3List.innerHTML = "";
  p4List.innerHTML = "";

  let c1 = 0, c3 = 0, c4 = 0;

  if (Array.isArray(tasks)) {
    tasks.forEach(t => {
      const card = document.createElement("div");
      card.className = "p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition space-y-2";
      
      const momentumBadge = t.momentum_critical 
        ? `<span class="text-[10px] px-1.5 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800">⚡ Pavlok</span>`
        : "";

      const statusBadge = t.is_completed 
        ? `<span class="text-[10px] text-emerald-400">✓ Done</span>`
        : `<span class="text-[10px] text-slate-400">${t.duration_minutes} mins</span>`;

      card.innerHTML = `
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold text-indigo-400">[${t.priority}]</span>
          ${statusBadge}
        </div>
        <div class="text-sm font-medium text-slate-200">${t.title}</div>
        ${t.sop_template ? `<div class="text-xs text-slate-400 bg-slate-950/50 p-2 rounded border border-slate-800/80 mono whitespace-pre-line">${t.sop_template}</div>` : ''}
        <div class="flex items-center justify-between pt-1">
          ${momentumBadge}
          <button onclick="toggleTaskDone(${t.id}, ${!t.is_completed})" class="text-xs text-slate-400 hover:text-emerald-400 transition">
            ${t.is_completed ? "Reopen" : "Mark Complete"}
          </button>
        </div>
      `;

      if (t.priority === "P1" || t.priority === "P2") {
        p1List.appendChild(card);
        c1++;
      } else if (t.priority === "P3") {
        p3List.appendChild(card);
        c3++;
      } else {
        p4List.appendChild(card);
        c4++;
      }
    });
  }

  document.getElementById("p1-count").innerText = c1;
  document.getElementById("p3-count").innerText = c3;
  document.getElementById("p4-count").innerText = c4;
}

async function toggleTaskDone(taskId, isDone) {
  const headers = {
    "Authorization": `Bearer ${currentToken}`,
    "Content-Type": "application/json"
  };
  await fetch(`/api/v1/tasks/${taskId}`, {
    method: "PATCH",
    headers,
    body: JSON.stringify({ is_completed: isDone })
  });
  showToast("Task updated");
  await loadAgenda();
  await loadProjects();
}

// TAB 3: Finance
async function loadFinance() {
  if (!currentToken) return;
  const headers = { "Authorization": `Bearer ${currentToken}` };
  const hhResp = await fetch("/api/v1/finance/households", { headers });
  const hhs = await hhResp.json();
  if (!Array.isArray(hhs) || hhs.length === 0) return;

  const hhId = hhs[0].id;
  currentHouseholdId = hhId;

  const [overResp, itemsResp] = await Promise.all([
    fetch(`/api/v1/finance/overview?household_id=${hhId}`, { headers }),
    fetch(`/api/v1/finance/items?household_id=${hhId}`, { headers })
  ]);

  const overview = await overResp.json();
  const items = await itemsResp.json();

  const setList = document.getElementById("settlement-list");
  if (setList) {
    setList.innerHTML = "";
    if (!overview.suggested_settlements || overview.suggested_settlements.length === 0) {
      setList.innerHTML = `<div class="text-xs text-slate-400 col-span-2">All balances are currently settled!</div>`;
    } else {
      overview.suggested_settlements.forEach(s => {
        const card = document.createElement("div");
        card.className = "p-3 rounded-xl bg-slate-900 border border-slate-700 flex items-center justify-between";
        card.innerHTML = `
          <div>
            <span class="text-xs font-medium text-rose-400">${s.from_user_name}</span>
            <span class="text-xs text-slate-400"> pays </span>
            <span class="text-xs font-medium text-emerald-400">${s.to_user_name}</span>
          </div>
          <div class="text-sm font-bold text-slate-100">$${s.amount.toFixed(2)}</div>
        `;
        setList.appendChild(card);
      });
    }
  }

  const tbody = document.getElementById("ledger-table-body");
  if (tbody && Array.isArray(items)) {
    tbody.innerHTML = "";
    items.forEach(item => {
      const tr = document.createElement("tr");
      tr.className = "hover:bg-slate-900/50";
      tr.innerHTML = `
        <td class="px-6 py-4 font-medium text-slate-200">${item.title}</td>
        <td class="px-6 py-4 text-slate-400 capitalize">${item.category}</td>
        <td class="px-6 py-4 font-semibold text-slate-100">$${item.total_amount.toFixed(2)}</td>
        <td class="px-6 py-4 text-slate-400 capitalize">${item.split_type}</td>
        <td class="px-6 py-4">
          ${item.is_settled 
            ? `<span class="px-2 py-0.5 rounded-full text-xs bg-emerald-950 text-emerald-300 border border-emerald-800">Settled</span>`
            : `<span class="px-2 py-0.5 rounded-full text-xs bg-amber-950 text-amber-300 border border-amber-800">Unsettled</span>`}
        </td>
        <td class="px-6 py-4 text-right">
          ${!item.is_settled 
            ? `<button onclick="settleItem(${item.id})" class="text-xs text-indigo-400 hover:text-indigo-300">Settle</button>`
            : `<span class="text-xs text-slate-500">Archived</span>`}
        </td>
      `;
      tbody.appendChild(tr);
    });
  }
}

async function settleItem(itemId) {
  const headers = { "Authorization": `Bearer ${currentToken}` };
  await fetch(`/api/v1/finance/items/${itemId}/settle`, { method: "POST", headers });
  showToast("Expense settled");
  await loadFinance();
}

// TAB 4: Biometrics & Integrations
async function loadBiometrics() {
  if (!currentToken) return;
  const headers = { "Authorization": `Bearer ${currentToken}` };
  try {
    const resp = await fetch("/api/v1/biometrics/capacity-evaluation", { headers });
    const data = await resp.json();

    const badge = document.getElementById("readiness-badge");
    const desc = document.getElementById("readiness-desc");
    if (badge) badge.innerText = `${Math.round(data.readiness_score)}% ${data.recovery_status.toUpperCase()}`;
    if (desc) desc.innerText = `${data.recommendation} Daily Capacity: ${data.adjusted_capacity_minutes}m (Scale: ${(data.fatigue_scaling_factor * 100).toFixed(0)}%).`;
  } catch (e) {}
}

// Hardware & Wearable Configuration Handlers
async function submitHAConfig() {
  const url = document.getElementById("ha-cfg-url").value.trim();
  const token = document.getElementById("ha-cfg-token").value.trim();
  const focus = document.getElementById("ha-cfg-focus").value.trim();
  const relax = document.getElementById("ha-cfg-relax").value.trim();

  if (!url || !token) {
    showToast("Please enter Home Assistant URL and token.");
    return;
  }

  showToast("Saving Home Assistant connection...");
  const headers = {
    "Authorization": `Bearer ${currentToken}`,
    "Content-Type": "application/json"
  };

  try {
    const resp = await fetch("/api/v1/integrations/home-assistant/config", {
      method: "POST",
      headers,
      body: JSON.stringify({
        base_url: url,
        token: token,
        focus_scene: focus || "scene.focus_time",
        relax_scene: relax || "scene.relax"
      })
    });

    if (resp.ok) {
      closeModal("modal-ha-config");
      showToast("Home Assistant linked successfully!");
    } else {
      showToast("Failed to save Home Assistant config.");
    }
  } catch (e) {
    showToast("Network error linking Home Assistant.");
  }
}

async function submitPavlokConfig() {
  const key = document.getElementById("pavlok-cfg-key").value.trim();
  const stim = document.getElementById("pavlok-cfg-stim").value;
  const intensity = parseInt(document.getElementById("pavlok-cfg-intensity").value) || 50;
  const delay = parseInt(document.getElementById("pavlok-cfg-delay").value) || 15;

  if (!key) {
    showToast("Please provide your Pavlok API key.");
    return;
  }

  showToast("Saving Pavlok 3 configuration...");
  const headers = {
    "Authorization": `Bearer ${currentToken}`,
    "Content-Type": "application/json"
  };

  try {
    const resp = await fetch("/api/v1/integrations/pavlok/config", {
      method: "POST",
      headers,
      body: JSON.stringify({
        api_key: key,
        default_stimulus: stim,
        default_intensity: intensity,
        overdue_threshold_minutes: delay
      })
    });

    if (resp.ok) {
      closeModal("modal-pavlok-config");
      showToast("Pavlok 3 configured successfully!");
      document.getElementById("pavlok-status-text").innerText = `${stim.toUpperCase()} (${intensity}%)`;
    } else {
      showToast("Failed to save Pavlok config.");
    }
  } catch (e) {
    showToast("Network error linking Pavlok.");
  }
}

async function testPavlokConfig() {
  const stim = document.getElementById("pavlok-cfg-stim").value;
  const intensity = parseInt(document.getElementById("pavlok-cfg-intensity").value) || 50;
  await sendPavlokNudge(stim, intensity);
}

async function submitRingConnConfig() {
  const token = document.getElementById("ringconn-cfg-token").value.trim();
  const devId = document.getElementById("ringconn-cfg-id").value.trim();
  const autoscale = document.getElementById("ringconn-cfg-autoscale").checked;

  if (!token) {
    showToast("Please enter RingConn token.");
    return;
  }

  showToast("Linking RingConn Gen 2 Air...");
  const headers = {
    "Authorization": `Bearer ${currentToken}`,
    "Content-Type": "application/json"
  };

  try {
    const resp = await fetch("/api/v1/integrations/ringconn/config", {
      method: "POST",
      headers,
      body: JSON.stringify({
        account_token: token,
        device_id: devId || "RingConn-Air-Gen2",
        auto_scale_capacity: autoscale
      })
    });

    if (resp.ok) {
      closeModal("modal-ringconn-config");
      showToast("RingConn Gen 2 Air linked!");
      await triggerRingConnSync();
    } else {
      showToast("Failed to save RingConn config.");
    }
  } catch (e) {
    showToast("Network error linking RingConn.");
  }
}

async function triggerRingConnSync() {
  showToast("Fetching biometrics from RingConn...");
  const headers = { "Authorization": `Bearer ${currentToken}` };

  try {
    const resp = await fetch("/api/v1/integrations/ringconn/sync", {
      method: "POST",
      headers
    });
    const data = await resp.json();
    if (resp.ok) {
      showToast(`✔ RingConn synced! Readiness: ${Math.round(data.readiness_score)}% (${data.recovery_status})`);
      await loadBiometrics();
    } else {
      showToast("Sync failed.");
    }
  } catch (e) {
    showToast("Network error syncing biometrics.");
  }
}

async function triggerHAScene(sceneId) {
  const headers = {
    "Authorization": `Bearer ${currentToken}`,
    "Content-Type": "application/json"
  };
  await fetch("/api/v1/integrations/home-assistant/scene", {
    method: "POST",
    headers,
    body: JSON.stringify({ scene_id: sceneId })
  });
  showToast(`Home Assistant: Scene '${sceneId}' triggered`);
}

async function sendPavlokNudge(type, intensity) {
  const headers = {
    "Authorization": `Bearer ${currentToken}`,
    "Content-Type": "application/json"
  };
  await fetch("/api/v1/integrations/pavlok/nudge", {
    method: "POST",
    headers,
    body: JSON.stringify({ stimulus_type: type, intensity: intensity, reason: "Manual Test Alert" })
  });
  showToast(`Pavlok 3: Sent ${type} (${intensity}%)`);
}

// ================= TAB 5: ENTERPRISE ADMIN & USER/HARDWARE MANAGEMENT =================
async function loadAdminData() {
  if (!currentToken) return;
  const headers = { "Authorization": `Bearer ${currentToken}` };

  try {
    const [usersResp, capResp] = await Promise.all([
      fetch("/api/v1/admin/users", { headers }),
      fetch("/api/v1/admin/team-capacity", { headers })
    ]);

    if (!usersResp.ok) {
      const adminBtn = document.getElementById("tab-admin");
      if (adminBtn) adminBtn.classList.add("hidden");
      return;
    }

    const users = await usersResp.json();
    const capacity = await capResp.json();
    allUsersCache = users;

    // 1. Metric Counters
    document.getElementById("admin-user-count").innerText = users.length;
    let totalDevices = 0;
    users.forEach(u => { totalDevices += (u.devices ? u.devices.length : 0); });
    document.getElementById("admin-device-count").innerText = totalDevices;

    const highRiskCount = capacity.filter(c => c.burnout_risk === "high" || c.burnout_risk === "overloaded").length;
    const burnoutStatus = document.getElementById("admin-burnout-status");
    if (highRiskCount > 0) {
      burnoutStatus.innerText = `${highRiskCount} Overloaded`;
      burnoutStatus.className = "text-2xl font-bold text-rose-400 mt-1";
    } else {
      burnoutStatus.innerText = "Optimal Balance";
      burnoutStatus.className = "text-2xl font-bold text-emerald-400 mt-1";
    }

    // 2. User Directory Table
    const tbody = document.getElementById("admin-users-table-body");
    tbody.innerHTML = "";

    users.forEach(u => {
      const roleBadges = {
        superadmin: 'bg-rose-950 text-rose-300 border-rose-800',
        admin: 'bg-indigo-950 text-indigo-300 border-indigo-800',
        manager: 'bg-amber-950 text-amber-300 border-amber-800',
        member: 'bg-slate-800 text-slate-300 border-slate-700'
      }[u.role] || 'bg-slate-800 text-slate-300 border-slate-700';

      const devPills = (u.devices && u.devices.length > 0)
        ? u.devices.map(d => `<span class="text-[10px] px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-amber-300 font-mono">${d.provider.toUpperCase()}</span>`).join(" ")
        : `<span class="text-xs text-slate-500">None</span>`;

      const tr = document.createElement("tr");
      tr.className = "hover:bg-slate-900/50";
      tr.innerHTML = `
        <td class="px-4 py-3.5">
          <div class="font-semibold text-slate-200">${u.full_name}</div>
          <div class="text-xs text-slate-400">${u.email}</div>
        </td>
        <td class="px-4 py-3.5">
          <span class="text-xs px-2 py-0.5 rounded-full border capitalize ${roleBadges}">${u.role}</span>
        </td>
        <td class="px-4 py-3.5 text-xs text-slate-300">${u.department}</td>
        <td class="px-4 py-3.5 text-xs text-slate-300 font-mono">${u.work_start_hour}:00 - ${u.work_end_hour}:00</td>
        <td class="px-4 py-3.5 text-xs text-slate-300 font-mono">${u.daily_capacity_minutes}m / day</td>
        <td class="px-4 py-3.5">${devPills}</td>
        <td class="px-4 py-3.5 text-right space-x-2">
          <button onclick="adminResetPasswordPrompt(${u.id}, '${u.email}')" class="text-xs text-sky-400 hover:underline">Reset Pass</button>
          <button onclick="adminDeleteUser(${u.id})" class="text-xs text-rose-400 hover:underline">Remove</button>
        </td>
      `;
      tbody.appendChild(tr);
    });

    // 3. Hardware & Wearables Matrix Grid
    const devMatrix = document.getElementById("admin-device-matrix");
    devMatrix.innerHTML = "";

    users.forEach(u => {
      const hasDevs = u.devices && u.devices.length > 0;
      const card = document.createElement("div");
      card.className = "p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3";

      let devContent = "";
      if (hasDevs) {
        u.devices.forEach(d => {
          devContent += `
            <div class="flex items-center justify-between p-2.5 rounded-xl bg-slate-950 border border-slate-800/80">
              <div class="space-y-0.5">
                <div class="text-xs font-semibold text-slate-200 flex items-center space-x-1">
                  <span>⚡ ${d.device_name}</span>
                </div>
                <div class="text-[10px] text-slate-400 font-mono">Provider: ${d.provider} • ID: ${d.device_id || 'Active'}</div>
              </div>
              <button onclick="testUserHardware(${u.id}, '${d.provider}')" class="px-2.5 py-1 rounded bg-amber-600/20 text-amber-300 border border-amber-500/30 text-[11px] font-semibold hover:bg-amber-600/30">
                Test Pulse
              </button>
            </div>
          `;
        });
      } else {
        devContent = `<div class="text-xs text-slate-500 italic">No wearables linked. Click 'Assign Hardware' to provision Pavlok / RingConn.</div>`;
      }

      card.innerHTML = `
        <div class="flex items-center justify-between pb-2 border-b border-slate-800">
          <div>
            <span class="text-sm font-bold text-slate-200">${u.full_name}</span>
            <span class="text-xs text-slate-400 block">${u.department}</span>
          </div>
          <span class="text-xs font-mono text-indigo-400">${u.devices ? u.devices.length : 0} Devices</span>
        </div>
        <div class="space-y-2">${devContent}</div>
      `;
      devMatrix.appendChild(card);
    });

    // 4. Team Capacity & Burnout Heatmap
    const capList = document.getElementById("admin-capacity-list");
    capList.innerHTML = "";

    capacity.forEach(c => {
      const riskColors = {
        overloaded: 'bg-rose-500 text-rose-300',
        high: 'bg-amber-500 text-amber-300',
        moderate: 'bg-indigo-500 text-indigo-300',
        low: 'bg-emerald-500 text-emerald-300'
      }[c.burnout_risk] || 'bg-indigo-500 text-indigo-300';

      const readText = c.readiness_score ? `• RingConn Readiness: <b>${Math.round(c.readiness_score)}%</b> (${c.recovery_status})` : '';

      const item = document.createElement("div");
      item.className = "p-3.5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2";
      item.innerHTML = `
        <div class="flex items-center justify-between text-xs">
          <div class="space-x-2">
            <span class="font-bold text-slate-200">${c.full_name}</span>
            <span class="text-slate-400">(${c.department} - ${c.role})</span>
            <span class="text-slate-400">${readText}</span>
          </div>
          <div class="font-mono font-bold text-slate-200">
            ${c.scheduled_minutes}m / ${c.daily_capacity_minutes}m (${c.utilization_percentage}%)
            <span class="ml-2 text-[10px] px-2 py-0.5 rounded-full uppercase ${riskColors}">${c.burnout_risk}</span>
          </div>
        </div>
        <div class="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
          <div class="h-full rounded-full ${c.utilization_percentage > 100 ? 'bg-rose-500' : 'bg-indigo-500'}" style="width: ${Math.min(c.utilization_percentage, 100)}%"></div>
        </div>
      `;
      capList.appendChild(item);
    });

    if (window.lucide) lucide.createIcons();
  } catch (e) {
    console.error("Admin fetch error:", e);
  }
}

async function submitAddUser() {
  const name = document.getElementById("new-user-name").value.trim();
  const email = document.getElementById("new-user-email").value.trim();
  const pass = document.getElementById("new-user-pass").value;
  const role = document.getElementById("new-user-role").value;
  const dept = document.getElementById("new-user-dept").value.trim();
  const cap = parseInt(document.getElementById("new-user-cap").value) || 480;
  const tz = document.getElementById("new-user-tz").value.trim() || "America/New_York";

  if (!name || !email || !pass) {
    showToast("Please provide name, email, and password.");
    return;
  }

  showToast("Provisioning team member...");
  const headers = {
    "Authorization": `Bearer ${currentToken}`,
    "Content-Type": "application/json"
  };

  try {
    const resp = await fetch("/api/v1/admin/users", {
      method: "POST",
      headers,
      body: JSON.stringify({
        full_name: name,
        email: email,
        password: pass,
        role: role,
        department: dept || "Operations",
        daily_capacity_minutes: cap,
        timezone: tz
      })
    });

    if (!resp.ok) {
      const err = await resp.json();
      showToast(`Error: ${err.detail || 'Failed to create user'}`);
      return;
    }

    closeModal("modal-add-user");
    showToast(`Successfully provisioned ${name}!`);
    await loadAdminData();
  } catch (e) {
    showToast("Network error creating user.");
  }
}

async function submitAssignDevice() {
  const userId = parseInt(document.getElementById("assign-device-user").value);
  const provider = document.getElementById("assign-device-provider").value;
  const label = document.getElementById("assign-device-label").value.trim();
  const key = document.getElementById("assign-device-key").value.trim();

  if (!userId || !key) {
    showToast("Please select user and enter device API key / token.");
    return;
  }

  showToast("Linking hardware to employee profile...");
  const headers = {
    "Authorization": `Bearer ${currentToken}`,
    "Content-Type": "application/json"
  };

  try {
    const resp = await fetch("/api/v1/admin/devices/assign", {
      method: "POST",
      headers,
      body: JSON.stringify({
        user_id: userId,
        provider: provider,
        device_name: label || `${provider.toUpperCase()} Unit`,
        credentials: { api_key: key, token: key }
      })
    });

    if (!resp.ok) {
      const err = await resp.json();
      showToast(`Error: ${err.detail || 'Failed to assign device'}`);
      return;
    }

    closeModal("modal-assign-device");
    showToast("Hardware device successfully assigned!");
    await loadAdminData();
  } catch (e) {
    showToast("Failed to assign hardware.");
  }
}

async function testUserHardware(userId, provider) {
  showToast(`Sending test pulse to ${provider.toUpperCase()}...`);
  const headers = {
    "Authorization": `Bearer ${currentToken}`,
    "Content-Type": "application/json"
  };

  try {
    const resp = await fetch("/api/v1/admin/devices/test", {
      method: "POST",
      headers,
      body: JSON.stringify({ user_id: userId, provider: provider, stimulus_type: "vibration", intensity: 60 })
    });

    const data = await resp.json();
    if (resp.ok) {
      showToast(`✔ ${provider.toUpperCase()} test signal delivered!`);
    } else {
      showToast(`Failed: ${data.detail || 'Test error'}`);
    }
  } catch (e) {
    showToast("Test request failed.");
  }
}

async function adminResetPasswordPrompt(userId, email) {
  const newPass = prompt(`Reset Password for ${email}:\nEnter new temporary password (min 6 chars):`);
  if (!newPass || newPass.length < 6) {
    if (newPass) showToast("Password must be at least 6 characters.");
    return;
  }

  const headers = {
    "Authorization": `Bearer ${currentToken}`,
    "Content-Type": "application/json"
  };

  const resp = await fetch(`/api/v1/admin/users/${userId}/reset-password`, {
    method: "POST",
    headers,
    body: JSON.stringify({ new_password: newPass })
  });

  if (resp.ok) {
    showToast("Password reset successfully!");
  } else {
    showToast("Failed to reset password.");
  }
}

async function adminDeleteUser(userId) {
  if (!confirm(`Are you sure you want to remove team member ID #${userId}?`)) return;

  const headers = { "Authorization": `Bearer ${currentToken}` };
  const resp = await fetch(`/api/v1/admin/users/${userId}`, { method: "DELETE", headers });
  if (resp.ok) {
    showToast("Member removed.");
    await loadAdminData();
  } else {
    showToast("Failed to remove user.");
  }
}

// AI Assistant Drawer & Chat
function toggleAssistantDrawer() {
  const drawer = document.getElementById("assistant-drawer");
  if (drawer) drawer.classList.toggle("translate-x-full");
}

async function sendChatMessage() {
  const input = document.getElementById("chat-input");
  if (!input) return;
  const text = input.value.trim();
  if (!text) return;

  input.value = "";
  const chatContainer = document.getElementById("chat-messages");

  const userDiv = document.createElement("div");
  userDiv.className = "bg-indigo-600/30 border border-indigo-500/40 p-3 rounded-xl text-slate-100 text-xs ml-6";
  userDiv.innerText = text;
  chatContainer.appendChild(userDiv);

  const loadDiv = document.createElement("div");
  loadDiv.className = "bg-slate-800 p-2.5 rounded-xl text-slate-400 text-xs mr-6 italic";
  loadDiv.innerText = "Analyzing schedule & tool actions...";
  chatContainer.appendChild(loadDiv);
  chatContainer.scrollTop = chatContainer.scrollHeight;

  const headers = {
    "Authorization": `Bearer ${currentToken}`,
    "Content-Type": "application/json"
  };

  try {
    const resp = await fetch("/api/v1/agent/chat", {
      method: "POST",
      headers,
      body: JSON.stringify({
        messages: [{ role: "user", content: text }]
      })
    });
    const data = await resp.json();
    chatContainer.removeChild(loadDiv);

    const assistantDiv = document.createElement("div");
    assistantDiv.className = "bg-slate-800 p-3 rounded-xl border border-slate-700 text-slate-200 text-xs mr-6 space-y-2";
    assistantDiv.innerHTML = `<p>${data.content}</p>`;

    if (data.tool_calls && data.tool_calls.length > 0) {
      const toolBox = document.createElement("div");
      toolBox.className = "bg-slate-950/70 p-2 rounded border border-slate-800 mono text-[11px] text-emerald-400 space-y-1";
      data.tool_calls.forEach(tc => {
        toolBox.innerHTML += `<div>⚙️ Tool: <span class="font-bold">${tc.name}</span>(${JSON.stringify(tc.args)})</div>`;
      });
      assistantDiv.appendChild(toolBox);
    }

    chatContainer.appendChild(assistantDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    await loadAgenda();
    await loadProjects();
    await loadFinance();
  } catch (e) {
    chatContainer.removeChild(loadDiv);
    showToast("Error connecting to Plexi Assistant");
  }
}

// Additional Task & Expense Submits
async function submitNewTask() {
  const title = document.getElementById("task-title-input").value.trim();
  const priority = document.getElementById("task-priority-input").value;
  const duration = parseInt(document.getElementById("task-duration-input").value) || 30;
  const momentum = document.getElementById("task-momentum-input").checked;

  if (!title) return;

  const headers = {
    "Authorization": `Bearer ${currentToken}`,
    "Content-Type": "application/json"
  };

  await fetch("/api/v1/tasks/", {
    method: "POST",
    headers,
    body: JSON.stringify({
      title,
      priority,
      duration_minutes: duration,
      momentum_critical: momentum
    })
  });

  closeModal("modal-task");
  showToast("Task created");
  await triggerAutoSchedule();
}

async function submitTaskDecomposition() {
  const desc = document.getElementById("decompose-input").value.trim();
  if (!desc) return;

  showToast("Decomposing workflow with AI...");
  const headers = {
    "Authorization": `Bearer ${currentToken}`,
    "Content-Type": "application/json"
  };

  await fetch("/api/v1/tasks/decompose", {
    method: "POST",
    headers,
    body: JSON.stringify({ task_description: desc })
  });

  closeModal("modal-decompose");
  showToast("Project decomposed into SOP subtasks!");
  await loadProjects();
}

async function submitNewExpense() {
  const title = document.getElementById("expense-title-input").value.trim();
  const amount = parseFloat(document.getElementById("expense-amount-input").value) || 0;
  const category = document.getElementById("expense-category-input").value;

  if (!title || amount <= 0) return;

  const headers = {
    "Authorization": `Bearer ${currentToken}`,
    "Content-Type": "application/json"
  };

  await fetch("/api/v1/finance/items", {
    method: "POST",
    headers,
    body: JSON.stringify({
      household_id: currentHouseholdId,
      title,
      total_amount: amount,
      category,
      split_type: "equal"
    })
  });

  closeModal("modal-expense");
  showToast("Shared expense logged!");
  await loadFinance();
}
