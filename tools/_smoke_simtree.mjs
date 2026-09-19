/* 冒烟测试：skills.html 树状图视图 + 模拟加点
   方向语义：低阶技能是高阶技能的前置（Ⅰ层=根）；属性门槛为「任一达标」 */
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME = "C:/Users/87088/AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe";
const URL = "file:///E:/GameProject/stoneshard-wiki/site/skills.html";
const PORT = 9344;
let pass = 0, fail = 0;
function check(name, ok, extra){
  console.log((ok ? "PASS" : "FAIL") + "  " + name + (ok ? "" : "  <- " + extra));
  ok ? pass++ : fail++;
}

const profile = mkdtempSync(join(tmpdir(), "ssw-sim-"));
const sleep = ms => new Promise(r => setTimeout(r, ms));
const chrome = spawn(CHROME, ["--headless=new","--disable-gpu","--no-first-run","--no-default-browser-check",
  "--window-size=1400,1200", `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, URL], { stdio: "ignore" });

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

const goPyro = `ATTRS={STR:30,AGL:30,PRC:30,VIT:30,WIL:30}; saveAttrs(); CTX=baseCtx();
  LVL=30; saveLvl(); cur=DATA.findIndex(b=>b.key==="pyromancy"); renderBranches(); render();`;
await evaluate(goPyro);
await sleep(200);

/* 1. 树状图渲染：14 节点 + 连线 + 默认树视图 */
check("tree view default", await evaluate(`viewMode`) === "tree", "");
check("pyro 14 nodes", await evaluate(`document.querySelectorAll("#content .tnode").length`) === 14, "");
check("edges drawn", await evaluate(`document.querySelectorAll("#content .edges line").length`) > 0, "");

/* 2. 方向：Ⅰ层是根（可点），Ⅳ层终极技能因前置未习得而锁定 */
const st = await evaluate(`(function(){
  const b = DATA[cur];
  const out = {};
  for (const n of b.nodes) out[n.id] = nodeState(b, n).st;
  return out;
})()`);
check("t1 roots available", ["Fire_Barrage","flame_saturation","baptism_of_fire","Flame_Ring"].every(k => st[k] === "avail"), JSON.stringify(st));
check("t4 capstone locked by prereq", st["Inferno"] === "lock" && st["pyromania"] === "lock", JSON.stringify(st));
check("t1 nodes have no prereqs", await evaluate(`DATA[cur].nodes.filter(n => n.tier === 1).every(n => n.from.length === 0)`), "");

/* 3. 链式加点：Ⅰ层根 → Ⅱ → Ⅲ → Ⅳ（自顶向下） */
const alloc = id => evaluate(`(function(){
  const b = DATA[cur];
  const el = [...document.querySelectorAll("#content .tnode")].find(x => x.dataset.id === "${id}");
  el.click(); return (sim[b.key]||[]).slice();
})()`);
await alloc("Fire_Barrage");
await sleep(150);
check("t2 unlocked after t1", await evaluate(`nodeState(DATA[cur], DATA[cur].nodes.find(n=>n.id==="feed_the_flames")).st`) === "avail", "");
await alloc("feed_the_flames"); await alloc("flame_saturation"); await alloc("Flame_Wave"); await alloc("Incineration"); await alloc("excess_heat");
await sleep(150);
check("chain allocated 6", await evaluate(`(sim[DATA[cur].key]||[]).length`) === 6, "");
check("t4 capstone lit", await evaluate(`nodeState(DATA[cur], DATA[cur].nodes.find(n=>n.id==="excess_heat")).st`) === "on", "");
check("edges lit", await evaluate(`[...document.querySelectorAll("#content .edges line")].filter(l => l.getAttribute("stroke") === "#7a4b2a").length`) > 0, "");
check("spent shown", /本树已投入 <b>6<\/b>/.test(await evaluate(`document.querySelector(".viewbar").innerHTML`)), "");

/* 4. 退款保护：Incineration 依赖它的 excess_heat 已习得，取消被拒 */
const refund = await evaluate(`(function(){
  const b = DATA[cur];
  toggleNode(b, b.nodes.find(n => n.id === "Incineration"));
  return (sim[b.key]||[]).length;
})()`);
check("refund blocked by dependent", refund === 6, "len=" + refund);
check("block reason shown", /依赖本技能/.test(await evaluate(`document.getElementById("ninfo").textContent`)), "");

/* 5. 等级门槛：LVL=5，习得 Ⅰ层根后，前置已满足但 lv10 的节点锁定（等级不足） */
await evaluate(`LVL=5; saveLvl(); delete sim[DATA[cur].key]; saveSim(); render()`);
await sleep(100);
await alloc("Fire_Barrage");
const lvReason = await evaluate(`nodeState(DATA[cur], DATA[cur].nodes.find(n=>n.id==="feed_the_flames")).why || ""`);
check("level gate reason", /等级不足/.test(lvReason), lvReason);
check("level gate blocks", await evaluate(`nodeState(DATA[cur], DATA[cur].nodes.find(n=>n.id==="feed_the_flames")).st`) === "lock", "");

/* 6. 属性门槛「任一」：余烬过载需 活力/意志 任一 ≥ 20 —— 单属性 20 即可通过 */
await evaluate(`LVL=30; saveLvl(); ATTRS={STR:10,AGL:14,PRC:10,VIT:10,WIL:10}; saveAttrs(); CTX=baseCtx(); render()`);
await sleep(100);
/* 注意：Fire_Barrage 已在第 5 节开头加点过，这里不能再 toggle，否则会被取消 */
await alloc("flame_saturation"); await alloc("feed_the_flames"); await alloc("Flame_Wave"); await alloc("Incineration");
await sleep(100);
const orWhy = await evaluate(`nodeState(DATA[cur], DATA[cur].nodes.find(n=>n.id==="excess_heat")).why || ""`);
check("attr gate reason mentions 任一", /属性不足.*任一/.test(orWhy), orWhy);
await evaluate(`ATTRS.WIL=20; saveAttrs(); CTX=baseCtx(); render()`);
await sleep(100);
const orOk = await evaluate(`nodeState(DATA[cur], DATA[cur].nodes.find(n=>n.id==="excess_heat")).st`);
check("attr gate is OR (WIL20 alone passes)", orOk === "avail", "st=" + orOk);

/* 7. 持久化 + 清空本树 */
await evaluate(`cur=DATA.findIndex(b=>b.key==="pyromancy"); renderBranches(); render()`);
check("sim persisted", await evaluate(`JSON.parse(localStorage.getItem("ssw_sim"))[DATA[cur].key].length`) === 5, "");
await evaluate(`document.getElementById("simreset").click()`);
await sleep(100);
check("reset clears tree", await evaluate(`(sim[DATA[cur].key]||[]).length`) === 0, "");
check("cards still work in list view", await evaluate(`(function(){
  document.querySelector('.viewbar .chip[data-v="list"]').click();
  return document.querySelectorAll("#content .node").length;
})()`) === 14, "");

/* 8. 悬停富提示：显示状态 + 门槛 + 锁定原因 + 描述，且在悬停结束时隐藏 */
await evaluate(`viewMode="tree"; ATTRS={STR:10,AGL:10,PRC:10,VIT:10,WIL:10}; saveAttrs(); CTX=baseCtx(); render()`);
await sleep(100);
const tip = await evaluate(`(function(){
  const b = DATA[cur];
  const el = [...document.querySelectorAll("#content .tnode")].find(x => nodeState(b, b.nodes.find(n => n.id === x.dataset.id)).st === "lock");
  if (!el) return "(no locked node)";
  el.dispatchEvent(new MouseEvent("mouseenter", { bubbles: true, clientX: 300, clientY: 300 }));
  const tip = document.getElementById("tip");
  return { shown: tip.style.display === "block", pos: tip.style.left + "," + tip.style.top,
           txt: tip.textContent.slice(0, 160) };
})()`);
check("tooltip shows on hover", tip.shown === true && tip.pos !== ",", JSON.stringify(tip).slice(0, 200));
check("tooltip has reason", tip.txt && /需先习得|属性不足|等级不足/.test(tip.txt), tip.txt);
check("tooltip has desc", tip.txt && tip.txt.length > 40, "");
await evaluate(`document.querySelector("#content .tnode").dispatchEvent(new MouseEvent("mouseleave", { bubbles: true }))`);
check("tooltip hides on leave", await evaluate(`document.getElementById("tip").style.display`) === "none", "");
await evaluate(`localStorage.removeItem("ssw_sim"); localStorage.removeItem("ssw_lvl")`);

try { chrome.kill(); rmSync(profile, { recursive: true, force: true }); } catch(e){}
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
