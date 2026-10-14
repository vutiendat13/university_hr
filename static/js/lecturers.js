/* lecturers.js — trang hồ sơ giảng viên (7 tab) */
(async function () {
  const root = $('#detail-root'), id = root.dataset.id, role = APP.user.role;
  const M = await Meta.load();
  let P;
  const tabs = [['info', 'Thông tin'], ['work', 'Công tác'], ['contracts', 'Hợp đồng'], ['attendance', 'Chấm công'], ['leave', 'Nghỉ phép'], ['evals', 'Đánh giá'], ['history', 'Lịch sử']];
  const kv = rows => `<dl class="kv">${rows.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${v ?? '—'}</dd></div>`).join('')}</dl>`;
  const table = (cols, rows, empty) => rows.length ? `<div class="table-wrap" style="border:0"><table class="table"><thead><tr>${cols.map(c => `<th>${esc(c[0])}</th>`).join('')}</tr></thead><tbody>${rows.map(r => `<tr>${cols.map(c => `<td data-label="${esc(c[0])}">${c[1](r)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>` : `<div class="empty"><i class="fa-regular fa-folder-open"></i>${empty}</div>`;
  const panels = () => {
    const l = P.lecturer;
    return {
      info: kv([['Họ và tên', esc(l.full_name)], ['Mã giảng viên', esc(l.id)], ['Giới tính', esc(l.gender)], ['Ngày sinh', `${fmtDate(l.dob)} (${l.age} tuổi)`], ['CCCD', esc(l.cccd)], ['Email', esc(l.email)], ['Số điện thoại', esc(l.phone)], ['Địa chỉ', esc(l.address || '—')]]),
      work: kv([['Khoa', esc(l.faculty_name)], ['Bộ môn', esc(l.department_name)], ['Chức vụ', esc(l.position)], ['Trình độ', badge(l.degree)], ['Ngày vào trường', fmtDate(l.join_date)], ['Thâm niên', `${P.seniority_years ?? '—'} năm`], ['Loại hợp đồng', esc(l.contract_type)], ['Trạng thái', badge(l.status)]]),
      contracts: table([['Mã HĐ', c => esc(c.id)], ['Loại', c => esc(c.type)], ['Bắt đầu', c => fmtDate(c.start_date)], ['Kết thúc', c => c.end_date ? fmtDate(c.end_date) : 'Không thời hạn'], ['Trạng thái', c => badge(c.status)]], P.contracts, 'Chưa có hợp đồng.'),
      attendance: table([['Ngày', a => fmtDate(a.date)], ['Giờ vào', a => esc(a.check_in || '—')], ['Giờ ra', a => esc(a.check_out || '—')], ['Trạng thái', a => badge(a.status)], ['Ghi chú', a => esc(a.note)]], P.attendance, 'Chưa có dữ liệu chấm công.'),
      leave: table([['Mã đơn', r => esc(r.id)], ['Loại', r => esc(r.type)], ['Từ ngày', r => fmtDate(r.from_date)], ['Đến ngày', r => fmtDate(r.to_date)], ['Lý do', r => esc(r.reason)], ['Trạng thái', r => badge(r.status)]], P.leave, 'Chưa có đơn nghỉ phép.'),
      evals: table([['Kỳ', e => esc(e.period)], ['Điểm TB', e => scoreBar(e.avg)], ['Xếp loại', e => badge(e.grade)], ['Nhận xét', e => esc(e.comment)]], P.evaluations, 'Chưa có đánh giá.'),
      history: P.history.length ? `<ul class="timeline">${P.history.map(h => `<li><b>${esc(h.action)}</b> bởi ${esc(h.user)} <small class="muted">· ${fmtDT(h.timestamp)}</small></li>`).join('')}</ul>` : '<div class="empty"><i class="fa-regular fa-clock"></i>Chưa có lịch sử thao tác.</div>'
    };
  };
  async function load(tab = 'info') {
    try { P = await api('GET', `/api/lecturers/${encodeURIComponent(id)}/profile`); } catch (e) { root.innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
    const l = P.lecturer, pn = panels();
    root.innerHTML = `
      <div class="page-head"><div>${isStaff() ? '<a href="/lecturers"><i class="fa-solid fa-arrow-left"></i> Danh sách giảng viên</a>' : ''}</div>
        <div class="head-actions"><button class="btn ghost" onclick="print()"><i class="fa-solid fa-print"></i> In hồ sơ</button>
          <button class="btn primary" id="edit-btn"><i class="fa-solid fa-pen"></i> ${isStaff() ? 'Sửa hồ sơ' : 'Cập nhật thông tin liên hệ'}</button>
          ${role === 'ADMIN' ? '<button class="btn danger" id="del-btn"><i class="fa-solid fa-trash"></i> Xóa</button>' : ''}</div></div>
      <div class="card card-pad row" style="gap:22px;margin-bottom:18px" id="hero-card">${avatar(l, 'lg')}
        <div style="flex:1;min-width:220px"><h1 style="font-size:24px">${esc(l.full_name)}</h1><p class="muted" style="margin:4px 0 10px">${esc(l.position)} · ${esc(l.faculty_name)}</p>
          <div class="row" style="gap:8px">${badge(l.status)}${badge(l.degree)}<span class="badge info">Mã GV: ${esc(l.id)}</span></div></div>
        <div class="stack" style="gap:6px"><span><i class="fa-regular fa-envelope"></i> ${esc(l.email)}</span><span><i class="fa-solid fa-phone"></i> ${esc(l.phone)}</span><span><i class="fa-regular fa-building"></i> ${esc(l.department_name)}</span></div></div>
      <div class="card"><div class="tabs" role="tablist" style="padding:0 12px;margin:0">${tabs.map(([k, t]) => `<button class="tab ${k === tab ? 'on' : ''}" data-tab="${k}" role="tab">${t}</button>`).join('')}</div><div class="card-pad" id="tab-body">${pn[tab]}</div></div>`;
    anim(g => g.from('#hero-card', { y: 14, opacity: 0, duration: .45 }));
    $$('.tab', root).forEach(b => b.onclick = () => { $$('.tab', root).forEach(x => x.classList.toggle('on', x === b)); const body = $('#tab-body'); body.innerHTML = panels()[b.dataset.tab]; anim(g => g.from(body, { opacity: 0, y: 6, duration: .25 })); });
    $('#edit-btn').onclick = async () => {
      const self = !isStaff(), fields = Pages.lecturerFields(M).filter(f => !self || ['email', 'phone', 'address', 'avatar'].includes(f.name));
      const r = await FormModal.open({ title: self ? 'Cập nhật thông tin liên hệ' : 'Sửa giảng viên', fields, values: l, editing: true, successMsg: 'Cập nhật hồ sơ thành công', onSubmit: p => api('PUT', `/api/lecturers/${encodeURIComponent(id)}`, p) });
      if (r) { Lookups.clear(); load($('.tab.on', root)?.dataset.tab); }
    };
    const del = $('#del-btn');
    if (del) del.onclick = async () => {
      if (!await Modal.confirm({ title: 'Xóa giảng viên?', message: `Xóa <b>${esc(l.full_name)}</b> sẽ xóa cả hợp đồng, chấm công, đơn nghỉ phép, đánh giá và tài khoản liên quan. Không thể hoàn tác.`, confirm: 'Xóa', danger: true })) return;
      try { await api('DELETE', `/api/lecturers/${encodeURIComponent(id)}`); toast('Xóa giảng viên thành công'); setTimeout(() => location.href = '/lecturers', 700); } catch (e) { toast(e.message, 'error'); }
    };
  }
  load();
})();
