const http = require('http');
const fs = require('fs');
const path = require('path');

const ARTIFACT_DIR = 'C:/Users/Miraj Hossain/.gemini/antigravity/brain/74e856ae-3d5a-4511-9400-a8dc99a74b39';

function send(ws, method, params = {}) {
  return new Promise((resolve) => {
    const id = Math.floor(Math.random() * 1000000);
    const handler = (msg) => {
      const data = JSON.parse(msg.data);
      if (data.id === id) {
        ws.removeEventListener('message', handler);
        resolve(data.result);
      }
    };
    ws.addEventListener('message', handler);
    ws.send(JSON.stringify({ id, method, params }));
  });
}

function delay(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function run() {
  const tabs = await new Promise((resolve, reject) => {
    http.get('http://127.0.0.1:9333/json', (res) => {
      let raw = '';
      res.on('data', chunk => raw += chunk);
      res.on('end', () => resolve(JSON.parse(raw)));
    }).on('error', reject);
  });

  const pageTab = tabs.find(t => t.type === 'page') || tabs[0];
  if (!pageTab) throw new Error('No page tab found');
  const ws = new WebSocket(pageTab.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);

  console.log('[+] Connected to Chrome DevTools');

  // 1. First, navigate to Seller URL and log in
  await send(ws, 'Page.navigate', { url: 'http://127.0.0.1:8799/' });
  await delay(1500);

  // Submit login form
  console.log('[+] Logging in as demo-seller-key...');
  await send(ws, 'Runtime.evaluate', {
    expression: `
      (() => {
        const keyInput = document.getElementById('seller-key');
        if (keyInput) {
          keyInput.value = 'demo-seller-key';
          keyInput.dispatchEvent(new Event('input', { bubbles: true }));
          const form = document.getElementById('login-form');
          form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
        }
      })()
    `
  });
  await delay(2000);

  // Capture Desktop Seller Dashboard (1440x900)
  console.log('[+] Capturing Desktop Seller Dashboard (1440x900)...');
  await send(ws, 'Emulation.setDeviceMetricsOverride', {
    width: 1440,
    height: 900,
    deviceScaleFactor: 1,
    mobile: false
  });
  await delay(800);
  let shot = await send(ws, 'Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(path.join(ARTIFACT_DIR, 'vibecheck_seller_logged_in_desktop.png'), Buffer.from(shot.data, 'base64'));
  console.log('[✓] Saved vibecheck_seller_logged_in_desktop.png');

  // Capture Mobile Seller Dashboard (390x844)
  console.log('[+] Capturing Mobile Seller Dashboard (390x844)...');
  await send(ws, 'Emulation.setDeviceMetricsOverride', {
    width: 390,
    height: 844,
    deviceScaleFactor: 2,
    mobile: true
  });
  await delay(800);
  shot = await send(ws, 'Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(path.join(ARTIFACT_DIR, 'vibecheck_seller_logged_in_mobile.png'), Buffer.from(shot.data, 'base64'));
  console.log('[✓] Saved vibecheck_seller_logged_in_mobile.png');

  // 2. Navigate to Buyer Checkout URL
  const buyerPath = process.argv[2] || '/buy/demo-token';
  console.log(`[+] Navigating to buyer checkout: http://127.0.0.1:8799${buyerPath}`);
  await send(ws, 'Page.navigate', { url: `http://127.0.0.1:8799${buyerPath}` });
  await delay(2000);

  // Capture Desktop Buyer Checkout (1440x900)
  console.log('[+] Capturing Desktop Buyer Checkout (1440x900)...');
  await send(ws, 'Emulation.setDeviceMetricsOverride', {
    width: 1440,
    height: 900,
    deviceScaleFactor: 1,
    mobile: false
  });
  await delay(800);
  shot = await send(ws, 'Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(path.join(ARTIFACT_DIR, 'vibecheck_buyer_desktop.png'), Buffer.from(shot.data, 'base64'));
  console.log('[✓] Saved vibecheck_buyer_desktop.png');

  // Capture Mobile Buyer Checkout (390x844)
  console.log('[+] Capturing Mobile Buyer Checkout (390x844)...');
  await send(ws, 'Emulation.setDeviceMetricsOverride', {
    width: 390,
    height: 844,
    deviceScaleFactor: 2,
    mobile: true
  });
  await delay(800);
  shot = await send(ws, 'Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(path.join(ARTIFACT_DIR, 'vibecheck_buyer_mobile.png'), Buffer.from(shot.data, 'base64'));
  console.log('[✓] Saved vibecheck_buyer_mobile.png');

  ws.close();
  console.log('[✓] ALL VIBE CHECKS CAPTURED SUCCESSFULLY');
}

run().catch(err => {
  console.error('Error during vibecheck:', err);
  process.exit(1);
});
