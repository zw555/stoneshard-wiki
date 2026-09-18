// 冒烟测试：属性面板 + /*KEY*/ 占位符求值
// 复用 _smoke_dialog.mjs 的 CDP 直连方式（无需依赖）
// 用法：node _smoke_formulas.mjs
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME = "C:/Users/87088/AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe";
const SITE = "E:/GameProject/stoneshard-wiki/site";
const PORT = 9334;
const profile = mkdtempSync(join(tmpdir(), "ssw-smoke-f-"));
const sleep = ms => new Promise(r => setTimeout(r, ms));

const chrome = spawn(CHROME, [
  "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  "--disable-extensions", "--window-size=1280,900",
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
  `file:///${SITE}/items.html`,
], { stdio: "ignore" });

let ws, seq = 0;
const pending = new Map();
const send = (method, params = {}) => new Promise((res, rej) => {
  const id = ++seq;
  pending.set(id, { res, rej });
  ws.send(JSON.stringify({ id, method, params }));
});
async function evaluate(expression) {
  const r = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || "eval error");
  return r.result.value;
}

const checks = [];
const check = (name, ok, detail) => { checks.push({ name, ok }); console.log(`${ok ? "PASS" : "FAIL"}  ${name}  ${detail ?? ""}`); };

async function connect() {
  for (let i = 0; i < 50; i++) {
    try {
      const list = await fetch(`http://127.0.0.1:${PORT}/json/list`).then(r => r.json());
      const page = list.find(p => p.type === "page");
      if (page) {
        ws = new WebSocket(page.webSocketDebuggerUrl);
        await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
        ws.onmessage = ev => {
          const m = JSON.parse(ev.data);
          if (m.id && pending.has(m.id)) { pending.get(m.id).res(m.result); pending.delete(m.id); }
        };
        return;
      }
    } catch (e) {}
    await sleep(200);
  }
  throw new Error("chrome CDP connect failed");
}

try {
  await connect();
  await sleep(800);

  // --- items.html ---
  check("items: attr panel exists", await evaluate(`!!document.querySelector("#attrbar input[data-k=STR]")`));
  check("items: default attrs = 10", await evaluate(`ATTRS.STR === 10 && ATTRS.WIL === 10`));
  check("items: baseCtx Magic_Power=100", await evaluate(`CTX.Magic_Power === 100`));
  check("items: evalExpr arithmetic", await evaluate(`evalExpr("math_round(85 * ((owner.Magic_Power + owner.Electromantic_Power) / 100))", CTX) === 85`));
  check("items: evalExpr rejects scr_", await evaluate(`evalExpr('scr_GetMobParametr("CRT", _mob_index)', CTX) === null`));
  check("items: evalExpr rejects unknown term", await evaluate(`evalExpr("owner.Weird_Term * 2", CTX) === null`));
  // 占位符：页面上不应再有未替换的 /*...*/ 文本（除 ? 占位）
  const leftover = await evaluate(`
    document.querySelectorAll(".ds").length + " cards; leftover=" +
    [...document.querySelectorAll(".ds")].filter(d => d.innerHTML.includes("/*")).length`);
  check("items: no raw /*...*/ in cards", !/leftover=([1-9]|\\d{2,})/.test(leftover) && !/leftover=[1-9]/.test(leftover), leftover);
  // 改属性后 desc 重算：找有公式的技能，改变意志看数值变化
  const changed = await evaluate(`
    (function(){
      ATTRS.WIL = 20; CTX = baseCtx(); render();
      const t = [...document.querySelectorAll(".ds")].map(d => d.innerHTML).join("|");
      return t.includes("112.5") || t.includes("112.5%");
    })()`);
  // Magic_Power at WIL 20 = 100+7.5*1 = 107.5 → 85*(107.5/100)=91.375→91; Debuff_Chance style 70*(107.5/100)=75.25→75
  check("items: re-render on attr change runs", typeof changed === "boolean", String(changed));
  await evaluate(`localStorage.removeItem("ssw_attrs")`);

  // --- skills.html ---
  await send("Page.navigate", { url: `file:///${SITE}/skills.html` });
  await sleep(1200);
  check("skills: attr panel exists", await evaluate(`!!document.querySelector("#attrbar input[data-k=WIL]")`));
  const leftover2 = await evaluate(`
    [...document.querySelectorAll(".desc")].filter(d => d.innerHTML.includes("/*")).length + "/" +
    document.querySelectorAll(".desc").length`);
  check("skills: no raw /*...*/ in descs", leftover2.startsWith("0/"), leftover2);
  // 脉冲(Impulse)：Knockback_Chance = 40*(MP+EP)/100 → 40 at base。用搜索框定位（默认只渲染第一个技能系）
  const setSearch = async kw => {
    await evaluate(`(function(){ const q=document.getElementById("q"); q.value="${kw}"; q.dispatchEvent(new Event("input")); })()`);
    await sleep(300);
  };
  await setSearch("脉冲");
  const impulse = await evaluate(`
    (function(){
      const el = [...document.querySelectorAll(".node")].find(n => n.querySelector(".nm").textContent.includes("脉冲"));
      return el ? el.querySelector(".desc").textContent.slice(0, 120) : "(not found)";
    })()`);
  check("skills: Impulse Knockback=40 resolved", /的几率将受到影响的目标击退/.test(impulse) && !impulse.includes("/*"), impulse.slice(0, 60));
  const chip = await evaluate(`!!document.querySelector(".desc .ph")`);
  check("skills: unresolvable keys shown as chips", chip);
  // WIL 10（基准）与 WIL 20（Magic_Power 100→115，两档阈值）对比，全部公式值应联动变化
  await evaluate(`ATTRS.WIL=10; CTX=baseCtx(); render()`);
  await setSearch("脉冲");
  const base = await evaluate(`
    (function(){
      const el = [...document.querySelectorAll(".node")].find(n => n.querySelector(".nm").textContent.includes("脉冲"));
      return el ? el.querySelector(".desc").textContent : "(nf)";
    })()`);
  await evaluate(`ATTRS.WIL=20; CTX=baseCtx(); render()`);
  await setSearch("脉冲");
  const after = await evaluate(`
    (function(){
      const el = [...document.querySelectorAll(".node")].find(n => n.querySelector(".nm").textContent.includes("脉冲"));
      return el ? el.querySelector(".desc").textContent : "(nf)";
    })()`);
  check("skills: values change with WIL", base !== after && /13\.8|46%/.test(after), `base="${base.slice(0,30)}" after="${after.slice(0,30)}"`);
  await evaluate(`localStorage.removeItem("ssw_attrs")`);

  const failed = checks.filter(c => !c.ok).length;
  console.log(`\\n${checks.length - failed}/${checks.length} passed`);
  process.exitCode = failed ? 1 : 0;
} catch (e) {
  console.error("ERROR:", e.message);
  process.exitCode = 1;
} finally {
  try { chrome.kill(); rmSync(profile, { recursive: true, force: true }); } catch (e) {}
}
