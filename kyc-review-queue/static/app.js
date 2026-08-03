let me = { email: "", role: "analyst", platformManaged: false };
let selectedId = null;

const $ = (id) => document.getElementById(id);
const isSenior = () => me.role === "senior_reviewer";

// Paths are resolved against the page URL so the same files work standalone
// ('/') and behind the POC platform gateway ('/apps/kyc-review-queue/').
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
  me = { email: data.email, role: data.role, platformManaged: data.platform_managed };
  const select = $("user");
  if (me.platformManaged) {
    // The platform console owns identity; show it instead of a switcher.
    select.hidden = true;
    $("acting-as").hidden = false;
    $("acting-as").textContent = data.display_name || data.email;
    $("console-link").hidden = false;
    $("console-link").href = data.platform_console_url || "/";
  } else if (!select.options.length) {
    for (const [addr, role] of Object.entries(data.users)) {
      const opt = document.createElement("option");
      opt.value = addr;
      opt.textContent = `${addr} (${role})`;
      select.appendChild(opt);
    }
  }
  if (!me.platformManaged) select.value = me.email;
  const role = $("role");
  role.textContent = me.role.replace("_", " ");
  role.className = `pill ${isSenior() ? "st-escalated" : "st-in_review"}`;
  $("escalation-note").hidden = false;
  showError(null);
}

function caseRow(c) {
  const tr = document.createElement("tr");
  tr.className = c.id === selectedId ? "case selected" : "case";
  const ref = document.createElement("td");
  ref.textContent = c.reference;
  const name = document.createElement("td");
  name.textContent = c.customer_name;
  const risk = document.createElement("td");
  risk.appendChild(pill(c.risk_level, `risk-${c.risk_level}`));
  const status = document.createElement("td");
  status.appendChild(pill(c.status, `st-${c.status}`));
  tr.append(ref, name, risk, status);
  tr.onclick = () => selectCase(c.id);
  return tr;
}

function decisionLine(entry) {
  const li = document.createElement("li");
  li.textContent =
    `${entry.created_at} — ${entry.actor} (${entry.actor_role}) ${entry.action}: ` +
    `${entry.status_before} → ${entry.status_after} — "${entry.reason}"`;
  return li;
}

async function renderDetail(caseId) {
  const detail = $("detail");
  const [c, history] = await Promise.all([
    api(`api/cases/${caseId}`),
    api(`api/cases/${caseId}/history`),
  ]);

  detail.innerHTML = "";
  const title = document.createElement("div");
  title.className = "row";
  const heading = document.createElement("strong");
  heading.textContent = `${c.reference} — ${c.customer_name}`;
  title.append(heading, pill(c.risk_level, `risk-${c.risk_level}`), pill(c.status, `st-${c.status}`));
  detail.appendChild(title);

  const meta = document.createElement("p");
  meta.className = "muted";
  meta.textContent =
    `${c.country} · ${c.document_type} · ${c.document_number} (synthetic) · opened ${c.created_at}`;
  detail.appendChild(meta);

  detail.appendChild(Object.assign(document.createElement("strong"), { textContent: "Submitted documents" }));
  const docs = document.createElement("ul");
  docs.className = "docs";
  c.documents.forEach((d) => {
    const li = document.createElement("li");
    li.textContent = `${d} (placeholder, no file stored)`;
    docs.appendChild(li);
  });
  detail.appendChild(docs);

  const closedForAnalyst = c.status === "closed" && !isSenior();
  detail.appendChild(
    Object.assign(document.createElement("strong"), {
      textContent: c.status === "closed" ? "Override" : "Decision",
      style: "display:block;margin-top:14px",
    })
  );
  const reason = document.createElement("textarea");
  reason.id = "reason";
  reason.placeholder = "Reason (required)";
  reason.disabled = closedForAnalyst;
  detail.appendChild(reason);

  const actions = document.createElement("div");
  actions.className = "row";
  actions.style.marginTop = "8px";
  const buttons = [
    ["Approve", "approve", ""],
    ["Reject", "reject", "danger"],
    ["Escalate", "escalate", "warn"],
    ["Claim", "claim", "secondary"],
  ];
  for (const [label, action, cls] of buttons) {
    const btn = document.createElement("button");
    btn.textContent = label;
    if (cls) btn.className = cls;
    btn.disabled = closedForAnalyst || (action === "escalate" && c.status === "escalated");
    btn.onclick = () => submitDecision(c.id, action, reason.value);
    actions.appendChild(btn);
  }
  detail.appendChild(actions);
  if (closedForAnalyst) {
    detail.appendChild(
      Object.assign(document.createElement("p"), {
        className: "muted",
        textContent: "This case is closed. Only a senior reviewer can override it.",
      })
    );
  }

  detail.appendChild(
    Object.assign(document.createElement("strong"), {
      textContent: "History",
      style: "display:block;margin-top:14px",
    })
  );
  const list = document.createElement("ul");
  list.className = "history";
  if (!history.length) {
    list.appendChild(Object.assign(document.createElement("li"), { textContent: "no decisions yet" }));
  }
  history.forEach((e) => list.appendChild(decisionLine(e)));
  detail.appendChild(list);
}

async function submitDecision(caseId, action, reason) {
  if (!reason.trim()) {
    showError(new Error("a reason is required for every decision"));
    return;
  }
  try {
    await api(`api/cases/${caseId}/decisions`, {
      method: "POST",
      body: JSON.stringify({ action, reason }),
    });
    showError(null);
    await refresh();
  } catch (err) {
    showError(err);
  }
}

async function selectCase(caseId) {
  selectedId = caseId;
  await refresh();
}

async function refresh() {
  const params = new URLSearchParams({ sort: $("f-sort").value });
  if ($("f-risk").value) params.set("risk_level", $("f-risk").value);
  if ($("f-status").value) params.set("status", $("f-status").value);
  const cases = await api(`api/cases?${params}`);

  const tbody = $("cases");
  tbody.innerHTML = "";
  if (!cases.some((c) => c.id === selectedId)) selectedId = null;
  cases.forEach((c) => tbody.appendChild(caseRow(c)));
  $("count").textContent = `${cases.length} case(s)`;

  if (selectedId === null) {
    $("detail").innerHTML = "<strong>Case detail</strong><p class='muted'>Select a case from the queue.</p>";
  } else {
    await renderDetail(selectedId);
  }
}

$("user").onchange = async (event) => {
  try {
    await loadMe(event.target.value);
    await refresh();
  } catch (err) {
    showError(err);
  }
};

["f-risk", "f-status", "f-sort"].forEach((id) => {
  $(id).onchange = () => refresh().catch(showError);
});

(async () => {
  await loadMe();
  await refresh();
})().catch(showError);
