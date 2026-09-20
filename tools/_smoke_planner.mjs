/* 冒烟测试：planner.html 配装规划器
   锚点 = 已验证的裸角色基准值（社区规划器/GML 一致）+ 装备/附魔/站姿公式抽查 */
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME = "C:/Users/87088/AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe";
const URL = "file:///E:/GameProject/stoneshard-wiki/site/planner.html";
const PORT = 9351;
let pass = 0, fail = 0;
function check(name, ok, extra){
  console.log((ok ? "PASS" : "FAIL") + "  " + name + (ok ? "" : "  <- " + extra));
  ok ? pass++ : fail++;
}

const profile = mkdtempSync(join(tmpdir(), "ssw-planner-"));
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
await sleep(1000);

/* 1. 裸角色基准（属性全 10） */
const bare = await evaluate(`compute().vals`);
check("bare HP 100", bare.HP === "100/100", bare.HP);
check("bare MP 100 (60+4×VIT)", bare.MP === "100/100", bare.MP);
check("bare Hit 80", bare.Hit_Chance === 80, bare.Hit_Chance);
check("bare CRT 1", bare.CRT === 1, bare.CRT);
check("bare CRTD 25", bare.CRTD === 25, bare.CRTD);
check("bare FMB 20", bare.FMB === 20, bare.FMB);
check("bare CTA 1", bare.CTA === 1, bare.CTA);
check("bare WD 100", bare.Weapon_Damage === 100, bare.Weapon_Damage);
check("bare DMG 7.3", bare.DMG === 7.3, bare.DMG);
check("bare AP 0", bare.Armor_Piercing === 0, bare.Armor_Piercing);
check("bare MagicPower 100", bare.Magic_Power === 100, bare.Magic_Power);
check("bare EVS 1", bare.EVS === 1, bare.EVS);
check("bare VSN 12", bare.VSN === 12, bare.VSN);
check("bare no block", bare.PRR === 0 && bare.Block_Power === "0/0", bare.PRR + "/" + bare.Block_Power);

/* 2. STR 20：过 15/20 两档 se=2 → CRTD 45 / 肢体 15 / 护甲破坏 30 / WD 115 */
await evaluate(`ST.attrs.STR = 20; renderPanel()`);
const str20 = await evaluate(`compute().vals`);
check("STR20 CRTD 45", str20.CRTD === 45, str20.CRTD);
check("STR20 Bodypart 15", str20.Bodypart_Damage === 15, str20.Bodypart_Damage);
check("STR20 ArmorDmg 30", str20.Armor_Damage === 30, str20.Armor_Damage);
check("STR20 WD 115", str20.Weapon_Damage === 115, str20.Weapon_Damage);

/* 3. 装备 旅人剑（劈砍18）：WD 不含武器伤害本身，DMG = 18×WD% = 18 */
await evaluate(`ST.attrs.STR = 10; ST.slots.weapon = "sword02"; renderPanel()`);
const sw = await evaluate(`(function(){ const r = compute(); return { v:r.vals, apSrc:Array.from(r.src.get("Armor_Piercing")||[]) }; })()`);
check("sword WD 100", sw.v.Weapon_Damage === 100, sw.v.Weapon_Damage);
check("sword DMG 18", sw.v.DMG === 18, sw.v.DMG);
check("sword AP +5", sw.v.Armor_Piercing === 5, sw.v.Armor_Piercing);
check("sword source tracked", sw.apSrc.some(x => x.who && x.who.name === "旅人剑"), JSON.stringify(sw.apSrc));

/* 4. 附魔：给武器加 吸血(Lifesteal +5) → Lifesteal 5 */
const enchId = await evaluate(`(PD.ench.find(e => e.mt.includes("Weapon") && e.fx.some(f => f.k === "Lifesteal" && f.v === 5)) || {}).id`);
await evaluate(`ST.mods.weapon = { ench: ["${enchId}"] }; renderPanel()`);
const en = await evaluate(`compute().vals`);
check("enchant Lifesteal 5", enchId && en.Lifesteal === 5, en.Lifesteal + " id=" + enchId);

/* 5. 副手盾 → 格挡：D=(STR×武器系数 + 主手/副手格挡力量)×(1+格挡强度加成%) */
const shRes = await evaluate(`(function(){
  const sh = PD.items.find(i => i.slot === "offhand" && (i.st.Block_Power||0) > 0);
  ST.slots.offhand = sh.id; renderPanel();
  const v = compute().vals;
  const sw = ITEM_BY_ID["sword02"];
  const expect = Math.round((10*PD.blockF["SWORDS"] + (sw.st.Block_Power||0) + sh.st.Block_Power));
  return { got: v.Block_Power, expect: expect + "/" + expect, swBP: sw.st.Block_Power||0, shBP: sh.st.Block_Power };
})()`);
check("shield block formula", shRes.got === shRes.expect, shRes.got + " expect " + shRes.expect + " (swBP=" + shRes.swBP + " shBP=" + shRes.shBP + ")");
check("shield enables PRR", shRes.got !== "0/0", String(shRes.got));

/* 5b. 无武器时格挡同样生效（官方机制：格挡不依赖盾牌）：防具自带的格挡几率/回复要计入面板 */
const blkRes = await evaluate(`(function(){
  ST.slots = {}; ST.mods = {}; renderPanel();
  const helm = PD.items.find(i => (i.st.PRR || 0) > 0 && i.slot === "head");
  const boots = PD.items.find(i => (i.st.Block_Recovery || 0) > 0 && i.slot === "boots");
  ST.slots.head = helm.id; if (boots) ST.slots.boots = boots.id;
  renderPanel();
  const v = compute().vals;
  return { helm: helm.zh, prrGear: helm.st.PRR, PRR: v.PRR, BR: v.Block_Recovery, bootsBR: boots ? boots.st.Block_Recovery : 0 };
})()`);
check("no-weapon armor PRR counts", blkRes.PRR === blkRes.prrGear, JSON.stringify(blkRes));
await evaluate(`ST.slots = {}; ST.mods = {}; renderPanel()`);
const brBare = await evaluate(`compute().vals.Block_Recovery`);
check("bare BR 5", brBare === 5, brBare);

/* 6. 站姿 buff：热血澎湃 阶段3 → CRT / 技能精力消耗 按阶段数值 */
const buffRes = await evaluate(`(function(){
  const buff = PD.buffs.find(b => b.zh === "热血澎湃");
  ST.buffs[buff.id] = 3; renderPanel();
  const v = compute().vals;
  const crtMod = buff.m.find(m => m.k === "CRT");
  const aec = buff.m.find(m => m.k === "Abilities_Energy_Cost");
  return { crt: v.CRT, crtExp: crtMod ? 1 + crtMod.vs[3] : null,
           aec: v.Abilities_Energy_Cost, aecExp: aec ? Math.min(300, Math.max(25, 100 + aec.vs[3])) : null };
})()`);
check("buff CRT stage3", buffRes.crtExp === null || buffRes.crt === buffRes.crtExp, buffRes.crt + " expect " + buffRes.crtExp);
check("buff AEC stage3", buffRes.aecExp === null || buffRes.aec === buffRes.aecExp, buffRes.aec + " expect " + buffRes.aecExp);

/* 7. 属性边界与 UI */
await evaluate(`ST.buffs = {}; renderPanel()`);
await evaluate(`document.querySelectorAll("#attrs button")[0].click()`);  // STR − → 9
check("attr stepper works", await evaluate(`ST.attrs.STR`) === 9, await evaluate(`ST.attrs.STR`));
const rows = await evaluate(`document.querySelectorAll("#panel .prow").length`);
check("panel rows rendered", rows > 60, String(rows));

/* 8. 持久化 */
await evaluate(`ST.attrs.STR = 14; save()`);
await evaluate(`location.reload()`);
await sleep(900);
check("persisted after reload", await evaluate(`ST.attrs.STR`) === 14, await evaluate(`ST.attrs.STR`));

console.log(`\\n${pass} passed, ${fail} failed`);
chrome.kill();
process.exit(fail ? 1 : 0);
