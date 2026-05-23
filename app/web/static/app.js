const $ = (sel) => document.querySelector(sel);
const api = async (path, opts) => {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.headers.get("content-type")?.includes("json") ? res.json() : res.text();
};
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// ---- tabs ----
document.querySelectorAll("nav button").forEach((btn) => {
  btn.onclick = () => {
    document.querySelectorAll("nav button").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    btn.classList.add("active");
    $("#" + btn.dataset.tab).classList.add("active");
  };
});

// ---- auth status ----
async function loadAuth() {
  const { connected } = await api("/api/auth/status");
  const el = $("#auth-status");
  if (connected) {
    el.textContent = "konto sprzedawcy: połączone";
    el.classList.add("connected");
  } else {
    el.innerHTML = '<a href="/auth/connect">Połącz konto Allegro</a>';
  }
}

// ---- opportunities ----
async function loadOpportunities() {
  const status = $("#opp-status").value;
  const rows = await api("/api/opportunities" + (status ? `?status=${status}` : ""));
  const tbody = $("#opp-table tbody");
  tbody.innerHTML = rows.map((r) => `
    <tr>
      <td class="roi">${(r.roi * 100).toFixed(1)}%</td>
      <td>${r.net_profit.toFixed(2)} zł</td>
      <td>${r.buy_total.toFixed(2)} zł</td>
      <td>${r.ref_price.toFixed(2)} zł</td>
      <td>${esc(r.name)}</td>
      <td>${esc(r.condition)}</td>
      <td><a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.allegro_offer_id)}</a></td>
      <td>
        <select data-id="${r.id}" class="opp-status">
          ${["new", "seen", "bought", "listed", "sold", "dismissed"]
            .map((s) => `<option ${s === r.status ? "selected" : ""}>${s}</option>`).join("")}
        </select>
      </td>
    </tr>`).join("");
  tbody.querySelectorAll(".opp-status").forEach((sel) => {
    sel.onchange = () => api(`/api/opportunities/${sel.dataset.id}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: sel.value }),
    });
  });
}
$("#opp-refresh").onclick = loadOpportunities;
$("#opp-status").onchange = loadOpportunities;

// ---- watchlists ----
async function loadWatchlists() {
  const rows = await api("/api/watchlists");
  $("#wl-table tbody").innerHTML = rows.map((r) => `
    <tr>
      <td>${esc(r.name)}</td><td>${esc(r.phrase || "")}</td>
      <td>${esc(r.category_id || "")}</td><td>${esc(r.condition)}</td>
      <td>${esc(r.last_scan_at || "—")}</td>
      <td><button class="secondary wl-del" data-id="${r.id}">usuń</button></td>
    </tr>`).join("");
  $("#wl-table").querySelectorAll(".wl-del").forEach((b) => {
    b.onclick = async () => { await api(`/api/watchlists/${b.dataset.id}`, { method: "DELETE" }); loadWatchlists(); };
  });
}
$("#wl-form").onsubmit = async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = {};
  for (const [k, v] of fd.entries()) if (v !== "") body[k] = v;
  ["price_from", "price_to"].forEach((k) => { if (body[k]) body[k] = parseFloat(body[k]); });
  await api("/api/watchlists", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  e.target.reset();
  loadWatchlists();
};

// ---- settings ----
async function loadSettings() {
  const s = await api("/api/settings");
  $("#settings-form").innerHTML = Object.entries(s).map(([k, v]) =>
    `<label>${esc(k)}<input name="${esc(k)}" value="${esc(v)}"></label>`).join("");
}
$("#settings-save").onclick = async () => {
  const fd = new FormData($("#settings-form"));
  const body = Object.fromEntries(fd.entries());
  await api("/api/settings", {
    method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  alert("zapisano");
};

// ---- preview ----
$("#pv-render").onclick = async () => {
  const image_urls = $("#pv-images").value.split("\n").map((s) => s.trim()).filter(Boolean);
  const { html } = await api("/api/preview", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: $("#pv-name").value, image_urls }),
  });
  $("#pv-output").innerHTML = html;
};

loadAuth();
loadOpportunities();
loadWatchlists();
loadSettings();
