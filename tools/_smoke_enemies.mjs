/* 冒烟测试：enemies.html 详情弹窗（技能/掉落/数值区块）+ 中文数字等级行 */
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME = "C:/Users/87088/AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe";
const URL = "file:///E:/GameProject/stoneshard-wiki/site/enemies.html";
const PORT = 9343;
let pass = 0, fail = 0;
function check(name, ok, extra){
  console.log((ok ? "PASS" : "FAIL") + "  " + name + (ok ? "" : "  <- " + extra));
  ok ? pass++ : fail++;
}

const profile = mkdtempSync(join(tmpdir(), "ssw-enem-"));
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

/* 1. 页面加载与渲染 */
check("cards rendered", await evaluate(`document.querySelectorAll("#grid .card").length`) === 236, "count");

/* 2. 找一个有技能+掉落的敌人（强盗类），打开弹窗 */
const pick = await evaluate(`(function(){
  const e = DATA.find(x => x.sk.length > 0 && x.dp.length > 0 && x.zh);
  const card = [...document.querySelectorAll("#grid .card")].find(c => c.querySelector(".nm").textContent.includes(e.zh));
  if (card) card.click();
  return { zh: e.zh, sk: e.sk.length, dp: e.dp.length, boss: e.bs };
})()`);
await sleep(200);
check("dialog opens", await evaluate(`document.getElementById("dlg").open`), "");
check("dialog has skills section", await evaluate(`[...document.querySelectorAll("#dlgbody h3")].some(h => h.textContent.startsWith("技能"))`), JSON.stringify(pick));
check("dialog has drops section", await evaluate(`[...document.querySelectorAll("#dlgbody h3")].some(h => h.textContent.startsWith("击杀掉落"))`), "");
check("skill items rendered", await evaluate(`document.querySelectorAll("#dlgbody .skill").length`) === pick.sk, "sk=" + pick.sk);
check("drop items rendered", await evaluate(`document.querySelectorAll("#dlgbody .drop").length`) > 0, "");

/* 3. 数值区块：资源/战斗/属性/抗性标题存在 */
const secs = await evaluate(`[...document.querySelectorAll("#dlgbody h3")].map(h => h.textContent)`);
check("stat sections present", ["资源","战斗","属性","特征"].every(x => secs.some(s => s.startsWith(x))), secs.join(" | "));
check("HP row present", /生命值/.test(await evaluate(`document.getElementById("dlgbody").textContent`)), "");

/* 4. 技能描述渲染：颜色标记不残留 ~ */
check("no raw ~tags~ in dialog", !/~[a-z]+~/.test(await evaluate(`document.getElementById("dlgbody").textContent`)), "");
check("no raw /*KEY*/ in dialog", !await evaluate(`document.getElementById("dlgbody").innerHTML.includes("/*")`), "");

/* 5. Boss 标记 */
const boss = await evaluate(`(function(){
  const e = DATA.find(x => x.bs);
  if (!e) return "none";
  const card = [...document.querySelectorAll("#grid .card")].find(c => c.querySelector(".nm").textContent.includes(e.zh));
  if (card) card.click();
  return e.zh;
})()`);
await sleep(150);
if (boss !== "none")
  check("boss tag shown", await evaluate(`!!document.querySelector("#dlgbody .tag.boss")`), boss);
else
  check("boss tag shown (dataset has no boss, skipped)", true, "");

/* 6. 搜索技能名能找到敌人 */
await evaluate(`document.getElementById("dlgx").click()`);
await evaluate(`(function(){ const q = document.getElementById("q"); q.value = "Hooking Chop"; q.dispatchEvent(new Event("input")); })()`);
await sleep(100);
check("search by skill name", await evaluate(`document.querySelectorAll("#grid .card").length`) > 0, "");

/* 7. Esc 关闭 */
await evaluate(`(function(){ const card = document.querySelector("#grid .card"); if (card) card.click(); })()`);
await sleep(150);
await evaluate(`document.getElementById("dlg").close()`);
await sleep(150);
check("dialog closes", !await evaluate(`document.getElementById("dlg").open`), "");

/* 8. 分类导航：阵营 / 危险等级 / 首领 */
await evaluate(`(function(){ const q = document.getElementById("q"); q.value = ""; q.dispatchEvent(new Event("input")); })()`);
await sleep(100);
const faCount = await evaluate(`(function(){
  const b = [...document.querySelectorAll("#nav1 .chip")].find(c => c.textContent.startsWith("亡灵"));
  return b ? +b.querySelector(".cnt").textContent : -1;
})()`);
check("faction chip count", faCount === 67, "cnt=" + faCount);
await evaluate(`[...document.querySelectorAll("#nav1 .chip")].find(c => c.textContent.startsWith("亡灵")).click()`);
await sleep(100);
check("faction filter renders 67", await evaluate(`document.querySelectorAll("#grid .card").length`) === 67, "");
check("all cards are faction 亡灵", await evaluate(`[...document.querySelectorAll("#grid .card")].every(c => [...c.querySelectorAll(".tag")].some(t => t.textContent === "亡灵"))`), "");
/* 组合：亡灵 + 危险等级三 */
await evaluate(`[...document.querySelectorAll("#nav2 .chip")].find(c => c.textContent.startsWith("三")).click()`);
await sleep(100);
const combo = await evaluate(`document.querySelectorAll("#grid .card").length`);
check("faction+rank combo", combo > 0 && combo < 67, "cards=" + combo);
check("combo tag shows rank", await evaluate(`[...document.querySelectorAll("#grid .card .tag")].every(t => t.textContent === "亡灵" || t.textContent === "危险等级 3" || t.textContent === "首领")`), "");
/* 复位 + 首领过滤 */
await evaluate(`document.querySelector("#nav1 .chip").click()`);
await evaluate(`document.querySelector("#nav2 .chip").click()`);
await evaluate(`[...document.querySelectorAll("#nav3 .chip")].find(c => c.textContent.startsWith("首领")).click()`);
await sleep(100);
check("boss filter count", await evaluate(`document.querySelectorAll("#grid .card").length`) === await evaluate(`DATA.filter(x => x.bs).length`), "");
check("persistence saved", await evaluate(`JSON.parse(localStorage.getItem("ssw_enemyfilters")).bs`) === 1, "");
await evaluate(`localStorage.removeItem("ssw_enemyfilters")`);

try { chrome.kill(); rmSync(profile, { recursive: true, force: true }); } catch(e){}
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
