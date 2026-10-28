import {$, money, request, notice, showItems, showHistory} from './shared.js';

const tracking = location.pathname.startsWith('/track/');
const token = encodeURIComponent(location.pathname.split('/').pop());
let summary;
let submitting = false;

function showReceipt(receipt) {
  showSummary(receipt);
  $('buyer-title').textContent = 'All set. Your order is confirmed.';
  $('buyer-intro').textContent = 'Follow your order using the link below.';
  $('delivery-panel').hidden = true;
  $('receipt-panel').hidden = false;
  $('tracking-link').href = receipt.tracking_path;
  notice('buyer-message');
}

function showSummary(value) {
  $('buyer-content').hidden = false;
  $('shop-name').textContent = value.shop_name;
  $('buyer-reference').textContent = value.reference;
  $('delivery-price').textContent = money(value.delivery_charge_paisa);
  $('buyer-total').textContent = money(value.total_paisa);
  showItems($('buyer-items'), value.items);
}

async function load() {
  try {
    summary = await request(tracking ? `/api/tracking/${token}` : `/checkout/${token}`);
    showSummary(summary);
    if (tracking) {
      $('buyer-title').textContent = 'Your order, step by step.';
      $('buyer-eyebrow').textContent = 'ORDER TRACKING · অর্ডারের আপডেট';
      $('buyer-intro').textContent = 'Keep this private link to check your order’s progress.';
      $('delivery-panel').hidden = true;
      $('tracking-panel').hidden = false;
      $('tracking-status').textContent = summary.status.charAt(0).toUpperCase() + summary.status.slice(1);
      showHistory($('tracking-history'), summary.history);
      $('shipment-details').hidden = !summary.shipment;
      $('courier-info').textContent = summary.shipment ? `${summary.shipment.courier_name} · ${summary.shipment.tracking_reference}` : '';
    }
    notice('buyer-message');
  } catch (error) {
    if (!tracking && error.status === 410) {
      try { showReceipt(await request(`/checkout/${token}/receipt`)); return; }
      catch { /* A revoked or expired draft has no receipt. */ }
    }
    $('buyer-content').hidden = true;
    notice('buyer-message', error.message, true);
  }
}

$('buyer-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (submitting || !summary) return;
  const form = new FormData(event.currentTarget);
  const body = {version: summary.version, customer_name: form.get('customer_name').trim(), phone: form.get('phone').trim(), address: form.get('address').trim()};
  submitting = true;
  $('buyer-fields').disabled = true;
  $('confirm-order').textContent = 'Confirming…';
  notice('buyer-message');
  try {
    const receipt = await request(`/checkout/${token}/confirm`, {method: 'POST', body: JSON.stringify(body)});
    showReceipt(receipt);
    // Keep no buyer details in storage. The receipt itself contains no contact data.
    event.target.reset();
  } catch (error) {
    notice('buyer-message', error.message + (error.status ? '' : ' Your details are still here. Retry to recover the same order.'), true);
    if (error.status === 410 || error.status === 409) {
      $('confirm-order').textContent = 'Ask the seller for an updated link';
      return;
    }
  } finally {
    submitting = false;
    if (!$('confirm-order').textContent.startsWith('Ask')) {
      $('buyer-fields').disabled = false;
      $('confirm-order').textContent = 'Confirm order · অর্ডার নিশ্চিত করুন';
    }
  }
});
$('refresh-tracking').addEventListener('click', load);
load();
