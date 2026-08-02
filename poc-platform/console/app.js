/**
 * Platform console: persona switcher, prototype supervisor and the guardrails
 * of this environment. Plain DOM on purpose - the platform has no build step.
 */

const $ = (id) => document.getElementById(id);
const REFRESH_MS = 3000;

let state = { overview: null, openDoc: null, logsFor: null };

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = (await response.json()).detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  const type = response.headers.get("content-type") ?? "";
  return type.includes("application/json") ? response.json() : response.text();
}

function el(tag, props = {}, children = []) {
  const node = Object.assign(document.createElement(tag), props);
  for (const child of [].concat(children)) {
    if (child) node.append(child);
  }
  return node;
}

function showProblems(problems) {
  const box = $("problems");
  box.hidden = problems.length === 0;
  box.textContent = "";
  if (!problems.length) return;
  box.append(el("strong", { textContent: "Configuration problems" }));
  const list = el("ul");
  for (const problem of problems) {
    list.append(el("li", { textContent: `${problem.path}: ${problem.error}` }));
  }
  box.append(list);
}

function renderPrincipals(overview) {
  const select = $("principal");
  select.textContent = "";
  for (const principal of overview.principals) {
    select.append(
      el("option", {
        value: principal.email,
        textContent: `${principal.display_name} — ${principal.title}`,
      }),
    );
  }
  select.value = overview.current_principal.email;
  $("principal-role").textContent = overview.current_principal.platform_role;
  $("env-badge").textContent = `${overview.environment} environment`;
}

function statusPill(status) {
  const label =
    status.state === "running"
      ? "running"
      : status.state === "starting"
        ? "starting…"
        : status.state;
  return el("span", { className: `pill ${status.state}`, textContent: label });
}

function appCard(app) {
  const { manifest, status, violations } = app;
  const running = status.state === "running";
  const busy = status.state === "starting";

  const card = el("article", { className: "card" });
  card.append(
    el("div", { className: "card-head" }, [
      el("div", {}, [
        el("h3", { textContent: manifest.name }),
        el("span", { className: "muted", textContent: manifest.summary }),
      ]),
      statusPill(status),
    ]),
    el("div", { className: "chips" }, [
      ...manifest.stack.map((tech) => el("span", { className: "chip", textContent: tech })),
      el("span", { className: "chip", textContent: `data: ${manifest.data.classification}` }),
    ]),
    el("div", { className: "muted" }, [
      el("span", { textContent: `${manifest.base_path}/ · port ${status.port} · your role here: ` }),
      el("span", { className: "pill accent", textContent: app.role_for_current_principal }),
    ]),
  );

  if (violations.length) {
    card.append(
      el("div", { className: "violations" }, [
        el("strong", { textContent: "Blocked by environment policy" }),
        el("ul", {}, violations.map((v) => el("li", { textContent: v }))),
      ]),
    );
  }

  const capabilities = el("details", {}, [
    el("summary", { textContent: "What it demonstrates / what it fakes" }),
    el("ul", {}, manifest.capabilities.map((c) => el("li", { textContent: `✓ ${c}` }))),
    el("ul", {}, manifest.limitations.map((l) => el("li", { textContent: `✗ ${l}` }))),
  ]);
  card.append(capabilities);

  const open = el("button", {
    className: "primary",
    textContent: "Open",
    disabled: !running,
    onclick: () => window.open(`${manifest.base_path}/`, "_blank"),
  });
  const start = el("button", {
    textContent: busy ? "Starting…" : "Start",
    disabled: running || busy || violations.length > 0,
    onclick: () => act(manifest.id, "start"),
  });
  const stop = el("button", {
    textContent: "Stop",
    disabled: status.state === "stopped",
    onclick: () => act(manifest.id, "stop"),
  });
  const logs = el("button", {
    className: "ghost",
    textContent: "Logs",
    onclick: () => openLogs(manifest.id, manifest.name),
  });
  card.append(el("div", { className: "card-actions" }, [open, start, stop, logs]));

  if (status.message) {
    card.append(el("p", { className: "muted", textContent: status.message }));
  }
  return card;
}

function renderApps(overview) {
  const grid = $("apps");
  grid.textContent = "";
  if (!overview.apps.length) {
    grid.append(el("p", { className: "muted", textContent: "No poc.yaml manifests found." }));
    return;
  }
  for (const app of overview.apps) grid.append(appCard(app));
}

function guardrailItem(rule) {
  return el("li", {}, [
    el("strong", { textContent: rule.title }),
    el("span", { textContent: rule.detail }),
    rule.instead ? el("em", { textContent: `Instead: ${rule.instead}` }) : null,
  ]);
}

function renderPolicy(policy) {
  $("allowed").replaceChildren(...policy.allowed.map(guardrailItem));
  $("not-allowed").replaceChildren(...policy.not_allowed.map(guardrailItem));
  const limits = policy.limits;
  $("limits").textContent =
    `Enforced on every manifest: stage ∈ [${limits.stages}], data ∈ ` +
    `[${limits.data_classifications}], store ∈ [${limits.data_stores}], identity ∈ ` +
    `[${limits.identity_modes}], at least ${limits.min_limitations} declared limitation. ` +
    "A prototype that breaks a rule cannot be started from this console.";
}

/** Minimal markdown -> HTML for the docs pane (headings, lists, tables, code). */
function renderMarkdown(markdown) {
  const inline = (text) =>
    text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');

  const lines = markdown.split("\n");
  const out = [];
  let list = null;
  let table = null;
  let code = null;

  const closeList = () => {
    if (list) out.push(`<ul>${list.join("")}</ul>`), (list = null);
  };
  const closeTable = () => {
    if (!table) return;
    const [head, ...rows] = table;
    const cells = (row, tag) =>
      row.map((cell) => `<${tag}>${inline(cell)}</${tag}>`).join("");
    out.push(
      `<table><thead><tr>${cells(head, "th")}</tr></thead><tbody>` +
        rows.map((row) => `<tr>${cells(row, "td")}</tr>`).join("") +
        "</tbody></table>",
    );
    table = null;
  };

  for (const line of lines) {
    if (line.startsWith("```")) {
      if (code === null) {
        closeList();
        closeTable();
        code = [];
      } else {
        out.push(`<pre><code>${inline(code.join("\n"))}</code></pre>`);
        code = null;
      }
      continue;
    }
    if (code !== null) {
      code.push(line);
      continue;
    }

    const heading = line.match(/^(#{1,4})\s+(.*)$/);
    const bullet = line.match(/^[-*]\s+(.*)$/);
    const isRow = line.trim().startsWith("|") && line.trim().endsWith("|");

    if (heading) {
      closeList();
      closeTable();
      out.push(`<h${heading[1].length}>${inline(heading[2])}</h${heading[1].length}>`);
    } else if (bullet) {
      closeTable();
      (list ??= []).push(`<li>${inline(bullet[1])}</li>`);
    } else if (isRow) {
      closeList();
      const cells = line.trim().slice(1, -1).split("|").map((cell) => cell.trim());
      if (cells.every((cell) => /^:?-{2,}:?$/.test(cell))) continue;
      (table ??= []).push(cells);
    } else if (line.trim() === "") {
      closeList();
      closeTable();
    } else {
      closeList();
      closeTable();
      out.push(`<p>${inline(line)}</p>`);
    }
  }
  closeList();
  closeTable();
  return out.join("\n");
}

function renderDocTabs(docs) {
  const tabs = $("doc-tabs");
  tabs.textContent = "";
  for (const doc of docs) {
    tabs.append(
      el("button", {
        textContent: doc.title,
        className: state.openDoc === doc.slug ? "active" : "",
        onclick: () => openDoc(doc.slug),
      }),
    );
  }
}

async function openDoc(slug) {
  state.openDoc = slug;
  renderDocTabs(state.overview.docs);
  const markdown = await api(`/api/platform/docs/${slug}`);
  $("doc-body").innerHTML = renderMarkdown(markdown);
}

async function openLogs(appId, name) {
  state.logsFor = appId;
  $("drawer").hidden = false;
  $("drawer-title").textContent = `${name} — logs`;
  $("drawer-body").textContent = await api(`/api/platform/apps/${appId}/logs`);
}

async function act(appId, action) {
  try {
    await api(`/api/platform/apps/${appId}/${action}`, { method: "POST" });
  } catch (error) {
    showProblems([{ path: appId, error: error.message }]);
  }
  await refresh();
}

async function refresh() {
  const overview = await api("/api/platform/overview");
  state.overview = overview;
  showProblems(overview.problems);
  renderPrincipals(overview);
  renderApps(overview);
  renderPolicy(overview.policy);
  if (!state.openDoc && overview.docs.length) {
    await openDoc(overview.docs[0].slug);
  } else {
    renderDocTabs(overview.docs);
  }
  if (state.logsFor && !$("drawer").hidden) {
    $("drawer-body").textContent = await api(`/api/platform/apps/${state.logsFor}/logs`);
  }
}

$("principal").onchange = async (event) => {
  await api("/api/platform/session", {
    method: "POST",
    body: JSON.stringify({ email: event.target.value }),
  });
  await refresh();
};

$("reload").onclick = async () => {
  await api("/api/platform/reload", { method: "POST" });
  await refresh();
};

$("drawer-close").onclick = () => {
  state.logsFor = null;
  $("drawer").hidden = true;
};

refresh().catch((error) => showProblems([{ path: "console", error: error.message }]));
setInterval(() => refresh().catch(() => {}), REFRESH_MS);
