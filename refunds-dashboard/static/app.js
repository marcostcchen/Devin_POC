let me = { email: "", role: "support_agent", proxyAuth: false };
let settings = { approval_threshold_amount: 200, reason_codes: [] };
let selectedId = null;

const $ = (id) => document.getElementById(id);
const isFinance = () => me.role === "finance_approver";
const money = (n) => `$${n.toFixed(2)}`;

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
  me = { email: data.email, role: data.role, proxyAuth: data.proxy_auth };
  const select = $("user");
  if (me.proxyAuth) {
    // Someone in front of the app owns identity; show it instead of a switcher.
    select.hidden = true;
    $("acting-as").hidden = false;
    $("acting-as").textContent = data.display_name || data.email;
  } else if (!select.options.length) {
    for (const [addr, role] of Object.entries(data.users)) {
      const opt = document.createElement("option");
      opt.value = addr;
      opt.textContent = `${addr} (${role})`;
      select.appendChild(opt);
    }
  }
  if (!me.proxyAuth) select.value = me.email;
  const role = $("role");
  role.textContent = me.role.replace("_", " ");
  role.className = `pill ${isFinance() ? "st-processed" : "st-approved"}`;
  showError(null);
}

async function loadConfig() {
  settings = await api("api/config");
  const reason = $("n-reason");
  settings.reason_codes.forEach((code) => {
    reason.appendChild(Object.assign(document.createElement("option"), { value: code, textContent: code }));
  });
  $("threshold-note").textContent =
    `Requests of ${money(settings.approval_threshold_amount)} or more need a finance approver's ` +
    `sign-off, and only finance can pay one out.`;
}

async function renderMetrics() {
  const m = await api("api/metrics/summary");
  const cards = [
    ["Refunded (processed)", money(m.total_refunded_amount)],
    ["Approved, awaiting payout", money(m.total_approved_amount)],
    ["Pending", `${m.pending_count} · ${money(m.pending_amount)}`],
    ["Denied", String(m.counts_by_status.denied)],
    ["Average request", money(m.average_request_amount)],
  ];
  const container = $("metrics");
  container.innerHTML = "";
  for (const [label, value] of cards) {
    const card = document.createElement("div");
    card.className = "metric";
    card.append(
      Object.assign(document.createElement("div"), { className: "value", textContent: value }),
      Object.assign(document.createElement("div"), { className: "muted", textContent: label })
    );
    container.appendChild(card);
  }
}

function requestRow(r) {
  const tr = document.createElement("tr");
  tr.className = r.id === selectedId ? "request selected" : "request";
  const order = document.createElement("td");
  order.textContent = r.order_id;
  const name = document.createElement("td");
  name.textContent = r.customer_name;
  const amount = document.createElement("td");
  amount.className = "amount";
  amount.textContent = money(r.amount);
  if (r.requires_finance_approval) amount.append(" ", pill("finance", "threshold"));
  const reason = document.createElement("td");
  reason.textContent = r.reason_code;
  const status = document.createElement("td");
  status.appendChild(pill(r.status, `st-${r.status}`));
  tr.append(order, name, amount, reason, status);
  tr.onclick = () => selectRequest(r.id);
  return tr;
}

function auditLine(entry) {
  const li = document.createElement("li");
  li.textContent =
    `${entry.created_at} — ${entry.actor} (${entry.actor_role}) ${entry.action}: ` +
    `${entry.status_before || "—"} → ${entry.status_after} — "${entry.reason}"`;
  return li;
}

async function renderDetail(requestId) {
  const detail = $("detail");
  const [r, trail] = await Promise.all([
    api(`api/refunds/${requestId}`),
    api(`api/refunds/${requestId}/audit`),
  ]);

  detail.innerHTML = "";
  const title = document.createElement("div");
  title.className = "row";
  title.append(
    Object.assign(document.createElement("strong"), {
      textContent: `${r.order_id} — ${r.customer_name}`,
    }),
    pill(r.status, `st-${r.status}`)
  );
  detail.appendChild(title);

  const meta = document.createElement("p");
  meta.className = "muted";
  meta.textContent =
    `${money(r.amount)} · ${r.reason_code} · raised by ${r.requested_by} on ${r.created_at}` +
    (r.requires_finance_approval ? " · finance sign-off required" : "");
  detail.appendChild(meta);

  const blockedByThreshold = r.requires_finance_approval && !isFinance();
  const decidable = r.status === "pending" && !blockedByThreshold;
  const payable = r.status === "approved" && isFinance();

  detail.appendChild(
    Object.assign(document.createElement("strong"), {
      textContent: r.status === "approved" ? "Payout" : "Decision",
      style: "display:block;margin-top:14px",
    })
  );
  const reason = document.createElement("textarea");
  reason.id = "reason";
  reason.placeholder = "Reason (required, at least 5 characters)";
  reason.disabled = !decidable && !payable;
  detail.appendChild(reason);

  const actions = document.createElement("div");
  actions.className = "row";
  actions.style.marginTop = "8px";
  const buttons = [
    ["Approve", "", decidable, () => submitDecision(r.id, "approve", reason.value)],
    ["Deny", "danger", decidable, () => submitDecision(r.id, "deny", reason.value)],
    ["Mark as processed", "warn", payable, () => submitPayout(r.id, reason.value)],
  ];
  for (const [label, cls, enabled, onclick] of buttons) {
    const btn = document.createElement("button");
    btn.textContent = label;
    if (cls) btn.className = cls;
    btn.disabled = !enabled;
    btn.onclick = onclick;
    actions.appendChild(btn);
  }
  detail.appendChild(actions);

  const note =
    (blockedByThreshold && r.status === "pending"
      ? `This refund is ${money(settings.approval_threshold_amount)} or more, so only a finance approver can decide it.`
      : "") ||
    (r.status === "approved" && !isFinance() ? "Only a finance approver can pay this out." : "") ||
    (r.status === "processed" ? "Paid out — the payout is mocked, no money moved." : "") ||
    (r.status === "denied" ? "Denied. A denial is final in this prototype." : "");
  if (note) {
    detail.appendChild(Object.assign(document.createElement("p"), { className: "muted", textContent: note }));
  }

  detail.appendChild(
    Object.assign(document.createElement("strong"), {
      textContent: "Audit trail",
      style: "display:block;margin-top:14px",
    })
  );
  const list = document.createElement("ul");
  list.className = "history";
  trail.forEach((e) => list.appendChild(auditLine(e)));
  detail.appendChild(list);
}

async function submitDecision(requestId, decision, reason) {
  await send(`api/refunds/${requestId}/decision`, { decision, reason });
}

async function submitPayout(requestId, reason) {
  await send(`api/refunds/${requestId}/process`, { reason });
}

async function send(path, body) {
  if (body.reason.trim().length < 5) {
    showError(new Error("a reason of at least 5 characters is required"));
    return;
  }
  try {
    await api(path, { method: "POST", body: JSON.stringify(body) });
    showError(null);
    await refresh();
  } catch (err) {
    showError(err);
  }
}

async function selectRequest(requestId) {
  selectedId = requestId;
  await refresh();
}

async function createRequest() {
  const amount = Number($("n-amount").value);
  if (!$("n-customer").value.trim() || !$("n-order").value.trim() || !(amount > 0)) {
    showError(new Error("customer, order id and a positive amount are required"));
    return;
  }
  try {
    const created = await api("api/refunds", {
      method: "POST",
      body: JSON.stringify({
        customer_name: $("n-customer").value.trim(),
        order_id: $("n-order").value.trim(),
        amount,
        reason_code: $("n-reason").value,
      }),
    });
    ["n-customer", "n-order", "n-amount"].forEach((id) => ($(id).value = ""));
    showError(null);
    await selectRequest(created.id);
  } catch (err) {
    showError(err);
  }
}

async function refresh() {
  const params = new URLSearchParams({
    status: $("f-status").value,
    sort_by: $("f-sort").value,
    sort_direction: $("f-dir").value,
  });
  if ($("f-min").value) params.set("min_amount", $("f-min").value);
  if ($("f-max").value) params.set("max_amount", $("f-max").value);
  const requests = await api(`api/refunds?${params}`);

  const tbody = $("requests");
  tbody.innerHTML = "";
  if (!requests.some((r) => r.id === selectedId)) selectedId = null;
  requests.forEach((r) => tbody.appendChild(requestRow(r)));
  $("count").textContent = `${requests.length} request(s)`;

  await renderMetrics();
  if (selectedId === null) {
    $("detail").innerHTML =
      "<strong>Request detail</strong><p class='muted'>Select a request from the queue.</p>";
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

["f-status", "f-min", "f-max", "f-sort", "f-dir"].forEach((id) => {
  $(id).onchange = () => refresh().catch(showError);
});

$("new-toggle").onclick = () => ($("new-form").hidden = !$("new-form").hidden);
$("n-submit").onclick = () => createRequest();

(async () => {
  await loadMe();
  await loadConfig();
  await refresh();
})().catch(showError);
