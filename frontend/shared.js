export const $ = (id) => document.getElementById(id);
export const money = (paisa) => new Intl.NumberFormat('en-BD', {style: 'currency', currency: 'BDT'}).format(paisa / 100);
export function node(tag, text, className = '') {
  const element = document.createElement(tag);
  element.textContent = text;
  element.className = className;
  return element;
}
export function notice(id, text = '', error = false) {
  $(id).textContent = text;
  $(id).classList.toggle('error', error);
}
export async function request(path, options = {}) {
  const response = await fetch(path, {credentials: 'same-origin', ...options, headers: {'Content-Type': 'application/json', ...options.headers}});
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    const detail = Array.isArray(data?.detail) ? data.detail.map(e => `${e.loc.at(-1)}: ${e.msg}`).join('; ') : data?.detail;
    const error = new Error(detail || 'Something went wrong. Please try again.');
    error.status = response.status;
    throw error;
  }
  return data;
}
export function showItems(container, items) {
  container.replaceChildren();
  for (const item of items) {
    const row = node('div', '', 'buyer-item');
    row.append(node('strong', item.product), node('p', [item.size && `Size: ${item.size}`, item.color && `Color: ${item.color}`].filter(Boolean).join(' · ')));
    const price = node('div', '', 'price-row');
    price.append(node('span', `${item.quantity} × ${money(item.unit_price_paisa)}`), node('span', money(item.quantity * item.unit_price_paisa)));
    row.append(price); container.append(row);
  }
}
export function showHistory(container, history) {
  container.replaceChildren();
  for (const entry of history) {
    const li = node('li', entry.event === 'courier_updated' ? 'Courier details updated' : entry.event === 'restocked' ? 'Returned items restocked' : entry.status.charAt(0).toUpperCase() + entry.status.slice(1));
    const time = node('time', new Date(entry.at).toLocaleString());
    time.dateTime = entry.at; li.append(time); container.append(li);
  }
}
