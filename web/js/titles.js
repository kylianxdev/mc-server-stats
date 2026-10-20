// A play style title for every player ("Miner", "Lumberjack", ...), from what they do most
// compared to the others on the server.
import { S } from "./state.js";

// title -> [icon, statistics that count]
export const TITLES = {
  miner: ["item/diamond_pickaxe", ["blocks_mined", "diamond_ore"]],
  lumberjack: ["item/iron_axe", ["logs_chopped", "saplings_planted"]],
  farmer: ["item/wheat", ["crops_harvested", "animals_bred"]],
  builder: ["block/bricks", ["blocks_used", "items_crafted"]],
  explorer: ["item/filled_map", ["walked_km", "elytra_km", "ridden_km", "swum_km"]],
  warrior: ["item/diamond_sword", ["mob_kills", "damage_dealt"]],
  trader: ["item/emerald", ["villager_trades"]],
  fisher: ["item/fishing_rod", ["fish_caught"]],
  enchanter: ["item/enchanted_book", ["items_enchanted"]],
};

/** {title, icon, score} for a player: the style where they score highest relative to the best. */
export function titleOf(p) {
  const rows = Object.fromEntries(S.data.fun.rows.map(r => [r.key, r.values]));
  let best = null;
  for (const [title, [icon, keys]] of Object.entries(TITLES)) {
    const parts = keys.filter(k => rows[k]).map(k => {
      const vals = Object.values(rows[k]).filter(v => typeof v === "number");
      const max = Math.max(...vals, 0);
      return max ? (rows[k][p] || 0) / max : 0;
    });
    const score = parts.length ? parts.reduce((a, b) => a + b, 0) / parts.length : 0;
    if (!best || score > best.score) best = { title, icon, score };
  }
  return best && best.score > 0 ? best : null;
}
