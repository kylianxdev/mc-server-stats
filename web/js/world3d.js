// The header as a real Minecraft world: the valley with everyone's home, seen from the air with a
// camera slowly circling it. The light follows the time of day and the weather.
//
// When the server runs BlueMap, its own 3D map is shown (every block, perfectly rendered, with the
// online players as live markers), without its buttons and menus. Otherwise this website draws the
// valley itself from the region files with three.js, and the land around it in coarser blocks.
//
// three.js is only loaded after the page itself is drawn; without WebGL the flat header stays.
import { S } from "./state.js";
import { color } from "./util.js";
import { composeSkin } from "./skins.js";

let THREE = null, renderer = null, scene = null, camera = null, canvas = null;
let solidMats = [], middle = 0, size = 24, homes = {}, players = new Map(), heightAt = () => null;
let running = false, visible = true, frame = 0, last = 0, angle = 0, light = 1, drawn = 0;
const still = matchMedia("(prefers-reduced-motion: reduce)").matches;

// Minecraft's plains colors for grass, leaves and water (the textures themselves are grey)
const GRASS = 0x91bd59, FOLIAGE = 0x77ab2f, WATER = 0x3f76e4;
const LEAF_TINT = { birch_leaves: 0x80a755, spruce_leaves: 0x619961 };
// how bright each side of a block is in the game: top, bottom, north/south, east/west
const SHADE = { py: 1, ny: 0.5, pz: 0.8, nz: 0.8, px: 0.6, nx: 0.6 };
// the four corners of every face (bottom left, bottom right, top right, top left seen from outside)
const FACES = {
  px: { n: [1, 0, 0], c: [[1, 0, 1], [1, 0, 0], [1, 1, 0], [1, 1, 1]] },
  nx: { n: [-1, 0, 0], c: [[0, 0, 0], [0, 0, 1], [0, 1, 1], [0, 1, 0]] },
  pz: { n: [0, 0, 1], c: [[0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]] },
  nz: { n: [0, 0, -1], c: [[1, 0, 0], [0, 0, 0], [0, 1, 0], [1, 1, 0]] },
  py: { n: [0, 1, 0], c: [[0, 1, 1], [1, 1, 1], [1, 1, 0], [0, 1, 0]] },
  ny: { n: [0, -1, 0], c: [[0, 0, 0], [1, 0, 0], [1, 0, 1], [0, 0, 1]] },
};
// sky colors near the horizon (the fog fades into these) and how light the world is
const SKY = {
  day: [0x8fbdf2, 1], dawn: [0xc9788a, 0.75], dusk: [0xc9788a, 0.75], night: [0x2a3470, 0.5],
};

const CROSS = /(^|_)(short_grass|tall_grass|fern|large_fern|sapling|sugar_cane|torch|lantern|mushroom|dead_bush|bush|tulip|dandelion|poppy|blue_orchid|allium|azure_bluet|oxeye_daisy|cornflower|lily_of_the_valley|wither_rose|rose_bush|lilac|peony|sunflower|wheat|carrots|potatoes|beetroots|sweet_berry_bush|roots|sprouts|seagrass|kelp|kelp_plant|bamboo_sapling|firefly_bush|short_dry_grass|tall_dry_grass|cactus_flower|eyeblossom|pitcher_plant|torchflower)$/;
const FLAT = /(^|_)(rail|carpet|lily_pad|snow|pink_petals|leaf_litter|wildflowers)$/;
const SKIP = /^potted_|stem$|ladder|sign$|banner|button|lever|pressure_plate|bed$|door$|pane$|fence|chain$|vine|cobweb|fire$|_head$|skull|frame$|^light$|tripwire|redstone_wire|scaffolding|item_frame/;
const SEE_THROUGH = /glass|leaves|ice$|portal|spawner|honey_block|slime_block|barrier/;
const GLOW = /glowstone|torch|lantern|lava|shroomlight|sea_lantern|jack_o_lantern|magma|froglight|portal|campfire/;
const TINT_PLANT = /^(short_grass|tall_grass|fern|large_fern|sugar_cane|lily_pad|vine)$/;

/** Start the 3D header once (it's skipped without WebGL or when the world has no blocks). */
export async function startWorld3d() {
  if (canvas || !window.WebGLRenderingContext) return;
  canvas = document.createElement("canvas");
  canvas.className = "world3d";
  let world;
  try {
    world = await fetch("/api/world3d").then(r => r.json());
    if (world.bluemap) return startBlueMap(world.bluemap);
    THREE = await import("/assets/js/three.module.min.js");
    if (!world.h?.length) throw new Error("no world");
    renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: false, powerPreference: "low-power" });
  } catch (e) {
    canvas = null;  // keep the flat header
    return;
  }
  renderer.setPixelRatio(1);  // pixel art: a sharper picture adds nothing but work
  renderer.setClearColor(0x000000, 0);
  scene = new THREE.Scene();
  scene.fog = new THREE.Fog(SKY.night[0], 14, 30);
  camera = new THREE.PerspectiveCamera(50, 2, 0.5, 1000);

  const textures = new Set(await fetch("/assets/textures.json").then(r => r.json()).catch(() => []));
  buildTerrain(world, textures);

  const hero = document.querySelector(".hero");
  hero.insertBefore(canvas, document.getElementById("rain"));
  hero.classList.add("w3d");
  document.body.classList.add("w3d");
  new ResizeObserver(resize).observe(hero);
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; wake(); }).observe(hero);
  document.addEventListener("visibilitychange", wake);
  resize();
  updateWorld3d();
  wake();
}

/* ---------- BlueMap ---------- */
let bluemap = null;

function startBlueMap(bm) {
  const frame = document.createElement("iframe");
  frame.className = "world3d";
  frame.tabIndex = -1;
  frame.setAttribute("aria-hidden", "true");
  // map:x:y:z:distance:rotation:angle:tilt:ortho:mode (angle: 0 is straight down)
  frame.src = `/bluemap/#${bm.map}:${bm.x}:${bm.y}:${bm.z}:${bm.distance}:0:0.78:0:0:perspective`;
  const hero = document.querySelector(".hero");
  hero.insertBefore(frame, document.getElementById("rain"));
  canvas = frame;
  frame.addEventListener("load", () => {
    const doc = frame.contentDocument, style = doc.createElement("style");
    style.textContent = "#app { display: none !important; } body { cursor: default; }";  // only the map, no menus
    doc.head.appendChild(style);
    const ready = () => {
      const app = frame.contentWindow.bluemap;
      if (!app?.mapViewer?.map) return setTimeout(ready, 250);
      bluemap = app;
      app.center = bm;
      const viewer = app.mapViewer, phone = innerWidth < 700;
      // every block up to the mountains on the horizon, but only in front of the camera: a square
      // around a point ahead of it (half the tiles of a square around the middle, the same view)
      app.reach = phone ? 200 : 320;
      app.ahead = phone ? 80 : 130;
      const lowres = Math.max(2500, bm.distance * 10), load = viewer.loadMapArea.bind(viewer);
      // BlueMap loads around the point the camera looks at, and resets the distances from its settings
      viewer.loadMapArea = () => load(app.ahead_x ?? bm.x, app.ahead_z ?? bm.z, app.reach, lowres);
      // sharp enough behind the title, without drawing four pixels for every pixel on retina screens
      viewer.superSampling = Math.min(1, 1.5 / devicePixelRatio);
      // BlueMap draws every frame of the screen (60 to 144 times a second), also when the banner is
      // scrolled away. Now: 30 evenly spaced frames a second, turning the camera right before each one,
      // and nothing while the banner can't be seen
      const inner = viewer.renderLoop;
      let shown = 0;
      viewer.renderLoop = now => {
        if (!visible || document.hidden || now - shown < 29) return requestAnimationFrame(viewer.renderLoop);
        turn(Math.min(0.1, (now - (shown || now)) / 1000));
        shown = now;
        inner(now);
      };
      turn(0);
      hero.classList.add("w3d", "bluemap");
      document.body.classList.add("w3d");
      new IntersectionObserver(([e]) => { visible = e.isIntersecting; wake(); }).observe(hero);
      document.addEventListener("visibilitychange", wake);
      updateWorld3d();
      wake();
    };
    ready();
  });
}

/** Called on every live update: light, fog and the online players. */
export function updateWorld3d() {
  if (bluemap) {
    const sky = document.querySelector(".hero").dataset.sky || "night";
    // a bit lighter than the game at night, so the valley stays visible behind the title
    const sun = { day: 1, dawn: 0.75, dusk: 0.75, night: 0.5 }[sky] * (S.data.world?.raining ? 0.8 : 1);
    const u = bluemap.mapViewer.data?.uniforms;
    if (u?.sunlightStrength) {
      u.sunlightStrength.value = sun;
      u.ambientLight.value = sky === "night" ? 0.3 : 0.15;
      bluemap.mapViewer.redraw();
    }
    return;
  }
  if (!scene) return;
  const sky = document.querySelector(".hero").dataset.sky || "night";
  const [fog, bright] = SKY[sky] || SKY.night;
  const rain = S.data.world?.raining ? 0.7 : 1;
  scene.fog.color.setHex(fog).multiplyScalar(rain);
  light = bright * rain;
  for (const m of solidMats) m.color.setScalar(m.userData.glow ? 1 : light);
  syncPlayers();
  if (still) draw(performance.now());
}

/* ---------- the blocks ---------- */
const loader = () => new THREE.TextureLoader();
const texCache = {};
function texture(path) {
  if (texCache[path]) return texCache[path];
  const t = loader().load(`/assets/${path}.png`, t => {
    const { width: w, height: h } = t.image;
    if (h > w) { t.repeat.set(1, w / h); t.offset.set(0, 1 - w / h); }  // animated: first frame only
    if (still) draw(performance.now());
  });
  t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestMipmapLinearFilter;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;  // the coarse land far away repeats a texture over several blocks
  t.colorSpace = THREE.SRGBColorSpace;
  return (texCache[path] = t);
}

// the texture of one side of a block, guessed from its name like the game's models name them
function resolver(textures) {
  const has = n => textures.has(`block/${n}`);
  const base = name => {
    const b = name.replace(/_(slab|stairs|wall)$/, "");
    for (const c of [b, `${b}s`, `${b}_planks`, `${b}_block`, b.replace(/^(chipped|damaged|lava|water|powder_snow|waxed)_/, "")])
      if (has(c) || has(`${c}_side`) || has(`${c}_top`)) return c;
    return b;
  };
  return (name, side) => {
    if (name === "grass_block") return side === "py" ? "block/grass_block_top" : side === "ny" ? "block/dirt" : "block/grass_block_side";
    if (name === "water") return "block/water_still";
    if (name === "lava") return "block/lava_still";
    if (name.endsWith("_carpet")) return `block/${name.replace("_carpet", "_wool")}`;
    if (name === "smooth_stone_slab") return side === "py" || side === "ny" ? "block/smooth_stone" : "block/smooth_stone_slab_side";
    const b = base(name);
    const order = side === "py" ? [`${b}_top`, b, `${b}_side`] : side === "ny" ? [`${b}_bottom`, `${b}_top`, b, `${b}_side`]
      : [`${b}_side`, b, `${b}_front`, `${b}_outside`, `${b}_top`];
    const hit = order.find(has);
    return hit ? `block/${hit}` : null;
  };
}

function buildTerrain(world, textures) {
  const tex = resolver(textures);
  const at = new Map(), key = (x, y, z) => `${x},${y},${z}`;
  const b = world.detail;  // every block around the homes, flat: x, y, z, palette index, x, y, …
  for (let i = 0; i < b.length; i += 4) at.set(key(b[i], b[i + 1], b[i + 2]), world.palette[b[i + 3]]);
  const name = s => s?.split(":")[0];
  const kind = s => {
    const n = name(s);
    if (!n || SKIP.test(n)) return "skip";
    if (n === "water" || n === "lava") return "liquid";
    if (CROSS.test(n)) return "cross";
    if (FLAT.test(n)) return "flat";
    if (n.endsWith("_slab")) return "slab";
    return "cube";
  };
  const opaque = s => kind(s) === "cube" && !SEE_THROUGH.test(name(s));

  // the ground: one height per column (from the game's heightmap), its top block and the block under it
  const [W, D] = world.size, [ox, oz] = world.origin;
  heightAt = (x, z) => {
    const i = Math.floor(x) - ox, j = Math.floor(z) - oz;
    return i < 0 || j < 0 || i >= W || j >= D ? null : world.h[j * W + i];
  };
  const inPatch = (x, z) => world.patches.some(([x0, z0, x1, z1]) => x >= x0 && x <= x1 && z >= z0 && z <= z1);
  homes = world.homes || {};
  size = Math.max(W, D) / 2;
  const hs = Object.values(homes).map(h => h[1]);
  middle = hs.length ? hs.reduce((a, b) => a + b, 0) / hs.length : heightAt(0, 0) ?? 0;
  scene.fog.near = size * 1.3; scene.fog.far = size * 3;

  const groups = {};  // texture|tint|mode -> arrays
  const group = (path, tint, mode) => {
    const k = `${path}|${tint}|${mode}`;
    return (groups[k] ??= { path, tint, mode, pos: [], uv: [], col: [], idx: [] });
  };
  const colors = {};
  const quad = (g, corners, uvs, shade, tint) => {
    const c = (colors[`${tint}|${shade}`] ??= new THREE.Color(tint ?? 0xffffff).multiplyScalar(shade)), n = g.pos.length / 3;
    for (let i = 0; i < 4; i++) { g.pos.push(...corners[i]); g.uv.push(...uvs[i]); g.col.push(c.r, c.g, c.b); }
    g.idx.push(n, n + 1, n + 2, n, n + 2, n + 3);
  };
  const tintOf = (n, side) => n === "grass_block" ? (side === "py" ? GRASS : null) : n.includes("leaves")
    ? (/cherry|azalea|pale/.test(n) ? null : LEAF_TINT[n] ?? FOLIAGE) : n === "water" ? WATER : TINT_PLANT.test(n) ? GRASS : null;

  for (const [k, s] of at) {
    const [x, y, z] = k.split(",").map(Number), n = name(s), kd = kind(s);
    if (kd === "skip") continue;
    if (kd === "cross") {
      const double = textures.has(`block/${n}_top`) && textures.has(`block/${n}_bottom`);
      const path = double ? `block/${n}_${name(at.get(key(x, y - 1, z))) === n ? "top" : "bottom"}` : `block/${n}`;
      if (!textures.has(path)) continue;
      const g = group(path, tintOf(n), "cross"), w = /torch|lantern/.test(n) ? 0.3 : 0.45, h = /torch/.test(n) ? 0.8 : 1;
      for (const [a, b] of [[[-w, -w], [w, w]], [[-w, w], [w, -w]]]) {
        const p = (dx, dz, dy) => [x + 0.5 + dx, y + dy, z + 0.5 + dz];
        quad(g, [p(a[0], a[1], 0), p(b[0], b[1], 0), p(b[0], b[1], h), p(a[0], a[1], h)], [[0, 0], [1, 0], [1, h], [0, h]], 0.9, tintOf(n));
      }
      continue;
    }
    if (kd === "flat") {
      const path = n === "snow" ? "block/snow" : tex(n, "py");
      if (!path) continue;
      const g = group(path, tintOf(n), "cross"), h = 0.04;
      quad(g, [[x, y + h, z + 1], [x + 1, y + h, z + 1], [x + 1, y + h, z], [x, y + h, z]], [[0, 0], [1, 0], [1, 1], [0, 1]], 1, tintOf(n));
      continue;
    }
    // cubes, slabs and liquids
    const top = s.endsWith(":top"), y0 = kd === "slab" && top ? 0.5 : 0;
    let y1 = kd === "slab" && !top ? 0.5 : 1;
    if (kd === "liquid" && name(at.get(key(x, y + 1, z))) !== n) y1 = 0.875;
    const mode = kd === "liquid" ? "liquid" : SEE_THROUGH.test(n) ? "cutout" : "solid";
    for (const [side, f] of Object.entries(FACES)) {
      const nb = at.get(key(x + f.n[0], y + f.n[1], z + f.n[2]));
      if (opaque(nb) || (nb && name(nb) === n && kd !== "slab" && (mode !== "cutout" || !n.includes("leaves")))) continue;
      const path = tex(n, side);
      if (!path) continue;
      const corners = f.c.map(([cx, cy, cz]) => [x + cx, y + (cy ? y1 : y0), z + cz]);
      const uvs = side === "py" || side === "ny" ? [[0, 0], [1, 0], [1, 1], [0, 1]]
        : [[0, y0], [1, y0], [1, y1], [0, y1]];
      quad(group(path, tintOf(n, side), mode), corners, uvs, SHADE[side], tintOf(n, side));
    }
  }

  // the ground around it: top faces, and sides where the land drops (as far as you can see from the air)
  const full = [[0, 0], [1, 0], [1, 1], [0, 1]];
  for (let j = 0; j < D; j++) for (let i = 0; i < W; i++) {
    const h = world.h[j * W + i], x = ox + i, z = oz + j;
    if (h == null || inPatch(x, z)) continue;
    const top = name(world.palette[world.t[j * W + i]]), under = name(world.palette[world.u[j * W + i]]);
    // seen from above, leaves and water are simply the surface (like the game's "fast" graphics)
    const mode = n => (n.includes("leaves") ? "opaque" : "solid");
    const topTex = tex(top, "py");
    if (topTex) quad(group(topTex, tintOf(top, "py"), mode(top)), FACES.py.c.map(([cx, , cz]) => [x + cx, h + 1, z + cz]), full, 1, tintOf(top, "py"));
    for (const side of ["px", "nx", "pz", "nz"]) {
      const f = FACES[side], n = heightAt(x + f.n[0], z + f.n[2]);
      for (let y = Math.max(n == null ? h - 3 : n + 1, h - 24); y <= h; y++) {
        const blk = y === h || !tex(under, side) ? top : under, path = tex(blk, side);
        if (!path) continue;
        quad(group(path, tintOf(blk, side), mode(blk)), f.c.map(([cx, cy, cz]) => [x + cx, y + cy, z + cz]), full, SHADE[side], tintOf(blk, side));
      }
    }
  }

  // the land around it up to the horizon: one column for every step×step blocks
  const far = world.far;
  if (far) {
    const { step: k, size: [FW, FD], origin: [fx, fz] } = far;
    const fh = (i, j) => (i < 0 || j < 0 || i >= FW || j >= FD ? undefined : far.h[j * FW + i]);
    const below = n => (/grass_block|dirt|podzol|mycelium/.test(n) ? "dirt" : n);
    for (let j = 0; j < FD; j++) for (let i = 0; i < FW; i++) {
      const h = fh(i, j);
      if (h == null) continue;
      const top = name(world.palette[far.t[j * FW + i]]), x = fx + i * k, z = fz + j * k, m = top.includes("leaves") ? "opaque" : "solid";
      const tt = tex(top, "py");
      if (tt) quad(group(tt, tintOf(top, "py"), m), FACES.py.c.map(([cx, , cz]) => [x + cx * k, h + 1, z + cz * k]), [[0, 0], [k, 0], [k, k], [0, k]], 1, tintOf(top, "py"));
      for (const side of ["px", "nx", "pz", "nz"]) {
        const f = FACES[side], n = fh(i + f.n[0], j + f.n[2]);
        if (n === null) continue;  // next to the detailed middle: that draws its own sides
        const lo = Math.max(n === undefined ? h - 6 : n + 1, h - 40);
        if (lo > h) continue;
        // the top block's side, and below it the ground it stands on
        const parts = [[h, h + 1, top], [lo, h, below(top)]];
        for (const [y0, y1, blk] of parts) {
          const path = y1 > y0 && tex(blk, side);
          if (!path) continue;
          quad(group(path, tintOf(blk, side), m), f.c.map(([cx, cy, cz]) => [x + cx * k, cy ? y1 : y0, z + cz * k]),
            [[0, 0], [k, 0], [k, y1 - y0], [0, y1 - y0]], SHADE[side], tintOf(blk, side));
        }
      }
    }
  }

  for (const g of Object.values(groups)) {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(g.pos, 3));
    geo.setAttribute("uv", new THREE.Float32BufferAttribute(g.uv, 2));
    geo.setAttribute("color", new THREE.Float32BufferAttribute(g.col, 3));
    geo.setIndex(g.idx);
    const mat = new THREE.MeshBasicMaterial({
      map: texture(g.path), vertexColors: true,
      side: g.mode === "cross" ? THREE.DoubleSide : THREE.FrontSide,
      alphaTest: g.mode === "cutout" || g.mode === "cross" ? 0.5 : 0,
      transparent: g.mode === "liquid" || g.path.includes("portal"), opacity: g.mode === "liquid" ? 0.78 : g.path.includes("portal") ? 0.8 : 1,
      depthWrite: g.mode !== "liquid",
    });
    mat.userData.glow = GLOW.test(g.path);
    solidMats.push(mat);
    scene.add(new THREE.Mesh(geo, mat));
  }
}

/* ---------- the players ---------- */
// a box with the UV layout of a skin: (u, v) is the top left of the box in the 64×64 skin
function skinBox(w, h, d, u, v, grow = 0) {
  const r = [ // face -> pixel rect [x, y, w, h] in the skin
    ["px", [u + d + w, v + d, d, h]], ["nx", [u, v + d, d, h]], ["pz", [u + d, v + d, w, h]],
    ["nz", [u + 2 * d + w, v + d, w, h]], ["py", [u + d, v, w, d]], ["ny", [u + d + w, v, w, d]],
  ];
  const pos = [], uv = [], idx = [];
  for (const [side, [rx, ry, rw, rh]] of r) {
    const n = pos.length / 3;
    for (const [cx, cy, cz] of FACES[side].c)
      pos.push((cx - 0.5) * (w + grow), cy * (h + grow) - grow / 2, (cz - 0.5) * (d + grow));
    uv.push(rx / 64, (ry + rh) / 64, (rx + rw) / 64, (ry + rh) / 64, (rx + rw) / 64, ry / 64, rx / 64, ry / 64);
    idx.push(n, n + 1, n + 2, n, n + 2, n + 3);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  return g;
}

const FIGURE = 2.6;

/** A name tag that keeps the same size on screen, however far away it is. */
function nameTag(p) {
  const c = document.createElement("canvas"), x = c.getContext("2d"), font = '28px "VT323", monospace';
  x.font = font;
  const w = Math.ceil(x.measureText(p).width) + 16;
  c.width = w; c.height = 36;
  x.font = font; x.fillStyle = "rgba(0,0,0,.45)"; x.fillRect(0, 0, w, 36);
  x.fillStyle = color(p); x.textBaseline = "middle"; x.fillText(p, 8, 19);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, fog: false, depthTest: false, sizeAttenuation: false }));
  s.scale.set(w / 36 * 0.05, 0.05, 1);
  s.renderOrder = 10;
  return s;
}

async function makePlayer(p) {
  const { canvas: skin } = await composeSkin(p);
  const map = new THREE.CanvasTexture(skin);
  map.magFilter = THREE.NearestFilter; map.minFilter = THREE.NearestFilter; map.flipY = false;
  map.colorSpace = THREE.SRGBColorSpace;
  const mat = new THREE.MeshBasicMaterial({ map, alphaTest: 0.5, side: THREE.DoubleSide });
  solidMats.push(mat);
  const slim = S.data.skins?.[p]?.model === "slim", aw = slim ? 3 : 4;
  const root = new THREE.Group(), parts = {};
  const part = (name, [w, h, d, u, v, ou, ov], at, hang = true) => {
    const pivot = new THREE.Group();
    pivot.position.set(...at);
    for (const [uu, vv, grow] of [[u, v, 0], [ou, ov, name === "head" ? 1 : 0.5]]) {
      const m = new THREE.Mesh(skinBox(w, h, d, uu, vv, grow), mat);
      if (hang) m.position.y = -h;
      pivot.add(m);
    }
    root.add(pivot);
    parts[name] = pivot;
  };
  part("head", [8, 8, 8, 0, 0, 32, 0], [0, 24, 0], false);
  part("body", [8, 12, 4, 16, 16, 16, 32], [0, 24, 0]);
  part("rarm", [aw, 12, 4, 40, 16, 40, 32], [-4 - aw / 2, 24, 0]);
  part("larm", [aw, 12, 4, 32, 48, 48, 48], [4 + aw / 2, 24, 0]);
  part("rleg", [4, 12, 4, 0, 16, 0, 32], [-2, 12, 0]);
  part("lleg", [4, 12, 4, 16, 48, 0, 48], [2, 12, 0]);
  root.scale.setScalar(FIGURE / 16);  // bigger than life, or you couldn't see them from up here
  const tag = nameTag(p);
  tag.position.y = 40;
  tag.scale.multiplyScalar(16 / FIGURE);  // undo the figure's scale: the tag keeps its size on screen
  root.add(tag);
  scene.add(root);
  return { root, parts, mat, map, phase: Math.random() * 14 };
}

// online players inside the picture: where they really are now (the server sends it every few seconds)
async function syncPlayers() {
  const live = S.data.live3d || {};
  for (const [p, pl] of players) {
    if (live[p]) continue;
    players.delete(p);
    if (pl.root) { scene.remove(pl.root); pl.map.dispose(); pl.mat.dispose(); }
  }
  for (const [p, pos] of Object.entries(live)) {
    if (players.has(p)) { players.get(p).goal = pos; continue; }
    players.set(p, { goal: pos });  // reserved while the skin loads
    const pl = await makePlayer(p).catch(() => null);
    if (!players.has(p) || !pl) continue;
    const goal = players.get(p).goal;
    pl.root.position.set(goal[0], goal[1], goal[2]);
    pl.root.rotation.y = -goal[3] * Math.PI / 180;
    pl.mat.color.setScalar(light);
    players.set(p, { ...pl, goal });
  }
}

// between updates players walk smoothly to where they are now; standing still they look around
function animate(pl, dt, t) {
  const pos = pl.root.position, [gx, gy, gz, yaw] = pl.goal, p = pl.parts;
  const dx = gx - pos.x, dz = gz - pos.z, dist = Math.hypot(dx, dz);
  if (dist > 40) pos.set(gx, gy, gz);  // teleported or flew far: jump there
  const speed = Math.min(dist, Math.max(4.3, dist / 5) * dt);  // about walking speed, faster when far behind
  const moving = dist > 0.15;
  if (moving) { pos.x += (dx / dist) * speed; pos.z += (dz / dist) * speed; }
  pos.y += (gy - pos.y) * Math.min(1, dt * 4);
  let want = moving ? Math.atan2(dx, dz) : -yaw * Math.PI / 180, turn = want - pl.root.rotation.y;
  pl.root.rotation.y += Math.atan2(Math.sin(turn), Math.cos(turn)) * Math.min(1, dt * 6);
  pl.step = (pl.step || 0) + (moving ? dt * 9 : 0);
  const swing = moving ? Math.sin(pl.step) * 0.8 : 0, k = t + pl.phase;
  p.rarm.rotation.x = swing; p.larm.rotation.x = -swing; p.rleg.rotation.x = -swing; p.lleg.rotation.x = swing;
  p.head.rotation.y = moving ? 0 : Math.sin(k * 0.35) * 0.5;
  p.rarm.rotation.z = -0.05 - Math.sin(k * 1.3) * 0.03; p.larm.rotation.z = 0.05 + Math.sin(k * 1.3) * 0.03;
}

/* ---------- camera and loop ---------- */
function resize() {
  const r = canvas.parentElement.getBoundingClientRect();
  renderer.setSize(r.width, r.height, false);
  camera.aspect = r.width / Math.max(1, r.height);
  camera.fov = camera.aspect < 1 ? 70 : 55;
  camera.updateProjectionMatrix();
  if (still || !running) draw(performance.now());
}

function wake() {
  if (!renderer) return;  // BlueMap has its own loop
  const should = visible && !document.hidden && !still;
  if (should && !running) { running = true; last = 0; frame = requestAnimationFrame(loop); }
  if (!should) { running = false; cancelAnimationFrame(frame); }
}

function loop(now) {
  if (!running) return;
  frame = requestAnimationFrame(loop);
  if (now - drawn < 45) return;  // ~20 frames per second is plenty for a slow camera and saves battery
  drawn = now;
  draw(now);
}

/** Turns BlueMap's camera slowly around the valley, at one height, and keeps the blocks in front loaded. */
function turn(dt) {
  const viewer = bluemap.mapViewer, cm = viewer.controlsManager, c = bluemap.center;
  if (!still) cm.rotation += dt * (Math.PI * 2 / 240);  // one round in four minutes
  // BlueMap lets the camera follow the ground under it, which bobs up and down while turning:
  // keep one height instead (checked every frame, BlueMap sets up its controls late)
  const height = cm._controls?.mapHeight;
  if (height && !height.fixed) { height.fixed = true; height.update = () => { cm.position.y = c.y; }; }
  // aim a bit past the middle, so the homes sit in the lower half of the banner, under the title
  const fx = Math.sin(cm.rotation), fz = -Math.cos(cm.rotation), k = c.distance * 0.3;
  cm.position.x = c.x + fx * k;
  cm.position.z = c.z + fz * k;
  const lx = cm.position.x + fx * bluemap.ahead, lz = cm.position.z + fz * bluemap.ahead;
  if (bluemap.ahead_x === undefined || Math.hypot(lx - bluemap.ahead_x, lz - bluemap.ahead_z) > 32) {  // a row of tiles every few seconds
    bluemap.ahead_x = lx; bluemap.ahead_z = lz;
    viewer.loadMapArea();
  }
}

function draw(now) {
  const dt = Math.min(0.1, (now - (last || now)) / 1000); last = now;
  if (!still) angle += dt * (Math.PI * 2 / 240);  // one round in four minutes
  // from the air: circling the valley, looking down at the homes in the middle
  const r = size * 1.05;
  camera.position.set(Math.sin(angle) * r, middle + size * 0.75, Math.cos(angle) * r);
  camera.lookAt(0, middle + size * 0.12, 0);
  const t = now / 1000;
  for (const pl of players.values()) if (pl.root) animate(pl, still ? 1 : dt, t);
  renderer.render(scene, camera);
}
