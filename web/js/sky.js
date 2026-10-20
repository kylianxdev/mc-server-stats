// The sky in the header, drawn with the game's own textures: clouds.png, the sun, the moon phase
// of the current day, and rain.png falling in columns like the game renders rain.
const MOONS = ["full_moon", "waning_gibbous", "third_quarter", "waning_crescent", "new_moon", "waxing_crescent", "first_quarter", "waxing_gibbous"];
const RAIN_TEX = "/assets/environment/rain.png";

let rainImg = null, canvas = null, ctx = null, columns = [], raining = false, last = 0, frame = 0;

function loadRain() {
  if (rainImg) return;
  rainImg = new Image();
  rainImg.src = RAIN_TEX;
}

// every column: which strip of rain.png, how fast and how far away (two layers like in the game)
function makeColumns(width, height) {
  columns = [];
  for (const layer of [{ scale: 2, speed: [380, 520], alpha: [0.35, 0.5] }, { scale: 3, speed: [560, 760], alpha: [0.55, 0.8] }]) {
    const w = 16 * layer.scale;
    for (let x = -w; x < width + w; x += w * (0.55 + Math.random() * 0.7)) {
      columns.push({
        x: Math.round(x), scale: layer.scale, u: 16 * Math.floor(Math.random() * 4),
        speed: layer.speed[0] + Math.random() * (layer.speed[1] - layer.speed[0]),
        alpha: layer.alpha[0] + Math.random() * (layer.alpha[1] - layer.alpha[0]),
        y: Math.random() * 256 * layer.scale,
      });
    }
  }
  columns.sort((a, b) => a.scale - b.scale);
}

function resize() {
  const r = canvas.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  canvas.width = Math.round(r.width * dpr); canvas.height = Math.round(r.height * dpr);
  ctx = canvas.getContext("2d"); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.imageSmoothingEnabled = false;
  makeColumns(r.width, r.height);
}

function draw(now) {
  if (!raining) { frame = 0; return; }
  frame = requestAnimationFrame(draw);
  const dt = Math.min(0.05, (now - (last || now)) / 1000); last = now;
  const { width, height } = canvas.getBoundingClientRect();
  ctx.clearRect(0, 0, width, height);
  if (!rainImg.complete || !rainImg.naturalWidth) return;
  for (const c of columns) {
    const tile = 256 * c.scale, w = 16 * c.scale;
    c.y = (c.y + c.speed * dt) % tile;  // endless: the texture just keeps scrolling
    ctx.globalAlpha = c.alpha;
    for (let y = c.y - tile; y < height; y += tile) ctx.drawImage(rainImg, c.u, 0, 16, 256, c.x, Math.round(y), w, tile);
  }
  ctx.globalAlpha = 1;
}

/** Update the sky for the world state ({time_of_day, day, raining, thundering}). */
export function updateSky(world = {}) {
  const hero = document.querySelector(".hero");
  const tod = world.time_of_day;
  const sky = tod == null ? "night" : tod < 12000 ? "day" : tod < 13800 ? "dusk" : tod < 22300 ? "night" : "dawn";
  hero.dataset.sky = sky;
  hero.classList.toggle("rain", !!world.raining);
  hero.classList.toggle("thunder", !!world.thundering);

  const moon = document.getElementById("moon");
  const phase = MOONS[((world.day || 1) - 1) % 8];
  if (moon && moon.dataset.phase !== phase) {
    moon.dataset.phase = phase;
    moon.src = `/assets/environment/celestial/moon/${phase}.png`;
  }

  canvas ??= document.getElementById("rain");
  const wasRaining = raining;
  raining = !!world.raining && !matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (raining && !wasRaining) {
    loadRain(); resize(); last = 0;
    if (!frame) frame = requestAnimationFrame(draw);
  }
  if (!raining && ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
}

addEventListener("resize", () => { if (raining) resize(); });
