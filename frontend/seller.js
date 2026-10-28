import {$, money, node, request, notice, showHistory} from './shared.js';

let csrf = '';
let orders = [];
let catalog = [];
let selected = null;
let dirty = false;
let shipmentDirty = false;
let busy = false;
const form = $('draft-form');
const transitions = {draft: ['confirmed', 'cancelled'], confirmed: ['packed', 'cancelled'], packed: ['shipped', 'cancelled'], shipped: ['delivered', 'returned'], delivered: ['returned'], cancelled: [], returned: []};

async function api(path, options = {}) {
  try { return await request(path, {...options, headers: {'X-CSRF-Token': csrf, ...options.headers}}); }
  catch (error) {
    if (error.status === 401) { $('workspace').hidden = true; $('login-panel').hidden = false; notice('login-message', 'Your session ended. Sign in again.', true); }
    throw error;
  }
}
async function run(action) {
  if (busy) return;
  busy = true;
  notice('message');
  const buttons = [...document.querySelectorAll('#workspace button')];
  const previous = buttons.map(b => b.disabled);
  buttons.forEach(b => { b.disabled = true; });
  try { await action(); }
  catch (error) { notice('message', error.message, true); }
  finally { buttons.forEach((b, i) => { b.disabled = previous[i]; }); busy = false; updateActions(); }
}
function canLeave() { return (!dirty && !shipmentDirty) || confirm('Discard your unsaved changes?'); }
function input(name) { return form.elements.namedItem(name); }
function paisa(value) {
  if (!/^\d+(\.\d{1,2})?$/.test(value)) throw new Error('Enter prices with at most two decimal places.');
  const [whole, fraction = ''] = value.split('.');
  return Number(whole) * 100 + Number(fraction.padEnd(2, '0'));
}
function populatePicker(picker, variantId = '') {
  picker.replaceChildren();
  const manual = node('option', 'Manual item — stock not tracked'); manual.value = ''; picker.append(manual);
  for (const variant of catalog.filter(v => v.active || v.variant_id === variantId)) {
    const option = node('option', `${variant.product} / ${variant.size || '—'} / ${variant.color || '—'} · ${variant.stock} available${variant.active ? '' : ' (inactive)'}`);
    option.value = variant.variant_id; picker.append(option);
  }
  picker.value = variantId;
}
function addItem(item = {}) {
  const row = node('div', '', 'line-item');
  row.innerHTML = '<label>Product<input data-field="product" required maxlength="300" placeholder="e.g. Cotton panjabi"></label><div class="field-grid"><label>Size<input data-field="size" placeholder="e.g. M"></label><label>Color<input data-field="color" placeholder="e.g. Blue"></label></div><div class="field-grid"><label>Quantity<input data-field="quantity" type="number" min="1" max="10000" step="1" required></label><label>Unit price (BDT)<input data-field="price" type="number" min="0" max="1000000" step="0.01" required></label></div><button type="button" class="quiet">Remove item</button>';
  for (const name of ['product', 'size', 'color']) row.querySelector(`[data-field="${name}"]`).value = item[name] || '';
  row.querySelector('[data-field="quantity"]').value = item.quantity ?? 1;
  row.querySelector('[data-field="price"]').value = item.unit_price_paisa === undefined ? '' : (item.unit_price_paisa / 100).toFixed(2);
  row.dataset.productId = item.product_id || '';
  row.dataset.variantId = item.variant_id || '';
  const catalogLabel = node('label', 'Stock tracking');
  const picker = document.createElement('select'); picker.dataset.field = 'variant';
  populatePicker(picker, item.variant_id || '');
  for (const name of ['product', 'size', 'color']) row.querySelector(`[data-field="${name}"]`).readOnly = Boolean(item.variant_id);
  picker.addEventListener('change', () => {
    const variant = catalog.find(v => v.variant_id === picker.value);
    row.dataset.productId = variant?.product_id || ''; row.dataset.variantId = variant?.variant_id || '';
    for (const name of ['product', 'size', 'color']) {
      const field = row.querySelector(`[data-field="${name}"]`);
      field.readOnly = Boolean(variant); if (variant) field.value = variant[name] || '';
    }
    if (variant) row.querySelector('[data-field="price"]').value = (variant.unit_price_paisa / 100).toFixed(2);
    changed();
  });
  catalogLabel.append(picker); row.prepend(catalogLabel);
  row.querySelector('button').addEventListener('click', () => { row.remove(); changed(); });
  $('line-items').append(row);
}
function readDraft() {
  const items = [...$('line-items').children].map(row => {
    const value = name => row.querySelector(`[data-field="${name}"]`).value.trim();
    return {product: value('product'), size: value('size') || null, color: value('color') || null,
      product_id: row.dataset.productId || null, variant_id: row.dataset.variantId || null,
      quantity: Number(value('quantity')), unit_price_paisa: paisa(value('price'))};
  });
  if (!items.length) throw new Error('Add at least one item to this draft.');
  return {shop_name: input('shop_name').value.trim(), customer_name: input('customer_name').value.trim() || null,
    phone: input('phone').value.trim() || null, address: input('address').value.trim() || null,
    delivery_charge_paisa: paisa(input('delivery').value), items, payment_method: 'cash_on_delivery'};
}
function changed() {
  dirty = true;
  $('share-box').hidden = true;
  try { const d = readDraft(); $('draft-total').textContent = money(d.delivery_charge_paisa + d.items.reduce((n, i) => n + i.quantity * i.unit_price_paisa, 0)); }
  catch { $('draft-total').textContent = 'Add prices to see total'; }
  updateActions();
}
function updateActions() {
  const draft = selected?.status === 'draft';
  $('create-link').disabled = busy || dirty || !draft;
  $('revoke-link').disabled = busy || !draft;
  $('update-status').disabled = busy || dirty || shipmentDirty || !selected || !(transitions[selected.status] || []).length;
}
function selectOrder(value) {
  selected = value;
  dirty = false;
  shipmentDirty = false;
  form.reset();
  $('line-items').replaceChildren();
  $('share-box').hidden = true;
  $('share-url').value = '';
  $('order-reference').textContent = value?.reference || 'START SOMETHING NEW';
  $('editor-title').textContent = value ? (value.status === 'draft' ? 'Review order draft' : 'Order details') : 'New order draft';
  $('order-status').textContent = value?.status || 'draft';
  $('order-status').className = 'badge ' + (value?.status || 'draft');
  const editable = !value || value.status === 'draft';
  $('draft-fields').disabled = !editable;
  $('save-draft').hidden = !editable;
  $('chat-section').hidden = Boolean(value);
  $('saved-actions').hidden = !value;
  $('link-actions').hidden = !value || !editable;
  $('restock-return').hidden = value?.status !== 'returned' || value?.restocked || !value?.items.some(i => i.variant_id);
  $('shipment-form').hidden = !value || ['draft', 'cancelled'].includes(value.status);
  $('courier-name').value = value?.shipment?.courier_name || '';
  $('courier-reference').value = value?.shipment?.tracking_reference || '';
  for (const key of ['shop_name', 'customer_name', 'phone', 'address']) input(key).value = value?.[key] || (key === 'shop_name' ? 'Online shop' : '');
  input('delivery').value = ((value?.delivery_charge_paisa || 0) / 100).toFixed(2);
  const extracted = value?.extracted_order;
  if (value?.items.length) value.items.forEach(addItem);
  else addItem({product: extracted?.product || '', quantity: extracted ? (extracted.quantity ?? '') : 1});
  $('draft-total').textContent = money(value?.total_paisa || 0);
  $('extraction-hints').hidden = !extracted;
  if (extracted) $('extraction-hints').textContent = ['Extracted draft: check product, quantity, price and missing buyer details.', ...(extracted.warnings || []), extracted.notes || ''].filter(Boolean).join(' ');
  $('next-status').replaceChildren();
  for (const status of transitions[value?.status] || []) {
    const option = node('option', status === 'confirmed' ? 'Record buyer agreement' : status.charAt(0).toUpperCase() + status.slice(1));
    option.value = status; $('next-status').append(option);
  }
  showHistory($('history'), value?.history || []);
  updateActions(); renderOrders();
}
function renderOrders() {
  $('stat-total').textContent = orders.length;
  $('stat-draft').textContent = orders.filter(o => o.status === 'draft').length;
  $('stat-active').textContent = orders.filter(o => ['confirmed', 'packed', 'shipped'].includes(o.status)).length;
  $('stat-delivered').textContent = orders.filter(o => o.status === 'delivered').length;
  const search = $('search').value.toLowerCase();
  const filtered = orders.filter(o => (!$('filter').value || o.status === $('filter').value) && [o.reference, o.customer_name, ...o.items.map(i => i.product), o.extracted_order?.product].join(' ').toLowerCase().includes(search));
  $('order-list').replaceChildren();
  for (const order of filtered) {
    const card = node('button', '', 'order-card' + (selected?.reference === order.reference ? ' selected' : ''));
    card.type = 'button';
    card.append(node('strong', order.customer_name || 'Buyer details pending'), node('span', order.items.map(i => i.product).join(', ') || order.extracted_order?.product || 'Items need review', 'small muted'));
    const bottom = node('span', '', 'card-bottom');
    bottom.append(node('span', order.status, 'badge ' + order.status), node('span', money(order.total_paisa)));
    card.append(bottom);
    card.addEventListener('click', () => { if (!busy && canLeave()) selectOrder(order); });
    $('order-list').append(card);
  }
  if (!filtered.length) $('order-list').append(node('p', orders.length ? 'No matching orders.' : 'Your first clear order starts here. Create a draft to get going.', 'empty'));
}
async function refresh() {
  [orders, catalog] = await Promise.all([api('/seller/orders'), api('/seller/catalog')]);
  renderOrders(); renderCatalog();
}
function renderCatalog() {
  for (const row of $('line-items').children) populatePicker(row.querySelector('[data-field=variant]'), row.dataset.variantId || '');
  $('catalog-list').replaceChildren();
  for (const variant of catalog) {
    const row = node('form', '', 'line-item');
    row.append(node('strong', `${variant.product} · ${variant.size || '—'} · ${variant.color || '—'}`));
    row.append(node('p', `${variant.stock} available${variant.stock <= 5 ? ' · Low stock' : ''}${variant.active ? '' : ' · Inactive'}`, 'small muted'));
    const fields = node('div', '', 'field-grid');
    const stockLabel = node('label', 'Actual available units'); const stock = document.createElement('input');
    stock.type = 'number'; stock.min = 0; stock.max = 1000000; stock.step = 1; stock.required = true; stock.value = variant.stock; stockLabel.append(stock);
    const priceLabel = node('label', 'Default unit price (BDT)'); const price = document.createElement('input');
    price.type = 'number'; price.min = 0; price.max = 1000000; price.step = '0.01'; price.required = true; price.value = (variant.unit_price_paisa / 100).toFixed(2); priceLabel.append(price);
    fields.append(stockLabel, priceLabel); row.append(fields);
    const activeLabel = node('label', 'Availability'); const active = document.createElement('select');
    for (const [value, label] of [['true', 'Active'], ['false', 'Inactive']]) { const option = node('option', label); option.value = value; active.append(option); }
    active.value = String(variant.active); activeLabel.append(active); row.append(activeLabel);
    const save = node('button', 'Save stock & price', 'secondary'); save.type = 'submit'; row.append(save);
    row.addEventListener('submit', event => { event.preventDefault(); run(async () => {
      await api(`/seller/catalog/${variant.variant_id}`, {method: 'PUT', body: JSON.stringify({expected_version: variant.version, stock: Number(stock.value), unit_price_paisa: paisa(price.value), active: active.value === 'true'})});
      catalog = await api('/seller/catalog'); renderCatalog(); notice('message', 'Catalog updated. Saved order prices remain unchanged.');
    }); });
    $('catalog-list').append(row);
  }
  if (!catalog.length) $('catalog-list').append(node('p', 'Add your first product variant above.', 'empty'));
}
async function openWorkspace(session) {
  csrf = session.csrf_token;
  $('seller-name').textContent = session.seller_id;
  $('login-panel').hidden = true; $('workspace').hidden = false;
  await refresh(); selectOrder(null);
}
$('login-form').addEventListener('submit', async event => {
  event.preventDefault();
  const button = event.target.querySelector('button'); button.disabled = true;
  try {
    const session = await request('/session', {method: 'POST', headers: {'X-Requested-With': 'checkout-app'}, body: JSON.stringify({key: $('seller-key').value})});
    $('seller-key').value = ''; notice('login-message'); await openWorkspace(session);
  } catch (error) { notice('login-message', error.message, true); }
  finally { button.disabled = false; }
});
$('logout').addEventListener('click', () => { if (canLeave()) run(async () => {
  await api('/session', {method: 'DELETE'}); csrf = ''; orders = []; catalog = []; renderCatalog(); $('catalog-form').reset(); selectOrder(null);
  $('workspace').hidden = true; $('login-panel').hidden = false;
}); });
$('new-order').addEventListener('click', () => { if (canLeave()) selectOrder(null); });
$('add-item').addEventListener('click', () => { addItem(); changed(); });
form.addEventListener('input', changed);
form.addEventListener('submit', event => { event.preventDefault(); run(async () => {
  const body = readDraft();
  const value = await api(selected ? `/seller/orders/${selected.reference}` : '/seller/orders', {method: selected ? 'PUT' : 'POST', body: JSON.stringify(body)});
  selectOrder(value); await refresh(); notice('message', 'Draft saved. Review it, then create a checkout link.');
}); });
$('extract').addEventListener('click', () => { if (canLeave()) run(async () => {
  const message = $('chat-message').value.trim();
  if (!message) throw new Error('Paste a chat message first.');
  const before = new Set(orders.map(o => o.reference));
  const extracted = await api('/extract', {method: 'POST', body: JSON.stringify({message})});
  await refresh();
  if (extracted.is_order) { selectOrder(orders.find(o => !before.has(o.reference) && o.source === 'chat') || null); notice('message', 'Extraction saved as a draft. Review every field and add prices.'); }
  else notice('message', 'This message was not identified as an order. You can still create a draft manually.');
}); });
$('refresh').addEventListener('click', () => { if (canLeave()) run(async () => { const reference = selected?.reference; await refresh(); selectOrder(orders.find(o => o.reference === reference) || null); }); });
$('search').addEventListener('input', renderOrders);
$('filter').addEventListener('change', renderOrders);
$('create-link').addEventListener('click', () => run(async () => {
  const link = await api(`/seller/orders/${selected.reference}/checkout-links`, {method: 'POST', body: '{}'});
  $('share-url').value = new URL(link.buyer_path, location.origin).href;
  $('link-expiry').textContent = 'Expires ' + new Date(link.expires_at).toLocaleString();
  $('share-box').hidden = false; notice('message', 'Checkout link ready. Copy it into your buyer’s Messenger chat.');
}));
$('copy-link').addEventListener('click', () => run(async () => {
  try { await navigator.clipboard.writeText($('share-url').value); notice('message', 'Link copied.'); }
  catch { $('share-url').select(); notice('message', 'Select and copy the link above.'); }
}));
$('revoke-link').addEventListener('click', () => run(async () => { await api(`/seller/orders/${selected.reference}/checkout-links`, {method: 'DELETE'}); $('share-box').hidden = true; notice('message', 'Checkout links revoked.'); }));
$('update-status').addEventListener('click', () => {
  const status = $('next-status').value;
  if (status === 'confirmed' && !confirm('Has the buyer agreed to these items, delivery details and total?')) return;
  run(async () => { const value = await api(`/seller/orders/${selected.reference}/status`, {method: 'POST', body: JSON.stringify({status})}); selectOrder(value); await refresh(); notice('message', 'Order status updated.'); });
});
window.addEventListener('beforeunload', event => { if (dirty || shipmentDirty) { event.preventDefault(); event.returnValue = ''; } });
$('shipment-form').addEventListener('input', () => { shipmentDirty = true; updateActions(); });
$('shipment-form').addEventListener('submit', event => {
  event.preventDefault();
  run(async () => {
    const value = await api(`/seller/orders/${selected.reference}/shipment`, {method: 'PUT', body: JSON.stringify({courier_name: $('courier-name').value.trim(), tracking_reference: $('courier-reference').value.trim()})});
    selectOrder(value); await refresh(); notice('message', 'Courier details saved and visible on the buyer tracking page.');
  });
});
$('catalog-form').addEventListener('submit', event => {
  event.preventDefault(); run(async () => {
    await api('/seller/catalog', {method: 'POST', body: JSON.stringify({product: $('catalog-product').value.trim(), size: $('catalog-size').value.trim() || null, color: $('catalog-color').value.trim() || null, unit_price_paisa: paisa($('catalog-price').value), stock: Number($('catalog-stock').value)})});
    $('catalog-form').reset(); catalog = await api('/seller/catalog'); renderCatalog();
    notice('message', 'Variant added. Select it using the item’s Stock tracking field.');
  });
});
$('refresh-catalog').addEventListener('click', () => run(async () => { catalog = await api('/seller/catalog'); renderCatalog(); notice('message', 'Stock refreshed.'); }));
$('restock-return').addEventListener('click', () => {
  if (!confirm('Have you inspected all returned catalog items and confirmed they can be sold again?')) return;
  run(async () => { const value = await api(`/seller/orders/${selected.reference}/restock`, {method: 'POST'}); selectOrder(value); await refresh(); notice('message', 'Returned stock restored once.'); });
});
$('login-form').querySelector('button').disabled = false;
request('/session').then(openWorkspace).catch(error => { if (error.status !== 401) notice('login-message', error.message, true); });
