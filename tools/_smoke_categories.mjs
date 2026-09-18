/* 冒烟测试：items.html 分类导航 + 详情/缩略视图切换
   用无头 Chromium + CDP 驱动本地文件，断言核心交互。 */
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME = "C:/Users/87088/AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe";
const URL = "file:///E:/GameProject/stoneshard-wiki/site/items.html";
const PORT = 9341;
let pass = 0, fail = 0;
function check(name, ok, extra){
  console.log((ok ? "PASS" : "FAIL") + "  " + name + (ok ? "" : "  <- " + extra));
  ok ? pass++ : fail++;
}

const profile = mkdtempSync(join(tmpdir(), "ssw-cat-"));
const sleep = ms => new Promise(r => setTimeout(r, ms));
const chrome = spawn(CHROME, ["--headless=new","--disable-gpu","--no-first-run","--no-default-browser-check",
  "--window-size=1400,900", `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, URL], { stdio: "ignore" });

let ws, seq = 0; const pending = new Map();
const send = (method, params = {}) => new Promise((res, rej) => {
  const id = ++seq; pending.set(id, { res, rej });
  ws.send(JSON.stringify({ id, method, params }));
});
const evaluate = async e => {
  const r = await send("Runtime.evaluate", { expression: e, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || "eval error");
  return r.result.value;
};

for (let i = 0; i < 50; i++){
  try {
    const list = await fetch(`http://127.0.0.1:${PORT}/json/list`).then(r => r.json());
    const page = list.find(p => p.type === "page");
    if (page){
      ws = new WebSocket(page.webSocketDebuggerUrl);
      await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
      ws.onmessage = ev => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)){ pending.get(m.id).res(m.result); pending.delete(m.id); } };
      break;
    }
  } catch (e){}
  await sleep(200);
}
await sleep(800);

/* 1. 一级导航存在且计数正确 */
const nav1 = await evaluate(`[...document.querySelectorAll("#nav1 .chip")].map(b => b.dataset.c + ":" + b.textContent.trim())`);
check("nav1 rendered with counts", nav1.length === 9 && nav1.some(s => s.startsWith("weapon:")), nav1.join(" | "));
const totalCount = await evaluate(`+document.querySelector('#nav1 .chip[data-c="all"] .cnt').textContent`);
check("nav1 total count == DATA length", totalCount === await evaluate(`DATA.length`), totalCount + " vs " + await evaluate(`DATA.length`));

/* 2. 分类过滤：武器 */
await evaluate(`document.querySelector('#nav1 .chip[data-c="weapon"]').click()`);
await sleep(100);
const w = await evaluate(`({shown: document.querySelectorAll("#grid .card").length, count: document.getElementById("count").textContent})`);
check("weapon filter shows cards", w.shown > 0 && /武器|分类/.test(w.count) === false, JSON.stringify(w));

/* 3. 二级导航出现且有细分 */
const nav2 = await evaluate(`[...document.querySelectorAll("#nav2:not([hidden]) .chip")].map(b => b.dataset.s + ":" + b.textContent.trim())`);
check("nav2 subs for weapon", nav2.length > 3 && nav2.some(s => s.startsWith(":")), nav2.join(" | ").slice(0, 120));
/* 点一个细分 */
const subName = await evaluate(`document.querySelector('#nav2 .chip[data-s]:not([data-s=""])').dataset.s`);
await evaluate(`[...document.querySelectorAll('#nav2 .chip')].find(b => b.dataset.s === ${JSON.stringify(subName)}).click()`);
await sleep(100);
const tagOk = await evaluate(`[...document.querySelectorAll("#grid .card .tag:not(.ttag)")].every(t => t.textContent.includes(${JSON.stringify(subName)}))`);
check("cards tagged with sub category", tagOk, subName);

/* 4. 食物页签下有 药水/酒水 细分 */
await evaluate(`document.querySelector('#nav1 .chip[data-c="food"]').click()`);
await sleep(100);
const foodSubs = await evaluate(`[...document.querySelectorAll("#nav2:not([hidden]) .chip")].map(b => b.dataset.s).filter(Boolean)`);
check("food has 药水/酒水 subs", foodSubs.includes("药水") && foodSubs.includes("酒水"), foodSubs.join(","));

/* 5. 视图切换：详情卡片带数值块，缩略不带 */
await evaluate(`document.querySelector('#nav1 .chip[data-c="all"]').click()`);
await evaluate(`setView("detail")`);
await sleep(100);
const dState = await evaluate(`({detail: document.getElementById("grid").classList.contains("detail"), stats: document.querySelectorAll("#grid .card .stats").length, cards: document.querySelectorAll("#grid .card").length})`);
check("detail view active + stats blocks", dState.detail && dState.stats > 0, JSON.stringify(dState));
check("view persisted", await evaluate(`localStorage.getItem("ssw_itemview")`) === "detail", "localStorage");
await evaluate(`setView("thumb")`);
await sleep(100);
const tState = await evaluate(`({detail: document.getElementById("grid").classList.contains("detail"), stats: document.querySelectorAll("#grid .card .stats").length})`);
check("thumb view: no stats blocks", !tState.detail && tState.stats === 0, JSON.stringify(tState));

/* 6. 详情视图内容与弹窗一致（抽一件有数值的物品对比） */
await evaluate(`setView("detail")`);
await evaluate(`(function(){ const c = [...document.querySelectorAll("#grid .card")].find(x => x.querySelector(".stats")); if (c) c.click(); })()`);
await sleep(200);
const cmp = await evaluate(`(function(){
  const dlg = document.getElementById("dlgbody").innerHTML;
  document.getElementById("dlgx").click();
  return { open: document.getElementById("dlg").open, len: dlg.length };
})()`);
check("dialog opens from detail card", cmp.open === false && cmp.len > 100, JSON.stringify(cmp));

/* 7. 搜索 + 分类组合 */
await evaluate(`setView("thumb")`);
await evaluate(`document.querySelector('#nav1 .chip[data-c="weapon"]').click()`);
await evaluate(`(function(){ const q = document.getElementById("q"); q.value = "剑"; q.dispatchEvent(new Event("input")); })()`);
await sleep(100);
const combo = await evaluate(`document.querySelectorAll("#grid .card").length`);
check("search + category combo", combo > 0, "cards=" + combo);

/* 8. 等级过滤：武器下点 Ⅴ 级 */
const tCounts = await evaluate(`[...document.querySelectorAll("#nav3 .chip")].map(b => b.dataset.tv + ":" + b.querySelector(".cnt").textContent)`);
check("nav3 rendered with counts", tCounts.length === 7 && tCounts.some(s => s.startsWith("-1:")), tCounts.join(" | "));
await evaluate(`[...document.querySelectorAll('#nav3 .chip')].find(b => b.dataset.tv === "5").click()`);
await sleep(100);
const t5 = await evaluate(`({badges: [...document.querySelectorAll("#grid .card .ttag")].map(b => b.textContent), n: document.querySelectorAll("#grid .card").length})`);
check("tier 5 filter: all cards badge Ⅴ", t5.n > 0 && t5.badges.length === t5.n && t5.badges.every(b => b === "五"), JSON.stringify(t5).slice(0, 120));

/* 9. 等级过滤与细分组合：武器 + Ⅰ 级 */
await evaluate(`[...document.querySelectorAll('#nav3 .chip')].find(b => b.dataset.tv === "1").click()`);
await sleep(100);
const t1sub = await evaluate(`(function(){
  const n = document.querySelectorAll("#grid .card").length;
  const badges = [...document.querySelectorAll("#grid .card .ttag")].map(b => b.textContent);
  return { n, ok: badges.length === n && badges.every(b => b === "一") };
})()`);
check("tier 1 filter within weapon", t1sub.n > 0 && t1sub.ok, JSON.stringify(t1sub));

/* 10. 切换一级分类后等级过滤复位 */
await evaluate(`document.querySelector('#nav1 .chip[data-c="food"]').click()`);
await sleep(100);
const reset = await evaluate(`document.querySelector('#nav3 .chip[data-tv="-1"]').classList.contains("on")`);
check("tier filter reset on category change", reset, "");

/* 11. 「无等级」过滤 */
await evaluate(`[...document.querySelectorAll('#nav3 .chip')].find(b => b.dataset.tv === "0").click()`);
await sleep(100);
const noTier = await evaluate(`document.querySelectorAll("#grid .card .ttag").length`);
check("no-tier filter hides badges", noTier === 0, "badges=" + noTier);

try { chrome.kill(); rmSync(profile, { recursive: true, force: true }); } catch(e){}
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
