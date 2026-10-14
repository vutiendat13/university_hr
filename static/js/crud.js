/* crud.js — CrudPage: bảng dữ liệu dùng chung (tìm kiếm, lọc, sắp xếp, phân trang, thêm/sửa/xoá/xem) gọi REST API */
class CrudPage {
  constructor(cfg) {
    this.cfg = cfg; this.role = APP.user.role;
    this.root = typeof cfg.root === 'string' ? $(cfg.root) : cfg.root;
    this.st = { page: 1, per_page: cfg.perPage || 10, q: new URLSearchParams(location.search).get('q') || '', filters: { ...(cfg.defaultFilters || {}) }, sort: cfg.sort || '', order: cfg.order || '' };
    this.rows = [];
    this.can = a => (cfg.can?.[a] || []).includes(this.role);
    this.shell(); this.bind(); this.load();
  }
  get url() { return `/api/${this.cfg.resource}`; }

  shell() {
    const c = this.cfg, H = c.embedded ? 'h3' : 'h1';
    const heads = (c.headActions || []).filter(a => !a.roles || a.roles.includes(this.role));
    this.root.innerHTML = `
      <div class="page-head"><div><${H}>${esc(c.title)}</${H}>${c.subtitle ? `<p class="sub">${esc(c.subtitle)}</p>` : ''}</div>
        <div class="head-actions">${heads.map((a, i) => `<button class="btn ${a.cls || 'ghost'}" data-head="${i}"><i class="fa-solid ${a.icon}"></i> ${esc(a.label)}</button>`).join('')}
        ${this.can('create') ? `<button class="btn primary" data-act="create"><i class="fa-solid fa-plus"></i> ${esc(c.addLabel || 'Thêm mới')}</button>` : ''}</div></div>
      <div data-banner></div>
      <div class="card">
        <div class="toolbar"><div class="search-inline"><i class="fa-solid fa-magnifying-glass"></i><input type="search" placeholder="${esc(c.searchPlaceholder || 'Tìm kiếm…')}" value="${esc(this.st.q)}" aria-label="Tìm kiếm"></div>
          ${c.filters?.length ? '<button class="btn ghost" data-act="toggle-filters"><i class="fa-solid fa-sliders"></i> Bộ lọc <span class="count" hidden></span></button>' : ''}
          <span class="muted" data-total></span></div>
        <div class="filters" hidden></div>
        <div class="table-wrap"></div><div class="pager"></div></div>`;
    this.$wrap = $('.table-wrap', this.root); this.$pager = $('.pager', this.root); this.$filters = $('.filters', this.root);
    if (c.filters?.length) this.buildFilters();
  }

  async buildFilters() {
    const fs = this.cfg.filters.filter(f => !f.roles || f.roles.includes(this.role));
    for (const f of fs) if (f.lookup) f._opts = await Lookups.get(f.lookup);
    this.$filters.innerHTML = fs.map(f => `<div class="field"><label>${esc(f.label)}</label>${f.type === 'date' || f.type === 'month'
      ? `<input type="${f.type}" name="${f.name}">`
      : `<select name="${f.name}"><option value="">Tất cả</option>${optHtml(f._opts || f.options || [], '')}</select>`}</div>`).join('') +
      '<div class="f-actions"><button class="btn primary sm" data-act="apply">Áp dụng</button><button class="btn ghost sm" data-act="reset">Đặt lại</button></div>';
    this.filterDefs = fs;
  }

  bind() {
    const root = this.root; let t;
    $('.search-inline input', root).addEventListener('input', e => { clearTimeout(t); t = setTimeout(() => { this.st.q = e.target.value.trim(); this.st.page = 1; this.load(); }, 280); });
    root.addEventListener('click', e => {
      const b = e.target.closest('[data-act],[data-page],[data-sort],[data-head]'); if (!b || !root.contains(b)) return;
      if (b.dataset.head !== undefined) return this.cfg.headActions.filter(a => !a.roles || a.roles.includes(this.role))[+b.dataset.head].run(this);
      if (b.dataset.page) { this.st.page = +b.dataset.page; return this.load(); }
      if (b.dataset.sort) { const k = b.dataset.sort; this.st.order = this.st.sort === k && this.st.order !== 'desc' ? 'desc' : 'asc'; this.st.sort = k; return this.load(); }
      const id = b.dataset.id, row = this.rows.find(r => String(r.id) === id);
      switch (b.dataset.act) {
        case 'create': return this.openForm(null);
        case 'edit': return this.openForm(row);
        case 'delete': return this.remove(row);
        case 'view': return this.view(row);
        case 'toggle-filters': this.$filters.hidden = !this.$filters.hidden; return;
        case 'apply': return this.applyFilters();
        case 'reset': $$('input,select', this.$filters).forEach(i => i.value = ''); return this.applyFilters();
        default: { const a = (this.cfg.actions || []).find(x => x.key === b.dataset.act); if (a) return a.run(row, this); }
      }
    });
    this.$filters.addEventListener('keydown', e => { if (e.key === 'Enter') this.applyFilters(); });
  }

  applyFilters() {
    this.st.filters = {};
    $$('input,select', this.$filters).forEach(i => { if (i.value) this.st.filters[i.name] = i.value; });
    const n = Object.keys(this.st.filters).length, cnt = $('.count', this.root);
    if (cnt) { cnt.hidden = !n; cnt.textContent = n; }
    this.st.page = 1; this.load();
  }

  skeleton() {
    this.$wrap.innerHTML = `<div style="padding:16px;display:grid;gap:12px">${'<div class="skeleton" style="height:38px"></div>'.repeat(6)}</div>`;
  }

  async load() {
    this.skeleton();
    const p = new URLSearchParams({ page: this.st.page, per_page: this.st.per_page, ...this.st.filters });
    if (this.st.q) p.set('q', this.st.q); if (this.st.sort) { p.set('sort', this.st.sort); p.set('order', this.st.order); }
    try {
      const d = await api('GET', `${this.url}?${p}`);
      this.rows = d.items; this.data = d; this.renderTable(); this.renderPager();
      $('[data-total]', this.root).textContent = `${d.total} bản ghi`;
      if (this.cfg.banner) { const h = await this.cfg.banner(this); $('[data-banner]', this.root).innerHTML = h || ''; }
      anim(g => g.from($$('tbody tr', this.$wrap), { opacity: 0, y: 8, stagger: .02, duration: .3, clearProps: 'all' }));
    } catch (e) { this.$wrap.innerHTML = `<div class="empty"><i class="fa-solid fa-circle-exclamation"></i>${esc(e.message)}</div>`; toast(e.message, 'error'); }
  }

  actionsFor(r) {
    const c = this.cfg, out = [];
    if (c.viewUrl) out.push(`<a class="icon-btn" href="${esc(c.viewUrl(r))}" title="Xem" aria-label="Xem"><i class="fa-solid fa-eye"></i></a>`);
    else if (c.viewable !== false) out.push(`<button class="icon-btn" data-act="view" data-id="${esc(r.id)}" title="Xem" aria-label="Xem"><i class="fa-solid fa-eye"></i></button>`);
    (c.actions || []).filter(a => (!a.roles || a.roles.includes(this.role)) && (!a.show || a.show(r)))
      .forEach(a => out.push(`<button class="icon-btn ${a.cls || ''}" data-act="${a.key}" data-id="${esc(r.id)}" title="${esc(a.title)}" aria-label="${esc(a.title)}"><i class="fa-solid ${a.icon}"></i></button>`));
    if (this.can('update') && (!c.canEditRow || c.canEditRow(r))) out.push(`<button class="icon-btn" data-act="edit" data-id="${esc(r.id)}" title="Sửa" aria-label="Sửa"><i class="fa-solid fa-pen"></i></button>`);
    if (this.can('delete') && (!c.canDeleteRow || c.canDeleteRow(r))) out.push(`<button class="icon-btn del" data-act="delete" data-id="${esc(r.id)}" title="Xóa" aria-label="Xóa"><i class="fa-solid fa-trash"></i></button>`);
    return out.join('');
  }

  renderTable() {
    const c = this.cfg, page = this.data.page, per_page = this.st.per_page;
    if (!this.rows.length) {
      this.$wrap.innerHTML = `<div class="empty"><i class="fa-regular fa-folder-open"></i><p>${this.st.q || Object.keys(this.st.filters).length ? 'Không có kết quả phù hợp với bộ lọc hiện tại.' : esc(c.emptyText || 'Chưa có dữ liệu.')}</p>${this.can('create') && !this.st.q ? `<button class="btn primary" data-act="create">${esc(c.addLabel || 'Thêm mới')}</button>` : ''}</div>`; return;
    }
    const ind = this.st.sort ? (this.st.order === 'desc' ? ' ▾' : ' ▴') : '';
    this.$wrap.innerHTML = `<table class="table"><thead><tr>${c.index === false ? '' : '<th style="width:56px">STT</th>'}${c.columns.map(col =>
      `<th ${col.sort ? `data-sort="${col.sort === true ? col.key : col.sort}"` : ''}>${esc(col.label)}${this.st.sort === (col.sort === true ? col.key : col.sort) && col.sort ? ind : ''}</th>`).join('')}<th style="text-align:right">Thao tác</th></tr></thead><tbody>${this.rows.map((r, i) =>
      `<tr>${c.index === false ? '' : `<td data-label="STT">${(page - 1) * per_page + i + 1}</td>`}${c.columns.map(col => `<td data-label="${esc(col.label)}" ${col.wrap ? 'class="wrap"' : ''}>${col.render ? col.render(r) : esc(r[col.key] ?? '')}</td>`).join('')}<td class="row-actions">${this.actionsFor(r)}</td></tr>`).join('')}</tbody></table>`;
  }

  renderPager() {
    const { page, pages, total } = this.data, per = this.st.per_page;
    if (total <= per) { this.$pager.innerHTML = `<span class="muted">${total ? `Hiển thị ${total}/${total}` : ''}</span>`; return; }
    const from = (page - 1) * per + 1, to = Math.min(total, page * per);
    const nums = []; for (let i = Math.max(1, page - 2); i <= Math.min(pages, page + 2); i++) nums.push(i);
    this.$pager.innerHTML = `<span class="muted">Hiển thị ${from}–${to} / ${total}</span><div class="pages">
      <button data-page="${page - 1}" ${page <= 1 ? 'disabled' : ''} aria-label="Trang trước"><i class="fa-solid fa-chevron-left"></i></button>
      ${nums[0] > 1 ? '<button data-page="1">1</button>' + (nums[0] > 2 ? '<span class="muted">…</span>' : '') : ''}
      ${nums.map(n => `<button data-page="${n}" class="${n === page ? 'on' : ''}">${n}</button>`).join('')}
      ${nums.at(-1) < pages ? (nums.at(-1) < pages - 1 ? '<span class="muted">…</span>' : '') + `<button data-page="${pages}">${pages}</button>` : ''}
      <button data-page="${page + 1}" ${page >= pages ? 'disabled' : ''} aria-label="Trang sau"><i class="fa-solid fa-chevron-right"></i></button></div>`;
  }

  /* ---- thêm / sửa ---- */
  async openForm(row) {
    const c = this.cfg, editing = !!row, noun = c.noun || 'bản ghi';
    const res = await FormModal.open({
      title: `${editing ? 'Sửa' : 'Thêm'} ${noun}`, fields: c.fields, values: row || c.defaults || {}, editing, size: c.formSize || 'lg',
      successMsg: `${editing ? 'Cập nhật' : 'Thêm'} ${noun} thành công`,
      onSubmit: p => api(editing ? 'PUT' : 'POST', editing ? `${this.url}/${encodeURIComponent(row.id)}` : this.url, c.beforeSubmit ? c.beforeSubmit(p, row) : p)
    });
    if (res) { Lookups.clear(); this.load(); c.afterChange && c.afterChange(this); }
  }

  async remove(row) {
    const c = this.cfg;
    if (!await Modal.confirm({ title: `Xóa ${c.noun || 'bản ghi'}?`, message: `Bạn có chắc muốn xóa <b>${esc(c.nameOf ? c.nameOf(row) : row.id)}</b>? Thao tác này không thể hoàn tác.`, confirm: 'Xóa', danger: true })) return;
    try { await api('DELETE', `${this.url}/${encodeURIComponent(row.id)}`); toast(`Xóa ${c.noun || 'bản ghi'} thành công`); Lookups.clear(); this.load(); }
    catch (e) { toast(e.message, 'error'); }
  }

  view(row) {
    const c = this.cfg;
    const body = `<dl class="kv">${c.columns.filter(x => x.detail !== false).map(col => `<div><dt>${esc(col.label)}</dt><dd>${col.render ? col.render(row) : esc(row[col.key] ?? '—')}</dd></div>`).join('')}</dl>${c.detail ? c.detail(row) : ''}`;
    Modal.info(`Chi tiết ${c.noun || 'bản ghi'}`, body, 'lg');
  }
}
