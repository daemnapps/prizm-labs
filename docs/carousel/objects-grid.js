/* objects-grid.js — every 3D object on its own tile, live.

   Markup:  <div class="gj-objs"> <figure class="gj-obj" data-glb="objects/koi.glb" data-life='{"coat":.7}'>
              <div class="gj-obj-view"></div><figcaption>…</figcaption> </figure> … </div>
   One WebGL renderer draws every tile (a fixed, click-through canvas; each tile is a scissored viewport), so
   twenty-five objects cost one context. A tile's model loads when it scrolls near. Each object turns slowly on its
   own; drag a tile (thumb or mouse) and it spins with weight. The light is the carousel's: interior.hdr, ACES.
   Focus mode (.gj-focus-mode, set by feed.js): the tiles sit in a row you swipe, one on screen; only the tile
   page.js has put in focus (.is-focus) turns, and the next one loads ahead.
   No colours here: the page paints the tiles, the objects carry their own materials. */
import * as THREE from 'three';
import {RGBELoader} from 'three/addons/loaders/RGBELoader.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {MeshoptDecoder} from 'three/addons/libs/meshopt_decoder.module.js';

// a grid builds its renderer (and fetches the light) only when it comes near the screen
const later = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { later.unobserve(e.target); setup(e.target); } }), {rootMargin: '600px 0px'});
for (const grid of document.querySelectorAll('.gj-objs')) later.observe(grid);
function setup(grid) {
  const tiles = [...grid.querySelectorAll('.gj-obj[data-glb]')];
  if (!tiles.length) return;
  const CALM = matchMedia('(prefers-reduced-motion:reduce)').matches;
  const renderer = new THREE.WebGLRenderer({antialias: true, alpha: true});
  renderer.setPixelRatio(Math.min(2, devicePixelRatio || 1));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = .95;
  renderer.setClearColor(0x000000, 0); renderer.setScissorTest(true);
  const cv = renderer.domElement; cv.className = 'gj-objs-canvas'; cv.setAttribute('aria-hidden', 'true');
  grid.appendChild(cv);
  const maxAniso = Math.min(8, renderer.capabilities.getMaxAnisotropy());

  let env = null;
  const pmrem = new THREE.PMREMGenerator(renderer);
  new RGBELoader().load(new URL('interior.hdr', import.meta.url).href, hdr => {
    hdr.mapping = THREE.EquirectangularReflectionMapping;
    env = pmrem.fromEquirectangular(hdr).texture; hdr.dispose(); pmrem.dispose();
    views.forEach(v => { v.scene.environment = env; }); wake();
  });

  const loader = new GLTFLoader(); loader.setMeshoptDecoder(MeshoptDecoder);
  function lifelike(m0, r) {
    const m = m0.isMeshPhysicalMaterial ? m0 : Object.assign(new THREE.MeshPhysicalMaterial(), {name: m0.name});
    if (m !== m0) {
      for (const k of ['color', 'map', 'normalMap', 'normalScale', 'roughness', 'metalness', 'roughnessMap', 'metalnessMap',
        'emissive', 'emissiveMap', 'emissiveIntensity', 'aoMap', 'transparent', 'opacity', 'alphaTest', 'transmission', 'transmissionMap'])
        if (m0[k] !== undefined) m[k] = m0[k] && m0[k].clone && !m0[k].isTexture ? m0[k].clone() : m0[k];
      m0.dispose();
    }
    for (const t of [m.map, m.normalMap, m.roughnessMap, m.emissiveMap]) if (t) { t.anisotropy = maxAniso; t.needsUpdate = true; }
    if (r.coat !== undefined) { m.clearcoat = r.coat; m.clearcoatRoughness = r.coatRough ?? .1; }
    if (r.sheen) { m.sheen = r.sheen; m.sheenRoughness = r.sheenRough ?? .5; m.sheenColor = new THREE.Color(1, 1, 1); }
    if (!m.normalMap && m.map) { m.bumpMap = m.map; m.bumpScale = .5; }
    if (r.env) m.envMapIntensity = r.env;
    if (r.glass) { m.transmission = m.transmission || 1; m.thickness = .35; m.ior = 1.5; m.attenuationColor = new THREE.Color().setRGB(.25, .6, .2); m.attenuationDistance = .6; }
    if (r.neon) { m.emissive = new THREE.Color(1, 1, 1); m.emissiveMap = m.emissiveMap || m.map; m.emissiveIntensity = r.neon; }
    if (r.clear) { m.transparent = true; m.opacity = r.clear; m.depthWrite = false; }
    m.needsUpdate = true; return m;
  }

  const views = tiles.map((tile, i) => {
    const view = tile.querySelector('.gj-obj-view') || tile;
    const scene = new THREE.Scene();
    const cam = new THREE.PerspectiveCamera(28, 1, .01, 50);
    const key = new THREE.DirectionalLight(0xfff1e2, 2.2); key.position.set(-2, 3, 4); scene.add(key);
    const rim = new THREE.DirectionalLight(0xb264ff, 1.4); rim.position.set(3, 1.5, -3); scene.add(rim);
    const pivot = new THREE.Group(); scene.add(pivot);
    const v = {tile, view, scene, cam, pivot, rot: i * .9, vel: 0, tilt: .18, state: 'idle', seen: false, drag: null};
    let px = 0, last = 0;
    view.addEventListener('pointerdown', e => { v.drag = e.pointerId; px = e.clientX; last = performance.now(); v.vel = 0; view.setPointerCapture(e.pointerId); wake(); });
    view.addEventListener('pointermove', e => {
      if (v.drag !== e.pointerId) return;
      const now = performance.now(), dx = e.clientX - px; px = e.clientX;
      v.rot += dx * .012; v.vel = dx * .012 / Math.max(8, now - last) * 16; last = now; wake();
    });
    const up = e => { if (v.drag === e.pointerId) v.drag = null; };
    view.addEventListener('pointerup', up); view.addEventListener('pointercancel', up);
    return v;
  });

  function load(v) {
    if (v.state !== 'idle') return; v.state = 'loading';
    const r = v.tile.dataset.life ? JSON.parse(v.tile.dataset.life) : {};
    loader.load(v.tile.dataset.glb, g => {
      const obj = g.scene;
      obj.traverse(o => { if (o.isMesh) o.material = Array.isArray(o.material) ? o.material.map(m => lifelike(m, r)) : lifelike(o.material, r); });
      const box = new THREE.Box3().setFromObject(obj), c = box.getCenter(new THREE.Vector3());
      obj.position.sub(c);
      const rad = box.getBoundingSphere(new THREE.Sphere()).radius;
      v.cam.position.set(0, rad * .35, rad / Math.tan(THREE.MathUtils.degToRad(14)) * 1.02);
      v.cam.lookAt(0, 0, 0); v.cam.near = rad * .05; v.cam.far = rad * 20; v.cam.updateProjectionMatrix();
      v.pivot.add(obj); if (env) v.scene.environment = env;
      v.state = 'ready'; v.tile.classList.add('ready'); wake();
    }, undefined, e => { v.state = 'failed'; v.tile.classList.add('failed'); console.warn('object', v.tile.dataset.glb, e); });
  }
  const io = new IntersectionObserver(es => es.forEach(e => {
    const v = views.find(v => v.view === e.target || v.tile === e.target); if (!v) return;
    v.seen = e.isIntersecting;
    if (e.isIntersecting) { load(v); const nx = views[views.indexOf(v) + 1]; if (nx && FOCUS) load(nx); wake(); }
  }), {rootMargin: '400px 0px'});
  views.forEach(v => io.observe(v.tile));

  const FOCUS = grid.classList.contains('gj-focus-mode');
  let raf = 0, t0 = performance.now();
  function frame(now) {
    raf = 0; const dt = Math.min(.05, (now - t0) / 1000); t0 = now;
    const G = grid.getBoundingClientRect(), W = G.width, H = G.height, VH = innerHeight;
    if (cv.width !== Math.round(W * renderer.getPixelRatio()) || cv.height !== Math.round(H * renderer.getPixelRatio())) renderer.setSize(W, H, false);
    renderer.setScissor(0, 0, W, H); renderer.clear();
    let any = false;
    for (const v of views) {
      if (!v.seen || v.state !== 'ready') continue;
      const b0 = v.view.getBoundingClientRect();
      if (b0.bottom < 0 || b0.top > VH || b0.right <= G.left || b0.left >= G.right) continue;
      const b = {left: b0.left - G.left, top: b0.top - G.top, width: b0.width, height: b0.height, bottom: b0.bottom - G.top};
      any = true;
      const turns = !FOCUS || v.view.classList.contains('is-focus');
      if (!v.drag) { v.vel *= Math.pow(.05, dt); v.rot += v.vel + (CALM || !turns ? 0 : .35 * dt); }
      v.pivot.rotation.set(v.tilt * .5, v.rot, 0);
      v.cam.aspect = b.width / b.height; v.cam.updateProjectionMatrix();
      const y = H - b.bottom;
      renderer.setViewport(b.left, y, b.width, b.height); renderer.setScissor(b.left, y, b.width, b.height);
      renderer.render(v.scene, v.cam);
    }
    if (any) raf = requestAnimationFrame(frame);
  }
  function wake() { if (!raf) raf = requestAnimationFrame(frame); }
  addEventListener('scroll', wake, {passive: true}); addEventListener('resize', wake);
  grid.addEventListener('scroll', wake, {passive: true, capture: true});   // the row scrolling sideways
  document.addEventListener('gj-focus', wake);
}
