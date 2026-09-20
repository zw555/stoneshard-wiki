/* 冒烟测试：caravan.html 马车营地 */
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME = "C:/Users/87088/AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe";
const URL = "file:///E:/GameProject/stoneshard-wiki/site/caravan.html";
const PORT = 9355;
let pass = 0, fail = 0;
const check = (name, ok, extra) => { console.log((ok ? "PASS" : "FAIL") + "  " + name + (ok ? "" : "  <- " + extra)); ok ? pass++ : fail++; };

const profile = mkdtempSync(join(tmpdir(), "ssw-caravan-"));
const chrome = spawn(CHROME, ["--headless=new","--disable-gpu","--no-first-run","--no-default-browser-check",
  "--window-size=1400,1400", `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, URL], { stdio: "ignore" });

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
  } catch {}
  await new Promise(r => setTimeout(r, 200));
}
await new Promise(r => setTimeout(r, 1200));

/* 1. 默认视图 */
const t0 = await evaluate(`(() => ({
  tabs: document.querySelectorAll(".tab").length,
  stat: document.getElementById("st-mats").textContent,
  crown: document.getElementById("st-crown").textContent,
  verren: document.getElementById("st-verren").textContent,
  nodes: document.querySelectorAll(".node").length,
  on: document.querySelector(".view.on").dataset.v
}))()`);
check("6 tabs", t0.tabs === 6, t0.tabs);
check("stat 材料数 > 50", +t0.stat > 50, t0.stat);
check("估算金币显示", /^[0-9,]+$/.test(t0.crown), t0.crown);
check("维伦 7000", t0.verren === "7,000 金币", t0.verren);
check("首视图=伙食分支", t0.on === "b:Cooking", t0.on);
const t0v = await evaluate(`document.querySelectorAll(".view.on .node").length`);
check("伙食 7 卡片", t0v === 7, t0v);

/* 2. 卡片内容 */
const c = await evaluate(`(() => {
  const wb = document.getElementById("node-Workbench");
  return {
    hasEff: !!wb.querySelector(".eff"),
    matRows: wb.querySelectorAll(".mrow").length,
    preChips: wb.querySelectorAll(".pre .chip").length,
    basicBadge: !!document.getElementById("node-Firepit").querySelector(".badge.basic"),
    imgs: [...document.querySelectorAll(".node img")].filter(i => i.naturalWidth > 0).length
  };
})()`);
check("工作台材料行=2", c.matRows === 2, c.matRows);
check("工作台有前置芯片", c.preChips > 0, c.preChips);
check("火堆自动解锁徽章", c.basicBadge);
check("节点图标加载 > 20", c.imgs > 20, c.imgs);

/* 3. 点击材料展开途径 */
const rt = await evaluate(`(() => {
  const row = document.querySelector("#node-Workbench .mrow");
  row.click();
  const box = row.parentElement.querySelector(".routes");
  return { on: box.classList.contains("on"), lines: box.querySelectorAll("li").length, text: box.textContent.slice(0, 60) };
})()`);
check("点击展开途径", rt.on && rt.lines > 0, rt.text);

/* 4. 材料大全 */
const mv = await evaluate(`(() => {
  document.querySelector('.tab[data-k="mats"]').click();
  return { on: document.querySelector('.view.on').dataset.v,
    groups: document.querySelectorAll("#views .view[data-v='mats'] .tgroup").length,
    items: document.querySelectorAll("#views .view[data-v='mats'] .mitem").length,
    verren: [...document.querySelectorAll("#views .view[data-v='mats'] .routes li")].some(li => li.textContent.includes("维伦")) };
})()`);
check("材料视图切换", mv.on === "mats", mv.on);
check("类型分组 >= 6", mv.groups >= 6, mv.groups);
check("材料条目 >= 50", mv.items >= 50, mv.items);
check("维伦途径可查", mv.verren);

/* 5. 累计清单 */
const tv = await evaluate(`(() => {
  document.querySelector('.tab[data-k="totals"]').click();
  const rows = document.querySelectorAll("#views .view[data-v='totals'] tbody tr");
  const nails = [...rows].find(r => r.cells[0].textContent === "钉子");
  return { rows: rows.length, nailsQty: nails ? nails.cells[2].textContent : "",
    hoof: [...rows].find(r => r.cells[0].textContent === "马蹄铁")?.cells[2].textContent,
    foot: document.querySelector("#views .view[data-v='totals'] tfoot td:last-child").textContent };
})()`);
check("累计清单有行", tv.rows > 20, tv.rows);
check("钉子累计×20", tv.nailsQty === "×20", tv.nailsQty);
check("马蹄铁累计×8", tv.hoof === "×8", tv.hoof);
check("合计行非空", tv.foot.includes("G"), tv.foot);

/* 6. 神台变体 */
const v = await evaluate(`(() => {
  document.querySelector('.tab[data-k="b:Resting"]').click();
  const sh = document.getElementById("node-Shrine");
  return { found: !!sh, variants: sh ? sh.querySelectorAll(".variant").length : 0,
    first: sh ? sh.querySelector(".variant .rt")?.textContent : "" };
})()`);
check("神台 3 出身变体", v.found && v.variants === 3, JSON.stringify(v));

chrome.kill(); rmSync(profile, { recursive: true, force: true });
console.log("\n" + pass + " passed, " + fail + " failed");
process.exit(fail ? 1 : 0);
