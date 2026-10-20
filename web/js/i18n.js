// Translations: website texts from /i18n/<lang>.json, and the names of mobs, items, enchantments,
// trims, advancements and death messages from Minecraft's own language files (/assets/lang/<lang>.json).
let ui = {}, uiEn = {}, mc = {}, mcEn = {};
let reverse = null, deathRules = null;
export let lang = "en", locale = "en";

const LOCALES = { en: "en-GB", nl: "nl-NL", es: "es-ES", de: "de-DE", fr: "fr-FR", pt: "pt-BR", it: "it-IT", pl: "pl-PL" };
const getJson = url => fetch(url).then(r => (r.ok ? r.json() : {})).catch(() => ({}));

export function pickLanguage(site) {
  const available = site.languages || ["en"];
  let saved = null;
  try { saved = localStorage.getItem("lang"); } catch (e) { /* private mode */ }
  const browser = (navigator.language || "").slice(0, 2).toLowerCase();
  return [saved, browser, site.default_language, "en"].find(l => l && available.includes(l)) || available[0];
}

export async function setLanguage(l) {
  lang = l; locale = LOCALES[l] || l;
  try { localStorage.setItem("lang", l); } catch (e) { /* private mode */ }
  [ui, uiEn, mc, mcEn] = await Promise.all([getJson(`/i18n/${l}.json`), getJson("/i18n/en.json"),
    getJson(`/assets/lang/${l}.json`), getJson("/assets/lang/en.json")]);
  reverse = deathRules = null;
  document.documentElement.lang = l;
}

/** Website text with {placeholders}; falls back to English, then to the key. */
export function t(key, vars = {}) {
  const s = ui[key] ?? uiEn[key] ?? key;
  return typeof s === "string" ? s.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? vars[k] : m)) : s;
}

const nice = id => String(id).replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
const mcKey = key => mc[key] ?? mcEn[key];

export const mcText = key => (key && (mc[key] ?? mcEn[key])) || "";
export const entityName = id => mcKey(`entity.minecraft.${id}`) || nice(id);
export const itemName = id => mcKey(`item.minecraft.${id}`) || mcKey(`block.minecraft.${id}`) || nice(id);
export const enchantName = id => mcKey(`enchantment.minecraft.${id}`) || nice(id);
export const trimPattern = id => mcKey(`trim_pattern.minecraft.${id}`) || nice(id);
export const trimMaterial = id => mcKey(`trim_material.minecraft.${id}`) || nice(id);

// English display name -> translation key (the server log is always in English)
function reverseIndex() {
  if (!reverse) {
    reverse = {};
    for (const [k, v] of Object.entries(mcEn)) if (/^(entity|item|block)\.minecraft\.[^.]+$|^advancements\..*\.title$/.test(k)) reverse[v] ??= k;
  }
  return reverse;
}
const translateName = name => { const k = reverseIndex()[name]; return (k && mcKey(k)) || name; };
export const advancementTitle = title => translateName(title);

// Death messages: match the English template, then fill in the template of the chosen language.
function rules() {
  if (!deathRules) {
    const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    deathRules = Object.entries(mcEn).filter(([k]) => k.startsWith("death.")).map(([k, v]) => {
      const order = [];
      let i = 0;
      const pattern = esc(v).replace(/%(\d+)\\\$s|%s/g, (m, n) => { order.push(n ? +n : ++i); return "(.+?)"; });
      return { key: k, re: new RegExp(`^${pattern}$`), order };
    }).sort((a, b) => b.re.source.length - a.re.source.length);
  }
  return deathRules;
}
export function deathMessage(player, message) {
  const full = `${player} ${message}`;
  const target = mc;
  for (const r of rules()) {
    const m = full.match(r.re);
    if (!m || !target[r.key]) continue;
    const args = {};
    r.order.forEach((n, i) => { args[n] = n === 1 ? player : translateName(m[i + 1]); });
    let i = 0;
    return target[r.key].replace(/%(\d+)\$s|%s/g, (s, n) => args[n ? +n : ++i] ?? s);
  }
  return full;
}
