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
  page.on('requestfailed', r => errors.push(`REQUEST ${r.url()} ${r.failure()?.errorText || 'failed'}`));
  const target = process.argv[2] || 'http://127.0.0.1:8899';
  const expectAudio = process.argv.includes('--audio');
  await page.goto(target, { waitUntil: 'domcontentloaded', timeout: 30000 });
  if (expectAudio) {
    await page.click('#audioStart');
    try {
      await page.waitForFunction(() => window.__AUDIO_STATUS && window.__AUDIO_STATUS.running && window.__AUDIO_STATUS.scheduled > 40 && window.__AUDIO_STATUS.voiceLoaded && window.__AUDIO_STATUS.voicePlays > 0, { timeout: 20000 });
    } catch (error) {
      console.error(JSON.stringify({ errors, diagnostics: await page.evaluate(() => ({ ready: window.__AV_READY, frame: window.__AV_FRAME, audio: window.__AUDIO_STATUS, status: window.__AV_STATUS, button: document.querySelector('#audioStart')?.textContent })) }, null, 2));
      throw error;
    }
  }
  await page.waitForFunction(() => window.__AV_READY === true && window.__AV_FRAME > 45, { timeout: 10000 });
  if (target.includes(':8899')) {
    await page.waitForFunction(() => window.__AV_STATUS && window.__AV_STATUS.connected && window.__AV_STATUS.received > 0, { timeout: 10000 });
  } else if (expectAudio) {
    await page.waitForFunction(() => window.__AV_STATUS && window.__AV_STATUS.audio === true, { timeout: 10000 });
  } else {
    await page.waitForFunction(() => window.__AV_STATUS && window.__AV_STATUS.demo === true, { timeout: 10000 });
  }
  const status = await page.evaluate(() => ({ frame: window.__AV_FRAME, status: window.__AV_STATUS, audio: window.__AUDIO_STATUS || null, canvas: { width: document.querySelector('canvas').width, height: document.querySelector('canvas').height } }));
  if (expectAudio) await page.waitForFunction(() => window.__AV_STATUS && (window.__AV_STATUS.butcherAttack > 0.95 || window.__AV_STATUS.ripperAttack > 0.95), { timeout: 5000 });
  const impactStatus = await page.evaluate(() => window.__AV_STATUS);
  const screenshot = path.join(__dirname, 'foundry-live-preview.png');
  await page.screenshot({ path: screenshot });
  console.log(JSON.stringify({ ok: errors.length === 0, errors, screenshot, impactStatus, ...status }, null, 2));
  await browser.close();
  process.exit(errors.length ? 1 : 0);
})().catch(error => { console.error(error); process.exit(1); });
