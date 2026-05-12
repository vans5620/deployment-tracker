"""Render a self-contained interactive HTML dashboard from dataset.json.

Aggregates tranches by (event × category × day_offset), filtering to only
staggered categories. Adds per-row 'Redeemed' / 'Deployed' checkboxes that
persist in browser localStorage and dynamically drive the status column,
weekly summary and filters.
"""

import json
from datetime import date
from pathlib import Path


def render(dataset_path: Path, output_path: Path, today: date):
    with open(dataset_path) as f:
        ds = json.load(f)

    embedded_json = json.dumps(ds, separators=(",", ":"))
    html = HTML_TEMPLATE.replace("__DATASET_JSON__", embedded_json)
    html = html.replace("__GENERATED_AT__", ds["generated_at"])
    html = html.replace("__TODAY__", today.isoformat())
    html = html.replace("__EVENT_COUNT__", str(len(ds["events"])))
    html = html.replace("__OUT_OF_SCOPE_COUNT__", str(len(ds["out_of_scope"])))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Wrote {output_path} ({output_path.stat().st_size:,} bytes)")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Allocate Deployment Tracker</title>
<style>
  :root {
    --bg: #f5f7fa; --card: #ffffff; --ink: #1a2332; --ink-mute: #5b6573;
    --accent: #1f4e79; --accent-2: #2e75b6;
    --good: #2e7d32; --warn: #ed8936; --grid: #e6ecf2;
    --redem: #b45309; --deploy: #047857; --awaiting: #7c3aed;
  }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: var(--bg); color: var(--ink); font-size: 13px; }
  header { background: linear-gradient(135deg, #1f4e79 0%, #2e75b6 100%); color: white; padding: 18px 28px; }
  header h1 { margin: 0 0 4px; font-size: 22px; font-weight: 600; }
  header .meta { font-size: 12px; opacity: 0.9; }
  .container { max-width: 1700px; margin: 0 auto; padding: 20px; }

  .week-summary { background: var(--card); border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 18px; overflow: hidden; }
  .week-summary .week-header { padding: 14px 22px; background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%); border-bottom: 1px solid var(--grid); display: flex; justify-content: space-between; align-items: center; }
  .week-summary .week-header h2 { margin: 0; font-size: 15px; font-weight: 600; }
  .week-summary .week-header .small { font-size: 11px; color: var(--ink-mute); }
  .week-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0; }
  .week-side { padding: 16px 22px; }
  .week-side.redem { border-right: 1px solid var(--grid); }
  .week-side h3 { margin: 0 0 10px; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
  .week-side.redem h3 { color: var(--redem); }
  .week-side.deploy h3 { color: var(--deploy); }
  .week-side .total { font-size: 24px; font-weight: 600; margin-bottom: 2px; }
  .week-side .count { font-size: 11px; color: var(--ink-mute); margin-bottom: 12px; }
  .breakdown { font-size: 12px; }
  .breakdown-row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px dotted var(--grid); }
  .breakdown-row:last-child { border-bottom: 0; }

  .filter-bar { background: var(--card); border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); padding: 14px 18px; margin-bottom: 16px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
  .filter-bar input, .filter-bar select { padding: 7px 12px; border: 1px solid #d0d7de; border-radius: 5px; font-size: 13px; }
  .filter-bar input { min-width: 220px; }
  .filter-bar label { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; color: var(--ink-mute); }
  .filter-bar button { padding: 7px 12px; border: 1px solid #d0d7de; border-radius: 5px; font-size: 12px; cursor: pointer; background: #f5f7fa; }
  .filter-bar button:hover { background: var(--grid); }
  .filter-bar button.primary { background: var(--accent); color: white; border-color: var(--accent); }
  .filter-bar button.primary:hover { background: var(--accent-2); }
  .filter-bar button.danger { color: var(--warn); }
  .row-count { margin-left: auto; font-size: 12px; color: var(--ink-mute); }

  .table-wrap { background: var(--card); border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); overflow: hidden; }
  table.tranches { width: 100%; border-collapse: collapse; font-size: 12px; }
  table.tranches th { background: #1f4e79; color: white; padding: 10px 8px; text-align: left; font-weight: 600; text-transform: uppercase; font-size: 10px; letter-spacing: 0.5px; cursor: pointer; user-select: none; position: sticky; top: 0; z-index: 2; }
  table.tranches th:hover { background: #2e75b6; }
  table.tranches td { padding: 7px 8px; border-bottom: 1px solid var(--grid); vertical-align: top; }
  table.tranches td.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
  table.tranches td.center { text-align: center; }
  table.tranches tr:hover td { background: #fafbfd; }
  table.tranches tr.row-done td { background: #f1f8f3; opacity: 0.85; }
  table.tranches tr.row-done:hover td { background: #e8f5e9; }
  .tab-cell-redem { color: var(--redem); }
  .tab-cell-deploy { color: var(--deploy); }
  .pill { display: inline-block; padding: 2px 8px; border-radius: 11px; font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }
  .pill.done { background: #e8f5e9; color: var(--good); }
  .pill.due  { background: #fff4e5; color: var(--warn); }
  .pill.up   { background: #e3f2fd; color: var(--accent-2); }
  .pill.dash { background: #eee; color: #666; }
  .pill.day0 { background: #f0e6ff; color: #6a1b9a; }
  .pill.awaiting { background: #ede9fe; color: var(--awaiting); }
  .small { font-size: 11px; color: var(--ink-mute); }
  .empty { padding: 40px; text-align: center; color: var(--ink-mute); font-style: italic; }
  .scroll-x { overflow-x: auto; max-height: 75vh; overflow-y: auto; }

  .badge-fund { display: inline-block; padding: 1px 7px; border-radius: 10px; font-size: 10px; font-weight: 600; }
  .badge-fund.zerodha { background: #e0e7ff; color: #4338ca; }
  .badge-fund.kotak { background: #ffe7e0; color: #9a3412; }
  .badge-fund.dsp { background: #d1fae5; color: #065f46; }
  .badge-fund.none { background: #f0f0f0; color: #888; }

  .badge-cat { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
  .badge-cat.equity { background: #dbeafe; color: #1e40af; }
  .badge-cat.gold   { background: #fef3c7; color: #92400e; }
  .badge-cat.silver { background: #f3f4f6; color: #374151; }
  .badge-cat.urgent { background: #fee2e2; color: #b91c1c; }

  .check {
    appearance: none; -webkit-appearance: none; width: 18px; height: 18px;
    border: 2px solid #c0c8d2; border-radius: 4px; cursor: pointer; position: relative;
    transition: all 0.12s ease;
  }
  .check:hover { border-color: var(--accent-2); }
  .check.redem:checked { background: var(--redem); border-color: var(--redem); }
  .check.deploy:checked { background: var(--deploy); border-color: var(--deploy); }
  .check:checked::after {
    content: ""; position: absolute; left: 4px; top: 0;
    width: 5px; height: 11px; border: solid white; border-width: 0 2px 2px 0;
    transform: rotate(45deg);
  }
  .toast {
    position: fixed; bottom: 24px; right: 24px; background: #1f2937; color: white;
    padding: 10px 16px; border-radius: 6px; font-size: 13px; opacity: 0;
    transition: opacity 0.2s ease; pointer-events: none; z-index: 100;
  }
  .toast.show { opacity: 0.92; }
  .stats { display: flex; gap: 24px; margin-left: 14px; font-size: 11px; color: var(--ink-mute); }
  .stats span strong { color: var(--ink); font-size: 13px; margin-right: 3px; }
</style>
</head>
<body>
<header>
  <h1>Allocate Deployment Tracker</h1>
  <div class="meta">Generated __GENERATED_AT__ · Today: __TODAY__ · __EVENT_COUNT__ events · __OUT_OF_SCOPE_COUNT__ out of scope · Tick redeem/deploy as completed — state persists in this browser</div>
</header>

<div class="container">

  <!-- Weekly summary -->
  <div class="week-summary">
    <div class="week-header">
      <h2>This Week's Action Summary</h2>
      <div class="small" id="week-range"></div>
    </div>
    <div class="week-grid">
      <div class="week-side redem">
        <h3>↑ Redemptions (Mon)</h3>
        <div class="total" id="redem-total">—</div>
        <div class="count" id="redem-count"></div>
        <div class="breakdown" id="redem-breakdown"></div>
      </div>
      <div class="week-side deploy">
        <h3>↓ Deployments (Thu)</h3>
        <div class="total" id="deploy-total">—</div>
        <div class="count" id="deploy-count"></div>
        <div class="breakdown" id="deploy-breakdown"></div>
      </div>
    </div>
  </div>

  <!-- Filters + state controls -->
  <div class="filter-bar">
    <input type="text" id="search" placeholder="Search client, code, model..." />
    <select id="status-filter">
      <option value="active">Active only (Due + Upcoming + Awaiting)</option>
      <option value="all">All rows</option>
      <option value="Due this week">Due this week</option>
      <option value="Upcoming">Upcoming</option>
      <option value="Awaiting Deploy">Awaiting Deploy</option>
      <option value="Done">Done only</option>
    </select>
    <select id="model-filter"><option value="">All models</option></select>
    <select id="category-filter">
      <option value="">All staggered categories</option>
      <option value="Domestic Equity (pending — redeem today)">Domestic Equity (pending — redeem today)</option>
      <option value="Gold">Gold</option>
      <option value="Silver">Silver</option>
    </select>
    <select id="fund-filter">
      <option value="">All liquid funds</option>
      <option value="Zerodha">Zerodha</option>
      <option value="Kotak">Kotak</option>
      <option value="DSP">DSP</option>
      <option value="(none)">No parking</option>
    </select>
    <label><input type="checkbox" id="thisweek-only" /> This week only</label>
    <button id="export-state">⬇ Export state</button>
    <button id="import-state">⬆ Import state</button>
    <input type="file" id="import-file" accept=".json" style="display:none" />
    <button id="reset-state" class="danger">Reset overrides</button>
    <span class="row-count" id="row-count"></span>
  </div>

  <!-- Table -->
  <div class="table-wrap">
    <div class="scroll-x">
      <table class="tranches">
        <thead>
          <tr>
            <th data-sort="client">Client</th>
            <th data-sort="code">Code</th>
            <th data-sort="date_deployed">Date Deployed</th>
            <th data-sort="corpus" class="num">Inflow Amount</th>
            <th data-sort="scheme">Scheme</th>
            <th data-sort="model">Model</th>
            <th data-sort="category">Deployment Category</th>
            <th data-sort="redem_date">Redem Date</th>
            <th data-sort="redem_amt" class="num">Redem Amount</th>
            <th class="center">Redeemed?</th>
            <th data-sort="fund">Liquid Fund</th>
            <th data-sort="deploy_date">Deploy Date</th>
            <th data-sort="deploy_amt" class="num">Deploy Amount</th>
            <th class="center">Deployed?</th>
            <th data-sort="status">Status</th>
          </tr>
        </thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>
  </div>

</div>

<div class="toast" id="toast"></div>

<script>
const DATASET = __DATASET_JSON__;
const TODAY = new Date(DATASET.today + "T00:00:00");
const STATE_KEY = "allocate-deployment-tracker-state-v1";
const fmtINR = n => "₹" + Math.round(n).toLocaleString('en-IN');
const fmtINRshort = n => {
  if (Math.abs(n) >= 10000000) return "₹" + (n/10000000).toFixed(2) + " Cr";
  if (Math.abs(n) >= 100000)   return "₹" + (n/100000).toFixed(2) + " L";
  return "₹" + Math.round(n).toLocaleString('en-IN');
};

// ── Storage helpers ──────────────────────────────────────────────────────
let STATE = {};
function loadState() {
  try {
    const raw = localStorage.getItem(STATE_KEY);
    STATE = raw ? JSON.parse(raw) : {};
  } catch (e) { STATE = {}; }
}
function saveState() {
  try { localStorage.setItem(STATE_KEY, JSON.stringify(STATE)); }
  catch (e) { showToast("Could not save — storage unavailable", true); }
}
function rowState(row_id) {
  return STATE[row_id] || {};
}
function setRowState(row_id, key, val) {
  STATE[row_id] = STATE[row_id] || {};
  if (val) {
    STATE[row_id][key] = true;
    STATE[row_id].ts = new Date().toISOString();
  } else {
    delete STATE[row_id][key];
    if (Object.keys(STATE[row_id]).filter(k => k !== "ts").length === 0) {
      delete STATE[row_id];
    }
  }
  saveState();
}

function showToast(msg, error) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.style.background = error ? '#c0392b' : '#1f2937';
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 1800);
}

// ── Build aggregated rows with stable row_id ─────────────────────────────
const CATEGORY_MAP = {
  "Gold":   "Gold",
  "Silver": "Silver",
};
// Gold stagger only began for events on or after this date; earlier events deployed lump-sum.
const GOLD_STAGGER_FROM = new Date("2026-03-01T00:00:00");
const ROWS = [];
// Pending Domestic Equity tranches (originally scheduled under the OLD 50/50 rule
// but not yet executed) are surfaced as "redeem today + deploy today" actions
// because the rule has been updated to 100% Day-0 deployment.
const DOMESTIC_LEGACY_BUCKETS = new Set(["Domestic Equity MF", "SBI Nifty 50 ETF"]);
const DOMESTIC_PENDING_CAT = "Domestic Equity (pending — redeem today)";

DATASET.events.forEach(e => {
  const eventDate = new Date(e.date_deployed + "T00:00:00");
  const groups = {};
  e.tranches.forEach(t => {
    let cat = CATEGORY_MAP[t.bucket];
    let isDomesticPending = false;
    // Surface pending domestic equity tranches as today's action
    if (DOMESTIC_LEGACY_BUCKETS.has(t.bucket) && t.status !== "Done") {
      cat = DOMESTIC_PENDING_CAT;
      isDomesticPending = true;
    }
    if (!cat) return;
    // Gold stagger only applies from March 2026 onwards.
    if (cat === "Gold" && eventDate < GOLD_STAGGER_FROM) return;
    // Override dates to today for pending domestic equity (rule change retroactive)
    const redemDate = isDomesticPending ? DATASET.today : t.redemption_date;
    const deployDate = isDomesticPending ? DATASET.today : t.deployment_date;
    const fund = isDomesticPending ? "Zerodha" : (t.parking_fund || "(none)");
    const dayOff = isDomesticPending ? "today" : t.day_offset;

    const key = cat + "|" + dayOff;
    if (!groups[key]) {
      groups[key] = { category: cat, day_offset: dayOff,
                      redem_date: redemDate, deploy_date: deployDate,
                      fund: fund,
                      deploy_amt: 0, statuses: [] };
    }
    groups[key].deploy_amt += t.tranche_inr;
    // For pending domestic, force "Due this week" status (since deploy date is today)
    groups[key].statuses.push(isDomesticPending ? "Due this week" : t.status);
  });
  Object.values(groups).forEach(g => {
    let baseStatus = "Done";
    if (g.statuses.some(s => s === "Due this week")) baseStatus = "Due this week";
    else if (g.statuses.some(s => s === "Upcoming")) baseStatus = "Upcoming";
    else if (g.statuses.every(s => s === "Done")) baseStatus = "Done";
    else baseStatus = "—";
    const row_id = e.event_id + "|" + g.category + "|" + g.day_offset;
    ROWS.push({
      row_id,
      event: e,
      client: e.client_name,
      code: e.client_code || e.custody_code || "",
      ws_id: e.ws_client_id,
      date_deployed: e.date_deployed,
      corpus: e.corpus,
      scheme: e.scheme,
      model: e.model,
      category: g.category,
      day_offset: g.day_offset,
      redem_date: g.redem_date,
      redem_amt: g.redem_date ? g.deploy_amt : null,
      deploy_date: g.deploy_date,
      deploy_amt: g.deploy_amt,
      fund: g.fund,
      base_status: baseStatus,
    });
  });
});

// ── Compute dynamic status (combines base status + checkbox state) ──────
function dynamicStatus(r) {
  const s = rowState(r.row_id);
  if (s.deploy_done) return "Done";
  if (s.redem_done) return "Awaiting Deploy";
  return r.base_status;
}

// ── Weekly summary ──────────────────────────────────────────────────────
function thisWeekRange() {
  const d = new Date(TODAY);
  const day = d.getDay();
  const diffToMon = (day === 0 ? -6 : 1 - day);
  const mon = new Date(d); mon.setDate(d.getDate() + diffToMon); mon.setHours(0,0,0,0);
  const sun = new Date(mon); sun.setDate(mon.getDate() + 6);
  return [mon, sun];
}

function renderWeekSummary() {
  const [ws, we] = thisWeekRange();
  document.getElementById('week-range').textContent =
    ws.toISOString().slice(0,10) + " (Mon) → " + we.toISOString().slice(0,10) + " (Sun)";

  const redemPending = [], deployPending = [];
  ROWS.forEach(r => {
    const st = rowState(r.row_id);
    // Redemption pending if redem_date is this week and not marked redem_done
    if (r.redem_date) {
      const dt = new Date(r.redem_date + "T00:00:00");
      if (dt >= ws && dt <= we && !st.redem_done) redemPending.push(r);
    }
    // Deployment pending if deploy_date is this week and not marked deploy_done
    if (r.deploy_date) {
      const dt = new Date(r.deploy_date + "T00:00:00");
      if (dt >= ws && dt <= we && !st.deploy_done) deployPending.push(r);
    }
  });

  const redemTotal = redemPending.reduce((s, r) => s + r.redem_amt, 0);
  const deployTotal = deployPending.reduce((s, r) => s + r.deploy_amt, 0);
  document.getElementById('redem-total').textContent = redemPending.length ? fmtINRshort(redemTotal) : "—";
  document.getElementById('deploy-total').textContent = deployPending.length ? fmtINRshort(deployTotal) : "—";
  document.getElementById('redem-count').textContent = redemPending.length ? `${redemPending.length} pending` : "All redemptions ticked";
  document.getElementById('deploy-count').textContent = deployPending.length ? `${deployPending.length} pending` : "All deployments ticked";

  const byFund = {};
  redemPending.forEach(r => { byFund[r.fund] = (byFund[r.fund] || 0) + r.redem_amt; });
  const fundOrder = ["Zerodha", "Kotak", "DSP", "(none)"];
  document.getElementById('redem-breakdown').innerHTML =
    fundOrder.filter(f => byFund[f]).map(f =>
      `<div class="breakdown-row"><span><strong>${f}</strong></span><span>${fmtINRshort(byFund[f])}</span></div>`
    ).join("") || (redemPending.length ? "" : '<div class="small">—</div>');

  const byCat = {};
  deployPending.forEach(r => { byCat[r.category] = (byCat[r.category] || 0) + r.deploy_amt; });
  document.getElementById('deploy-breakdown').innerHTML =
    Object.entries(byCat).sort((a,b)=>b[1]-a[1]).map(([b, v]) =>
      `<div class="breakdown-row"><span><strong>${b}</strong></span><span>${fmtINRshort(v)}</span></div>`
    ).join("") || (deployPending.length ? "" : '<div class="small">—</div>');
}

// ── Populate filters ─────────────────────────────────────────────────────
function populateFilters() {
  const models = Array.from(new Set(ROWS.map(r => r.model))).sort();
  models.forEach(m => {
    const o = document.createElement('option');
    o.value = m; o.textContent = m;
    document.getElementById('model-filter').appendChild(o);
  });
}

// ── Sort state ──────────────────────────────────────────────────────────
let sortKey = 'deploy_date', sortDir = 'asc';
document.querySelectorAll('th[data-sort]').forEach(th => {
  th.addEventListener('click', () => {
    const k = th.dataset.sort;
    if (sortKey === k) sortDir = (sortDir === 'asc' ? 'desc' : 'asc');
    else { sortKey = k; sortDir = 'asc'; }
    renderTable();
  });
});

// ── Render table ────────────────────────────────────────────────────────
function renderTable() {
  const search = document.getElementById('search').value.toLowerCase();
  const sf = document.getElementById('status-filter').value;
  const mf = document.getElementById('model-filter').value;
  const cf = document.getElementById('category-filter').value;
  const ff = document.getElementById('fund-filter').value;
  const thisWeekOnly = document.getElementById('thisweek-only').checked;
  const [wsM, weM] = thisWeekRange();

  let rows = ROWS.filter(r => {
    const status = dynamicStatus(r);
    if (sf === 'active' && status === 'Done') return false;
    if (sf && sf !== 'active' && sf !== 'all' && status !== sf) return false;
    if (mf && r.model !== mf) return false;
    if (cf && r.category !== cf) return false;
    if (ff && r.fund !== ff) return false;
    if (search) {
      const hay = (r.client + " " + r.code + " " + r.model + " " + (r.scheme || "") + " " + r.category).toLowerCase();
      if (!hay.includes(search)) return false;
    }
    if (thisWeekOnly) {
      const inWeek = (d) => { if (!d) return false; const dt = new Date(d + "T00:00:00"); return dt >= wsM && dt <= weM; };
      if (!(inWeek(r.redem_date) || inWeek(r.deploy_date))) return false;
    }
    return true;
  });

  const get = (r, k) => {
    if (k === 'status') return dynamicStatus(r);
    if (k === 'redem_amt' || k === 'deploy_amt' || k === 'corpus') {
      return r[k] === null || r[k] === undefined ? -1 : r[k];
    }
    return r[k] === null || r[k] === undefined ? '' : String(r[k]);
  };
  rows.sort((a, b) => {
    const va = get(a, sortKey), vb = get(b, sortKey);
    if (va < vb) return sortDir === 'asc' ? -1 : 1;
    if (va > vb) return sortDir === 'asc' ? 1 : -1;
    return 0;
  });

  document.getElementById('row-count').textContent = rows.length.toLocaleString() + " rows";

  if (!rows.length) {
    document.getElementById('tbody').innerHTML = '<tr><td colspan="15" class="empty">No rows match the current filters.</td></tr>';
    return;
  }

  const fundClass = (f) => {
    const k = f.toLowerCase();
    if (k.includes('zerodha')) return 'zerodha';
    if (k.includes('kotak')) return 'kotak';
    if (k.includes('dsp')) return 'dsp';
    return 'none';
  };
  const catClass = (c) => c.startsWith('Domestic Equity (pending') ? 'urgent'
                            : c.startsWith('Domestic') ? 'equity'
                            : c === 'Gold' ? 'gold'
                            : c === 'Silver' ? 'silver'
                            : 'equity';
  const statusPill = (s) => {
    const cls = {Done:'done','Due this week':'due',Upcoming:'up','Awaiting Deploy':'awaiting','—':'dash'}[s] || 'dash';
    return `<span class="pill ${cls}">${s}</span>`;
  };
  const dayLabel = (d) => {
    if (d === null || d === undefined) return '<span class="pill dash">—</span>';
    if (d === "today") return '<span class="pill due">REDEEM TODAY</span>';
    if (d === 0) return '<span class="pill day0">Day 0</span>';
    return `<span class="small">Day ${d}</span>`;
  };
  const wd = (s) => {
    if (!s) return '';
    const dt = new Date(s + 'T00:00:00');
    const idx = (dt.getDay() + 6) % 7;
    return ' (' + ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][idx] + ')';
  };

  // Build via DOM (so checkbox handlers attach cleanly)
  const tbody = document.getElementById('tbody');
  tbody.innerHTML = '';
  for (const r of rows) {
    const status = dynamicStatus(r);
    const st = rowState(r.row_id);
    const rowClass = status === 'Done' ? 'row-done' : '';
    const tr = document.createElement('tr');
    tr.className = rowClass;
    tr.innerHTML = `
      <td><strong>${r.client}</strong><div class="small">WS ${r.ws_id}</div></td>
      <td>${r.code}</td>
      <td>${r.date_deployed || '—'}</td>
      <td class="num">${r.corpus !== null && r.corpus !== undefined ? fmtINR(r.corpus) : '—'}</td>
      <td>${r.scheme || '—'}</td>
      <td>${r.model}</td>
      <td><span class="badge-cat ${catClass(r.category)}">${r.category}</span> ${dayLabel(r.day_offset)}</td>
      <td class="tab-cell-redem">${r.redem_date ? r.redem_date + wd(r.redem_date) : '—'}</td>
      <td class="num tab-cell-redem">${r.redem_amt !== null ? fmtINR(r.redem_amt) : '—'}</td>
      <td class="center">${r.redem_date
          ? `<input type="checkbox" class="check redem" data-row="${r.row_id}" ${st.redem_done ? 'checked' : ''}>`
          : '—'}</td>
      <td><span class="badge-fund ${fundClass(r.fund)}">${r.fund}</span></td>
      <td class="tab-cell-deploy">${r.deploy_date ? r.deploy_date + wd(r.deploy_date) : '—'}</td>
      <td class="num tab-cell-deploy">${r.deploy_amt !== null ? fmtINR(r.deploy_amt) : '—'}</td>
      <td class="center">${r.deploy_date
          ? `<input type="checkbox" class="check deploy" data-row="${r.row_id}" ${st.deploy_done ? 'checked' : ''}>`
          : '—'}</td>
      <td>${statusPill(status)}</td>`;
    tbody.appendChild(tr);
  }

  // Attach checkbox handlers
  tbody.querySelectorAll('input.check').forEach(cb => {
    cb.addEventListener('change', (ev) => {
      const t = ev.target;
      const row_id = t.dataset.row;
      const isRedem = t.classList.contains('redem');
      setRowState(row_id, isRedem ? 'redem_done' : 'deploy_done', t.checked);
      // If user marks deploy done, auto-mark redeem done as well (you can't have deployed without redeeming)
      if (!isRedem && t.checked) {
        setRowState(row_id, 'redem_done', true);
      }
      // If user unmarks redeem, also unmark deploy
      if (isRedem && !t.checked) {
        setRowState(row_id, 'deploy_done', false);
      }
      renderTable();
      renderWeekSummary();
      showToast("Saved");
    });
  });
}

// ── State controls (export / import / reset) ─────────────────────────────
document.getElementById('export-state').addEventListener('click', () => {
  const blob = new Blob([JSON.stringify(STATE, null, 2)], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `deployment-tracker-state-${DATASET.today}.json`;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast(`Exported ${Object.keys(STATE).length} marked rows`);
});

document.getElementById('import-state').addEventListener('click', () => {
  document.getElementById('import-file').click();
});
document.getElementById('import-file').addEventListener('change', (ev) => {
  const f = ev.target.files[0];
  if (!f) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const incoming = JSON.parse(e.target.result);
      if (typeof incoming !== 'object') throw new Error('not an object');
      // Merge: existing state + incoming; incoming wins on conflict
      STATE = {...STATE, ...incoming};
      saveState();
      renderTable(); renderWeekSummary();
      showToast(`Imported ${Object.keys(incoming).length} rows`);
    } catch (err) {
      showToast("Import failed: " + err.message, true);
    }
  };
  reader.readAsText(f);
  ev.target.value = '';
});
document.getElementById('reset-state').addEventListener('click', () => {
  if (!confirm("Clear all checkbox overrides? This cannot be undone (export first if you want to keep them).")) return;
  STATE = {};
  saveState();
  renderTable(); renderWeekSummary();
  showToast("All overrides cleared");
});

// ── Init ────────────────────────────────────────────────────────────────
loadState();
populateFilters();
renderWeekSummary();
renderTable();

['search','status-filter','model-filter','category-filter','fund-filter','thisweek-only'].forEach(id => {
  document.getElementById(id).addEventListener('input', renderTable);
  document.getElementById(id).addEventListener('change', renderTable);
});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    here = Path(__file__).resolve().parent.parent
    render(here / "outputs" / "dataset.json", here / "outputs" / "dashboard.html", date.today())
