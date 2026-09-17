// 冒烟测试：物品图鉴弹窗的定位与关闭行为
// 直接用本机已缓存的 Chromium + CDP（无需安装依赖）
// 用法：node _smoke_dialog.mjs [file:///绝对路径/items.html]
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME = "C:/Users/87088/AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe";
const URL_ = process.argv[2] || "file:///E:/GameProject/stoneshard-wiki/site/items.html";
const PORT = 9333;
const profile = mkdtempSync(join(tmpdir(), "ssw-smoke-"));
const sleep = ms => new Promise(r => setTimeout(r, ms));

const chrome = spawn(CHROME, [
  "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  "--disable-extensions", "--window-size=1280,900",
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, URL_,
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
async function mouse(x, y) {
  for (const type of ["mousePressed", "mouseReleased"])
    await send("Input.dispatchMouseEvent", { type, x, y, button: "left", clickCount: 1 });
}

const checks = [];
const check = (name, ok, detail) => { checks.push({ name, ok, detail }); console.log(`${ok ? "PASS" : "FAIL"}  ${name}  ${detail}`); };

try {
  // 等 CDP 端口就绪
  let targets;
  for (let i = 0; i < 40; i++) {
    try { targets = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json(); if (targets.some(t => t.type === "page")) break; } catch {}
    await sleep(250);
  }
  const page = targets.find(t => t.type === "page");
  if (!page) throw new Error("未找到页面 target");
  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  ws.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id).res(m.result); pending.delete(m.id); }
  };
  await send("Runtime.enable");
  await send("Page.enable");

  // 等页面渲染出卡片
  for (let i = 0; i < 40; i++) {
    const n = await evaluate(`document.querySelectorAll(".card").length`);
    if (n > 100) break;
    await sleep(250);
  }
  const cards = await evaluate(`document.querySelectorAll(".card").length`);

  // 1) 滚到下方，打开一张卡片
  await evaluate(`window.scrollTo(0, 2200); new Promise(r => requestAnimationFrame(() => r(1)))`);
  await sleep(150);
  const before = await evaluate(`window.scrollY`);
  await evaluate(`document.querySelectorAll(".card")[60].click(); 1`);
  await sleep(200);
  check("卡片可打开弹窗", await evaluate(`document.getElementById("dlg").open`) === true, `cards=${cards}`);
  check("滚动位置在打开时未被改动", Math.abs((await evaluate(`window.scrollY`)) - before) < 2, `before=${before} now=${await evaluate(`window.scrollY`)}`);

  // 2) 弹窗是否水平+垂直居中（注意：要用 clientWidth/clientHeight，innerWidth 含滚动条）
  const box = await evaluate(`(() => { const r = document.getElementById("dlg").getBoundingClientRect();
      const de = document.documentElement;
      return {cx:r.left + r.width/2, cy:r.top + r.height/2, w:r.width, h:r.height,
              vw:de.clientWidth, vh:de.clientHeight, top:r.top}; })()`);
  check("弹窗水平居中", Math.abs(box.cx - box.vw / 2) <= 2, `cx=${box.cx.toFixed(1)} 视口中心=${box.vw / 2}`);
  check("弹窗垂直居中", Math.abs(box.cy - box.vh / 2) <= 2, `cy=${box.cy.toFixed(1)} 视口中心=${box.vh / 2} (top=${box.top.toFixed(1)}, h=${box.h.toFixed(1)})`);

  // 3) 点 × 关闭 → 滚动位置保持
  await evaluate(`document.getElementById("dlgx").click(); 1`);
  await sleep(250);
  check("× 按钮能关闭", await evaluate(`document.getElementById("dlg").open`) === false, "");
  check("关闭后滚动位置保持", Math.abs((await evaluate(`window.scrollY`)) - before) < 2, `before=${before} after=${await evaluate(`window.scrollY`)}`);

  // 4) 点弹窗外空白关闭
  await evaluate(`document.querySelectorAll(".card")[60].click(); 1`);
  await sleep(200);
  await mouse(8, 300);
  await sleep(250);
  check("点弹窗外空白能关闭", await evaluate(`document.getElementById("dlg").open`) === false, "");
  check("该方式关闭后滚动位置保持", Math.abs((await evaluate(`window.scrollY`)) - before) < 2, `after=${await evaluate(`window.scrollY`)}`);

  // 5) 弹窗内点击不应关闭 + 长内容滚动区从顶部开始
  await evaluate(`document.querySelectorAll(".card")[60].click(); 1`);
  await sleep(200);
  const r0 = await evaluate(`(() => { const r = document.getElementById("dlg").getBoundingClientRect(); return {x:r.left+r.width/2, y:r.top+r.height/2}; })()`);
  await mouse(Math.round(r0.x), Math.round(r0.y));
  await sleep(200);
  check("点弹窗内部不会误关", await evaluate(`document.getElementById("dlg").open`) === true, "");

  // 截图留档（弹窗打开状态）
  const shot = process.argv[3];
  if (shot) {
    const { data } = await send("Page.captureScreenshot", { format: "png" });
    writeFileSync(shot, Buffer.from(data, "base64"));
    console.log(`      截图 -> ${shot}`);
  }

  // 6) 打开新卡片时正文回到顶部（长描述场景）
  await evaluate(`document.getElementById("dlgbody").scrollTop = 9999; 1`);
  const scrolled = await evaluate(`document.getElementById("dlgbody").scrollTop`);
  await evaluate(`document.getElementById("dlgx").click(); 1`);
  await sleep(150);
  await evaluate(`document.querySelectorAll(".card")[3].click(); 1`);
  await sleep(200);
  check("重新打开时正文从顶部显示", await evaluate(`document.getElementById("dlgbody").scrollTop`) === 0, `上一张曾滚到 ${scrolled}`);

  await evaluate(`document.getElementById("dlgx").click(); 1`);

  // 7) 数值配色：由游戏数据（stat_polarity 表）决定，而不是数值正负号
  const RED = "rgb(192, 57, 43)", GREEN = "rgb(61, 122, 61)";

  // 7a) 函数级：全量 stat 项，statCls 必须与极性表一致
  const audit = await evaluate(`(() => {
    const signOf = v => { v = String(v == null ? "" : v).trim();
      return v.startsWith("-") ? "-" : (v.startsWith("+") ? "+" : "0"); };
    let total = 0, mismatch = 0, signDiff = 0, noPol = 0, samples = [];
    for (const it of DATA) {
      if (!it.st || !it.st.stats) continue;
      for (const s of it.st.stats) {
        total++;
        const sg = signOf(s.value);
        const pol = POLARITY[String(s.label || "").trim()];
        if (!pol) { noPol++; continue; }
        const kind = pol[sg];
        const expect = kind === "neg" ? "c-red" : (kind === "pos" ? "c-green" : "c-w");
        const got = statCls(s.label, s.value);
        if (expect !== got) { mismatch++; if (samples.length < 5) samples.push({l:s.label, v:s.value, expect, got}); }
        // 与"按符号判色"的结论差异 —— 即本次修复纠正的条目数
        const bySign = sg === "-" ? "c-red" : (sg === "+" ? "c-green" : "c-w");
        if (bySign !== got) signDiff++;
      }
    }
    return { total, mismatch, signDiff, noPol, samples };
  })()`);
  check("配色与游戏数据极性表一致", audit.mismatch === 0,
        `${audit.total} 项数值，不一致 ${audit.mismatch}${audit.mismatch ? " -> " + JSON.stringify(audit.samples) : ""}`);
  check("存在被纠正的\"按符号会判错\"的条目", audit.signDiff > 0,
        `按符号会判错的共 ${audit.signDiff} 项（无极性数据 ${audit.noPol} 项）`);

  // 7b) DOM 级：验证"负号但是绿色"的关键用例（失手几率/冷却时间/所受伤害 的负值）
  const cases = [
    { label: "失手几率", sign: "-", expect: GREEN, note: "减失手=好事" },
    { label: "冷却时间", sign: "-", expect: GREEN, note: "减冷却=好事" },
    { label: "所受伤害", sign: "-", expect: GREEN, note: "减受伤=好事" },
    { label: "失手几率", sign: "+", expect: RED,   note: "加失手=坏事" },
    { label: "准度",     sign: "-", expect: RED,   note: "减准度=坏事" },
    { label: "技能精力消耗", sign: "+", expect: RED, note: "技能更耗精力=坏事" },
  ];
  for (const c of cases) {
    const idx = await evaluate(`(() => {
      const i = DATA.findIndex(it => it.st && it.st.stats &&
        it.st.stats.some(s => s.label === ${JSON.stringify(c.label)} && String(s.value).trim().startsWith(${JSON.stringify(c.sign)})));
      return i;
    })()`);
    if (idx < 0) { check(`配色用例 ${c.label} ${c.sign}`, false, "数据中未找到用例"); continue; }
    // 直接打开该条目（同名物品有多个变体，按名字找卡片会拿错）
    const hit = await evaluate(`(() => {
      openDlg(DATA[${idx}]);
      const b = [...document.querySelectorAll("#dlgbody .strow b")]
        .find(x => x.textContent.trim().startsWith(${JSON.stringify(c.sign)}) &&
                   x.parentElement.textContent.trim().startsWith(${JSON.stringify(c.label)}));
      return b ? { name: DATA[${idx}].zh, v: b.textContent.trim(), color: getComputedStyle(b).color, title: b.title } : null;
    })()`);
    check(`配色用例 ${c.label} ${c.sign}（${c.note}）`,
          !!hit && hit.color === c.expect,
          hit ? `${hit.name}｜${hit.v} -> ${hit.color === RED ? "红" : hit.color === GREEN ? "绿" : hit.color}｜${hit.title}` : "弹窗中未找到该数值行");
    await evaluate(`document.getElementById("dlgx").click(); 1`);
    await sleep(120);
  }

  if (shot) {
    await evaluate(`(() => { const q = document.getElementById("q"); q.value = "风箱面甲"; q.dispatchEvent(new Event("input")); })()`);
    await sleep(250);
    await evaluate(`document.querySelectorAll(".card")[0].click(); 1`);
    await sleep(300);
    const rows = await evaluate(`[...document.querySelectorAll("#dlgbody .strow b")].map(b => ({ v: b.textContent.trim(), color: getComputedStyle(b).color }))`);
    console.log(`      样例：${rows.map(r => `${r.v}=${r.color === RED ? "红" : r.color === GREEN ? "绿" : "其他"}`).join("  ")}`);
    const { data } = await send("Page.captureScreenshot", { format: "png" });
    writeFileSync(shot.replace(/\.png$/, "_colors.png"), Buffer.from(data, "base64"));
    console.log(`      配色截图 -> ${shot.replace(/\.png$/, "_colors.png")}`);
    await evaluate(`document.getElementById("dlgx").click(); 1`);
  }
  console.log(`\n${checks.filter(c => c.ok).length}/${checks.length} 项通过`);
  process.exitCode = checks.every(c => c.ok) ? 0 : 1;
} catch (e) {
  console.log("ERROR:", e.message);
  process.exitCode = 2;
} finally {
  try { ws?.close(); } catch {}
  chrome.kill();
  await sleep(400);
  try { rmSync(profile, { recursive: true, force: true }); } catch {}
}
