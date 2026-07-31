let me = { email: "", role: "analyst" };
let selectedId = null;

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

function pill(text, className) {
  const span = document.createElement("span");
  span.className = `pill ${className}`;
  span.textContent = text;
  return span;
}

function shortTime(iso) {
  return iso.replace("T", " ").replace("+00:00", "Z");
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
  const role = $("role");
  role.textContent = me.role;
  role.className = `pill ${me.role === "senior_reviewer" ? "status-escalated" : "status-new"}`;
  $("escalated-card").hidden = me.role !== "senior_reviewer";
  showError(null);
}

function caseRow(c, columns) {
  const tr = document.createElement("tr");
  tr.dataset.caseId = c.id;
  if (c.id === selectedId) tr.className = "selected";
  tr.onclick = () => openCase(c.id);
  columns.forEach((cell) => {
    const td = document.createElement("td");
    if (cell instanceof Node) td.appendChild(cell);
    else td.innerHTML = cell;
    tr.appendChild(td);
  });
  return tr;
}

function statusLabel(c) {
  return c.status === "closed" && c.outcome ? `closed · ${c.outcome}` : c.status;
}

async function loadQueue() {
  const params = new URLSearchParams({ sort: $("f-sort").value });
  if ($("f-risk").value) params.set("risk", $("f-risk").value);
  if ($("f-status").value) params.set("status", $("f-status").value);

  const [cases, audit] = await Promise.all([api(`/api/cases?${params}`), api("/api/audit?limit=15")]);
  const tbody = $("cases");
  tbody.innerHTML = "";
  cases.forEach((c) =>
    tbody.appendChild(
      caseRow(c, [
        `<strong>${c.reference}</strong><div class="muted">${c.jurisdiction}</div>`,
        `${c.customer_name}<div class="muted">${c.customer_ref}</div>`,
        pill(c.risk_level, `risk-${c.risk_level}`),
        pill(statusLabel(c), `status-${c.status}`),
        `<span class="muted">${shortTime(c.submitted_at)}</span>`,
      ]),
    ),
  );
  $("count").textContent = `${cases.length} case${cases.length === 1 ? "" : "s"}`;

  if (me.role === "senior_reviewer") {
    const escalated = await api("/api/cases?status=escalated&sort=risk");
    const body = $("escalated");
    body.innerHTML = "";
    if (!escalated.length) {
      body.innerHTML = '<tr><td colspan="4" class="muted">nothing escalated right now</td></tr>';
    }
    escalated.forEach((c) =>
      body.appendChild(
        caseRow(c, [
          `<strong>${c.reference}</strong>`,
          c.customer_name,
          pill(c.risk_level, `risk-${c.risk_level}`),
          `<span class="muted">${c.risk_note}</span>`,
        ]),
      ),
    );
  }

  const list = $("global-audit");
  list.innerHTML = "";
  if (!audit.length) list.innerHTML = "<li>no activity yet</li>";
  audit.forEach((e) => list.appendChild(eventLine(e)));
}

function eventLine(e) {
  const li = document.createElement("li");
  li.textContent = `${shortTime(e.created_at)} — ${e.actor} · ${e.action} · ${e.case_reference}${
    e.reason ? ` — "${e.reason}"` : ""
  }`;
  return li;
}

function decisionPanel(detail) {
  const wrap = document.createElement("div");
  const isSenior = me.role === "senior_reviewer";
  const overriding = detail.status === "closed" || detail.status === "escalated";

  if (overriding && !isSenior) {
    wrap.innerHTML = '<div class="banner">Closed — only a senior reviewer can override this decision.</div>';
    return wrap;
  }

  const title = document.createElement("strong");
  title.textContent = overriding ? "Override decision" : "Decision";
  const reason = document.createElement("textarea");
  reason.rows = 3;
  reason.placeholder = "Reason (required) — what you checked and why you decided this";
  reason.style.marginTop = "8px";

  const buttons = document.createElement("div");
  buttons.className = "row";
  buttons.style.marginTop = "8px";

  const options = [["approve", "Approve"], ["reject", "Reject"]];
  if (detail.status !== "escalated") options.push(["escalate", "Escalate"]);
  options.forEach(([decision, label]) => {
    const button = document.createElement("button");
    button.textContent = label;
    if (decision !== "approve") button.className = "secondary";
    button.onclick = async () => {
      if (!reason.value.trim()) {
        showError(new Error("a reason is required for every decision"));
        return;
      }
      try {
        await api(`/api/cases/${detail.id}/decision`, {
          method: "POST",
          body: JSON.stringify({ decision, reason: reason.value }),
        });
        showError(null);
        if (decision === "escalate" && me.role !== "senior_reviewer") {
          selectedId = null;
          $("detail").innerHTML =
            `<span class="muted">${detail.reference} escalated — it now sits in the senior reviewer queue.</span>`;
        } else {
          await openCase(detail.id);
        }
        await loadQueue();
      } catch (err) {
        showError(err);
      }
    };
    buttons.append(button);
  });

  wrap.append(title, reason, buttons);
  return wrap;
}

async function openCase(caseId) {
  try {
    const detail = await api(`/api/cases/${caseId}`);
    selectedId = caseId;
    const panel = $("detail");
    panel.innerHTML = "";

    const head = document.createElement("div");
    head.className = "row";
    const ref = document.createElement("strong");
    ref.textContent = detail.reference;
    head.append(ref, pill(detail.risk_level, `risk-${detail.risk_level}`), pill(statusLabel(detail), `status-${detail.status}`));

    const facts = document.createElement("div");
    facts.style.marginTop = "8px";
    facts.innerHTML = `
      <div>${detail.customer_name}</div>
      <div class="muted">${detail.customer_ref} · doc ${detail.document_number} · ${detail.jurisdiction}</div>
      <div class="muted">submitted ${shortTime(detail.submitted_at)}</div>
      <div class="muted">${detail.risk_note}</div>`;

    const docs = document.createElement("div");
    docs.style.marginTop = "12px";
    docs.innerHTML = "<strong>Submitted documents</strong>";
    const docList = document.createElement("ul");
    docList.className = "plain";
    detail.documents.forEach((d) => {
      const li = document.createElement("li");
      li.textContent = `${d.doc_type}: ${d.filename}`;
      const note = document.createElement("span");
      note.className = "muted";
      note.textContent = " (placeholder — no file stored)";
      li.appendChild(note);
      docList.appendChild(li);
    });
    docs.appendChild(docList);

    const actions = document.createElement("div");
    actions.className = "row";
    actions.style.marginTop = "12px";
    if (detail.status === "new") {
      const claim = document.createElement("button");
      claim.className = "secondary";
      claim.textContent = "Start review";
      claim.onclick = async () => {
        try {
          await api(`/api/cases/${detail.id}/claim`, { method: "POST" });
          showError(null);
          await openCase(detail.id);
          await loadQueue();
        } catch (err) {
          showError(err);
        }
      };
      actions.appendChild(claim);
    }

    const decision = document.createElement("div");
    decision.style.marginTop = "12px";
    decision.appendChild(decisionPanel(detail));

    const history = document.createElement("div");
    history.style.marginTop = "16px";
    history.innerHTML = "<strong>History</strong>";
    const historyList = document.createElement("ul");
    historyList.className = "plain";
    detail.history.forEach((e) => {
      const li = document.createElement("li");
      li.textContent = `${shortTime(e.created_at)} — ${e.actor} (${e.actor_role}) ${e.action}${
        e.reason ? `: "${e.reason}"` : ""
      }`;
      historyList.appendChild(li);
    });
    history.appendChild(historyList);

    panel.append(head, facts, docs, actions, decision, history);
    document.querySelectorAll("tbody tr").forEach((tr) => {
      tr.classList.toggle("selected", Number(tr.dataset.caseId) === selectedId);
    });
    showError(null);
  } catch (err) {
    showError(err);
  }
}

["f-risk", "f-status", "f-sort"].forEach((id) => {
  $(id).onchange = () => loadQueue().catch(showError);
});

$("user").onchange = async (event) => {
  await loadMe(event.target.value);
  selectedId = null;
  $("detail").innerHTML = '<span class="muted">Select a case to review it.</span>';
  await loadQueue();
};

(async () => {
  await loadMe();
  await loadQueue();
})().catch(showError);
