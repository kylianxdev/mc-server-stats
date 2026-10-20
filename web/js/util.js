// Small helpers shared by all views.
import { S } from "./state.js";
import { t, locale } from "./i18n.js";

export const $ = id => document.getElementById(id);
export const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
export const nf = v => (typeof v === "number" ? v.toLocaleString(locale) : esc(v));

export function dur(s) {
  s = Math.max(0, Math.round(s));
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  const [ud, uh, um] = [t("unit.d"), t("unit.h"), t("unit.m")];
  return d ? `${d}${ud} ${h}${uh}` : h ? `${h}${uh} ${m}${um}` : `${m}${um}`;
}

// "2026-10-19 18:04:12" -> short local date (+ time)
export function fmtDate(stamp) {
  if (!stamp) return "–";
  const [d, time] = stamp.split(" ");
  const date = new Date(`${d}T12:00:00Z`).toLocaleDateString(locale, { day: "numeric", month: "numeric", timeZone: "UTC" });
  return time ? `${date} ${time.slice(0, 5)}` : date;
}
export const weekday = d => new Date(`${d}T12:00:00Z`).toLocaleDateString(locale, { weekday: "short", timeZone: "UTC" });

// the icon of an item or block; blocks with a 3D model fall back to their front/side/top texture
const FALLBACKS = id => [`item/${id}`, `block/${id}`, `block/${id}_front`, `block/${id}_side`, `block/${id}_top`, "item/barrier"];
export const itemImg = (id, cls = "") =>
  `<img class="${cls}" src="/assets/item/${id}.png" data-fb="${FALLBACKS(id).slice(1).join(",")}" alt="">`;
document.addEventListener("error", e => {
  const img = e.target;
  if (img.tagName !== "IMG" || !img.dataset.fb) return;
  const [next, ...rest] = img.dataset.fb.split(",");
  img.dataset.fb = rest.join(",");
  if (next) img.src = `/assets/${next}.png`;
}, true);

// a texture from the game, e.g. tex("item/diamond")
export const tex = (path, cls = "") => `<img class="ico ${cls}" src="/assets/${path}.png" alt="">`;

// Minecraft name colors (dark shades a bit lighter, readable on dark backgrounds)
const NAME_COLORS = { white: "#ffffff", gray: "#aaaaaa", dark_gray: "#8a8a8a", gold: "#ffaa00", yellow: "#ffff55", red: "#ff5555",
  dark_red: "#e23b3b", green: "#55ff55", aqua: "#55ffff", dark_aqua: "#2fc4c4", blue: "#7a7aff", dark_blue: "#5a5ad8",
  dark_green: "#3cbf3c", light_purple: "#ff55ff", dark_purple: "#c24dc2" };
export const color = p => NAME_COLORS[S.data.colors?.[p]] || "#ffffff";

// statistic / site XP part -> texture
export const ICONS = {
  blocks_mined: "item/diamond_pickaxe", diamond_ore: "block/diamond_ore", ancient_debris: "block/ancient_debris_side",
  logs_chopped: "block/oak_log", saplings_planted: "block/oak_sapling", crops_harvested: "item/wheat",
  blocks_used: "block/oak_planks", items_crafted: "block/crafting_table_front", tools_broken: "item/iron_pickaxe",
  walked_km: "item/leather_boots", swum_km: "item/water_bucket", elytra_km: "item/elytra", ridden_km: "item/oak_boat",
  jumps: "item/rabbit_foot", mob_kills: "item/iron_sword", most_killed: "item/bone", deaths: "item/totem_of_undying",
  killed_by_most: "item/arrow", player_kills: "item/bow", damage_dealt: "gui/hud/heart/full", damage_taken: "item/golden_apple",
  animals_bred: "item/egg", fish_caught: "item/fishing_rod", villager_trades: "item/emerald", items_enchanted: "item/enchanted_book",
  chests_opened: "block/barrel_side", favourite_block: "block/grass_block_side", most_used: "block/oak_planks", most_crafted: "block/crafting_table_front", times_slept: "block/red_wool", cake_slices: "item/cake", items_dropped: "item/barrier",
  advancements: "item/experience_bottle", hard_advancements: "item/nether_star", mob_variety: "item/iron_sword",
  gear: "item/diamond_chestplate", distance_km: "item/leather_boots",
};
export const icon = (key, cls) => tex(ICONS[key] || "item/paper", cls);

// players, best site level first
export const players = () => {
  const d = S.data;
  return [...new Set([...d.fun.players, ...Object.keys(d.profiles)])]
    .sort((a, b) => (d.progress?.[b]?.xp ?? 0) - (d.progress?.[a]?.xp ?? 0) || (d.playtime[b] ?? 0) - (d.playtime[a] ?? 0));
};
export const onlineNow = () => Object.entries(S.data.profiles).filter(([, p]) => p.online).map(([n]) => n);
export const row = key => S.data.fun.rows.find(r => r.key === key);
export const sumRow = key => { const r = row(key); return r ? Object.values(r.values).reduce((a, b) => a + (typeof b === "number" ? b : 0), 0) : 0; };
export const bestXp = () => Math.max(1, ...Object.values(S.data.progress || {}).map(x => x.xp));
export const xpPerHour = p => Math.round((S.data.progress?.[p]?.xp || 0) / Math.max((S.data.playtime[p] || 0) / 3600, 1));
