/* charts.js — bọc Chart.js, tự đổi màu theo Light/Dark mode */
const Charts = (() => {
  const store = {};
  const theme = () => {
    const d = document.documentElement.dataset.theme === 'dark';
    return { text: d ? '#90A1C5' : '#59698A', grid: d ? 'rgba(255,255,255,.07)' : 'rgba(10,30,74,.07)', surface: d ? '#0F1A34' : '#fff',
      pal: d ? ['#6C98FF', '#3DD9A0', '#F3B948', '#62CDF3', '#FF8199', '#C8D6FF'] : ['#2155E8', '#0B8F64', '#E0A030', '#2FB5C9', '#CB2C4B', '#0A1E4A'] };
  };
  function render(id) {
    const s = store[id], el = document.getElementById(id); if (!s || !el || !window.Chart) return;
    s.chart?.destroy(); const th = theme();
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily; Chart.defaults.color = th.text;
    s.chart = new Chart(el, s.build(th));
  }
  const tip = titles => titles ? { callbacks: { title: i => titles[i[0].dataIndex] } } : {};
  return {
    bar(id, labels, data, { horizontal = false, label = 'Giảng viên', titles } = {}) {
      store[id] = { build: th => ({ type: 'bar', data: { labels, datasets: [{ label, data, backgroundColor: th.pal[0], borderRadius: 6, maxBarThickness: 26 }] },
        options: { indexAxis: horizontal ? 'y' : 'x', responsive: true, maintainAspectRatio: false, animation: { duration: 700 }, plugins: { legend: { display: false }, tooltip: tip(titles) },
          scales: { x: { grid: { display: !horizontal, color: th.grid }, ticks: { precision: 0 } }, y: { beginAtZero: true, grid: { display: horizontal ? false : true, color: th.grid }, ticks: { precision: 0 } } } } }) };
      render(id);
    },
    doughnut(id, labels, data) {
      store[id] = { build: th => ({ type: 'doughnut', data: { labels, datasets: [{ data, backgroundColor: th.pal, borderColor: th.surface, borderWidth: 3 }] },
        options: { responsive: true, maintainAspectRatio: false, cutout: '62%', animation: { duration: 800 }, plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, padding: 14 } } } } }) };
      render(id);
    },
    refresh() { Object.keys(store).forEach(render); }
  };
})();
window.addEventListener('themechange', () => Charts.refresh());
