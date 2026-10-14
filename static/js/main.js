/* main.js — tiện ích dùng chung: API client, toast, modal, form, theme, tìm kiếm, sidebar */
const APP = window.APP || {};
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
const anim = fn => { if (window.gsap && !REDUCED) fn(window.gsap); };
const fmtDate = s => { if (!s) return '—'; const [y, m, d] = String(s).slice(0, 10).split('-'); return d ? `${d}/${m}/${y}` : s; };
const fmtDT = s => s ? `${fmtDate(s)} ${String(s).slice(11, 16)}` : '—';
const timeAgo = s => {
  const sec = (Date.now() - new Date(String(s).replace(' ', 'T'))) / 1000;
  if (isNaN(sec)) return '';
  if (sec < 60) return 'vừa xong'; if (sec < 3600) return `${Math.floor(sec / 60)} phút trước`;
  if (sec < 86400) return `${Math.floor(sec / 3600)} giờ trước`; if (sec < 604800) return `${Math.floor(sec / 86400)} ngày trước`;
  return fmtDate(s);
};
const isStaff = () => ['ADMIN', 'MANAGER'].includes(APP.user?.role);

/* ---------- API client: tự gắn CSRF token, chuẩn hoá lỗi ---------- */
async function api(method, url, body) {
  const headers = { 'X-CSRF-Token': APP.csrf, 'Accept': 'application/json' };
  const init = { method, headers, credentials: 'same-origin' };
  if (body instanceof FormData) init.body = body;
  else if (body !== undefined) { headers['Content-Type'] = 'application/json'; init.body = JSON.stringify(body); }
  let res;
  try { res = await fetch(url, init); } catch { throw Object.assign(new Error('Không kết nối được máy chủ'), { errors: {} }); }
  let data = null; try { data = await res.json(); } catch { /* không phải JSON */ }
  if (res.status === 401 && APP.user) { location.href = '/login'; throw new Error('Phiên đăng nhập đã hết hạn'); }
  if (!res.ok) throw Object.assign(new Error(data?.message || 'Không thể thực hiện thao tác'), { errors: data?.errors || {}, status: res.status });
  return data;
}

/* ---------- Badge / avatar ---------- */
const TONE = {
  ok: ['Có mặt', 'Đã duyệt', 'Đang hiệu lực', 'Đang làm việc', 'Hoạt động', 'Xuất sắc', 'Tốt'],
  warn: ['Đi muộn', 'Chờ duyệt', 'Sắp hết hạn', 'Đang nghỉ phép', 'Khá', 'Tạm ngưng'],
  bad: ['Vắng', 'Từ chối', 'Đã hết hạn', 'Đã nghỉ việc', 'Chưa đạt'],
  info: ['Nghỉ phép', 'Trung bình'], blue: ['ADMIN', 'MANAGER', 'LECTURER']
};
const badge = t => !t ? '<span class="muted">—</span>' : `<span class="badge ${Object.keys(TONE).find(k => TONE[k].includes(t)) || ''}">${esc(t)}</span>`;
const AV = ['#2155E8', '#0B8F64', '#B7791F', '#7C3AED', '#0E7490', '#CB2C4B', '#475569'];
function avatar(p, cls = '') {
  if (p.avatar && String(p.avatar).startsWith('/static/uploads/')) return `<img class="avatar ${cls}" src="${esc(p.avatar)}" alt="">`;
  const parts = String(p.full_name || p.name || '?').trim().split(/\s+/);
  const ini = ((parts.length > 1 ? parts[parts.length - 2][0] : '') + parts[parts.length - 1][0]).toUpperCase();
  const c = AV[[...(p.id || p.full_name || '?')].reduce((a, ch) => a + ch.charCodeAt(0), 0) % AV.length];
  return `<span class="avatar ${cls}" style="background:${c}">${esc(ini)}</span>`;
}

/* ---------- Toast ---------- */
function toast(msg, type = 'success', ms = 3600) {
  const el = document.createElement('div');
  el.className = `toast ${type}`; el.setAttribute('role', 'status');
  const ico = { success: 'fa-circle-check', error: 'fa-circle-xmark', warn: 'fa-triangle-exclamation' }[type] || 'fa-bell';
  el.innerHTML = `<i class="fa-solid ${ico} ico"></i><span>${esc(msg)}</span>`;
  $('#toasts').appendChild(el);
  anim(g => g.from(el, { x: 60, opacity: 0, duration: .35, ease: 'power3.out' }));
  setTimeout(() => { window.gsap && !REDUCED ? gsap.to(el, { opacity: 0, x: 40, duration: .25, onComplete: () => el.remove() }) : el.remove(); }, ms);
  el.onclick = () => el.remove();
}

/* ---------- Modal ---------- */
const Modal = {
  open({ title, body, size = 'md', actions = [], onMount, onClose }) {
    const el = document.createElement('div');
    el.className = 'modal-backdrop';
    el.innerHTML = `<div class="modal ${size}" role="dialog" aria-modal="true" aria-label="${esc(title)}"><header><h3>${esc(title)}</h3><button class="icon-btn" data-x aria-label="Đóng"><i class="fa-solid fa-xmark"></i></button></header><div class="modal-body">${body}</div>${actions.length ? '<footer></footer>' : ''}</div>`;
    document.body.appendChild(el); document.body.style.overflow = 'hidden';
    let closed = false;
    const ctl = {
      el, body: $('.modal-body', el),
      close(result) {
        if (closed) return; closed = true; document.removeEventListener('keydown', onKey);
        const done = () => { el.remove(); if (!$$('.modal-backdrop').length) document.body.style.overflow = ''; onClose && onClose(result); };
        window.gsap && !REDUCED ? gsap.to(el, { opacity: 0, duration: .15, onComplete: done }) : done();
      }
    };
    const onKey = e => { if (e.key === 'Escape' && el === $$('.modal-backdrop').pop()) ctl.close(); };
    document.addEventListener('keydown', onKey);
    el.addEventListener('mousedown', e => { if (e.target === el) ctl.close(); });
    $('[data-x]', el).onclick = () => ctl.close();
    const foot = $('footer', el);
    actions.forEach(a => {
      const b = document.createElement('button'); b.type = 'button'; b.className = `btn ${a.cls || 'ghost'}`; b.textContent = a.label; foot.appendChild(b);
      b.onclick = async () => {
        if (a.close) return ctl.close(false);
        b.classList.add('loading'); b.disabled = true;
        try { const r = await a.onClick(ctl); if (r !== false) ctl.close(r === undefined ? true : r); }
        finally { b.classList.remove('loading'); b.disabled = false; }
      };
    });
    anim(g => { g.from(el, { opacity: 0, duration: .18 }); g.from($('.modal', el), { y: 24, scale: .97, duration: .28, ease: 'power3.out' }); });
    onMount && onMount(ctl);
    setTimeout(() => ($('input:not([type=hidden]):not([type=file]),select,textarea', ctl.body) || $('[data-x]', el)).focus(), 60);
    return ctl;
  },
  confirm({ title, message, confirm = 'Xác nhận', danger = false }) {
    return new Promise(res => {
      let settled = false; const fin = v => { if (!settled) { settled = true; res(v); } };
      Modal.open({ title, size: 'sm', body: `<p style="margin:0">${message}</p>`, onClose: r => fin(r === true),
        actions: [{ label: 'Hủy', close: true }, { label: confirm, cls: danger ? 'danger' : 'primary', onClick: () => true }] });
    });
  },
  prompt({ title, label, placeholder = '', confirm = 'Xác nhận', cls = 'primary' }) {
    return new Promise(res => {
      let val = null;
      Modal.open({ title, size: 'sm', body: `<div class="field"><label>${esc(label)}</label><textarea id="pr-input" placeholder="${esc(placeholder)}" maxlength="300"></textarea></div>`,
        onClose: r => res(r === true ? val : null),
        actions: [{ label: 'Hủy', close: true }, { label: confirm, cls, onClick: ctl => { val = $('#pr-input', ctl.body).value.trim(); return true; } }] });
    });
  },
  info(title, html, size = 'md') { return Modal.open({ title, body: html, size, actions: [{ label: 'Đóng', close: true }] }); }
};

/* ---------- Meta + Lookups (danh mục cho select) ---------- */
const Meta = { data: null, async load() { return this.data || (this.data = await api('GET', '/api/meta')); } };
const LOOKUPS = {
  faculties: { url: '/api/faculties', v: r => r.id, l: r => r.name },
  departments: { url: '/api/departments', v: r => r.id, l: r => r.name },
  lecturers: { url: '/api/lecturers', v: r => r.id, l: r => `${r.id} – ${r.full_name}` }
};
const Lookups = {
  cache: new Map(), clear() { this.cache.clear(); },
  async get(name, params = {}) {
    const key = name + JSON.stringify(params);
    if (!this.cache.has(key)) {
      const d = LOOKUPS[name];
      const r = await api('GET', `${d.url}?${new URLSearchParams({ per_page: 500, ...params })}`);
      this.cache.set(key, r.items.map(x => ({ value: d.v(x), label: d.l(x) })));
    }
    return this.cache.get(key);
  }
};

/* ---------- FormModal: dựng form từ danh sách field, validate, hiển thị lỗi theo field ---------- */
const optHtml = (opts, sel) => opts.map(o => { const v = typeof o === 'object' ? o.value : o, l = typeof o === 'object' ? o.label : o; return `<option value="${esc(v)}" ${String(v) === String(sel) ? 'selected' : ''}>${esc(l)}</option>`; }).join('');
function fieldHtml(f, v, editing) {
  const val = v[f.name] ?? f.default ?? '';
  const dis = editing && f.readonlyOnEdit ? 'disabled' : '';
  let ctl;
  if (f.type === 'select') ctl = `<select name="${f.name}" ${dis}><option value="">— Chọn —</option>${optHtml(f._opts || f.options || [], val)}</select>`;
  else if (f.type === 'textarea') ctl = `<textarea name="${f.name}" maxlength="${f.max || 500}" ${dis}>${esc(val)}</textarea>`;
  else if (f.type === 'checkbox') ctl = `<label class="switch"><input type="checkbox" name="${f.name}" ${(v[f.name] === undefined ? f.default !== false : v[f.name]) ? 'checked' : ''}> ${esc(f.hint || 'Đang hoạt động')}</label>`;
  else if (f.type === 'avatar') ctl = `<div class="avatar-up"><span data-preview>${avatar({ avatar: val, full_name: v.full_name || 'GV' }, 'lg')}</span><div><input type="file" accept="image/png,image/jpeg,image/webp,image/gif" data-upload="${f.name}"><small class="muted">PNG/JPG/WEBP, tối đa 2MB</small></div><input type="hidden" name="${f.name}" value="${esc(val)}"></div>`;
  else ctl = `<input type="${f.type || 'text'}" name="${f.name}" value="${f.type === 'password' ? '' : esc(val)}" placeholder="${esc(f.placeholder || '')}" maxlength="${f.max || 200}" autocomplete="off" ${f.min ? `min="${f.min}"` : ''} ${dis}>`;
  const lab = f.type === 'checkbox' ? '' : `<label>${esc(f.label)}${f.required ? '<i class="req">*</i>' : ''}</label>`;
  const hint = editing && f.hintEdit ? `<small class="muted">${esc(f.hintEdit)}</small>` : '';
  return `<div class="field col-${f.col || 6}" data-name="${f.name}">${lab}${ctl}${hint}<small class="err" role="alert"></small></div>`;
}
function showErrors(form, errors) {
  $$('.field', form).forEach(x => { x.classList.remove('invalid'); $('.err', x).textContent = ''; });
  let first = null;
  for (const [k, m] of Object.entries(errors || {})) {
    const f = form.querySelector(`.field[data-name="${k}"]`);
    if (f) { f.classList.add('invalid'); $('.err', f).textContent = m; first = first || f; }
  }
  if (first) { first.scrollIntoView({ block: 'center', behavior: 'smooth' }); anim(g => g.fromTo(first, { x: -5 }, { x: 0, duration: .4, ease: 'elastic.out(1,.4)' })); }
  return !!first;
}
const FormModal = {
  open({ title, fields, values = {}, editing = false, size = 'lg', submitLabel = 'Lưu', onSubmit, successMsg }) {
    return new Promise(async resolve => {
      const role = APP.user?.role;
      fields = fields.filter(f => (!f.roles || f.roles.includes(role)) && !(editing && f.hideOnEdit) && !(!editing && f.hideOnCreate));
      for (const f of fields) if (f.lookup) f._opts = f.dependsOn && !values[f.dependsOn] ? [] : await Lookups.get(f.lookup, f.dependsOn ? { [f.dependsOn]: values[f.dependsOn] } : {});
      let result = null;
      Modal.open({
        title, size, body: `<form class="form-grid" novalidate>${fields.map(f => fieldHtml(f, values, editing)).join('')}</form>`,
        onClose: () => resolve(result),
        actions: [{ label: 'Hủy', close: true }, {
          label: submitLabel, cls: 'primary', onClick: async ctl => {
            const form = $('form', ctl.body), payload = {}, errs = {};
            for (const f of fields) {
              if (editing && f.readonlyOnEdit) continue;
              const el = form.elements[f.name]; if (!el) continue;
              if (f.type === 'checkbox') { payload[f.name] = el.checked; continue; }
              const v = el.value.trim();
              if (f.type === 'password' && editing && !v) continue;
              if (f.required && !v) errs[f.name] = 'Trường này là bắt buộc';
              payload[f.name] = v;
            }
            if (showErrors(form, errs)) return false;
            try { result = await onSubmit(payload); if (successMsg) toast(successMsg, 'success'); return true; }
            catch (e) { showErrors(form, e.errors); toast(Object.keys(e.errors || {}).length ? 'Vui lòng kiểm tra lại các trường được đánh dấu' : e.message, 'error'); return false; }
          }
        }],
        onMount: ctl => {
          const form = $('form', ctl.body);
          form.addEventListener('submit', e => { e.preventDefault(); $('footer .primary', ctl.el).click(); });
          fields.filter(f => f.dependsOn).forEach(f => {
            const parent = form.elements[f.dependsOn], sel = form.elements[f.name];
            parent?.addEventListener('change', async () => {
              const opts = parent.value ? await Lookups.get(f.lookup, { [f.dependsOn]: parent.value }) : [];
              sel.innerHTML = `<option value="">— Chọn —</option>${optHtml(opts, '')}`;
            });
          });
          $$('[data-upload]', form).forEach(inp => inp.addEventListener('change', async () => {
            if (!inp.files[0]) return; const fd = new FormData(); fd.append('file', inp.files[0]);
            try { const r = await api('POST', '/api/upload', fd); form.elements[inp.dataset.upload].value = r.url; $('[data-preview]', form).innerHTML = avatar({ avatar: r.url }, 'lg'); }
            catch (e) { toast(e.message, 'error'); inp.value = ''; }
          }));
        }
      });
    });
  }
};

/* ---------- Theme + ngôn ngữ ---------- */
const Theme = {
  get: () => document.documentElement.dataset.theme || 'light',
  set(t) {
    const h = document.documentElement; h.classList.add('theme-anim'); h.dataset.theme = t;
    try { localStorage.setItem('theme', t); } catch { }
    setTimeout(() => h.classList.remove('theme-anim'), 500);
    $$('#theme-btn i').forEach(i => i.className = `fa-solid ${t === 'dark' ? 'fa-sun' : 'fa-moon'}`);
    window.dispatchEvent(new Event('themechange'));
  },
  toggle() { this.set(this.get() === 'dark' ? 'light' : 'dark'); }
};
const I18N = { en: {
  'nav.dashboard': 'Overview', 'nav.profile': 'My profile', 'nav.lecturers': 'Lecturers', 'nav.faculties': 'Faculties', 'nav.departments': 'Departments',
  'nav.contracts': 'Contracts', 'nav.attendance': 'Attendance', 'nav.leave': 'Leave', 'nav.evaluations': 'Evaluations', 'nav.notifications': 'Notifications',
  'nav.audit': 'Audit log', 'nav.settings': 'Settings', 'ui.brand': 'HR management', 'ui.search': 'Search lecturers, faculties, contracts…' } };
function applyLang() {
  const lang = localStorage.getItem('lang') || 'vi'; document.documentElement.lang = lang;
  $$('[data-i18n]').forEach(el => { el.dataset.vi ??= el.textContent; el.textContent = (lang === 'en' && I18N.en[el.dataset.i18n]) || el.dataset.vi; });
  $$('[data-i18n-ph]').forEach(el => { el.dataset.vi ??= el.placeholder; el.placeholder = (lang === 'en' && I18N.en[el.dataset.i18nPh]) || el.dataset.vi; });
}

/* ---------- Khởi tạo khung giao diện ---------- */
document.addEventListener('DOMContentLoaded', () => {
  if (!APP.user) return;
  Theme.set(Theme.get()); applyLang();
  $$('#side-avatar,#top-avatar').forEach(e => e.outerHTML = avatar({ full_name: APP.user.full_name, id: APP.user.id }, e.id === 'top-avatar' ? 'sm' : ''));
  $('#theme-btn').onclick = () => Theme.toggle();
  $('#logout-btn').onclick = async () => { try { await api('POST', '/api/auth/logout'); } finally { location.href = '/login'; } };
  const side = $('#sidebar'), scrim = $('#scrim'), setNav = on => { side.classList.toggle('open', on); scrim.classList.toggle('on', on); };
  $('#menu-btn').onclick = () => setNav(!side.classList.contains('open')); scrim.onclick = () => setNav(false);
  anim(g => {
    g.from('.nav-link', { x: -14, opacity: 0, stagger: .035, duration: .4, ease: 'power2.out' });
    g.from('#page', { y: 12, opacity: 0, duration: .45, ease: 'power2.out', clearProps: 'all' });
  });
  // chuyển trang mượt: mờ dần rồi mới điều hướng
  document.addEventListener('click', e => {
    const a = e.target.closest('a[href]');
    if (!a || a.target || e.metaKey || e.ctrlKey || e.shiftKey || a.origin !== location.origin || a.getAttribute('href').startsWith('#') || a.hasAttribute('download') || a.pathname.startsWith('/api/')) return;
    setNav(false);
    if (!window.gsap || REDUCED) return;
    e.preventDefault(); gsap.to('#page', { opacity: 0, y: -8, duration: .16, onComplete: () => location.href = a.href });
  });
  initSearch();
});

/* ---------- Tìm kiếm toàn hệ thống ---------- */
function initSearch() {
  const input = $('#global-q'), box = $('#search-results'); let timer, seq = 0;
  const link = { lecturers: r => isStaff() ? `/lecturers/${r.id}` : '/me', faculties: r => isStaff() ? `/faculties?q=${encodeURIComponent(r.id)}` : null, departments: r => isStaff() ? `/departments?q=${encodeURIComponent(r.name)}` : null, contracts: r => isStaff() ? `/contracts?q=${encodeURIComponent(r.id)}` : null };
  const title = { lecturers: 'Giảng viên', faculties: 'Khoa', departments: 'Bộ môn', contracts: 'Hợp đồng' };
  const label = { lecturers: r => [`${esc(r.full_name)}`, `${esc(r.id)} · ${esc(r.faculty_name)} · ${esc(r.degree)}`], faculties: r => [esc(r.name), `Mã ${esc(r.id)} · ${r.lecturer_count} giảng viên`],
    departments: r => [esc(r.name), esc(r.faculty_name)], contracts: r => [`${esc(r.id)} – ${esc(r.lecturer_name)}`, `${esc(r.type)} · ${esc(r.status)}`] };
  const run = async () => {
    const q = input.value.trim(); if (!q) { box.hidden = true; return; }
    const my = ++seq; box.hidden = false; box.innerHTML = '<div class="dd-item"><span class="muted">Đang tìm…</span></div>';
    try {
      const r = await api('GET', `/api/search?q=${encodeURIComponent(q)}`); if (my !== seq) return;
      const html = Object.keys(title).map(k => r[k].length ? `<div class="dd-group">${title[k]}</div>` + r[k].map(x => { const [a, b] = label[k](x), href = link[k](x); return `<${href ? `a href="${href}"` : 'div'} class="dd-item"><div><b>${a}</b><br><small>${b}</small></div></${href ? 'a' : 'div'}>`; }).join('') : '').join('');
      box.innerHTML = `<div class="dd-list">${html || '<div class="empty" style="padding:24px"><i class="fa-regular fa-face-frown"></i>Không có kết quả phù hợp</div>'}</div>`;
    } catch (e) { box.innerHTML = `<div class="dd-item">${esc(e.message)}</div>`; }
  };
  input.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(run, 250); });
  input.addEventListener('keydown', e => { if (e.key === 'Escape') { box.hidden = true; input.blur(); } if (e.key === 'Enter') { const a = $('a.dd-item', box); if (a) location.href = a.href; } });
  document.addEventListener('click', e => { if (!e.target.closest('.global-search')) box.hidden = true; });
  document.addEventListener('keydown', e => { if (e.key === '/' && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) { e.preventDefault(); input.focus(); } });
}
