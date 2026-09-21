/* 冒烟测试：全站统一外壳（导航通栏 / 页头与正文左边线对齐 / 无深色页面）
   回归背景：8 个页面此前各写各的头部（紫渐变 / 白底 / 无页头 + 深色主题），
   切换页面时观感撕裂。本次统一到 tools/_nav.py 里的单一真源，本测试守住它。 */
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME = "C:/Users/87088/AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe";
const ROOT = "file:///E:/GameProject/stoneshard-wiki/site/";
const PAGES = ["index.html", "items.html", "skills.html", "planner.html",
               "enemies.html", "trade.html", "caravan.html", "icons.html"];
const PORT = 9357;
let pass = 0, fail = 0;
const check = (name, ok, extra) => { console.log((ok ? "PASS" : "FAIL") + "  " + name + (ok ? "" : "  <- " + extra)); ok ? pass++ : fail++; };

const profile = mkdtempSync(join(tmpdir(), "ssw-shell-"));
const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  "--window-size=1400,1000", `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, ROOT + PAGES[0]], { stdio: "ignore" });

let ws, seq = 0; const pending = new Map();
const send = (method, params = {}) => new Promise((res) => {
  const id = ++seq; pending.set(id, { res });
  ws.send(JSON.stringify({ id, method, params }));
});
const evaluate = async e => {
  const r = await send("Runtime.evaluate", { expression: e, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || "eval error");
  return r.result.value;
};
for (let i = 0; i < 50; i++) {
  try {
    const list = await fetch(`http://127.0.0.1:${PORT}/json/list`).then(r => r.json());
    const page = list.find(p => p.type === "page");
    if (page) {
      ws = new WebSocket(page.webSocketDebuggerUrl);
      await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
      ws.onmessage = ev => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id).res(m.result); pending.delete(m.id); } };
      break;
    }
  } catch {}
  await new Promise(r => setTimeout(r, 200));
}

const PROBE = `(() => {
  const cs = el => getComputedStyle(el);
  const inner = document.querySelector('.ssw-head-inner');
  const h1 = document.querySelector('.ssw-head h1');
  const nav = document.querySelector('.ssw-nav');
  const navInner = document.querySelector('.ssw-nav-inner');
  const content = [...document.body.children].find(el =>
    !el.matches('.ssw-nav, .ssw-head, style, script, dialog, #tip'));
  const box = el => { const r = el.getBoundingClientRect(); return { l: r.left, w: r.width }; };
  const txtLeft = el => box(el).l + parseFloat(cs(el).paddingLeft);
  const bg = cs(document.body).backgroundColor.match(/\\d+/g).slice(0, 3).map(Number);
  return {
    // 注意：scrollbar-gutter:stable 会在无滚动条的页面也预留槽位，
    // 此时 documentElement.clientWidth 仍报「整窗宽」，不代表可用宽度。用 body 实测。
    availW: document.body.getBoundingClientRect().width,
    navTags: document.querySelectorAll('.ssw-nav').length,
    navBgLeft: box(nav).l,
    navBgWidth: box(nav).w,
    navTxtLeft: txtLeft(navInner),
    headH: document.querySelector('.ssw-head').getBoundingClientRect().height,
    subH: document.querySelector('.ssw-sub').getBoundingClientRect().height,
    headKids: document.querySelector('.ssw-head-inner').children.length,
    headTxtLeft: txtLeft(inner),
    headH1Left: txtLeft(h1.parentElement) + (h1.getBoundingClientRect().left - h1.parentElement.getBoundingClientRect().left) - parseFloat(cs(h1.parentElement).paddingLeft),
    h1Size: parseFloat(cs(h1).fontSize),
    contentTag: content ? content.className || content.id || content.tagName : '(none)',
    contentTxtLeft: content ? txtLeft(content) : -1,
    bodyPad: parseFloat(cs(document.body).paddingLeft),
    bg, fg: cs(document.body).color
  };
})()`;

const rows = [];
for (const pg of PAGES) {
  await send("Page.navigate", { url: ROOT + pg });
  await new Promise(r => setTimeout(r, 1500));
  const m = await evaluate(PROBE);
  rows.push([pg, m]);
  const dHead = Math.abs(m.headTxtLeft - m.contentTxtLeft);
  const dNav = Math.abs(m.navTxtLeft - m.headTxtLeft);
  const lum = 0.299 * m.bg[0] + 0.587 * m.bg[1] + 0.114 * m.bg[2];
  check(`${pg} 导航唯一`, m.navTags === 1, m.navTags);
  check(`${pg} 导航通栏(左0/宽${m.availW})`, Math.abs(m.navBgLeft) < 1 && Math.abs(m.navBgWidth - m.availW) < 2, `l=${m.navBgLeft} w=${m.navBgWidth}`);
  check(`${pg} body 无边距`, m.bodyPad === 0, m.bodyPad);
  check(`${pg} 页头与正文左边线对齐`, dHead < 1, `head=${m.headTxtLeft} content(${m.contentTag})=${m.contentTxtLeft} Δ=${dHead.toFixed(1)}`);
  check(`${pg} 导航文字与页头对齐`, dNav < 1, `nav=${m.navTxtLeft} head=${m.headTxtLeft}`);
  check(`${pg} 标题字号 22px`, m.h1Size === 22, m.h1Size);
  check(`${pg} 页头只含标题+副标题`, m.headKids === 2, `children=${m.headKids}`);
  check(`${pg} 浅色主题`, lum > 220, `bg=rgb(${m.bg}) lum=${lum.toFixed(0)}`);
}

console.log("\n--- 汇总（页头高度 / 副标题高 / 左边线）---");
for (const [pg, m] of rows) console.log(`${pg.padEnd(13)} headH=${String(m.headH).padEnd(7)} subH=${String(m.subH).padEnd(6)} head=${m.headTxtLeft.toFixed(1)}  content=${m.contentTxtLeft.toFixed(1)} (${m.contentTag})`);

// 跨页一致性：切换页面时左边线必须完全不动（滚动条槽 / 容器宽度差异都会在这里暴露）
const uniq = (k, d = 10) => [...new Set(rows.map(([, m]) => Math.round(m[k] * d) / d))];
const uContent = uniq("contentTxtLeft"), uHead = uniq("headTxtLeft"), uNav = uniq("navTxtLeft");
check(`全站正文左边线唯一(${uContent.join("/")})`, uContent.length === 1, uContent.join("/"));
check(`全站页头左边线唯一(${uHead.join("/")})`, uHead.length === 1, uHead.join("/"));
check(`全站导航文字左边线唯一(${uNav.join("/")})`, uNav.length === 1, uNav.join("/"));
const uH = uniq("headH", 1), uSub = uniq("subH", 1);
check(`全站页头高度唯一(${uH.join("/")})`, uH.length === 1, uH.join("/"));
check(`全站副标题高度唯一(${uSub.join("/")})`, uSub.length === 1, uSub.join("/"));

chrome.kill();
try { rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 300 }); } catch {}
console.log("\n" + pass + " passed, " + fail + " failed");
process.exit(fail ? 1 : 0);
