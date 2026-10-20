// The advancement screen of a player, like in the game: one tab per category, every advancement
// in its real frame, obtained or not. Definitions come from /assets/advancements.json.
import { S } from "../state.js";
import { mcText, t } from "../i18n.js";
import { esc, fmtDate, itemImg } from "../util.js";

const TABS = ["story", "nether", "end", "adventure", "husbandry"];
let defs = null;
export const loadAdvancements = async () => {
  defs ??= await fetch("/assets/advancements.json").then(r => (r.ok ? r.json() : {})).catch(() => ({}));
  return defs;
};

// depth in the advancement tree, so the grid follows the order of the game
function depth(id) {
  let n = 0;
  for (let p = defs[id]?.parent; p && n < 30; p = defs[p]?.parent) n++;
  return n;
}

export function advancementScreen(p) {
  if (!defs || !Object.keys(defs).length) return "";
  const done = S.data.advancements?.[p] || {};
  const tab = S.advTab || "story";
  const ids = id => Object.keys(defs).filter(k => defs[k].tab === id && !k.endsWith("/root"));
  const count = id => ids(id).filter(k => done[k]).length;
  const total = TABS.reduce((a, id) => a + ids(id).length, 0);
  const got = TABS.reduce((a, id) => a + count(id), 0);
  const list = ids(tab).sort((a, b) => depth(a) - depth(b) || a.localeCompare(b));
  return `
    <div class="adv-head"><span class="adv-total"><b>${got}</b> / ${total}</span>
      <span class="xp adv-bar" data-tip="${Math.round((100 * got) / total)}%"><i style="clip-path: inset(0 ${(100 - (100 * got) / total).toFixed(1)}% 0 0)"></i></span></div>
    <div class="adv-tabs">${TABS.map(id => `<button class="adv-tab ${id === tab ? "on" : ""}" data-advtab="${id}" data-tip="${esc(mcText(defs[`${id}/root`]?.title) || id)}">
      ${itemImg(defs[`${id}/root`]?.icon)}
      <span>${count(id)}/${ids(id).length}</span></button>`).join("")}</div>
    <div class="adv-grid">${list.map(id => {
      const a = defs[id], when = done[id], secret = a.hidden && !when;
      const tip = secret ? `<b>???</b>` : `<b class='adv-${a.frame}'>${esc(mcText(a.title))}</b><br>${esc(mcText(a.desc))}${when ? `<br><span style='color:#7fe33a'>${t("adv.done", { d: fmtDate(when) })}</span>` : ""}`;
      return `<div class="adv-cell ${when ? "got" : "not"}" data-tip="${tip}"
        style="background-image:url(/assets/gui/advancements/${a.frame}_frame_${when ? "obtained" : "unobtained"}.png)">
        ${secret ? "<span class='q'>?</span>" : itemImg(a.icon)}</div>`;
    }).join("")}</div>`;
}
