// Skins: 3D players (skinview3d), 3D block heads (CSS), and armor drawn onto the skin like the game does.
import { S } from "./state.js";
import { esc } from "./util.js";

// skin url with version: a new skin gets a new ?v=, so no stale cache
export const skinUrl = p => `/skin/${encodeURIComponent(p)}.png?v=${encodeURIComponent(S.data.skins?.[p]?.v || "0")}`;
export const isSlim = p => S.data.skins?.[p]?.model === "slim";
const capeUrl = p => (S.data.skins?.[p]?.cape ? `/cape/${encodeURIComponent(p)}.png?v=${encodeURIComponent(S.data.skins[p].cape)}` : null);

const imgCache = {};
const loadImg = url => (imgCache[url] ??= new Promise(res => {
  const im = new Image(); im.onload = () => res(im); im.onerror = () => res(null); im.src = url;
}));

/* ---------- 3D block head: six faces (+ hat layer) taken from the 64×64 skin texture ---------- */
export function head3d(p, size = 24) {
  const u = skinUrl(p);
  const face = (cls, x, y) => `<div class="f ${cls}" style="background-image:url(${u});background-position:calc(var(--s) * -${x / 8}) calc(var(--s) * -${y / 8})"></div>`;
  const six = ox => face("fr", 8 + ox, 8) + face("bk", 24 + ox, 8) + face("rt", ox, 8) + face("lt", 16 + ox, 8) + face("tp", 8 + ox, 0) + face("bt", 16 + ox, 0);
  return `<span class="head3d" style="--s:${size}px"><span class="cube">${six(0)}<span class="hat">${six(32)}</span></span></span>`;
}

/* ---------- armor on the skin: armor layer + trim with the real color palette ---------- */
function armorInfo(it) {
  if (!it) return null;
  if (it.id === "elytra") return { elytra: true };
  const m = it.id.match(/^(.*)_(helmet|chestplate|leggings|boots)$/);
  if (!m) return null;
  return { mat: { golden: "gold", turtle: "turtle_scute" }[m[1]] || m[1], piece: m[2], color: it.color, trim: it.trim };
}
// box UV: where the six faces of a cuboid are in a skin/armor texture
function boxFaces(u, v, w, h, d) {
  return { top: [u + d, v, w, d], bottom: [u + d + w, v, w, d], right: [u, v + d, d, h], front: [u + d, v + d, w, h],
           left: [u + d + w, v + d, d, h], back: [u + d + w + d, v + d, w, h] };
}
// copy a cuboid face by face (scales, e.g. 4 → 3 wide for slim arms; mirrors for the left side)
function copyBox(ctx, src, s, dst, mirror = false) {
  const S_ = boxFaces(...s), D = boxFaces(...dst);
  const swap = { top: "top", bottom: "bottom", right: "left", left: "right", front: "front", back: "back" };
  for (const f of Object.keys(D)) {
    const [sx, sy, sw, sh] = S_[mirror ? swap[f] : f], [dx, dy, dw, dh] = D[f];
    if (!sw || !sh || !dw || !dh) continue;
    if (mirror) { ctx.save(); ctx.translate(dx + dw, dy); ctx.scale(-1, 1); ctx.drawImage(src, sx, sy, sw, sh, 0, 0, dw, dh); ctx.restore(); }
    else ctx.drawImage(src, sx, sy, sw, sh, dx, dy, dw, dh);
  }
}
const DARKER = ["copper", "diamond", "gold", "iron", "netherite"];
async function paletteSwap(img, material, armorMat) {
  const [base, darker, normal] = await Promise.all([loadImg("/assets/palettes/trim_base.png"),
    DARKER.includes(material) ? loadImg(`/assets/palettes/trim/${material}_darker.png`) : null,
    loadImg(`/assets/palettes/trim/${material}.png`)]);
  const pal = material === armorMat && darker ? darker : normal; // same material as the armor: darker variant, like the game
  const c = document.createElement("canvas"); c.width = img.width; c.height = img.height;
  const x = c.getContext("2d"); x.drawImage(img, 0, 0);
  if (!base || !pal) return c;
  const pixels = im => { const k = document.createElement("canvas"); k.width = im.width; k.height = 1; const kx = k.getContext("2d"); kx.drawImage(im, 0, 0); return kx.getImageData(0, 0, im.width, 1).data; };
  const b = pixels(base), p = pixels(pal), d = x.getImageData(0, 0, c.width, c.height);
  for (let i = 0; i < d.data.length; i += 4) {
    if (!d.data[i + 3]) continue;
    for (let j = 0; j < b.length; j += 4) {
      if (b[j] === d.data[i] && b[j + 1] === d.data[i + 1] && b[j + 2] === d.data[i + 2]) {
        d.data[i] = p[j]; d.data[i + 1] = p[j + 1]; d.data[i + 2] = p[j + 2]; break;
      }
    }
  }
  x.putImageData(d, 0, 0);
  return c;
}
async function armorLayer(a) {
  const folder = a.piece === "leggings" ? "humanoid_leggings" : "humanoid";
  const c = document.createElement("canvas"); c.width = 64; c.height = 32;
  const x = c.getContext("2d");
  const tex = await loadImg(`/assets/entity/equipment/${folder}/${a.mat}.png`);
  if (!tex) return null;
  if (a.mat === "leather") { // dyed leather (default brown), then the undyed overlay
    x.drawImage(tex, 0, 0);
    x.globalCompositeOperation = "multiply"; x.fillStyle = "#" + ((a.color ?? 0xa06540) & 0xffffff).toString(16).padStart(6, "0"); x.fillRect(0, 0, 64, 32);
    x.globalCompositeOperation = "destination-in"; x.drawImage(tex, 0, 0); x.globalCompositeOperation = "source-over";
    const overlay = await loadImg(`/assets/entity/equipment/${folder}/leather_overlay.png`);
    if (overlay) x.drawImage(overlay, 0, 0);
  } else x.drawImage(tex, 0, 0);
  if (a.trim?.pattern) {
    const trim = await loadImg(`/assets/trims/entity/${folder}/${a.trim.pattern}.png`);
    if (trim) x.drawImage(await paletteSwap(trim, a.trim.material, a.mat), 0, 0);
  }
  return c;
}
async function composeSkin(p) {
  const skin = await loadImg(skinUrl(p));
  const aw = isSlim(p) ? 3 : 4;
  const c = document.createElement("canvas"); c.width = 64; c.height = 64;
  const x = c.getContext("2d"); x.imageSmoothingEnabled = false;
  if (skin) {
    x.drawImage(skin, 0, 0);
    if (skin.height === 32) { // old 64×32 skins: left arm/leg are the mirrored right ones
      copyBox(x, skin, [40, 16, 4, 12, 4], [32, 48, 4, 12, 4], true);
      copyBox(x, skin, [0, 16, 4, 12, 4], [16, 48, 4, 12, 4], true);
    }
  }
  const eq = S.showArmor ? S.data.armor?.[p] || {} : {};
  for (const a of ["legs", "feet", "chest", "head"].map(s => armorInfo(eq[s])).filter(a => a && !a.elytra)) {
    const L = await armorLayer(a);
    if (!L) continue;
    if (a.piece === "helmet") copyBox(x, L, [0, 0, 8, 8, 8], [32, 0, 8, 8, 8]);
    if (a.piece === "chestplate") {
      copyBox(x, L, [16, 16, 8, 12, 4], [16, 32, 8, 12, 4]);
      copyBox(x, L, [40, 16, 4, 12, 4], [40, 32, aw, 12, 4]);
      copyBox(x, L, [40, 16, 4, 12, 4], [48, 48, aw, 12, 4], true);
    }
    if (a.piece === "leggings") {
      copyBox(x, L, [16, 16, 8, 12, 4], [16, 32, 8, 12, 4]);
      copyBox(x, L, [0, 16, 4, 12, 4], [0, 32, 4, 12, 4]);
      copyBox(x, L, [0, 16, 4, 12, 4], [0, 48, 4, 12, 4], true);
    }
    if (a.piece === "boots") {
      copyBox(x, L, [0, 16, 4, 12, 4], [0, 32, 4, 12, 4]);
      copyBox(x, L, [0, 16, 4, 12, 4], [0, 48, 4, 12, 4], true);
    }
  }
  return { canvas: c, elytra: S.showArmor && armorInfo(eq.chest)?.elytra };
}

/* ---------- 3D players (skinview3d) ---------- */
const ANIMS = { idle: "IdleAnimation", walk: "WalkingAnimation", run: "RunningAnimation", wave: "WaveAnimation", fly: "FlyingAnimation" };
const viewers = [];

// data-key: same player + place + size = the same viewer, which survives a live update
export const v3d = (p, w, h, anim, extra = "") =>
  `<canvas class="v3d" data-3d="${esc(p)}" data-anim="${anim}" data-key="${esc(p)}|${anim}|${w}x${h}|${extra}" width="${w}" height="${h}" style="width:${w}px;height:${h}px" ${extra}></canvas>`;

// skin signature: only redraw when the skin or what the player wears changed (not on durability changes)
const signature = p => skinUrl(p) + (capeUrl(p) || "") + JSON.stringify(Object.fromEntries(Object.entries(S.data.armor?.[p] || {})
  .map(([k, i]) => [k, i && [i.id, i.trim, i.color]]))) + (S.showArmor ? "" : "|off");

async function applySkin(cv) {
  const p = cv.dataset["3d"], sig = signature(p), v = cv._viewer;
  if (!v || cv._sig === sig) return;
  cv._sig = sig;
  const { canvas, elytra } = await composeSkin(p);
  if (cv._sig !== sig) return; // changed again in the meantime
  v.loadSkin(canvas, { model: isSlim(p) ? "slim" : "default" });
  // the active cape; with an elytra the game shows the cape design on the elytra
  const cape = capeUrl(p);
  if (elytra) v.loadCape(cape || "/assets/entity/equipment/wings/elytra.png", { backEquipment: "elytra" });
  else v.loadCape(cape, { backEquipment: "cape" });
}

/** Before re-rendering: set the existing 3D viewers aside so they can be reused. */
export function keepViewers() {
  const keep = new Map();
  for (const cv of document.querySelectorAll("canvas[data-3d]")) if (cv._viewer) keep.set(cv.dataset.key, cv);
  return keep;
}

/** After re-rendering: put reused viewers back, dispose the rest, start new ones. */
export function restoreViewers(keep) {
  for (const cv of document.querySelectorAll("canvas[data-3d]")) {
    const old = keep.get(cv.dataset.key);
    if (old) { cv.replaceWith(old); keep.delete(cv.dataset.key); }
  }
  for (const cv of keep.values()) {
    try { cv._viewer.dispose(); } catch (e) { /* already gone */ }
    viewers.splice(viewers.indexOf(cv._viewer), 1);
  }
  if (!window.skinview3d) return;
  for (const cv of document.querySelectorAll("canvas[data-3d]")) {
    if (cv._viewer) { applySkin(cv); continue; }
    try {
      const v = new skinview3d.SkinViewer({ canvas: cv, width: cv.width, height: cv.height });
      v.animation = new skinview3d[ANIMS[cv.dataset.anim] || "IdleAnimation"]();
      v.controls.enableZoom = false; v.controls.enablePan = false;
      if (cv.dataset.big) { v.autoRotate = true; v.autoRotateSpeed = 0.6; v.zoom = 0.7; }
      else if (cv.dataset.mob) { v.controls.enableRotate = false; v.zoom = 0.9; v.playerObject.rotation.y = 0.35; v.animation.speed = 0.8; }
      else { v.zoom = 0.68; v.playerObject.rotation.y = 0.5; }
      viewers.push(v); cv._viewer = v; applySkin(cv);
    } catch (e) { console.warn("3D viewer unavailable", e); }
  }
}

export function setAnimation(cv, name) {
  if (cv?._viewer && window.skinview3d) cv._viewer.animation = new skinview3d[ANIMS[name] || "IdleAnimation"]();
}
