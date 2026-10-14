/* notifications.js — chuông thông báo trên topbar + trang /notifications */
const NOTI_ICON = { contract: 'fa-file-circle-exclamation', leave: 'fa-umbrella-beach', evaluation: 'fa-star', system: 'fa-bell' };
const NOTI_TYPE = { contract: 'Hợp đồng', leave: 'Nghỉ phép', evaluation: 'Đánh giá', system: 'Hệ thống' };
const Notif = {
  unread: null,
  item: n => `<a class="dd-item ${n.read ? '' : 'unread'}" href="${esc(n.link || '#')}" data-nid="${esc(n.id)}"><span class="n-ico ${esc(n.type)}"><i class="fa-solid ${NOTI_ICON[n.type] || 'fa-bell'}"></i></span><div><div>${esc(n.message)}</div><small>${esc(NOTI_TYPE[n.type] || '')} · ${timeAgo(n.created_at)}</small></div></a>`,
  async refresh(first) {
    try {
      const d = await api('GET', '/api/notifications');
      const dot = $('#bell-dot'), nav = $('#nav-unread');
      [dot, nav].forEach(e => { if (e) { e.hidden = !d.unread; e.textContent = d.unread > 99 ? '99+' : d.unread; } });
      $('#notif-list').innerHTML = d.items.slice(0, 8).map(Notif.item).join('') || '<div class="empty" style="padding:28px"><i class="fa-regular fa-bell-slash"></i>Chưa có thông báo</div>';
      if (!first && this.unread !== null && d.unread > this.unread && localStorage.getItem('toastNotif') !== '0') {
        const n = d.items.find(x => !x.read); if (n) toast(`🔔 ${n.message}`, 'warn', 5000);
      }
      this.unread = d.unread; return d;
    } catch { /* bỏ qua lỗi mạng khi polling */ }
  },
  async markAll() { await api('POST', '/api/notifications/read-all'); toast('Đã đánh dấu đã đọc tất cả'); await this.refresh(true); }
};
document.addEventListener('DOMContentLoaded', () => {
  if (!APP.user) return;
  const panel = $('#notif-panel');
  $('#bell-btn').onclick = e => { e.stopPropagation(); panel.hidden = !panel.hidden; if (!panel.hidden) anim(g => g.from(panel, { y: -8, opacity: 0, duration: .2 })); };
  document.addEventListener('click', e => { if (!e.target.closest('.user-menu')) panel.hidden = true; });
  $('#notif-readall').onclick = () => Notif.markAll();
  $('#notif-list').addEventListener('click', async e => {
    const a = e.target.closest('[data-nid]'); if (!a) return;
    try { await api('POST', `/api/notifications/${a.dataset.nid}/read`); } catch { }
  });
  Notif.refresh(true); setInterval(() => document.hidden || Notif.refresh(), 60000);
  if ($('#notif-page')) initNotifPage();
});

function initNotifPage() {
  let type = '', unreadOnly = false;
  const f = $('#np-filters'), box = $('#notif-page');
  const chips = [['', 'Tất cả'], ['unread', 'Chưa đọc'], ...Object.entries(NOTI_TYPE)];
  f.innerHTML = chips.map(([k, l]) => `<button class="btn sm ${k === '' ? 'primary' : 'ghost'}" data-chip="${k}">${l}</button>`).join('');
  async function render() {
    const q = new URLSearchParams(); if (type) q.set('type', type); if (unreadOnly) q.set('unread', '1');
    const d = await api('GET', `/api/notifications?${q}`);
    box.innerHTML = d.items.length ? d.items.map(n => `<div class="li" style="${n.read ? '' : 'background:color-mix(in srgb,var(--blue-soft) 55%,transparent)'}">
      <span class="n-ico ${esc(n.type)}"><i class="fa-solid ${NOTI_ICON[n.type] || 'fa-bell'}"></i></span>
      <div class="grow"><a href="${esc(n.link || '#')}" data-nid="${esc(n.id)}" style="color:inherit"><b style="font-weight:${n.read ? 500 : 700}">${esc(n.message)}</b></a><small>${esc(NOTI_TYPE[n.type] || '')} · ${fmtDT(n.created_at)} (${timeAgo(n.created_at)})</small></div>
      ${n.read ? '' : `<button class="icon-btn" data-read="${esc(n.id)}" title="Đánh dấu đã đọc" aria-label="Đánh dấu đã đọc"><i class="fa-solid fa-check"></i></button>`}
      <button class="icon-btn del" data-del="${esc(n.id)}" title="Xóa" aria-label="Xóa thông báo"><i class="fa-solid fa-trash"></i></button></div>`).join('')
      : '<div class="empty"><i class="fa-regular fa-bell-slash"></i>Không có thông báo nào.</div>';
  }
  f.onclick = e => { const b = e.target.closest('[data-chip]'); if (!b) return; const k = b.dataset.chip; unreadOnly = k === 'unread'; type = unreadOnly ? '' : k;
    $$('button', f).forEach(x => { x.classList.toggle('primary', x === b); x.classList.toggle('ghost', x !== b); }); render(); };
  box.onclick = async e => {
    const r = e.target.closest('[data-read]'), d = e.target.closest('[data-del]'), a = e.target.closest('[data-nid]');
    try {
      if (r) { await api('POST', `/api/notifications/${r.dataset.read}/read`); toast('Đã đánh dấu đã đọc'); }
      else if (d) { await api('DELETE', `/api/notifications/${d.dataset.del}`); toast('Đã xóa thông báo'); }
      else if (a) { api('POST', `/api/notifications/${a.dataset.nid}/read`); return; } else return;
      render(); Notif.refresh(true);
    } catch (err) { toast(err.message, 'error'); }
  };
  $('#np-readall').onclick = async () => { await Notif.markAll(); render(); };
  render();
}
