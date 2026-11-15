import {$, money, request, notice, showItems, showHistory} from './shared.js';

const tracking = location.pathname.startsWith('/track/');
const token = encodeURIComponent(location.pathname.split('/').pop());
let summary;
let submitting = false;

const STEPS = ['confirmed', 'packed', 'shipped', 'delivered'];

function renderTrackingStepper(status) {
  const currentIdx = STEPS.indexOf(status);
  const isSpecial = status === 'cancelled' || status === 'returned';

  document.querySelectorAll('.stepper-step').forEach((el) => {
    const stepName = el.dataset.step;
    const stepIdx = STEPS.indexOf(stepName);
    const node = el.querySelector('.stepper-node');

    if (isSpecial) {
      el.className = 'stepper-step inactive';
      return;
    }

    if (stepIdx < currentIdx) {
      el.className = 'stepper-step completed';
      if (node) node.innerHTML = '<span class="node-icon">✓</span>';
    } else if (stepIdx === currentIdx) {
      el.className = 'stepper-step active';
      if (node) node.innerHTML = `<span class="node-icon">${stepIdx + 1}</span>`;
    } else {
      el.className = 'stepper-step pending';
      if (node) node.innerHTML = `<span class="node-icon">${stepIdx + 1}</span>`;
    }
  });

  document.querySelectorAll('.stepper-line').forEach((line) => {
    const lineNum = parseInt(line.dataset.line, 10);
    line.className = 'stepper-line' + (lineNum <= currentIdx && !isSpecial ? ' active' : '');
  });
}

function showReceipt(receipt) {
  showSummary(receipt);
  $('buyer-title').textContent = 'All set. Your order is confirmed.';
  $('buyer-intro').textContent = 'Follow your parcel updates using the tracking link below.';
  $('delivery-panel').hidden = true;
  $('receipt-panel').hidden = false;
  $('tracking-link').href = receipt.tracking_path;

  const copyBtn = $('copy-tracking-btn');
  if (copyBtn) {
    const fullUrl = location.origin + receipt.tracking_path;
    copyBtn.onclick = async () => {
      try {
        await navigator.clipboard.writeText(fullUrl);
        const textSpan = $('copy-btn-text');
        if (textSpan) textSpan.textContent = '✓ লিংক কপি হয়েছে (Copied!)';
        setTimeout(() => {
          if (textSpan) textSpan.textContent = 'Copy tracking link · ট্র্যাকিং লিংক কপি করুন';
        }, 2500);
      } catch {
        prompt('Copy this link:', fullUrl);
      }
    };
  }
  notice('buyer-message');
}

function showSummary(value) {
  $('buyer-content').hidden = false;
  $('shop-name').textContent = value.shop_name;
  $('buyer-reference').textContent = 'Reference: ' + value.reference;
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
      $('buyer-eyebrow').textContent = 'ORDER TRACKING · অর্ডারের বর্তমান অবস্থা';
      $('buyer-intro').textContent = 'Keep this private link to check your order’s delivery progress.';
      $('delivery-panel').hidden = true;
      $('tracking-panel').hidden = false;
      const statusText = summary.status.charAt(0).toUpperCase() + summary.status.slice(1);
      $('tracking-status').innerHTML = `<span class="badge ${summary.status}">${statusText}</span>`;
      renderTrackingStepper(summary.status);
      showHistory($('tracking-history'), summary.history);
      $('shipment-details').hidden = !summary.shipment;
      $('courier-info').textContent = summary.shipment ? `${summary.shipment.courier_name} · Consignment/Ref: ${summary.shipment.tracking_reference}` : '';
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

function cleanBanglaDigits(text) {
  const map = {'০':'0','১':'1','২':'2','৩':'3','৪':'4','৫':'5','৬':'6','৭':'7','৮':'8','৯':'9'};
  return text.replace(/[০-৯]/g, (d) => map[d] || d).replace(/[\s\-_]/g, '');
}

const phoneInput = $('buyer-phone');
if (phoneInput) {
  phoneInput.addEventListener('input', (e) => {
    const cleaned = cleanBanglaDigits(e.target.value);
    if (cleaned !== e.target.value) {
      e.target.value = cleaned;
    }
    const hint = $('phone-hint');
    if (!hint) return;
    if (cleaned.length === 11 && /^01[3-9]\d{8}$/.test(cleaned)) {
      hint.textContent = '✓ সঠিক মোবাইল নম্বর (Valid 11-digit number)';
      hint.className = 'field-hint success';
    } else if (cleaned.length > 0 && cleaned.length < 11) {
      hint.textContent = `১১ ডিজিটের নম্বর লিখুন (${cleaned.length}/11)`;
      hint.className = 'field-hint';
    } else if (cleaned.length > 11) {
      hint.textContent = 'নম্বরটি ১১ ডিজিটের বেশি হতে পারবে না';
      hint.className = 'field-hint warning';
    } else {
      hint.textContent = '১১ ডিজিটের সচল নম্বর (ডেলিভারির সময় কল করা হবে)';
      hint.className = 'field-hint';
    }
  });
}

$('buyer-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (submitting || !summary) return;
  const form = new FormData(event.currentTarget);
  const rawPhone = cleanBanglaDigits((form.get('phone') || '').trim());
  const name = (form.get('customer_name') || '').trim();
  const address = (form.get('address') || '').trim();

  if (!name) {
    notice('buyer-message', 'অনুগ্রহ করে আপনার নাম লিখুন (Please enter your name)', true);
    $('buyer-name')?.focus();
    return;
  }
  if (!rawPhone || !/^01[3-9]\d{8}$/.test(rawPhone)) {
    notice('buyer-message', 'সঠিক ১১ ডিজিটের মোবাইল নম্বর দিন (যেমন: 01712345678)', true);
    $('buyer-phone')?.focus();
    return;
  }
  if (!address || address.length < 5) {
    notice('buyer-message', 'সম্পূর্ণ ডেলিভারি ঠিকানা লিখুন (বাসা, রোড, থানা, জেলা)', true);
    $('buyer-address')?.focus();
    return;
  }

  const body = {
    version: summary.version,
    customer_name: name,
    phone: rawPhone,
    address: address
  };
  submitting = true;
  $('buyer-fields').disabled = true;
  $('confirm-order').innerHTML = '<span class="spinner"></span> Confirming order…';
  notice('buyer-message');
  try {
    const receipt = await request(`/checkout/${token}/confirm`, {method: 'POST', body: JSON.stringify(body)});
    showReceipt(receipt);
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
      $('confirm-order').innerHTML = '<span class="btn-text">Confirm order · অর্ডার নিশ্চিত করুন</span><span class="btn-arrow" aria-hidden="true">→</span>';
    }
  }
});

$('refresh-tracking').addEventListener('click', load);
load();
