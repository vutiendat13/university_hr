/* three-scene.js — mô hình campus 3D nhẹ: mỗi khoa là một toà nhà, chiều cao ~ số giảng viên.
   Tối ưu máy yếu: pixel ratio <= 1.5, ít polygon (box), không đổ bóng, tạm dừng khi ẩn tab/khuất khỏi màn hình,
   tôn trọng prefers-reduced-motion, dispose toàn bộ geometry/material/texture khi rời trang. */
const CampusScene = (() => {
  const DEMO = [{ id: 'CNTT', total: 35 }, { id: 'KT', total: 28 }, { id: 'NN', total: 20 }, { id: 'DDT', total: 24 }, { id: 'CK', total: 18 }, { id: 'SP', total: 22 }];

  function labelSprite(text) {
    const c = document.createElement('canvas'); c.width = 256; c.height = 64;
    const x = c.getContext('2d'); x.font = '700 30px "Be Vietnam Pro",system-ui,sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle';
    x.fillStyle = 'rgba(255,255,255,.95)'; x.fillText(text, 128, 34);
    const tex = new THREE.CanvasTexture(c);
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false }));
    s.scale.set(2.6, .65, 1); return s;
  }

  function init(host, faculties, onSelect, opts = {}) {
    if (!window.THREE || !host) return null;
    const ambient = !!opts.ambient, reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
    let renderer;
    try { renderer = new THREE.WebGLRenderer({ antialias: !ambient, alpha: true, powerPreference: 'low-power' }); }
    catch (e) { return null; }  // máy không hỗ trợ WebGL: giao diện vẫn dùng được
    let w = host.clientWidth || 600, h = host.clientHeight || 360;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    renderer.setSize(w, h, false); host.appendChild(renderer.domElement);

    const scene = new THREE.Scene(); scene.fog = new THREE.Fog(0x0a1e4a, 16, 44);
    const camera = new THREE.PerspectiveCamera(42, w / h, .1, 100), base = new THREE.Vector3(10, 8.5, 13);
    camera.position.copy(base); camera.lookAt(0, 1.4, 0);
    scene.add(new THREE.AmbientLight(0xffffff, .7));
    const sun = new THREE.DirectionalLight(0xa9c2ff, .95); sun.position.set(8, 14, 6); scene.add(sun);
    const grid = new THREE.GridHelper(46, 46, 0x3a5bb0, 0x1b3068); grid.material.transparent = true; grid.material.opacity = .5; scene.add(grid);

    const group = new THREE.Group(); scene.add(group);
    const max = Math.max(...faculties.map(f => f.total), 1), cols = 3, buildings = [];
    faculties.forEach((f, i) => {
      const hgt = 1.1 + 3.4 * (f.total / max);
      const mat = new THREE.MeshStandardMaterial({ color: 0x2f5fd6, roughness: .55, metalness: .1, emissive: 0x0b2a7a, emissiveIntensity: .35 });
      const m = new THREE.Mesh(new THREE.BoxGeometry(2.3, hgt, 2.3), mat);
      m.position.set((i % cols - (cols - 1) / 2) * 4.6, hgt / 2, (Math.floor(i / cols) - .5) * 5);
      m.userData = { faculty: f };
      m.add(new THREE.LineSegments(new THREE.EdgesGeometry(m.geometry), new THREE.LineBasicMaterial({ color: 0x9db8ff, transparent: true, opacity: .5 })));
      const roof = new THREE.Mesh(new THREE.BoxGeometry(1.1, .35, 1.1), new THREE.MeshStandardMaterial({ color: 0xcfe0ff })); roof.position.y = hgt / 2 + .17; m.add(roof);
      const sp = labelSprite(f.id); sp.position.y = hgt / 2 + 1; m.add(sp);
      group.add(m); buildings.push(m);
    });

    const N = ambient ? 150 : 220, pos = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) { pos[i * 3] = (Math.random() - .5) * 32; pos[i * 3 + 1] = Math.random() * 10; pos[i * 3 + 2] = (Math.random() - .5) * 32; }
    const pg = new THREE.BufferGeometry(); pg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    scene.add(new THREE.Points(pg, new THREE.PointsMaterial({ color: 0xbcd0ff, size: .07, transparent: true, opacity: .75, depthWrite: false })));

    // ---- tương tác chuột
    const ray = new THREE.Raycaster(), ndc = new THREE.Vector2(); let hover = null, selected = null, moved = false;
    const cv = renderer.domElement;
    const setNdc = e => { const r = cv.getBoundingClientRect(); ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1); moved = true; };
    const pick = () => { ray.setFromCamera(ndc, camera); const hit = ray.intersectObjects(buildings, false)[0]; return hit ? hit.object : null; };
    const select = o => { selected = o; onSelect && onSelect(o ? o.userData.faculty : null); if (reduced) draw(); };
    if (!ambient) {
      cv.addEventListener('pointermove', setNdc);
      cv.addEventListener('pointerleave', () => { ndc.set(0, 0); hover = null; moved = false; });
      cv.addEventListener('click', e => { setNdc(e); select(pick()); });
    }

    // ---- vòng lặp
    const clock = new THREE.Clock(); let raf = 0, t = 0;
    function draw() { renderer.render(scene, camera); }
    function frame() {
      raf = requestAnimationFrame(frame);
      const dt = Math.min(clock.getDelta(), .05), f = Math.min(1, dt * 3.5); t += dt;
      if (ambient) camera.position.set(Math.cos(t * .1) * 15, 8 + Math.sin(t * .2), Math.sin(t * .1) * 15);
      else { camera.position.x += (base.x + ndc.x * 3 - camera.position.x) * f; camera.position.y += (base.y + ndc.y * 1.6 - camera.position.y) * f; }
      camera.lookAt(0, 1.4, 0);
      if (moved) { hover = pick(); cv.style.cursor = hover ? 'pointer' : 'grab'; moved = false; }
      for (const b of buildings) {
        const on = b === selected, hv = b === hover, s = on ? 1.1 : hv ? 1.06 : 1;
        b.scale.x += (s - b.scale.x) * f; b.scale.z = b.scale.x;
        b.material.emissiveIntensity += ((on ? 1.1 : hv ? .8 : .35) - b.material.emissiveIntensity) * f;
      }
      const p = pg.attributes.position;
      for (let i = 0; i < N; i++) { let y = p.getY(i) + dt * .25; if (y > 10) y = 0; p.setY(i, y); }
      p.needsUpdate = true; draw();
    }
    const start = () => { if (!raf && !reduced) { clock.getDelta(); frame(); } };
    const stop = () => { cancelAnimationFrame(raf); raf = 0; };
    const io = new IntersectionObserver(es => es[0].isIntersecting ? start() : stop());   io.observe(host);
    const onVis = () => document.hidden ? stop() : start(); document.addEventListener('visibilitychange', onVis);
    const ro = new ResizeObserver(() => { w = host.clientWidth; h = host.clientHeight; if (!w || !h) return; camera.aspect = w / h; camera.updateProjectionMatrix(); renderer.setSize(w, h, false); if (reduced) draw(); });
    ro.observe(host);
    if (reduced) draw();

    function dispose() {
      stop(); io.disconnect(); ro.disconnect(); document.removeEventListener('visibilitychange', onVis);
      scene.traverse(o => { o.geometry?.dispose(); if (o.material) { o.material.map?.dispose(); o.material.dispose(); } });
      renderer.dispose(); cv.remove();
    }
    window.addEventListener('pagehide', dispose, { once: true });
    return { dispose, selectById: id => select(buildings.find(b => b.userData.faculty.id === id) || null) };
  }
  return { init, DEMO };
})();
