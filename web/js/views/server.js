// Home page: totals, charts, player cards and leaderboards.
import { S } from "../state.js";
import { t } from "../i18n.js";
import { dayBars, hourStrip, kpi, xpBar } from "../charts.js";
import { head3d, v3d } from "../skins.js";
import { bestXp, color, dur, esc, fmtDate, icon, nf, players, sumRow, tex, xpPerHour } from "../util.js";
import { titleOf } from "../titles.js";
import { activityPanel, buddiesPanel, hallOfFame, pvpPanel, togetherPanel, weekPanel } from "./social.js";

const DIMENSIONS = { overworld: "block/grass_block_side", the_nether: "block/netherrack", the_end: "block/end_stone" };
export const dimensionIcon = p => {
  const dim = S.data.armor?.[p]?.dimension;
  return dim && DIMENSIONS[dim] ? `<span class="dim" data-tip="${t(`dim.${dim}`)}">${tex(DIMENSIONS[dim], "xs")}</span>` : "";
};
export const titleBadge = (p, cls = "") => {
  const ti = titleOf(p);
  const why = ti.key ? (ti.ratio ? t("title.why", { stat: t(`stat.${ti.key}`), x: nf(Math.round(ti.ratio * 10) / 10) })
                                 : t("title.why_only", { stat: t(`stat.${ti.key}`) })) : t("title.why_all");
  return `<span class="title-badge ${cls}" data-tip="<b>${t(`title.${ti.title}`)}</b><br>${why}">${tex(ti.icon, "xs")} ${t(`title.${ti.title}`)}</span>`;
};

export function viewServer() {
  const d = S.data, ps = players();
  const totalPt = Object.values(d.playtime).reduce((a, b) => a + b, 0);
  const perDay = {}, perHour = Array(24).fill(0);
  for (const p of Object.values(d.profiles)) {
    for (const [day, v] of Object.entries(p.per_day)) perDay[day] = (perDay[day] || 0) + v;
    p.per_hour.forEach((v, h) => (perHour[h] += v));
  }
  const whoPlayed = day => {
    const parts = ps.map(p => [p, d.profiles[p]?.per_day[day] || 0]).filter(x => x[1] > 0).sort((a, b) => b[1] - a[1]);
    return parts.length ? "<br>" + parts.map(([p, v]) => `<span style='color:${color(p)}'>${esc(p)}</span> ${dur(v)}`).join("<br>") : "";
  };
  const sessions = Object.values(d.profiles).reduce((a, p) => a + p.sessions, 0);
  const longest = Math.max(0, ...Object.values(d.profiles).map(p => p.longest));
  return `
    <div class="grid kpis">
      ${kpi("item/clock_00", t("kpi.total_playtime"), dur(totalPt), t("kpi.players", { n: ps.length }))}
      ${kpi("item/diamond_pickaxe", t("stat.blocks_mined"), nf(sumRow("blocks_mined")))}
      ${kpi("block/diamond_ore", t("stat.diamond_ore"), nf(sumRow("diamond_ore")))}
      ${kpi("item/iron_sword", t("stat.mob_kills"), nf(sumRow("mob_kills")))}
      ${kpi("item/totem_of_undying", t("stat.deaths"), nf(sumRow("deaths")))}
      ${kpi("item/leather_boots", t("kpi.walked_together"), nf(Math.round(sumRow("walked_km"))) + " km")}
    </div>
    <div class="grid two">
      <div class="panel"><h2>${tex("item/clock_00", "s")} ${t("chart.per_day")}</h2>${dayBars(perDay, whoPlayed)}</div>
      <div class="panel"><h2>${tex("item/compass_00", "s")} ${t("chart.when")}</h2>${hourStrip(perHour, perDay, sessions, longest)}</div>
    </div>
    <h2>${tex("item/name_tag", "s")} ${t("section.players")}</h2>${playerCards()}
    ${flow(weekPanel(), buddiesPanel())}
    ${hallOfFame()}
    ${togetherPanel()}
    <h2>${tex("item/gold_ingot", "s")} ${t("section.leaderboards")}</h2>
    <div class="grid lbs">${leaderboards(ps)}</div>
    ${flow(activityPanel(), pvpPanel())}`;
}

// panels side by side that fill the width together: an empty one disappears, a single one takes the full row
export const flow = (...panels) => {
  const shown = panels.filter(Boolean);
  return shown.length ? `<div class="grid flow flow-${shown.length}">${shown.join("")}</div>` : "";
};

export function playerCards() {
  const d = S.data;
  return `<div class="grid players">${players().map(p => {
    const pr = d.profiles[p] || {}, pt = d.playtime[p] || 0, g = d.progress?.[p] || { level: 0, xp: 0 };
    const tip = `<b>${t("level.label", { n: g.level })}</b><br>${t("level.xp_rate", { xp: nf(g.xp), rate: nf(xpPerHour(p)) })}<br>${t("card.played", { d: dur(pt) })}<br><span style='color:#aaa'>${t("level.not_ingame")}</span>`;
    return `<a class="panel pcard" href="#player/${encodeURIComponent(p)}" data-hoverwalk>
      ${v3d(p, 150, 210, "idle")}
      <div class="nm" style="color:${color(p)}">${esc(p)}</div>
      <div class="meta">${titleBadge(p)}</div>
      <div class="meta"><span class="dot ${pr.online ? "on" : ""}"></span> ${pr.online ? t("card.online") : t("card.last_seen", { d: fmtDate(pr.last?.slice(0, 10)) })} ${dimensionIcon(p)}</div>
      <div class="xp-lvl" data-tip="${tip}"><span class="site-tag">${t("level.tag")}</span>${g.level}</div>
      ${xpBar(g.xp / bestXp(), t("level.bar", { xp: nf(g.xp), pct: Math.round((100 * g.xp) / bestXp()) }))}
    </a>`;
  }).join("")}</div>`;
}

const value = v => (v && typeof v === "object" ? v.n : v);

function leaderboards(ps) {
  const d = S.data;
  const board = (title, ic, entries, highlight = false) => `<div class="panel lb${highlight ? " special" : ""}"><h3>${ic} ${title}</h3>${entries.map(([p, shown]) =>
    `<div class="r" data-p="${esc(p)}">${head3d(p)}<span class="n" style="color:${color(p)}">${esc(p)}</span><span class="val">${shown}</span></div>`).join("")}</div>`;
  const special = [
    board(t("lb.highest_level"), tex("item/experience_bottle", "s"),
      ps.map(p => [p, `${t("level.short")} ${d.progress?.[p]?.level ?? 0}`]), true),
    board(t("lb.xp_per_hour"), tex("item/clock_00", "s"),
      ps.slice().sort((a, b) => xpPerHour(b) - xpPerHour(a)).map(p => [p, `${nf(xpPerHour(p))} ${t("level.per_hour_short")}`]), true),
  ];
  const stats = d.fun.rows
    .filter(r => Object.values(r.values).some(v => typeof v === "number" && v > 0))
    .map(r => board(t(`stat.${r.key}`), icon(r.key, "s"),
      Object.entries(r.values).filter(([, v]) => typeof v === "number").sort((a, b) => b[1] - a[1]).map(([p, v]) => [p, nf(value(v))])));
  return special.join("") + stats.join("");
}
