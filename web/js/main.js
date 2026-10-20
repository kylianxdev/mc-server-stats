// Entry point: routing, live updates every 5 seconds, language switcher and event handlers.
import { S } from "./state.js";
import { lang, pickLanguage, setLanguage, t } from "./i18n.js";
import { keepViewers, restoreViewers, setAnimation, v3d } from "./skins.js";
import { $, color, esc, loadTextures, onlineNow, tex } from "./util.js";
import { playerCards, viewServer } from "./views/server.js";
import { viewPlayer } from "./views/player.js";
import { renderTable, viewLog } from "./views/log.js";
import { viewVersus } from "./views/versus.js";
import { advancementScreen, loadAdvancements } from "./views/advancements.js";
import { updateSky } from "./sky.js";
import { startWorld3d, updateWorld3d } from "./world3d.js";

const POLL_MS = 5000;
// remember the scroll position of every page, so "back" returns to the same spot
const scrollPos = {};
let currentHash = location.hash, steps = 0;
addEventListener("scroll", () => { scrollPos[currentHash] = scrollY; }, { passive: true });

function route() {
  const h = decodeURIComponent(location.hash.slice(1));
  if (h.startsWith("player/")) { S.view = "player"; S.who = h.slice(7); }
  else if (h.startsWith("versus")) { S.view = "versus"; [S.vsA, S.vsB] = h.split("/").slice(1); }
  else S.view = ["players", "log"].includes(h) ? h : "server";
  if (S.view === "log" && !S.data?.site?.show_log) S.view = "server";
  render();
}

// the world line under the title: day number and weather (the sky itself is drawn by sky.js)
function renderSky() {
  const w = S.data.world || {};
  updateSky(w);
  updateWorld3d();
  const weather = w.thundering ? "thunder" : w.raining ? "rain" : "clear";
  $("world").innerHTML = w.day ? `<span>${tex("item/clock_00", "xs")} ${t("world.day", { n: w.day.toLocaleString() })}</span>
    <span>${tex({ clear: "block/sunflower_front", rain: "item/water_bucket", thunder: "block/lightning_rod" }[weather], "xs")} ${t(`weather.${weather}`)}</span>
    <span data-tip="${t("kpi.dragon")}">${tex("block/dragon_egg", "xs")} ${t(w.dragon_killed ? "world.dragon_dead" : "world.dragon_alive")}</span>` : "";
}

function renderChrome() {
  const site = S.data.site;
  renderSky();
  document.title = site.title;
  $("title").textContent = site.title;
  $("tagline").textContent = site.tagline || "";
  $("navServer").innerHTML = `${tex("block/grass_block_side", "s")} ${t("nav.server")}`;
  $("navPlayers").innerHTML = `${tex("item/name_tag", "s")} ${t("nav.players")}`;
  $("navLog").innerHTML = `${tex("item/writable_book", "s")} ${t("nav.log")}`;
  $("navLog").classList.toggle("hidden", !site.show_log);
  $("lang").innerHTML = site.languages.map(l => `<option value="${l}" ${l === lang ? "selected" : ""}>${t(`language.${l}`)}</option>`).join("");
  const splashes = t("splashes");
  if (!$("splash").textContent && Array.isArray(splashes)) $("splash").textContent = splashes[Math.floor(Math.random() * splashes.length)];
}

function render() {
  if (!S.data) return;
  const keep = keepViewers(); // existing 3D players are reused instead of reloaded
  renderChrome();
  document.querySelectorAll("#nav [data-v]").forEach(b =>
    b.classList.toggle("on", b.dataset.v === S.view || (["player", "versus"].includes(S.view) && b.dataset.v === "players")));
  const app = $("app");
  if (S.view === "server") app.innerHTML = viewServer();
  else if (S.view === "players") app.innerHTML = `<h2 class="first">${tex("item/name_tag", "s")} ${t("section.choose")}</h2>` + playerCards();
  else if (S.view === "player") app.innerHTML = viewPlayer(S.who);
  else if (S.view === "versus") app.innerHTML = viewVersus(decodeURIComponent(S.vsA || ""), decodeURIComponent(S.vsB || ""));
  else {
    const prev = $("q") ? { q: $("q").value, pf: $("pf").value, ao: $("ao").checked } : null;
    app.innerHTML = viewLog();
    ["q", "pf", "ao"].forEach(id => $(id).addEventListener("input", renderTable));
    if (prev) { $("q").value = prev.q; $("pf").value = prev.pf; $("ao").checked = prev.ao; }
    renderTable();
  }
  const on = onlineNow();
  $("onlinePill").innerHTML = `<span class="dot ${on.length ? "on" : ""}"></span> ${on.length
    ? t("online.some", { n: on.length }) + " " + on.map(p => `<span style="color:${color(p)}">${esc(p)}</span>`).join(", ")
    : t("online.none")}`;
  // online players walk over the grass in the header
  // with the 3D world the online players walk around in it instead
  $("mobs").innerHTML = document.body.classList.contains("w3d") ? "" : on.slice(0, 6).map(p => v3d(p, 70, 120, "walk", "data-mob=1")).join("");
  $("foot").textContent = `${t("footer.updated", { time: S.data.generated })} · mc-server-stats v${S.data.site.version}`;
  $("live").innerHTML = `<span class="dot on"></span> ${t("live")}`;
  restoreViewers(keep);
}

const CACHE_KEY = "mcstats-data";
async function load() {
  try {
    const early = window.firstData; window.firstData = null;
    const txt = (early && await early) || await (await fetch("/api/data", { cache: "no-store" })).text();
    try { localStorage.setItem(CACHE_KEY, txt); } catch (e) { /* full or private mode */ }
    $("live").innerHTML = `<span class="dot on"></span> ${t("live")}`;
    if (txt === S.raw) return;
    if (!S.ready && S.starting) await S.starting;  // the cached version is still being drawn
    S.raw = txt; S.data = JSON.parse(txt);
    if (!S.ready) { await firstRender(); return; }
    if (S.view === "log" && document.activeElement?.closest?.(".tools")) { renderTable(); return; } // don't disturb typing
    const y = scrollY; render(); scrollTo(0, y);
    $("live").classList.add("flash"); setTimeout(() => $("live").classList.remove("flash"), 600);
  } catch (e) {
    $("live").innerHTML = `<span class="dot"></span> ${t("live.lost")}`;
  }
}

/* ---------- events ---------- */
const go = v => { location.hash = v === "server" ? "#" : "#" + v; };
$("nav").addEventListener("click", e => { const v = e.target.closest("[data-v]")?.dataset.v; if (v) go(v); });
$("lang").addEventListener("change", async e => {
  const { names } = await setLanguage(e.target.value);
  $("splash").textContent = ""; render();
  names.then(render);
});
// the 3D library loads in the background; start the 3D players once it's there
addEventListener("skinview3d-ready", () => render());
$("app").addEventListener("change", e => {
  const pick = e.target.closest("[data-vs]");
  if (!pick) return;
  const a = pick.dataset.vs === "a" ? pick.value : S.vsA, b = pick.dataset.vs === "b" ? pick.value : S.vsB;
  location.hash = `#versus/${encodeURIComponent(decodeURIComponent(a || ""))}/${encodeURIComponent(decodeURIComponent(b || ""))}`;
});
$("app").addEventListener("click", e => {
  if (e.target.closest("[data-armor]")) { S.showArmor = !S.showArmor; render(); return; }
  const tab = e.target.closest("[data-advtab]");
  if (tab) { S.advTab = tab.dataset.advtab; $("advScreen").innerHTML = advancementScreen(S.who); return; }
  const anim = e.target.closest(".btn[data-anim]");
  if (anim) { setAnimation(document.querySelector("canvas[data-big]"), anim.dataset.anim); return; }
  const el = e.target.closest("[data-log],[data-go],[data-p]");
  if (!el) return;
  if (el.dataset.log) { S.logTab = el.dataset.log; render(); }
  else if (el.dataset.go === "back") { if (steps > 0) history.back(); else go("players"); }
  else if (el.dataset.go) go(el.dataset.go);
  else location.hash = "#player/" + encodeURIComponent(el.dataset.p);
});
// player cards start walking on hover
$("app").addEventListener("mouseover", e => {
  const card = e.target.closest("[data-hoverwalk]");
  if (card && card._walking !== true) { card._walking = true; setAnimation(card.querySelector("canvas"), "walk"); }
});
$("app").addEventListener("mouseout", e => {
  const card = e.target.closest("[data-hoverwalk]");
  if (card && !card.contains(e.relatedTarget)) { card._walking = false; setAnimation(card.querySelector("canvas"), "idle"); }
});
addEventListener("hashchange", () => {
  currentHash = location.hash;
  const saved = scrollPos[currentHash]; // read before rendering: rendering itself can fire scroll events
  steps++;
  route();
  // a page you were on before: back to the same spot; a new page: start at the menu
  if (saved !== undefined) scrollTo(0, saved);
  else if (scrollY > $("nav").offsetTop) scrollTo(0, $("nav").offsetTop);
});

// tooltip in the style of the game
const tip = $("tip");
document.addEventListener("mousemove", e => {
  const el = e.target.closest("[data-tip]");
  if (!el) { tip.style.display = "none"; return; }
  tip.innerHTML = el.dataset.tip; tip.style.display = "block";
  const x = Math.min(e.clientX + 14, innerWidth - tip.offsetWidth - 8), y = e.clientY - tip.offsetHeight - 12;
  tip.style.left = Math.max(4, x) + "px"; tip.style.top = (y < 4 ? e.clientY + 18 : y) + "px";
});

// draw as soon as the website texts are there; Minecraft names and advancements follow a moment later
async function firstRender() {
  if (S.starting) return S.starting;
  S.starting = (async () => {
    const { names } = await setLanguage(pickLanguage(S.data.site));
    S.ready = true;
    route();
    Promise.all([names, loadAdvancements(), loadTextures()]).then(render);
  })();
  return S.starting;
}

// coming back: show the last known data immediately; the live data replaces it a moment later
function fromCache() {
  let txt = null;
  try { txt = localStorage.getItem(CACHE_KEY); } catch (e) { /* private mode */ }
  if (!txt || S.data) return;
  try { S.data = JSON.parse(txt); } catch (e) { return; }
  firstRender();
}

fromCache();
// the 3D header loads right away, next to the page (BlueMap's map in a frame; our own world waits until the page is idle)
startWorld3d().then(() => S.ready && render());
load();
setInterval(load, POLL_MS);
