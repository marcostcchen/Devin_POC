let me = { email: "", role: "viewer" };
const openAudits = new Set();

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", "X-User": me.email, ...(options.headers || {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch (_) {}
    if (Array.isArray(detail)) {
      detail = detail.map((e) => `${(e.loc || []).slice(-1)[0]}: ${e.msg}`).join("; ");
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.status === 204 ? null : res.json();
}

function showError(err) {
  $("error").textContent = err ? `⚠ ${err.message}` : "";
}

async function loadMe(email) {
  const data = await fetch("/api/me", { headers: email ? { "X-User": email } : {} }).then((r) => r.json());
  me = { email: data.email, role: data.role };
  const select = $("user");
  if (!select.options.length) {
    for (const [addr, role] of Object.entries(data.users)) {
      const opt = document.createElement("option");
      opt.value = addr;
      opt.textContent = `${addr} (${role})`;
      select.appendChild(opt);
    }
  }
  select.value = me.email;
  showError(null);
  const isAdmin = me.role === "admin";
  ["n-name", "n-desc", "n-rollout", "n-team", "n-enabled", "create"].forEach((id) => {
    $(id).disabled = !isAdmin;
  });
  const role = $("role");
  role.textContent = me.role;
  role.className = `pill ${me.role === "admin" ? "on" : "off"}`;
}

function auditLine(entry) {
  const li = document.createElement("li");
  li.textContent = `${entry.created_at} — ${entry.actor} ${entry.action} ${entry.flag_name}${
    entry.detail ? ` (${entry.detail})` : ""
  }`;
  return li;
}

async function renderAuditInto(container, flagId) {
  const entries = await api(`/api/flags/${flagId}/audit`);
  container.innerHTML = "";
  if (!entries.length) {
    container.appendChild(Object.assign(document.createElement("li"), { textContent: "no history yet" }));
  }
  entries.forEach((e) => container.appendChild(auditLine(e)));
}

function flagRow(flag) {
  const isAdmin = me.role === "admin";
  const tr = document.createElement("tr");

  const nameCell = document.createElement("td");
  nameCell.innerHTML = `<strong>${flag.name}</strong>`;
  const desc = document.createElement("div");
  desc.className = "muted";
  desc.textContent = flag.description || "no description";
  nameCell.appendChild(desc);
  const auditList = document.createElement("ul");
  auditList.className = "audit";
  auditList.hidden = !openAudits.has(flag.id);
  nameCell.appendChild(auditList);
  if (!auditList.hidden) renderAuditInto(auditList, flag.id).catch(showError);

  const stateCell = document.createElement("td");
  stateCell.innerHTML = `<span class="pill ${flag.enabled ? "on" : "off"}">${flag.enabled ? "ON" : "OFF"}</span>`;

  const targetCell = document.createElement("td");
  const rollout = document.createElement("input");
  rollout.type = "number";
  rollout.min = 0;
  rollout.max = 100;
  rollout.value = flag.rollout_percentage;
  rollout.style.width = "72px";
  rollout.disabled = !isAdmin;
  const team = document.createElement("input");
  team.placeholder = "team";
  team.value = flag.target_team;
  team.style.width = "110px";
  team.disabled = !isAdmin;
  const saveTargeting = document.createElement("button");
  saveTargeting.textContent = "Save";
  saveTargeting.className = "secondary";
  saveTargeting.disabled = !isAdmin;
  saveTargeting.onclick = () =>
    patch(flag.id, { rollout_percentage: Number(rollout.value), target_team: team.value });
  const wrap = document.createElement("div");
  wrap.className = "row";
  wrap.append(rollout, document.createTextNode("%"), team, saveTargeting);
  targetCell.appendChild(wrap);

  const actions = document.createElement("td");
  const toggle = document.createElement("button");
  toggle.textContent = flag.enabled ? "Disable" : "Enable";
  toggle.disabled = !isAdmin;
  toggle.onclick = () => patch(flag.id, { enabled: !flag.enabled });

  const editDesc = document.createElement("button");
  editDesc.textContent = "Edit description";
  editDesc.className = "secondary";
  editDesc.disabled = !isAdmin;
  editDesc.onclick = () => {
    const next = prompt(`Description for ${flag.name}`, flag.description);
    if (next !== null) patch(flag.id, { description: next });
  };

  const history = document.createElement("button");
  history.textContent = "History";
  history.className = "secondary";
  history.onclick = async () => {
    auditList.hidden = !auditList.hidden;
    if (auditList.hidden) openAudits.delete(flag.id);
    else {
      openAudits.add(flag.id);
      await renderAuditInto(auditList, flag.id).catch(showError);
    }
  };

  const del = document.createElement("button");
  del.textContent = "Delete";
  del.className = "secondary";
  del.disabled = !isAdmin;
  del.onclick = async () => {
    if (!confirm(`Delete ${flag.name}?`)) return;
    try {
      await api(`/api/flags/${flag.id}`, { method: "DELETE" });
      showError(null);
      await refresh();
    } catch (err) {
      showError(err);
    }
  };

  const row = document.createElement("div");
  row.className = "row";
  row.append(toggle, editDesc, history, del);
  actions.appendChild(row);

  tr.append(nameCell, stateCell, targetCell, actions);
  return tr;
}

async function patch(flagId, body) {
  try {
    await api(`/api/flags/${flagId}`, { method: "PATCH", body: JSON.stringify(body) });
    showError(null);
    await refresh();
  } catch (err) {
    showError(err);
  }
}

async function refresh() {
  const [flags, audit] = await Promise.all([api("/api/flags"), api("/api/audit?limit=15")]);
  const tbody = $("flags");
  tbody.innerHTML = "";
  flags.forEach((f) => tbody.appendChild(flagRow(f)));

  const list = $("global-audit");
  list.innerHTML = "";
  if (!audit.length) list.appendChild(Object.assign(document.createElement("li"), { textContent: "no activity yet" }));
  audit.forEach((e) => list.appendChild(auditLine(e)));
}

$("user").onchange = async (event) => {
  await loadMe(event.target.value);
  await refresh();
};

$("create").onclick = async () => {
  try {
    await api("/api/flags", {
      method: "POST",
      body: JSON.stringify({
        name: $("n-name").value,
        description: $("n-desc").value,
        enabled: $("n-enabled").checked,
        rollout_percentage: Number($("n-rollout").value),
        target_team: $("n-team").value,
      }),
    });
    showError(null);
    $("n-name").value = "";
    $("n-desc").value = "";
    $("n-team").value = "";
    $("n-enabled").checked = false;
    await refresh();
  } catch (err) {
    showError(err);
  }
};

$("evaluate").onclick = async () => {
  const params = new URLSearchParams({ user_id: $("e-user").value, team: $("e-team").value });
  try {
    const result = await api(`/api/evaluate/${encodeURIComponent($("e-flag").value)}?${params}`);
    $("e-result").textContent = `${result.enabled ? "ENABLED" : "DISABLED"} — ${result.reason}`;
    showError(null);
  } catch (err) {
    $("e-result").textContent = "";
    showError(err);
  }
};

(async () => {
  await loadMe();
  await refresh();
})().catch(showError);
