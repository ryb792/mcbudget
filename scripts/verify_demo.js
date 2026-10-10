/* 演示页交互验收（Playwright + 系统 Chrome，headless）：
 * 1) 三档渲染与金额断言  2) 滑块与数字输入联动  3) 到店/外送切换
 * 4) PNG 挑战卡导出（modal 预览 dataURL）  5) 手机宽度布局
 * 运行：NODE_PATH=<workspace>/node_modules node scripts/verify_demo.js
 */
const path = require("path");

const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const DEMO = "file:///" + encodeURI("Z:/Ruanjian/WorkBuddy_data/麦当劳/mcbudget/demo/index.html").replace(/%25/g, "%");
const SHOT_DIR = "C:/Users/83705/AppData/Local/Temp";

let pass = 0;
const fails = [];
function check(name, cond, detail) {
  if (cond) { pass++; console.log("  ok  " + name); }
  else { fails.push(name); console.log("FAIL  " + name + "  " + (detail || "")); }
}

(async () => {
  const { chromium } = require("playwright-core");
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ["--no-sandbox"] });

  // ---------- 桌面 ----------
  const page = await browser.newPage({ viewport: { width: 1280, height: 1400 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(DEMO);
  await page.waitForSelector(".tier");

  const tierHeads = await page.$$eval(".tier-head", (els) => els.map((e) => e.textContent.replace(/\s+/g, " ")));
  const tierFull = await page.$$eval(".tier", (els) => els.map((e) => e.textContent.replace(/\s+/g, " ")));
  check("三档渲染（含沿用徽章）", tierHeads.length === 3 && /B-5/.test(tierHeads[0]) && /B\+5/.test(tierHeads[2]), JSON.stringify(tierHeads));
  check("B-5 默认推荐麦香鱼堡 ¥12", /麦香鱼堡/.test(tierFull[0]) && /¥12/.test(tierFull[0]), tierFull[0].slice(0, 140));
  const tierBodyB = tierFull[1];
  check("B 档套餐组成完整", /套餐含：麦辣鸡腿堡 \+ 中薯条 \+ 中可乐/.test(tierBodyB), tierBodyB.slice(0, 120));
  check("B 档金额 ¥22.5（满25减4）", /¥22\.5/.test(tierBodyB) && /满25元减4元/.test(tierBodyB), tierBodyB.slice(0, 160));

  // 滑块 → 40：B-5(35元) 推套餐，B(40元) 沿用（无符合偏好的升级）为合法语义
  await page.$eval("#budgetRange", (el) => {
    el.value = "40";
    el.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await page.waitForTimeout(120);
  const afterRange = await page.$$eval(".tier", (els) => els.map((e) => e.textContent.replace(/\s+/g, " ")));
  check("滑块 40 元：B-5 档为麦辣套餐 ¥22.5", /麦辣鸡腿堡套餐/.test(afterRange[0]) && /¥22\.5/.test(afterRange[0]), afterRange[0].slice(0, 140));
  check("滑块 40 元：B 档正确触发沿用语义", /沿用 B-5 档方案/.test(afterRange[1]), afterRange[1].slice(0, 100));

  // 数字输入 → 12：外送场景下验证无可行方案的差额文案
  await page.$eval("#budgetNum", (el) => {
    el.value = "12";
    el.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await page.waitForTimeout(120);
  check("数字输入 12 元同步滑块", (await page.$eval("#budgetRange", (el) => el.value)) === "12", "");

  // 得来速切换（与到店同为 0 配送费，标签独立）
  await page.click("#modeDt");
  await page.waitForTimeout(120);
  const dtActive = await page.$eval("#modeDt", (e) => e.classList.contains("active"));
  const dtNote = await page.$eval("#deliveryNote", (e) => getComputedStyle(e).display);
  check("得来速选项可切换且不显示外送说明", dtActive && dtNote === "none", `active=${dtActive} note=${dtNote}`);
  await page.click("#modePickup");
  await page.waitForTimeout(80);

  // 外送切换 + 低预算差额文案
  await page.click("#modeDelivery");
  await page.waitForTimeout(120);
  const deliveryNote = await page.$eval("#deliveryNote", (e) => getComputedStyle(e).display);
  const afterMode = await page.$$eval(".tier", (els) => els.map((e) => e.textContent.replace(/\s+/g, " ")));
  check("外送模式显示配送费说明", deliveryNote !== "none", "");
  check("外送低预算报最低候选与差额（不编造）", /还差 ¥9/.test(afterMode[1]) && /麦香鱼堡/.test(afterMode[1]) && /不会虚构低价套餐/.test(afterMode[1]), afterMode[1].slice(0, 160));

  // 恢复可下单场景：回到店、25 元
  await page.click("#modePickup");
  await page.waitForTimeout(80);
  await page.$eval("#budgetNum", (el) => {
    el.value = "25";
    el.dispatchEvent(new Event("change", { bubbles: true }));
  });
  await page.waitForTimeout(120);

  page.on("dialog", (d) => d.dismiss()); // 无方案时 drawCard 会 alert；此场景预算 25 有方案，不应触发

  // PNG 挑战卡导出
  await page.click("#btnCard");
  await page.waitForSelector("#cardModal.show");
  const src = await page.$eval("#cardImg", (e) => e.getAttribute("src") || "");
  check("挑战卡 PNG 生成（dataURL）", src.startsWith("data:image/png;base64,") && src.length > 50000, "len=" + src.length);
  await page.screenshot({ path: path.join(SHOT_DIR, "demo_card_modal.png") });
  await page.click("#btnClose");
  await page.waitForTimeout(120);
  const modalHidden = await page.$eval("#cardModal", (e) => !e.classList.contains("show"));
  check("挑战卡弹窗可关闭", modalHidden, "");

  check("页面无 JS 运行时错误", errors.length === 0, errors.join("; ").slice(0, 300));
  await page.screenshot({ path: path.join(SHOT_DIR, "demo_desktop_pw.png"), fullPage: true });

  // ---------- 手机宽度 ----------
  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await mobile.goto(DEMO);
  await mobile.waitForSelector(".tier");
  const overflow = await mobile.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  check("390px 宽无横向溢出", overflow <= 1, "overflow=" + overflow);
  await mobile.screenshot({ path: path.join(SHOT_DIR, "demo_mobile_pw.png"), fullPage: true });

  await browser.close();
  console.log(fails.length ? `\n结果：${pass} 通过，${fails.length} 失败 -> ${fails}` : `\n结果：全部 ${pass} 项通过`);
  process.exit(fails.length ? 1 : 0);
})().catch((e) => { console.error("RUNNER ERROR:", e); process.exit(2); });
