// A play style title for every player: the thing they do far MORE than the others.
//
// For every statistic we compare a player with the average of the other players. The title is the
// style where someone stands out most. It also has to be a real amount (a "significant" number):
// catching 3 fish when nobody else fishes doesn't make you a Fisher.
import { S } from "./state.js";

// title -> [icon, statistics]
export const TITLES = {
  trader: ["item/emerald", ["villager_trades"]],
  miner: ["item/diamond_pickaxe", ["blocks_mined", "diamond_ore"]],
  lumberjack: ["item/iron_axe", ["logs_chopped", "saplings_planted"]],
  farmer: ["item/wheat", ["crops_harvested", "animals_bred"]],
  builder: ["block/bricks", ["blocks_used", "items_crafted"]],
  explorer: ["item/filled_map", ["walked_km", "elytra_km", "ridden_km", "swum_km"]],
  warrior: ["item/diamond_sword", ["mob_kills", "damage_dealt"]],
  fisher: ["item/fishing_rod", ["fish_caught"]],
  enchanter: ["item/enchanted_book", ["items_enchanted"]],
};
// how much of something is "a real amount"
const SIGNIFICANT = {
  villager_trades: 100, blocks_mined: 5000, diamond_ore: 50, logs_chopped: 500, saplings_planted: 100, crops_harvested: 200,
  animals_bred: 50, blocks_used: 5000, items_crafted: 2000, walked_km: 30, elytra_km: 10, ridden_km: 10, swum_km: 5,
  mob_kills: 300, damage_dealt: 2000, fish_caught: 30, items_enchanted: 15,
};
const STANDS_OUT = 0.6; // below this (in doublings over the others) a player is an all-rounder

/** {title, icon, key, ratio} for a player, or the all-rounder title. */
export function titleOf(p) {
  const rows = Object.fromEntries(S.data.fun.rows.map(r => [r.key, r.values]));
  let best = { title: "allrounder", icon: "item/compass_00", score: STANDS_OUT };
  for (const [title, [icon, keys]] of Object.entries(TITLES)) {
    for (const key of keys) {
      const values = rows[key];
      if (!values) continue;
      const v = values[p] || 0, sig = SIGNIFICANT[key] || 1;
      const others = Object.entries(values).filter(([q, x]) => q !== p && typeof x === "number").map(([, x]) => x);
      const avg = others.length ? others.reduce((a, b) => a + b, 0) / others.length : 0;
      // doublings above the others (smoothed), counted fully only when it's a real amount
      const score = Math.log2((v + sig / 4) / (avg + sig / 4)) * Math.min(1, v / sig);
      if (score > best.score) best = { title, icon, key, score, ratio: avg ? v / avg : null, value: v };
    }
  }
  return best;
}
