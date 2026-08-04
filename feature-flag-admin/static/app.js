let me = { email: "", role: "viewer" };
let flags = [];
let openHistory = null;

const $ = (id) => document.getElementById(id);
const isAdmin = () => me.role === "admin";

// Paths are resolved against the page URL, so the app does not care which
// host or mount point it is served from.
const url = (path) => new URL(path, document.baseURI).toString();

async function api(path, options = {}) {
  const res = await fetch(url(path), {
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

function pill(text, cls) {
  const span = document.createElement("span");
  span.className = `pill ${cls}`;
  span.textContent = text;
  return span;
}

async function loadMe(email) {
  const data = await fetch(url("api/me"), {
    headers: email ? { "X-User": email } : {},
  }).then((r) => r.json());
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
  const role = $("role");
  role.textContent = me.role;
  role.className = `pill ${isAdmin() ? "st-admin" : "st-viewer"}`;
  $("viewer-note").hidden = isAdmin();
  $("toggle-create").disabled = !isAdmin();
  if (!isAdmin()) $("create").hidden = true;
  showError(null);
}

function visibleFlags() {
  const text = $("f-text").value.trim().toLowerCase();
  const state = $("f-state").value;
  return flags.filter((flag) => {
    const matchesText =
      !text ||
      flag.name.toLowerCase().includes(text) ||
      flag.description.toLowerCase().includes(text);
    const matchesState = !state || (state === "on") === flag.enabled;
    return matchesText && matchesState;
  });
}

function flagRow(flag) {
  const tr = document.createElement("tr");

  const name = document.createElement("td");
  const label = document.createElement("div");
  label.className = "name";
  label.textContent = flag.name;
  const description = document.createElement("div");
  description.className = "muted";
  description.textContent = flag.description || "no description";
  if (isAdmin()) {
    description.title = "Click to edit the description";
    description.style.cursor = "pointer";
    description.onclick = () => editField(flag, "description", "Description", flag.description);
  }
  name.append(label, description);

  const state = document.createElement("td");
  const toggle = document.createElement("button");
  toggle.className = "secondary";
  toggle.textContent = flag.enabled ? "on" : "off";
  toggle.disabled = !isAdmin();
  toggle.onclick = () => patch(flag.id, { enabled: !flag.enabled });
  state.append(pill(flag.enabled ? "on" : "off", flag.enabled ? "st-on" : "st-off"), " ", toggle);

  const rollout = document.createElement("td");
  const meta = document.createElement("div");
  meta.className = "flag-meta";
  const bar = document.createElement("div");
  bar.className = "bar";
  const fill = document.createElement("span");
  fill.style.width = `${flag.rollout_percentage}%`;
  bar.appendChild(fill);
  const percent = document.createElement("span");
  percent.className = "muted";
  percent.textContent = `${flag.rollout_percentage}%`;
  meta.append(bar, percent);
  if (isAdmin()) {
    const edit = document.createElement("button");
    edit.className = "secondary";
    edit.textContent = "edit";
    edit.onclick = () =>
      editField(flag, "rollout_percentage", "Rollout percentage (0-100)", flag.rollout_percentage);
    meta.appendChild(edit);
  }
  rollout.appendChild(meta);

  const team = document.createElement("td");
  team.textContent = flag.target_team || "—";
  if (isAdmin()) {
    team.title = "Click to edit the target team";
    team.style.cursor = "pointer";
    team.onclick = () => editField(flag, "target_team", "Target team (blank for none)", flag.target_team);
  }

  const actions = document.createElement("td");
  actions.className = "actions";
  const history = document.createElement("button");
  history.className = "secondary";
  history.textContent = openHistory === flag.id ? "Hide" : "History";
  history.onclick = () => {
    openHistory = openHistory === flag.id ? null : flag.id;
    render();
  };
  const remove = document.createElement("button");
  remove.className = "danger";
  remove.textContent = "Delete";
  remove.disabled = !isAdmin();
  remove.onclick = () => {
    if (confirm(`Delete ${flag.name}? Its audit history is kept.`)) del(flag.id);
  };
  actions.append(history, " ", remove);

  tr.append(name, state, rollout, team, actions);
  return tr;
}

function historyRow(flag) {
  const tr = document.createElement("tr");
  const cell = document.createElement("td");
  cell.colSpan = 5;
  const list = document.createElement("ul");
  list.className = "history";
  const item = document.createElement("li");
  item.className = "muted";
  item.textContent = "loading…";
  list.appendChild(item);
  cell.appendChild(list);
  tr.appendChild(cell);

  api(`api/flags/${flag.id}/audit`)
    .then((entries) => {
      list.textContent = "";
      if (!entries.length) {
        const empty = document.createElement("li");
        empty.className = "muted";
        empty.textContent = "no history yet";
        list.appendChild(empty);
        return;
      }
      for (const entry of entries) list.appendChild(auditLine(entry, false));
    })
    .catch(showError);
  return tr;
}

function auditLine(entry, withFlagName) {
  const li = document.createElement("li");
  const what = withFlagName ? `${entry.flag_name}: ${entry.action}` : entry.action;
  const detail = entry.detail ? ` (${entry.detail})` : "";
  li.textContent = `${entry.created_at} — ${entry.actor} ${what}${detail}`;
  return li;
}

function render() {
  const rows = visibleFlags();
  const body = $("flags");
  body.textContent = "";
  for (const flag of rows) {
    body.appendChild(flagRow(flag));
    if (openHistory === flag.id) body.appendChild(historyRow(flag));
  }
  if (!rows.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 5;
    td.className = "muted";
    td.textContent = flags.length ? "no flag matches the filter" : "no flags yet";
    tr.appendChild(td);
    body.appendChild(tr);
  }

  $("count").textContent = `${rows.length} of ${flags.length} shown`;
  $("c-total").textContent = flags.length;
  $("c-on").textContent = flags.filter((f) => f.enabled).length;
  $("c-partial").textContent = flags.filter((f) => f.rollout_percentage < 100).length;
  $("c-targeted").textContent = flags.filter((f) => f.target_team).length;

  const chooser = $("e-flag");
  const previous = chooser.value;
  chooser.textContent = "";
  for (const flag of flags) {
    const opt = document.createElement("option");
    opt.value = flag.name;
    opt.textContent = flag.name;
    chooser.appendChild(opt);
  }
  if (flags.some((f) => f.name === previous)) chooser.value = previous;
}

async function loadFlags() {
  flags = await api("api/flags");
  render();
}

async function loadActivity() {
  const entries = await api("api/audit?limit=15");
  const list = $("activity");
  list.textContent = "";
  if (!entries.length) {
    const empty = document.createElement("li");
    empty.className = "muted";
    empty.textContent = "nothing yet";
    list.appendChild(empty);
    return;
  }
  for (const entry of entries) list.appendChild(auditLine(entry, true));
}

async function refresh() {
  try {
    await loadFlags();
    await loadActivity();
    showError(null);
  } catch (err) {
    showError(err);
  }
}

async function patch(id, body) {
  try {
    await api(`api/flags/${id}`, { method: "PATCH", body: JSON.stringify(body) });
    await refresh();
  } catch (err) {
    showError(err);
  }
}

async function del(id) {
  try {
    await api(`api/flags/${id}`, { method: "DELETE" });
    if (openHistory === id) openHistory = null;
    await refresh();
  } catch (err) {
    showError(err);
  }
}

function editField(flag, field, prompt_text, current) {
  const answer = prompt(prompt_text, current === null || current === undefined ? "" : current);
  if (answer === null) return;
  const value = field === "rollout_percentage" ? Number(answer) : answer;
  if (field === "rollout_percentage" && Number.isNaN(value)) {
    showError(new Error("rollout percentage must be a number"));
    return;
  }
  patch(flag.id, { [field]: value });
}

async function evaluate() {
  const name = $("e-flag").value;
  if (!name) return;
  const query = new URLSearchParams({ user_id: $("e-user").value || "anonymous", team: $("e-team").value });
  try {
    const result = await api(`api/evaluate/${encodeURIComponent(name)}?${query}`);
    $("e-result").textContent = `${result.enabled ? "ON" : "OFF"} for ${result.user_id} — ${result.reason}`;
    showError(null);
  } catch (err) {
    $("e-result").textContent = "";
    showError(err);
  }
}

$("user").onchange = async (event) => {
  try {
    await loadMe(event.target.value);
    openHistory = null;
    await refresh();
  } catch (err) {
    showError(err);
  }
};
$("f-text").oninput = render;
$("f-state").onchange = render;
$("toggle-create").onclick = () => {
  $("create").hidden = !$("create").hidden;
};
$("create").onsubmit = async (event) => {
  event.preventDefault();
  try {
    await api("api/flags", {
      method: "POST",
      body: JSON.stringify({
        name: $("n-name").value,
        description: $("n-description").value,
        enabled: $("n-enabled").checked,
        rollout_percentage: Number($("n-rollout").value),
        target_team: $("n-team").value,
      }),
    });
    event.target.reset();
    $("n-rollout").value = 100;
    $("create").hidden = true;
    await refresh();
  } catch (err) {
    showError(err);
  }
};
$("e-run").onclick = evaluate;

loadMe().then(refresh).catch(showError);
