// Entry point: routing, live updates every 5 seconds, language switcher and event handlers.
import { S } from "./state.js";
import { lang, pickLanguage, setLanguage, t } from "./i18n.js";
import { keepViewers, restoreViewers, setAnimation, v3d } from "./skins.js";
import { $, color, esc, onlineNow, tex } from "./util.js";
import { playerCards, viewServer } from "./views/server.js";
import { viewPlayer } from "./views/player.js";
import { renderTable, viewLog } from "./views/log.js";

const POLL_MS = 5000;
// remember the scroll position of every page, so "back" returns to the same spot
const scrollPos = {};
let currentHash = location.hash, steps = 0;
addEventListener("scroll", () => { scrollPos[currentHash] = scrollY; }, { passive: true });

function route() {
  const h = decodeURIComponent(location.hash.slice(1));
  if (h.startsWith("player/")) { S.view = "player"; S.who = h.slice(7); }
  else S.view = ["players", "log"].includes(h) ? h : "server";
  if (S.view === "log" && !S.data?.site?.show_log) S.view = "server";
  render();
}

function renderChrome() {
  const site = S.data.site;
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
    b.classList.toggle("on", b.dataset.v === S.view || (S.view === "player" && b.dataset.v === "players")));
  const app = $("app");
  if (S.view === "server") app.innerHTML = viewServer();
  else if (S.view === "players") app.innerHTML = `<h2 class="first">${tex("item/name_tag", "s")} ${t("section.choose")}</h2>` + playerCards();
  else if (S.view === "player") app.innerHTML = viewPlayer(S.who);
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
  $("mobs").innerHTML = on.slice(0, 6).map(p => v3d(p, 70, 120, "walk", "data-mob=1")).join("");
  $("foot").textContent = `${t("footer.updated", { time: S.data.generated })} · mc-server-stats v${S.data.site.version}`;
  restoreViewers(keep);
}

async function load() {
  try {
    const txt = await (await fetch("/api/data", { cache: "no-store" })).text();
    $("live").innerHTML = `<span class="dot on"></span> ${t("live")}`;
    if (txt === S.raw) return;
    const first = !S.data;
    S.raw = txt; S.data = JSON.parse(txt);
    if (first) { await setLanguage(pickLanguage(S.data.site)); route(); return; }
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
$("lang").addEventListener("change", async e => { await setLanguage(e.target.value); $("splash").textContent = ""; render(); });
$("app").addEventListener("click", e => {
  if (e.target.closest("[data-armor]")) { S.showArmor = !S.showArmor; render(); return; }
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

load();
setInterval(load, POLL_MS);
