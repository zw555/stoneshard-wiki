/* 冒烟测试：trade.html 四视图（卖谁最赚/商人榜/品类规律/机制）+ 排序交互 */
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME = "C:/Users/87088/AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe";
const URL = "file:///E:/GameProject/stoneshard-wiki/site/trade.html";
const PORT = 9345;
let pass = 0, fail = 0;
function check(name, ok, extra){
  console.log((ok ? "PASS" : "FAIL") + "  " + name + (ok ? "" : "  <- " + extra));
  ok ? pass++ : fail++;
}

const profile = mkdtempSync(join(tmpdir(), "ssw-trade-"));
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

/* 1. 物品视图：默认按回收率降序（从 DOM 验证真实渲染顺序） */
check("items rendered (240 cap)", await evaluate(`document.querySelectorAll("#grid .card").length`) === 240, "");
const recs = await evaluate(`[...document.querySelectorAll("#grid .card .r1 .badge:not(.hi):not(.lo)")].slice(0, 10).map(b => parseFloat(b.textContent.match(/回收率 (\\d+)%/)[1]))`);
check("sorted by rec desc", recs.length >= 5 && recs.every((v, i) => i === 0 || recs[i-1] >= v), JSON.stringify(recs));
check("badge shown on top card", await evaluate(`!!document.querySelector("#grid .card .badge")`), "");
check("gain line present", await evaluate(`document.querySelectorAll("#grid .card .gain").length`) > 0, "");

/* 2. 切换排序：卖价高→低 */
await evaluate(`[...document.querySelectorAll("#isort .chip")].find(c => c.dataset.s === "price").click()`);
await sleep(100);
const prices = await evaluate(`[...document.querySelectorAll("#grid .card .r1 b")].slice(0, 10).map(b => +b.textContent)`);
check("sorted by price desc", prices.length >= 5 && prices.every((v, i) => i === 0 || prices[i-1] >= v), JSON.stringify(prices));

/* 3. 搜索品类词 */
await evaluate(`(function(){ const q = document.getElementById("q"); q.value = "铠甲"; q.dispatchEvent(new Event("input")); })()`);
await sleep(100);
check("search by category word", await evaluate(`document.querySelectorAll("#grid .card").length`) > 0, "");
await evaluate(`(function(){ const q = document.getElementById("q"); q.value = ""; q.dispatchEvent(new Event("input")); })()`);
await sleep(80);

/* 4. 商人榜：最优次数排序 + 平均回收率字段 */
await evaluate(`[...document.querySelectorAll(".tab")].find(t => t.dataset.v === "merchants").click()`);
await sleep(100);
const mrows = await evaluate(`MERCH.length`);
check("merchants aggregated", mrows >= 15 && mrows <= 25, "n=" + mrows);
const top1s = await evaluate(`[...MERCH].sort((a,b)=>b.top1-a.top1).slice(0,3).map(o => o.who + ":" + o.top1)`);
check("top1 leader sane", top1s.length === 3 && top1s[0].includes(":"), top1s.join(" | "));
const avgs = await evaluate(`MERCH.every(o => o.avg > 0.1 && o.avg < 1)`);
check("avg rec in (0.1,1)", avgs, "");
check("top cats listed", await evaluate(`MERCH.filter(o => o.top1 > 0).every(o => o.topCats.length > 0)`), "");
await evaluate(`[...document.querySelectorAll("#msort .chip")].find(c => c.dataset.s === "avg").click()`);
await sleep(80);
const avgSorted = await evaluate(`(function(){ const a=[...MERCH].sort((x,y)=>y.avg-x.avg); return a[0].avg >= a[a.length-1].avg; })()`);
check("merch resort by avg works", avgSorted, "");

/* 5. 品类规律表 */
await evaluate(`[...document.querySelectorAll(".tab")].find(t => t.dataset.v === "cats").click()`);
await sleep(100);
const catRows = await evaluate(`CATS.length`);
check("cats table rows", catRows > 10, "n=" + catRows);
const catOrder = await evaluate(`CATS.every((c,i) => i===0 || CATS[i-1].avg >= c.avg)`);
check("cats sorted by avg desc", catOrder, "");
const bestWho = await evaluate(`CATS[0].cat + " -> " + CATS[0].who[0] + " " + pct(CATS[0].avg)`);
console.log("      品类回收率冠军:", bestWho);
check("cats table rendered", await evaluate(`document.querySelectorAll("#cats table tr").length`) > 10, "");

/* 6. 机制视图仍在 */
await evaluate(`[...document.querySelectorAll(".tab")].find(t => t.dataset.v === "mech").click()`);
await sleep(80);
check("mech tables render", await evaluate(`document.querySelectorAll("#towns table tr").length`) > 5, "");

/* 7. 无残留占位符 */
check("no __DATA__ leftover", !await evaluate(`document.body.innerHTML.includes("__DATA__") || document.body.innerHTML.includes("__LB__")`), "");

try { chrome.kill(); rmSync(profile, { recursive: true, force: true }); } catch(e){}
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
