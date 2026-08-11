const puppeteer = require('puppeteer-core');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: true,
    args: ['--no-sandbox', '--disable-gpu', '--autoplay-policy=no-user-gesture-required']
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 720, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  const target = process.argv[2] || 'http://127.0.0.1:8899';
  await page.goto(target, { waitUntil: 'networkidle0' });
  await page.waitForFunction(() => window.__AV_READY === true && window.__AV_FRAME > 45, { timeout: 10000 });
  if (target.includes(':8899')) {
    await page.waitForFunction(() => window.__AV_STATUS && window.__AV_STATUS.connected && window.__AV_STATUS.received > 0, { timeout: 10000 });
  } else {
    await page.waitForFunction(() => window.__AV_STATUS && window.__AV_STATUS.demo === true, { timeout: 10000 });
  }
  const status = await page.evaluate(() => ({ frame: window.__AV_FRAME, status: window.__AV_STATUS, canvas: { width: document.querySelector('canvas').width, height: document.querySelector('canvas').height } }));
  const screenshot = path.join(__dirname, 'foundry-live-preview.png');
  await page.screenshot({ path: screenshot });
  console.log(JSON.stringify({ ok: errors.length === 0, errors, screenshot, ...status }, null, 2));
  await browser.close();
  process.exit(errors.length ? 1 : 0);
})().catch(error => { console.error(error); process.exit(1); });
