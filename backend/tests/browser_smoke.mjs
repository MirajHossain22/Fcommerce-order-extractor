// Optional local browser integration check. Requires Node 22+, Chrome and .venv.
// Uses synthetic data in .pytest_cache only; never opens the real order database.
import {spawn} from 'node:child_process';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {setTimeout as delay} from 'node:timers/promises';
import assert from 'node:assert/strict';

const root = process.cwd();
const work = resolve(root, '.pytest_cache', 'browser-' + Date.now());
await mkdir(work, {recursive: true});
const chromePath = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const pythonPath = process.env.PYTHON_PATH || resolve(root, '.venv/Scripts/python.exe');
const key = 'synthetic-browser-test-key';
const python = `import socket, uvicorn\nfrom pathlib import Path\nfrom app.main import create_app\nsock = socket.socket()\nsock.bind(('127.0.0.1', 0))\nPath(${JSON.stringify(work.replaceAll('\\', '/') + '/port')}).write_text(str(sock.getsockname()[1]))\napp = create_app(Path(${JSON.stringify(work.replaceAll('\\', '/') + '/orders.db')}), seller_keys={${JSON.stringify(key)}: 'test-shop'})\nuvicorn.Server(uvicorn.Config(app, log_level='error', access_log=False)).run(sockets=[sock])\n`;
const server = spawn(pythonPath, ['-c', python], {cwd: root, env: {...process.env, PYTHONPATH: resolve(root, 'backend'), SELLER_API_KEYS: '{}'}, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe']});
let serverErrors = '';
server.stderr.on('data', chunk => { serverErrors += chunk; });
let chrome, ws;
const pending = new Map();
let counter = 0;
const browserErrors = [];
async function until(fn, description) {
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    try { const result = await fn(); if (result) return result; } catch {}
    await delay(100);
  }
  throw new Error('Timed out: ' + description + '\n' + serverErrors);
}
function command(method, params = {}) {
  const id = ++counter;
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => { pending.delete(id); reject(new Error('CDP timeout: ' + method)); }, 15000);
    pending.set(id, {resolve: value => { clearTimeout(timeout); resolve(value); }, reject: error => { clearTimeout(timeout); reject(error); }});
    ws.send(JSON.stringify({id, method, params}));
  });
}
async function evaluate(expression) {
  const result = await command('Runtime.evaluate', {expression, awaitPromise: true, returnByValue: true});
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
  return result.result.value;
}
async function fill(selector, value) {
  await evaluate(`(() => {const element=document.querySelector(${JSON.stringify(selector)}); element.value=${JSON.stringify(value)}; element.dispatchEvent(new Event('input', {bubbles:true}));})()`);
}
async function click(selector) { await evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`); }
async function waitFor(expression, description) { return until(() => evaluate(expression), description); }
async function screenshot(name) {
  const {data} = await command('Page.captureScreenshot', {format: 'png'});
  await writeFile(resolve(work, name), Buffer.from(data, 'base64'));
}

try {
  const port = await until(() => readFile(resolve(work, 'port'), 'utf8'), 'server port');
  const base = 'http://127.0.0.1:' + port;
  await until(async () => (await fetch(base)).ok, 'API ready');
  chrome = spawn(chromePath, ['--headless=new', '--disable-gpu', '--disable-extensions', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', '--user-data-dir=' + resolve(work, 'chrome'), 'about:blank'], {windowsHide: true, stdio: ['ignore', 'ignore', 'pipe']});
  chrome.stderr.on('data', chunk => { serverErrors += chunk; });
  chrome.on('error', error => { serverErrors += error.message; });
  const debugPort = (await until(() => readFile(resolve(work, 'chrome/DevToolsActivePort'), 'utf8'), 'Chrome debugging port')).split('\n')[0];
  const target = (await (await fetch(`http://127.0.0.1:${debugPort}/json`)).json()).find(t => t.type === 'page');
  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
  ws.onclose = event => { for (const task of pending.values()) task.reject(new Error('Browser connection closed: ' + event.code + '\n' + serverErrors)); pending.clear(); };
  ws.onmessage = event => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const task = pending.get(message.id); pending.delete(message.id);
      if (message.error) task.reject(new Error(message.error.message)); else task.resolve(message.result);
    }
    if (message.method === 'Runtime.exceptionThrown') browserErrors.push(message.params.exceptionDetails.text);
    if (message.method === 'Log.entryAdded' && message.params.entry.source === 'javascript' && message.params.entry.level === 'error') browserErrors.push(message.params.entry.text);
  };
  await command('Runtime.enable'); await command('Page.enable'); await command('Log.enable');
  await command('Emulation.setDeviceMetricsOverride', {width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false});
  await command('Page.navigate', {url: base});
  await waitFor("document.querySelector('#seller-key') && !document.querySelector('#login-form button').disabled", 'login form ready');
  await fill('#seller-key', key); await click('#login-form button');
  await waitFor("!document.querySelector('#workspace').hidden && document.querySelector('#line-items input')", 'seller workspace');
  await evaluate("document.querySelector('#catalog-panel').open = true");
  await fill('#catalog-product', 'Cotton panjabi'); await fill('#catalog-size', 'M'); await fill('#catalog-color', 'Olive');
  await fill('#catalog-price', '850'); await fill('#catalog-stock', '3'); await click('#catalog-form button');
  await waitFor("document.querySelector('#catalog-list').textContent.includes('3 available') && !document.querySelector('#new-order').disabled", 'catalog variant created');
  await click('#new-order');
  await fill('[name="shop_name"]', 'Dhaka Cotton');
  await evaluate("(() => {const picker=document.querySelector('[data-field=variant]'); picker.selectedIndex=1; picker.dispatchEvent(new Event('change', {bubbles:true}));})()");
  assert.equal(await evaluate("document.querySelector('[data-field=product]').value"), 'Cotton panjabi');
  await fill('[data-field="quantity"]', '2'); await fill('[data-field="price"]', '850');
  await fill('[name="delivery"]', '80'); await click('#save-draft');
  await waitFor("!document.querySelector('#saved-actions').hidden && !document.querySelector('#create-link').disabled", 'draft saved');
  assert.match(await evaluate("document.querySelector('#draft-total').textContent"), /1,780/);
  await click('#create-link');
  await waitFor("!document.querySelector('#share-box').hidden", 'checkout link');
  const url = await evaluate("document.querySelector('#share-url').value");
  assert.match(url, /\/buy\//);
  await screenshot('seller-desktop.png');
  await command('Emulation.setDeviceMetricsOverride', {width: 390, height: 844, deviceScaleFactor: 1, mobile: true});
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), true);
  await screenshot('seller-mobile.png');
  await command('Page.navigate', {url});
  await waitFor("document.querySelector('#buyer-content') && !document.querySelector('#buyer-content').hidden", 'buyer checkout');
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), true);
  await screenshot('buyer-mobile.png');
  await fill('[name="customer_name"]', 'TEST_BUYER'); await fill('[name="phone"]', '01800000001'); await fill('[name="address"]', 'TEST_ADDRESS');
  await click('#confirm-order');
  await waitFor("!document.querySelector('#receipt-panel').hidden", 'buyer receipt');
  await screenshot('receipt-mobile.png');
  const trackUrl = await evaluate("document.querySelector('#tracking-link').href");
  await command('Page.reload');
  await waitFor("document.querySelector('#receipt-panel') && !document.querySelector('#receipt-panel').hidden", 'receipt recovery after reload');
  const orders = await (await fetch(base + '/seller/orders', {headers: {Authorization: 'Bearer ' + key}})).json();
  assert.equal(orders.length, 1); assert.equal(orders[0].status, 'confirmed'); assert.equal(orders[0].phone, '01800000001');
  const available = await (await fetch(base + '/seller/catalog', {headers: {Authorization: 'Bearer ' + key}})).json();
  assert.equal(available[0].stock, 1);
  const response = await fetch(base + '/seller/orders/' + orders[0].reference + '/status', {method: 'POST', headers: {Authorization: 'Bearer ' + key, 'Content-Type': 'application/json'}, body: JSON.stringify({status: 'packed'})});
  assert.equal(response.status, 200);
  await command('Page.navigate', {url: trackUrl});
  await waitFor("document.querySelector('#tracking-status')?.textContent === 'Packed'", 'live seller-entered tracking update');
  await screenshot('tracking-mobile.png');
  await command('Page.navigate', {url: base});
  await waitFor("document.querySelector('#workspace') && !document.querySelector('#workspace').hidden && document.querySelector('.order-card')", 'seller session restored');
  await click('.order-card');
  await waitFor("!document.querySelector('#update-status').disabled", 'seller status action ready');
  await fill('#courier-name', 'TEST_COURIER');
  await fill('#courier-reference', 'TEST_PARCEL_001');
  await click('#save-shipment');
  await waitFor("document.querySelector('#message').textContent.includes('Courier details saved') && !document.querySelector('#update-status').disabled", 'courier details saved');
  await click('#update-status');
  await waitFor("document.querySelector('#order-status').textContent === 'shipped' && !document.querySelector('#logout').disabled", 'seller UI status update');
  await command('Page.navigate', {url: trackUrl});
  await waitFor("document.querySelector('#courier-info')?.textContent.includes('TEST_PARCEL_001')", 'buyer courier display');
  await screenshot('courier-mobile.png');
  await command('Page.navigate', {url: base});
  await waitFor("document.querySelector('#workspace') && !document.querySelector('#workspace').hidden && document.querySelector('.order-card')", 'return to seller');
  await click('.order-card');
  await evaluate("document.querySelector('#next-status').value = 'returned'");
  await click('#update-status');
  await waitFor("!document.querySelector('#restock-return').hidden && !document.querySelector('#restock-return').disabled", 'return ready for inspection');
  await evaluate('window.confirm = () => true');
  await click('#restock-return');
  await waitFor("document.querySelector('#restock-return').hidden && document.querySelector('#catalog-list').textContent.includes('3 available')", 'inspected return restocked');
  await click('#logout');
  await waitFor("!document.querySelector('#login-panel').hidden && document.querySelector('#workspace').hidden", 'seller logout');
  assert.equal(await evaluate("document.querySelector('#seller-key').value"), '');
  assert.deepEqual(browserErrors, []);
  console.log(JSON.stringify({result: 'passed', checks: ['seller login', 'catalog creation and variant selection', 'computed total', 'shareable link', 'mobile layout', 'buyer confirmation and stock deduction', 'receipt reload', 'one order only', 'seller status tracking', 'session restoration', 'courier details saved and displayed', 'seller UI status update', 'inspected return restocked', 'logout', 'no JavaScript exceptions'], artifacts: work}, null, 2));
} catch (error) {
  if (ws?.readyState === WebSocket.OPEN) {
    try {
      console.error(JSON.stringify({browserErrors, screen: await evaluate('document.body.innerText'), url: await evaluate('location.href')}, null, 2));
      await screenshot('failure.png');
    } catch {}
  }
  throw error;
} finally {
  if (ws?.readyState === WebSocket.OPEN) { try { await command('Browser.close'); } catch {} ws.close(); }
  chrome?.kill(); server.kill();
}
