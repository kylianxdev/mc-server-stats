// Hall of Fame, player of the week, best buddies and PvP: the parts about the group.
import { S } from "../state.js";
import { advancementTitle, deathMessage, t } from "../i18n.js";
import { head3d } from "../skins.js";
import { color, dur, esc, fmtDate, itemImg, nf, tex } from "../util.js";

// milestone -> icon
const HALL_ICONS = {
  first_join: "oak_door", first_iron: "iron_ingot", first_diamond: "diamond", first_nether: "obsidian",
  first_enchant: "enchanting_table", first_fortress: "nether_bricks", first_debris: "ancient_debris",
  first_netherite_armor: "netherite_chestplate", first_end: "end_portal_frame", first_dragon: "dragon_egg",
  first_elytra: "elytra", first_totem: "totem_of_undying", first_raid: "white_banner", first_wither: "nether_star",
  first_death: "bone",
};
const who = p => `<span class="who" data-p="${esc(p)}">${head3d(p, 20)}<span style="color:${color(p)}">${esc(p)}</span></span>`;

export function hallOfFame() {
  const hall = S.data.hall || [];
  if (!hall.length) return "";
  return `<h2>${tex("item/nether_star", "s")} ${t("hall.title")}</h2>
    <div class="grid hall">${hall.map(h => `
      <div class="panel hof" data-tip="${t("hall.tip", { n: h.n ?? 1 })}">
        <div class="hof-ico">${itemImg(h.key === "first_dragon" ? "dragon_egg" : HALL_ICONS[h.key] || "paper")}</div>
        <div><div class="hof-k">${t(`hall.${h.key}`)}</div>${who(h.p)}<div class="t">${fmtDate(h.t)}</div></div>
      </div>`).join("")}</div>`;
}

/** Player of the week + the gains of everyone this week (one color, bars). */
export function weekPanel() {
  const w = S.data.history?.week;
  if (!w) return "";
  const rows = Object.entries(w.players).sort((a, b) => (b[1].xp || 0) - (a[1].xp || 0));
  const max = Math.max(1, ...rows.map(([, v]) => v.xp || 0));
  const collecting = w.since === S.data.history.dates.at(-1);
  if (collecting || !rows.length || (rows[0][1].xp || 0) <= 0)
    return `<div class="panel"><h2>${tex("item/clock_00", "s")} ${t("week.title")}</h2><div class="empty">${t("week.collecting")}</div></div>`;
  const [best, b] = rows[0];
  return `<div class="panel week"><h2>${tex("item/clock_00", "s")} ${t("week.title")}</h2>
    <div class="potw">${head3d(best, 56)}<div><div class="potw-k">${t("week.player")}</div>
      <div class="potw-n" style="color:${color(best)}" data-p="${esc(best)}">${esc(best)}</div>
      <div class="muted">${t("week.summary", { xp: nf(b.xp), mined: nf(b.blocks_mined || 0), kills: nf(b.mob_kills || 0), time: dur(b.playtime || 0) })}</div></div></div>
    <div class="cmp">${rows.map(([p, v]) => `<div class="row" data-p="${esc(p)}" data-tip="<b>${esc(p)}</b><br>+${nf(v.xp || 0)} site XP<br>${dur(v.playtime || 0)}">
      <span class="lbl">${head3d(p, 18)} <span style="color:${color(p)}">${esc(p)}</span></span>
      <span class="track"><i style="width:${Math.max(0, (100 * (v.xp || 0)) / max).toFixed(1)}%"></i></span>
      <span class="rk"><b>+${nf(v.xp || 0)}</b> XP</span></div>`).join("")}</div>
    <div class="note">${t("week.note", { d: fmtDate(w.since) })}</div></div>`;
}

export function buddiesPanel(onlyFor = null) {
  let pairs = S.data.buddies || [];
  if (onlyFor) pairs = pairs.filter(b => b.a === onlyFor || b.b === onlyFor);
  pairs = pairs.slice(0, onlyFor ? 3 : 6);
  if (!pairs.length) return "";
  const max = Math.max(1, ...pairs.map(b => b.s));
  return `<div class="panel"><h2>${tex("item/cake", "s")} ${t(onlyFor ? "buddies.player" : "buddies.title")}</h2>
    <div class="buddies">${pairs.map(b => `<div class="buddy" data-tip="${t("buddies.tip", { d: dur(b.s) })}">
      <div class="pair">${who(b.a)} <span class="amp">&amp;</span> ${who(b.b)}</div>
      <div class="xp"><i style="clip-path: inset(0 ${(100 - (100 * b.s) / max).toFixed(1)}% 0 0)"></i></div>
      <div class="t">${dur(b.s)}</div></div>`).join("")}</div></div>`;
}

export function pvpPanel(onlyFor = null) {
  let fights = S.data.pvp || [];
  if (onlyFor) fights = fights.filter(f => f.killer === onlyFor || f.victim === onlyFor);
  if (!fights.length) return "";
  return `<div class="panel"><h2>${tex("item/iron_sword", "s")} ${t("pvp.title")}</h2>
    <div class="pvp">${fights.map(f => `<div class="fight">${who(f.killer)}<span class="vs">${tex("item/iron_sword", "xs")} ${f.n}×</span>${who(f.victim)}</div>`).join("")}</div>
    <div class="note">${t("pvp.note")}</div></div>`;
}

/** The newest advancements and deaths of everyone on the server. */
export function activityPanel(limit = 12) {
  const events = Object.entries(S.data.profiles).flatMap(([p, pr]) => [
    ...(pr.advancements || []).map(a => ({ ...a, p, type: "adv" })), ...(pr.deaths || []).map(x => ({ ...x, p, type: "death" }))])
    .sort((a, b) => b.t.localeCompare(a.t)).slice(0, limit);
  if (!events.length) return "";
  return `<div class="panel"><h2>${tex("item/writable_book", "s")} ${t("activity.title")}</h2>
    <div class="feed">${events.map(e => e.type === "adv"
      ? `<div class="it"><div class="frame ${e.kind}">${tex("item/book")}</div><div>${who(e.p)} <span class="adv-${e.kind}">[${esc(advancementTitle(e.a))}]</span><div class="t">${fmtDate(e.t)}</div></div></div>`
      : `<div class="it"><div class="frame task">${tex("item/bone")}</div><div>${esc(deathMessage(e.p, e.m))}<div class="t">${fmtDate(e.t)}</div></div></div>`).join("")}</div></div>`;
}
