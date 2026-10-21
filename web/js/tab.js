// The browser tab: who is online and what you're looking at, with the server icon and a green dot.
import { S } from "./state.js";
import { t } from "./i18n.js";

let base = null, drawn = -1;

export function updateTab(online) {
  const page = { player: S.who, versus: S.vsA && S.vsB ? `${S.vsA} vs ${S.vsB}` : "", players: t("nav.players"), log: t("nav.log") }[S.view];
  document.title = [online.length ? `● ${t("tab.online", { n: online.length })}` : "", page, S.data.site.title].filter(Boolean).join(" · ");
  if (online.length !== drawn) icon(online.length);
}

// the server icon, with the number of players online in a green dot (like a game notification)
function icon(n) {
  drawn = n;
  if (!base) {
    base = new Image();
    base.onload = () => { const m = drawn; drawn = -1; icon(m); };
    base.src = "/favicon.png";
    return;
  }
  if (!base.complete || !base.naturalWidth) return;
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const g = c.getContext("2d");
  g.imageSmoothingEnabled = false;
  g.drawImage(base, 0, 0, 64, 64);
  if (n) {
    g.fillStyle = "#000";
    g.beginPath(); g.arc(46, 46, 18, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#55ff55";
    g.beginPath(); g.arc(46, 46, 15, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#003300";
    g.font = "bold 24px sans-serif"; g.textAlign = "center"; g.textBaseline = "middle";
    g.fillText(n > 9 ? "9+" : String(n), 46, 48);
  }
  let link = document.querySelector("link[rel=icon]");
  if (!link) { link = document.createElement("link"); link.rel = "icon"; document.head.appendChild(link); }
  link.type = "image/png";
  link.href = c.toDataURL("image/png");
}
