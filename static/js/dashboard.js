/* dashboard.js — tổng quan: cảnh 3D, thẻ thống kê, biểu đồ, danh sách việc cần xử lý */
(function () {
  const staff = isStaff();
  const countUp = () => $$('.num[data-n]').forEach(el => {
    const n = +el.dataset.n, o = { v: 0 };
    window.gsap && !REDUCED ? gsap.to(o, { v: n, duration: 1, ease: 'power2.out', onUpdate: () => el.textContent = Math.round(o.v) }) : el.textContent = n;
  });
  const statCard = (ico, tone, label, n, raw) => `<div class="card stat ${tone}"><span class="ico"><i class="fa-solid ${ico}"></i></span><span class="num" ${raw === undefined ? `data-n="${n}"` : ''}>${raw === undefined ? 0 : esc(raw)}</span><span class="lbl">${esc(label)}</span></div>`;
  const reveal = () => anim(g => g.from('#stats .stat', { y: 18, opacity: 0, stagger: .06, duration: .5, ease: 'power2.out', clearProps: 'all' }));
  const empty = t => `<div class="empty" style="padding:28px 20px">${esc(t)}</div>`;

  /* ----- cảnh 3D ----- */
  function showFaculty(f) {
    const c = $('#fac-card'); if (!f) { c.hidden = true; return; }
    const deg = Object.entries(f.degrees).filter(([, n]) => n > 0);
    c.hidden = false;
    c.innerHTML = `<h4>${esc(f.name.toUpperCase())}</h4><div class="big">${f.total}</div><small style="opacity:.75">giảng viên</small><ul>${deg.map(([k, n]) => `<li><span>${esc(k)}</span><b>${n}</b></li>`).join('')}</ul>`;
    anim(g => g.from(c, { scale: .9, opacity: 0, duration: .3, ease: 'back.out(1.6)' }));
  }
  api('GET', '/api/dashboard/campus').then(data => {
    if (!CampusScene.init($('#scene'), data, showFaculty)) $('.hero-hint').textContent = 'Trình duyệt không hỗ trợ WebGL nên mô hình 3D bị tắt.';
  }).catch(() => { });

  /* ----- Admin / Manager ----- */
  async function loadStaff() {
    const d = await api('GET', '/api/dashboard/stats'), c = d.cards;
    $('#stats').innerHTML = [['fa-users', '', 'Tổng giảng viên', c.total], ['fa-user-check', 'ok', 'Giảng viên chính thức', c.official], ['fa-file-contract', 'info', 'Giảng viên hợp đồng', c.contract],
      ['fa-building-columns', '', 'Khoa', c.faculties], ['fa-sitemap', '', 'Bộ môn', c.departments], ['fa-umbrella-beach', 'warn', 'Đang nghỉ phép', c.on_leave], ['fa-briefcase', 'ok', 'Đang làm việc', c.working]]
      .map(a => statCard(...a)).join('');
    reveal(); countUp();
    Charts.bar('ch-faculty', d.by_faculty.map(x => x.id), d.by_faculty.map(x => x.count), { horizontal: true, titles: d.by_faculty.map(x => x.name) });
    Charts.doughnut('ch-gender', Object.keys(d.gender), Object.values(d.gender));
    Charts.bar('ch-age', Object.keys(d.ages), Object.values(d.ages));
    Charts.doughnut('ch-degree', Object.keys(d.degrees), Object.values(d.degrees));
    renderLists(d);
  }
  function renderLists(d) {
    $('#ls-contracts').innerHTML = d.expiring_contracts.length ? d.expiring_contracts.map(c => `<div class="li"><div class="grow"><b>${esc(c.lecturer_name)}</b><small>${esc(c.id)} · hết hạn ${fmtDate(c.end_date)}</small></div><span class="badge warn">còn ${c.days_left} ngày</span></div>`).join('') : empty('Không có hợp đồng nào sắp hết hạn.');
    $('#ls-leave').innerHTML = d.pending_leave.length ? d.pending_leave.map(r => `<div class="li"><div class="grow"><b>${esc(r.lecturer_name)}</b><small>${esc(r.type)} · ${fmtDate(r.from_date)} – ${fmtDate(r.to_date)}</small><small>${esc(r.reason)}</small></div>
      <button class="btn sm ok" data-d="approve" data-id="${esc(r.id)}">Duyệt</button><button class="btn sm ghost" data-d="reject" data-id="${esc(r.id)}">Từ chối</button></div>`).join('') : empty('Không có đơn nào chờ duyệt.');
    $('#ls-activity').innerHTML = d.activities.length ? d.activities.map(a => `<div class="li"><div class="grow"><b>${esc(a.user)}</b> ${esc(a.action)}<small>${esc(a.target)} · ${timeAgo(a.timestamp)}</small></div></div>`).join('') : empty('Chưa có hoạt động.');
  }
  $('#ls-leave')?.addEventListener('click', async e => {
    const b = e.target.closest('[data-d]'); if (!b) return;
    const approve = b.dataset.d === 'approve';
    const note = await Modal.prompt({ title: `${approve ? 'Duyệt' : 'Từ chối'} đơn ${b.dataset.id}`, label: 'Ghi chú (không bắt buộc)', confirm: approve ? 'Duyệt đơn' : 'Từ chối đơn', cls: approve ? 'ok' : 'danger' });
    if (note === null) return;
    try { await api('POST', `/api/leave/${b.dataset.id}/${b.dataset.d}`, { note }); toast(approve ? 'Đã duyệt đơn nghỉ phép' : 'Đã từ chối đơn nghỉ phép'); loadStaff(); }
    catch (err) { toast(err.message, 'error'); }
  });

  /* ----- Giảng viên ----- */
  async function loadMe() {
    const d = await api('GET', '/api/dashboard/me');
    if (!d.week) { $('#stats').innerHTML = '<div class="card card-pad" style="grid-column:1/-1">Tài khoản chưa được gắn với hồ sơ giảng viên. Vui lòng liên hệ Quản trị viên.</div>'; return; }
    const ev = d.latest_eval;
    $('#stats').innerHTML = [statCard('fa-calendar-check', 'ok', 'Ngày có mặt tháng này', d.month_present), statCard('fa-clock', 'warn', 'Lần đi muộn trong tháng', d.month_late),
      statCard('fa-hourglass-half', 'info', 'Đơn nghỉ phép chờ duyệt', d.pending_leave), statCard('fa-star', '', ev ? `Xếp loại ${ev.period}` : 'Chưa có đánh giá', 0, ev ? ev.grade : '—')].join('');
    reveal(); countUp();
    const tr = d.today_record, box = $('#checkin-box');
    box.innerHTML = !tr?.check_in ? '<button class="btn primary sm" id="ci"><i class="fa-solid fa-right-to-bracket"></i> Chấm công vào</button>'
      : !tr.check_out ? `<span class="muted">Vào lúc ${esc(tr.check_in)}</span><button class="btn sm" id="co"><i class="fa-solid fa-right-from-bracket"></i> Chấm công ra</button>` : `<span class="badge ok">Đã hoàn thành hôm nay (${esc(tr.check_in)}–${esc(tr.check_out)})</span>`;
    const act = async (url, msg) => { try { await api('POST', url); toast(msg); loadMe(); } catch (e) { toast(e.message, 'error'); } };
    $('#ci')?.addEventListener('click', () => act('/api/attendance/check-in', 'Chấm công vào thành công'));
    $('#co')?.addEventListener('click', () => act('/api/attendance/check-out', 'Chấm công ra thành công'));
    $('#week').innerHTML = d.week.map(x => `<div class="day ${x.today ? 'today' : ''}"><b>${x.weekday} · ${fmtDate(x.date).slice(0, 5)}</b>${badge(x.status === 'Chưa đến' || x.status === 'Chưa chấm công' ? '' : x.status) === '<span class="muted">—</span>' ? `<span class="muted">${esc(x.status)}</span>` : badge(x.status)}<small>${x.check_in ? esc(x.check_in) + ' – ' + esc(x.check_out || '…') : `Ca ${esc(d.settings.work_start)} – ${esc(d.settings.work_end)}`}</small></div>`).join('');
    const c = d.contract;
    $('#my-contract').innerHTML = c ? `<div class="card-pad"><dl class="kv" style="grid-template-columns:1fr 1fr"><div><dt>Loại</dt><dd>${esc(c.type)}</dd></div><div><dt>Trạng thái</dt><dd>${badge(c.status)}</dd></div><div><dt>Bắt đầu</dt><dd>${fmtDate(c.start_date)}</dd></div><div><dt>Kết thúc</dt><dd>${c.end_date ? fmtDate(c.end_date) : 'Không thời hạn'}</dd></div></dl></div>` : empty('Chưa có hợp đồng.');
    const n = await api('GET', '/api/notifications');
    $('#my-notifs').innerHTML = n.items.slice(0, 5).map(Notif.item).join('') || empty('Chưa có thông báo.');
  }
  (staff ? loadStaff() : loadMe()).catch(e => toast(e.message, 'error'));
})();
