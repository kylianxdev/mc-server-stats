// The header as a real Minecraft world, like the title screen: the blocks around the world spawn
// (read from the region files by the server), a camera slowly turning around, the online players
// hanging around at spawn, and the light following the time of day and the weather.
//
// three.js is only loaded after the page itself is drawn; without WebGL the flat header stays.
import { S } from "./state.js";
import { color } from "./util.js";
import { composeSkin } from "./skins.js";

let THREE = null, renderer = null, scene = null, camera = null, canvas = null;
let solidMats = [], center = { y: 0 }, size = 24, surface = {}, walkable = [], players = new Map();
let running = false, visible = true, frame = 0, last = 0, angle = 0, camY = null, light = 1, drawn = 0;
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
    [THREE, world] = await Promise.all([import("/assets/js/three.module.min.js"), fetch("/api/world3d").then(r => r.json())]);
    if (!world.blocks?.length) throw new Error("no blocks");
    renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: false, powerPreference: "low-power" });
  } catch (e) {
    canvas = null;  // keep the flat header
    return;
  }
  renderer.setPixelRatio(1);  // pixel art: a sharper picture adds nothing but work
  renderer.setClearColor(0x000000, 0);
  scene = new THREE.Scene();
  scene.fog = new THREE.Fog(SKY.night[0], 14, 30);
  camera = new THREE.PerspectiveCamera(55, 2, 0.1, 200);

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

/** Called on every live update: light, fog and the online players. */
export function updateWorld3d() {
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
  const b = world.blocks;  // flat: x, y, z, palette index, x, y, …
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

  surface = world.surface || {};
  center.y = surface["0,0"] ?? 0;
  // how far the world goes: the camera circles at a fitting distance and the fog hides the edges
  size = Math.max(8, ...Object.keys(surface).map(k => Math.max(...k.split(",").map(v => Math.abs(+v)))));
  scene.fog.near = size * 0.4; scene.fog.far = size * 1.05;
  // where players may stand: the top of the column is a normal block, near the spawn height
  walkable = Object.entries(surface).map(([k, y]) => [...k.split(",").map(Number), y])
    .filter(([x, z, y]) => Math.hypot(x, z) > 4 && Math.hypot(x, z) < 9 && kind(at.get(key(x, y, z))) !== "liquid"
      && !/leaves|log/.test(at.get(key(x, y, z)) || ""));

  const groups = {};  // texture|tint|mode -> arrays
  const group = (path, tint, mode) => {
    const k = `${path}|${tint}|${mode}`;
    return (groups[k] ??= { path, tint, mode, pos: [], uv: [], col: [], idx: [] });
  };
  const quad = (g, corners, uvs, shade, tint) => {
    const c = new THREE.Color(tint ?? 0xffffff).multiplyScalar(shade), n = g.pos.length / 3;
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

function nameTag(p) {
  const c = document.createElement("canvas"), x = c.getContext("2d"), font = '28px "VT323", monospace';
  x.font = font;
  const w = Math.ceil(x.measureText(p).width) + 16;
  c.width = w; c.height = 36;
  x.font = font; x.fillStyle = "rgba(0,0,0,.45)"; x.fillRect(0, 0, w, 36);
  x.fillStyle = color(p); x.textBaseline = "middle"; x.fillText(p, 8, 19);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, fog: false, depthTest: false }));
  s.scale.set(w / 36 * 0.5, 0.5, 1);
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
  root.scale.setScalar(0.9 / 16);
  const tag = nameTag(p);
  tag.position.y = 38;
  tag.scale.multiplyScalar(16 / 0.9);
  root.add(tag);
  // everyone on their own spot near spawn, facing more or less towards the middle
  const taken = [...players.values()].filter(q => q.root).map(q => q.root.position);
  const free = walkable.filter(([x, z]) => taken.every(q => Math.hypot(q.x - x - 0.5, q.z - z - 0.5) > 1.5));
  const spot = free[Math.floor(Math.random() * free.length)] || [2, 2, center.y];
  root.position.set(spot[0] + 0.5, spot[2] + 1, spot[1] + 0.5);
  root.rotation.y = Math.atan2(-spot[0], -spot[1]) + (Math.random() - 0.5);
  scene.add(root);
  return { root, parts, mat, map, phase: Math.random() * 14 };
}

async function syncPlayers() {
  const online = Object.entries(S.data.profiles || {}).filter(([, v]) => v.online).map(([p]) => p).slice(0, 8);
  for (const [p, pl] of players) {
    if (online.includes(p)) continue;
    players.delete(p);
    if (pl.root) { scene.remove(pl.root); pl.map.dispose(); pl.mat.dispose(); }
  }
  for (const p of online) {
    if (players.has(p)) continue;
    players.set(p, {});  // reserved while the skin loads
    const pl = await makePlayer(p).catch(() => null);
    if (players.has(p) && pl) { players.set(p, pl); pl.mat.color.setScalar(light); }
  }
}

const heightAt = (x, z) => surface[`${Math.floor(x)},${Math.floor(z)}`];

// players just hang around at spawn: looking around, breathing, now and then a wave
function idle(pl, t) {
  const p = pl.parts, k = t + pl.phase;
  p.head.rotation.y = Math.sin(k * 0.35) * 0.6;
  p.head.rotation.x = Math.sin(k * 0.23) * 0.12;
  const wave = k % 14 < 1.6 ? Math.sin((k % 14) / 1.6 * Math.PI) : 0;  // every 14 seconds or so
  p.rarm.rotation.x = -2.6 * wave;
  p.rarm.rotation.z = -0.05 - Math.sin(k * 1.3) * 0.03 - 0.3 * wave * (1 + Math.sin(k * 14) * 0.5);
  p.larm.rotation.z = 0.05 + Math.sin(k * 1.3) * 0.03;
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

function draw(now) {
  const dt = Math.min(0.1, (now - (last || now)) / 1000); last = now;
  if (!still) angle += dt * (Math.PI * 2 / 150);  // one round in two and a half minutes
  // like the title screen: standing on the spawn, slowly turning around, looking a bit down over the land
  let ground = center.y;
  for (let dx = -1; dx <= 1; dx++) for (let dz = -1; dz <= 1; dz++) ground = Math.max(ground, heightAt(dx + 0.5, dz + 0.5) ?? -1e9);
  const want = ground + 3.2;
  camY = camY == null ? want : camY + (want - camY) * Math.min(1, dt * 0.8);
  camera.position.set(0.5, camY, 0.5);
  const pitch = -0.22;
  camera.lookAt(0.5 + Math.sin(angle) * Math.cos(pitch), camY + Math.sin(pitch), 0.5 + Math.cos(angle) * Math.cos(pitch));
  const t = now / 1000;
  for (const pl of players.values()) if (pl.root) idle(pl, t);
  renderer.render(scene, camera);
}
