// Player page: 3D skin with armor, site level, equipment, charts, statistics and timeline.
import { S } from "../state.js";
import { advancementTitle, deathMessage, enchantName, entityName, itemName, t, trimMaterial, trimPattern } from "../i18n.js";
import { dayBars, hourStrip, kpi, xpBar } from "../charts.js";
import { v3d } from "../skins.js";
import { bestXp, color, dur, esc, fmtDate, icon, nf, players, tex, xpPerHour } from "../util.js";

const ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"];
const itemIcon = id => `<img src="/assets/item/${id}.png" alt="" onerror="this.onerror=()=>{this.onerror=null;this.src='/assets/item/barrier.png'};this.src='/assets/block/${id}.png'">`;
// site XP parts are either statistics (stat.*) or their own categories (part.*)
const PARTS = ["advancements", "hard_advancements", "mob_variety", "gear", "distance_km"];
const partLabel = key => t(PARTS.includes(key) ? `part.${key}` : `stat.${key}`);
const statValue = v => (v && typeof v === "object" ? `${entityName(v.id)} (${nf(v.n)}×)` : nf(v));

function gearPanel(p) {
  const eq = S.data.armor?.[p];
  if (!eq) return `<div class="empty">${t("gear.no_data", { p: esc(p) })}</div>`;
  return `<div class="gear">${["head", "chest", "legs", "feet", "mainhand", "offhand"].map(slot => {
    const it = eq[slot];
    if (!it) return `<div class="slot empty"><div class="box"></div><div><div class="nm">${t("gear.empty", { slot: t(`slot.${slot}`) })}</div></div></div>`;
    const ench = Object.entries(it.ench || {}).map(([n, lv]) => enchantName(n) + (lv > 1 || n !== "mending" ? " " + (ROMAN[lv] || lv) : "")).join(", ");
    const trim = it.trim ? t("gear.trim", { pattern: trimPattern(it.trim.pattern), material: trimMaterial(it.trim.material) }) : "";
    return `<div class="slot"><div class="box ${ench ? "glint" : ""}">${itemIcon(it.id)}</div>
      <div><div class="nm">${esc(itemName(it.id))}</div>${trim ? `<div class="sub">${esc(trim)}</div>` : ""}${ench ? `<div class="ench">${esc(ench)}</div>` : ""}</div></div>`;
  }).join("")}</div>`;
}

export function viewPlayer(p) {
  const d = S.data, ps = players();
  const pr = d.profiles[p] || { sessions: 0, longest: 0, per_day: {}, per_hour: Array(24).fill(0), advancements: [], deaths: [], online: false };
  const pt = d.playtime[p] || 0, afk = d.afk.players[p] || { afk: 0, active: 0, afk_now: false };
  const measured = afk.afk + afk.active;
  const prog = d.progress?.[p] || { level: 0, xp: 0, parts: [], advancements: 0 };
  const rateRank = ps.slice().sort((a, b) => xpPerHour(b) - xpPerHour(a)).indexOf(p) + 1;
  const levelRank = 1 + ps.filter(x => (d.progress?.[x]?.xp || 0) > prog.xp).length;

  const ranked = d.fun.rows.filter(r => typeof r.values[p] === "number").map(r => {
    const vals = ps.map(x => r.values[x]).filter(v => typeof v === "number");
    return { key: r.key, v: r.values[p], max: Math.max(...vals, 0), rank: 1 + vals.filter(v => v > r.values[p]).length, n: vals.length };
  });
  const texts = d.fun.rows.filter(r => r.values[p] && typeof r.values[p] === "object");
  const firsts = ranked.filter(x => x.rank === 1 && x.v > 0);
  const maxPart = Math.max(1, ...prog.parts.map(x => x[1]));
  const feed = [...pr.advancements.map(a => ({ ...a, type: "adv" })), ...pr.deaths.map(x => ({ ...x, type: "death" }))].sort((a, b) => b.t.localeCompare(a.t));
  const cmds = (d.commands || []).filter(c => c.p === p).slice(0, 20);
  const badge = (ic, text) => `<span class="badge">${ic} ${text}</span>`;

  return `
    <button class="btn back" data-go="back">← ${t("profile.back")}</button>
    <div class="panel prof">
      <div class="skin">${v3d(p, 220, 340, "walk", "data-big=1")}
        <div class="anims">${["walk", "run", "wave", "fly", "idle"].map(k => `<button class="btn" data-anim="${k}">${t(`anim.${k}`)}</button>`).join("")}
          <button class="btn ${S.showArmor ? "on" : ""}" data-armor>${tex("item/iron_chestplate", "xs")} ${t(S.showArmor ? "armor.on" : "armor.off")}</button></div>
        <div class="note">${t("profile.drag")}</div></div>
      <div>
        <div class="nm" style="color:${color(p)}">${esc(p)}</div>
        <div class="muted status"><span class="dot ${pr.online ? "on" : ""}"></span>
          ${pr.online ? t(afk.afk_now ? "profile.online_afk" : "profile.online") : t("profile.last_online", { d: fmtDate(pr.last) })} · ${t("profile.first_seen", { d: fmtDate(pr.first) })}</div>
        <div class="level">
          <span class="xp-lvl" data-tip="${t("level.tip")}"><span class="site-tag">${t("level.tag")}</span>${t("level.label", { n: prog.level })}</span>
          <span class="muted level-sub">${t("level.xp_rank", { xp: nf(prog.xp), rate: nf(xpPerHour(p)), rank: rateRank, n: ps.length })}</span>
          ${xpBar(prog.xp / bestXp(), t("level.bar", { xp: nf(prog.xp), pct: Math.round((100 * prog.xp) / bestXp()) }))}
        </div>
        <div class="badges">${levelRank === 1 ? badge(tex("item/experience_bottle", "xs"), t("badge.top_level")) : ""}${rateRank === 1 ? badge(tex("item/clock_00", "xs"), t("badge.top_rate")) : ""}${
          firsts.length ? firsts.map(x => badge(icon(x.key, "xs"), t("badge.first", { stat: t(`stat.${x.key}`) }))).join("") : `<span class="muted">${t("badge.none")}</span>`}</div>
        <div class="grid kpis" style="margin-top:14px">
          ${kpi("item/clock_00", t("kpi.playtime"), dur(pt))}
          ${kpi("item/compass_00", t("kpi.sessions"), nf(pr.sessions), t("kpi.longest", { d: dur(pr.longest) }))}
          ${measured ? kpi("block/red_wool", t("kpi.afk"), Math.round((100 * afk.afk) / measured) + "%", t("kpi.afk_measured", { a: dur(afk.afk), b: dur(measured) }))
                     : kpi("block/red_wool", t("kpi.afk"), "–", t("kpi.not_measured"))}
          ${kpi("item/experience_bottle", t("part.advancements"), nf(prog.advancements))}
        </div>
      </div>
    </div>

    <h2>${tex("item/experience_bottle", "s")} ${t("section.level_from")}</h2>
    <div class="panel"><div class="cmp">${prog.parts.filter(x => x[1] > 0).map(([key, v]) => `
      <div class="row" data-tip="<b>${partLabel(key)}</b><br>${nf(v)} XP">
        <span class="lbl">${icon(key, "s")} ${partLabel(key)}</span>
        <span class="track"><i style="width:${((100 * v) / maxPart).toFixed(1)}%"></i></span>
        <span class="rk"><b>${nf(v)}</b> XP</span></div>`).join("")}</div>
      <div class="note">${t("level.note")}</div></div>

    <h2>${tex("item/diamond_chestplate", "s")} ${t("section.gear")}</h2>
    <div class="panel">${gearPanel(p)}<div class="note">${t("gear.note", { p: esc(p) })}</div></div>

    <div class="grid two">
      <div class="panel"><h2>${tex("item/clock_00", "s")} ${t("chart.per_day")}</h2>${dayBars(pr.per_day)}</div>
      <div class="panel"><h2>${tex("item/compass_00", "s")} ${t("chart.when_player", { p: esc(p) })}</h2>${hourStrip(pr.per_hour, pr.per_day, pr.sessions, pr.longest)}</div>
    </div>

    <h2>${tex("item/book", "s")} ${t("section.stats")}</h2>
    <div class="panel"><div class="cmp">${ranked.map(x => `
      <div class="row" data-tip="<b>${t(`stat.${x.key}`)}</b><br>${esc(p)}: ${nf(x.v)}<br>${t("stats.best", { v: nf(x.max) })}">
        <span class="lbl">${icon(x.key, "s")} ${t(`stat.${x.key}`)}</span>
        <span class="track"><i class="${x.rank === 1 && x.v > 0 ? "top" : ""}" style="width:${x.max ? ((100 * x.v) / x.max).toFixed(1) : 0}%"></i></span>
        <span class="rk"><b>${nf(x.v)}</b> · ${x.v > 0 ? t("stats.rank", { r: x.rank, n: x.n }) : "–"}</span>
      </div>`).join("")}
      ${texts.map(r => `<div class="row"><span class="lbl">${icon(r.key, "s")} ${t(`stat.${r.key}`)}</span><span class="muted">${statValue(r.values[p])}</span><span></span></div>`).join("")}
    </div><div class="note">${t("stats.note", { p: esc(p) })}</div></div>

    <div class="grid two">
      <div class="panel"><h2>${tex("item/experience_bottle", "s")} ${t("section.feed")}</h2>
        <div class="feed">${feed.length ? feed.map(f => f.type === "adv"
          ? `<div class="it"><div class="frame ${f.kind}">${tex("item/book")}</div><div><span class="adv-${f.kind}">[${esc(advancementTitle(f.a))}]</span><div class="t">${fmtDate(f.t)}</div></div></div>`
          : `<div class="it"><div class="frame task">${tex("item/bone")}</div><div>${esc(deathMessage(p, f.m))}<div class="t">${fmtDate(f.t)}</div></div></div>`).join("")
          : `<div class="empty">${t("feed.empty")}</div>`}</div></div>
      ${d.site.show_log ? `<div class="panel"><h2>${tex("item/command_block_minecart", "s")} ${t("section.commands")}</h2>
        <div class="feed">${cmds.length ? cmds.map(c => `<div class="it"><div class="frame task">${tex(c.admin ? "item/command_block_minecart" : "item/paper")}</div><div><code>${esc(c.c)}</code>${
          c.admin ? ` <span class="chip warn">${t("chip.admin")}</span>` : c.tried ? ` <span class="chip">${t("chip.no_perm")}</span>` : ""}<div class="t">${fmtDate(c.t)}</div></div></div>`).join("")
          : `<div class="empty">${t("cmds.empty")}</div>`}</div></div>` : ""}
    </div>`;
}
