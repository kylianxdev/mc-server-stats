// Charts and small building blocks: playtime per day, hours of the day, KPI tiles, XP bar.
import { t } from "./i18n.js";
import { dur, fmtDate, tex, weekday } from "./util.js";

function lastDays(n) {
  const out = [], d = new Date(); d.setUTCHours(12, 0, 0, 0);
  for (let i = n - 1; i >= 0; i--) out.push(new Date(d.getTime() - i * 864e5).toISOString().slice(0, 10));
  return out;
}

/** Bar chart of the last 14 days; extra(day) adds lines to the tooltip. */
export function dayBars(perDay, extra) {
  const days = lastDays(14), vals = days.map(d => perDay[d] || 0), max = Math.max(...vals, 1);
  return `<div class="bars">${days.map((d, i) => {
      const v = vals[i], h = v ? Math.max(3, (100 * v) / max) : 0;
      const tip = `<b>${weekday(d)} ${fmtDate(d)}</b><br>${v ? t("chart.played", { d: dur(v) }) : t("chart.not_played")}${extra ? extra(d) : ""}`;
      return `<div class="b" data-tip="${tip}"><i style="height:${h}%"></i></div>`;
    }).join("")}</div>
    <div class="xlab">${days.map((d, i) => `<span>${i % 2 === 0 ? +d.slice(8) : ""}</span>`).join("")}</div>
    <div class="note">${t("chart.last14")}</div>`;
}

/** 24 cells (hour of day, one green hue: brighter = more), plus a few facts. */
export function hourStrip(perHour, perDay, sessions, longest) {
  const max = Math.max(...perHour, 1);
  const hh = h => `${String(h).padStart(2, "0")}:00`;
  const busiestDay = Object.entries(perDay || {}).sort((a, b) => b[1] - a[1])[0];
  const total = Object.values(perDay || {}).reduce((a, b) => a + b, 0);
  const cell = v => (v === 0 ? "#141414" : `rgba(128,255,32,${(0.12 + (0.88 * v) / max).toFixed(2)})`);
  const fact = (ic, label, value) => `<div class="fact"><div class="k">${tex(ic, "xs")} ${label}</div><div class="v">${value}</div></div>`;
  return `<div class="hours">${perHour.map((v, h) => `<div class="h" style="background:${cell(v)}" data-tip="<b>${hh(h)}–${hh(h + 1)}</b><br>${t("chart.in_total", { d: dur(v) })}"></div>`).join("")}</div>
    <div class="hours-lab">${perHour.map((_, h) => `<span>${h % 3 === 0 ? h : ""}</span>`).join("")}</div>
    <div class="note">${t("chart.hours_note")}</div>
    <div class="facts">
      ${fact("item/clock_00", t("fact.busiest_hour"), max > 1 ? hh(perHour.indexOf(Math.max(...perHour))) : "–")}
      ${fact("item/map", t("fact.busiest_day"), busiestDay ? `${weekday(busiestDay[0])} ${fmtDate(busiestDay[0])}` : "–")}
      ${fact("item/compass_00", t("fact.avg_session"), sessions ? dur(total / sessions) : "–")}
      ${fact("item/experience_bottle", t("fact.longest_session"), longest ? dur(longest) : "–")}
    </div>`;
}

export const kpi = (ic, label, value, sub = "") =>
  `<div class="panel kpi">${tex(ic)}<div class="k">${label}</div><div class="v">${value}</div>${sub ? `<div class="s">${sub}</div>` : ""}</div>`;

// the real experience bar from the game
export const xpBar = (frac, tip) =>
  `<div class="xp" data-tip="${tip}"><i style="clip-path: inset(0 ${(100 - 100 * Math.min(1, frac)).toFixed(1)}% 0 0)"></i></div>`;
