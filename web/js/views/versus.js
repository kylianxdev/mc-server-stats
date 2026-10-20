// Versus: two players side by side, statistic by statistic.
import { S } from "../state.js";
import { t } from "../i18n.js";
import { v3d } from "../skins.js";
import { color, dur, esc, icon, nf, players, tex, xpPerHour } from "../util.js";

export function viewVersus(a, b) {
  const ps = players();
  a = ps.includes(a) ? a : ps[0];
  b = ps.includes(b) && b !== a ? b : ps.find(p => p !== a);
  const d = S.data;
  const rows = [
    ["level", tex("item/experience_bottle", "s"), t("versus.level"), p => d.progress?.[p]?.xp || 0, p => `${t("level.short")} ${d.progress?.[p]?.level ?? 0}`],
    ["rate", tex("item/clock_00", "s"), t("lb.xp_per_hour"), xpPerHour, p => nf(xpPerHour(p))],
    ["playtime", tex("item/compass_00", "s"), t("kpi.playtime"), p => d.playtime[p] || 0, p => dur(d.playtime[p] || 0)],
    ["adv", tex("item/book", "s"), t("part.advancements"), p => d.progress?.[p]?.advancements || 0, p => nf(d.progress?.[p]?.advancements || 0)],
    ...d.fun.rows.filter(r => typeof r.values[a] === "number" && (r.values[a] || r.values[b]))
      .map(r => [r.key, icon(r.key, "s"), t(`stat.${r.key}`), p => r.values[p] || 0, p => nf(r.values[p] || 0), r.key === "deaths"]),
  ];
  let winsA = 0, winsB = 0;
  const lines = rows.map(([, ic, label, val, show, lowerWins]) => {
    const va = val(a), vb = val(b), max = Math.max(va, vb, 1);
    const aWins = lowerWins ? va < vb : va > vb, bWins = lowerWins ? vb < va : vb > va;
    winsA += aWins; winsB += bWins;
    return `<div class="vs-row">
      <span class="vs-v ${aWins ? "win" : ""}">${show(a)}</span>
      <span class="vs-bar left"><i class="${aWins ? "top" : ""}" style="width:${((100 * va) / max).toFixed(1)}%"></i></span>
      <span class="vs-l">${ic}<span>${label}</span></span>
      <span class="vs-bar"><i class="${bWins ? "top" : ""}" style="width:${((100 * vb) / max).toFixed(1)}%"></i></span>
      <span class="vs-v ${bWins ? "win" : ""}">${show(b)}</span></div>`;
  }).join("");
  const select = (side, cur) => `<label class="vs-name" style="color:${color(cur)}" data-tip="${t("versus.pick")}"><select data-vs="${side}" aria-label="${t("versus.pick")}">${ps.map(p => `<option ${p === cur ? "selected" : ""}>${esc(p)}</option>`).join("")}</select></label>`;
  return `
    <button class="btn back" data-go="back">← ${t("profile.back")}</button>
    <div class="panel versus">
      <div class="vs-head">
        <div class="vs-side">${v3d(a, 150, 220, "idle", "data-vsa=1")}${select("a", a)}</div>
        <div class="vs-score"><span class="${winsA > winsB ? "win" : ""}">${winsA}</span> – <span class="${winsB > winsA ? "win" : ""}">${winsB}</span>
          <div class="muted">${t(winsA === winsB ? "versus.draw" : "versus.wins", { p: esc(winsA > winsB ? a : b) })}</div></div>
        <div class="vs-side">${v3d(b, 150, 220, "idle", "data-vsb=1")}${select("b", b)}</div>
      </div>
      <div class="vs-rows">${lines}</div>
      <div class="note">${t("versus.note")}</div>
    </div>`;
}
