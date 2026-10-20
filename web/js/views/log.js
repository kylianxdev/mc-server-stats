// Log page: commands, operator history, admin actions, whitelist/bans, logins and warnings.
import { S } from "../state.js";
import { t } from "../i18n.js";
import { kpi } from "../charts.js";
import { $, color, esc, nf, players } from "../util.js";

const TABS = {
  commands: [["t", "col.time"], ["p", "col.player"], ["c", "col.command"]],
  ops: [["t", "col.time"], ["p", "col.player"], ["op", "col.action"], ["by", "col.by"]],
  feedback: [["t", "col.time"], ["p", "col.by"], ["m", "col.result"]],
  moderation: [["t", "col.time"], ["p", "col.player"], ["a", "col.action"], ["by", "col.by"]],
  logins: [["t", "col.time"], ["p", "col.player"]],
  warnings: [["t", "col.time"], ["m", "col.message"]],
};

function cell(k, r) {
  const v = r[k];
  if (k === "t") return `<td class="t">${esc(v)}</td>`;
  if (k === "p") return `<td style="color:${color(v)}">${esc(v)}</td>`;
  if (k === "c") return `<td><code>${esc(v)}</code>${r.admin ? ` <span class="chip warn">${t("chip.admin")}</span>` : r.tried ? ` <span class="chip">${t("chip.tried")}</span>` : ""}</td>`;
  if (k === "op") return `<td>${v ? `<span class="chip bad">${t("chip.became_op")}</span>` : `<span class="chip good">${t("chip.lost_op")}</span>`}</td>`;
  if (k === "by") return `<td>${v === "console" ? `<span class="chip">${t("chip.console")}</span>` : esc(v)}</td>`;
  if (k === "a") return `<td>${esc(t(`mod.${v}`, { reason: r.reason || "" }))}</td>`;
  if (k === "m") return `<td><code>${esc(v)}</code></td>`;
  return `<td>${esc(v)}</td>`;
}

export function viewLog() {
  const d = S.data;
  return `
    <div class="grid kpis">
      ${kpi("item/command_block_minecart", t("log.current_ops"), d.current_ops.length, esc(d.current_ops.join(", ")) || t("nobody"))}
      ${kpi("item/name_tag", t("log.ever_ops"), d.ever_ops.length, esc(d.ever_ops.join(", ")) || t("nobody"))}
      ${kpi("item/writable_book", t("log.commands"), nf(d.commands.length), t("log.admin_n", { n: d.commands.filter(c => c.admin).length }))}
      ${kpi("item/barrier", t("log.warnings"), nf(d.warnings.length))}
    </div>
    <div class="sub-tabs">${Object.keys(TABS).map(k => `<button class="btn ${k === S.logTab ? "on" : ""}" data-log="${k}">${t(`log.${k}`)}</button>`).join("")}</div>
    <div class="tools">
      <input type="search" id="q" placeholder="${t("log.search")}">
      <select id="pf"><option value="">${t("log.all_players")}</option>${players().map(p => `<option>${esc(p)}</option>`).join("")}</select>
      <label class="tg ${S.logTab === "commands" ? "" : "hidden"}"><input type="checkbox" id="ao"> ${t("log.admin_only")}</label>
    </div>
    <div class="tablewrap" id="tbl"></div>`;
}

export function renderTable() {
  const cols = TABS[S.logTab];
  let rows = S.data[S.logTab] || [];
  const q = $("q").value.trim().toLowerCase(), p = $("pf").value;
  if (p) rows = rows.filter(r => r.p === p);
  if (S.logTab === "commands" && $("ao").checked) rows = rows.filter(r => r.admin);
  if (q) rows = rows.filter(r => Object.values(r).some(v => String(v).toLowerCase().includes(q)));
  $("tbl").innerHTML = rows.length
    ? `<table><thead><tr>${cols.map(c => `<th>${t(c[1])}</th>`).join("")}</tr></thead><tbody>${rows.slice(0, 500).map(r =>
        `<tr class="${r.admin === true ? "admin" : ""}">${cols.map(c => cell(c[0], r)).join("")}</tr>`).join("")}</tbody></table>`
    : `<div class="empty">${t("log.nothing")}</div>`;
}
