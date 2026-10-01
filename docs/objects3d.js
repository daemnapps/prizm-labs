/* objects3d.js — the chrome and glass objects, as real 3D, anywhere on the site.

   Put an element on any page:
       <div class="obj" data-obj="torus" role="img" aria-label="…"></div>
   and it becomes that object, floating, turning with the scroll, leaning
   toward the pointer. There is no poster image (2026-10-01: the old stills
   showed behind the 3D as it faded in, and read as tacky); without WebGL the
   page gets a `no-webgl` class and a plain disc of colour instead.

   Kinds: prism · lens · ribbon · cube · torus · sphere · monolith · cards,
   and glb:<file> for any model in /media/desk/ (head, laptop, phone …).
   Change data-obj on the fly and the object morphs into the new one.

   One WebGL renderer draws every object on the page, each into its own small
   canvas, so a page can hold as many as it likes. Nothing renders while it
   is off screen; nothing moves for anyone who asked their device for less.
*/
import * as THREE from 'three';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {DRACOLoader} from 'three/addons/loaders/DRACOLoader.js';

const CALM = matchMedia('(prefers-reduced-motion:reduce)').matches;
const DPR = Math.min(matchMedia('(pointer:coarse)').matches ? 1.5 : 2, devicePixelRatio || 1);
const SPECTRUM = [0x6D3BF5, 0x2F5BFF, 0x00A8CC, 0x12A06F, 0xF09000, 0xF04A2E, 0xDB2A8C];

/* ── materials ─────────────────────────────────────────────────────── */
const M = {
  chrome:  () => new THREE.MeshPhysicalMaterial({color:0xffffff, metalness:1, roughness:.07, envMapIntensity:1.25}),
  brushed: () => new THREE.MeshPhysicalMaterial({color:0xe9e6e1, metalness:1, roughness:.26, envMapIntensity:1.1}),
  dark:    () => new THREE.MeshPhysicalMaterial({color:0x8d8a86, metalness:1, roughness:.2, envMapIntensity:1.1, clearcoat:.6, clearcoatRoughness:.15}),
  // Real transmission refracts what is behind the glass, and on a
  // transparent canvas there is nothing behind it, so it renders as a white
  // block. Glass here is what the eye actually reads: bright reflections,
  // a thin-film rainbow at the edges, and the paper showing through.
  glass:   () => new THREE.MeshPhysicalMaterial({color:0xdfe6f2, metalness:0, roughness:0, transparent:true, opacity:.5,
                 side:THREE.DoubleSide, depthWrite:false, envMapIntensity:2.4, clearcoat:1, clearcoatRoughness:0,
                 iridescence:.9, iridescenceIOR:1.6, iridescenceThicknessRange:[250, 800], specularIntensity:1}),
  bone:    () => new THREE.MeshPhysicalMaterial({color:0xE9E2D7, roughness:.55, metalness:0, sheen:.4, sheenRoughness:.8, sheenColor:new THREE.Color(0xffffff)}),
  film:    () => new THREE.MeshPhysicalMaterial({color:0xffffff, metalness:.2, roughness:.05, iridescence:1, iridescenceIOR:1.8,
                 iridescenceThicknessRange:[200, 900], transmission:.6, transparent:true, opacity:.85, side:THREE.DoubleSide}),
};

function roundedSlab(w, h, d, r){
  const s = new THREE.Shape(), x = -w / 2, y = -h / 2;
  s.moveTo(x + r, y); s.lineTo(x + w - r, y); s.quadraticCurveTo(x + w, y, x + w, y + r);
  s.lineTo(x + w, y + h - r); s.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  s.lineTo(x + r, y + h); s.quadraticCurveTo(x, y + h, x, y + h - r);
  s.lineTo(x, y + r); s.quadraticCurveTo(x, y, x + r, y);
  const g = new THREE.ExtrudeGeometry(s, {depth:d, bevelEnabled:true, bevelThickness:Math.min(.04, d / 3), bevelSize:Math.min(.04, r / 2), bevelSegments:6, curveSegments:16});
  g.center(); return g;
}

function mobius(){
  const U = 420, V = 24, R = .78, W = .3, pos = [], idx = [];
  for(let i = 0; i <= U; i++){
    const u = i / U * Math.PI * 2;
    for(let j = 0; j <= V; j++){
      const v = (j / V - .5) * 2 * W, c = Math.cos(u / 2);
      pos.push((R + v * c) * Math.cos(u), (R + v * c) * Math.sin(u), v * Math.sin(u / 2));
    }
  }
  for(let i = 0; i < U; i++) for(let j = 0; j < V; j++){
    const a = i * (V + 1) + j, b = a + V + 1;
    idx.push(a, b, a + 1, b, b + 1, a + 1);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setIndex(idx); g.computeVertexNormals();
  return g;
}

// a fan of spectrum light, for the prism: additive, soft at the edges
function spectrumFan(){
  const g = new THREE.PlaneGeometry(2.6, .9, 1, 1);
  const m = new THREE.ShaderMaterial({transparent:true, depthWrite:false, blending:THREE.AdditiveBlending, side:THREE.DoubleSide,
    uniforms:{t:{value:0}},
    vertexShader:'varying vec2 v;void main(){v=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
    fragmentShader:`varying vec2 v;uniform float t;
      vec3 hue(float h){return clamp(abs(mod(h*6.+vec3(0.,4.,2.),6.)-3.)-1.,0.,1.);}
      void main(){float a=smoothstep(0.,.25,v.x)*(1.-smoothstep(.55,1.,v.x));float band=1.-abs(v.y-.5)*2.;
        a*=smoothstep(0.,.5,band)*.55*(.85+.15*sin(t*1.3+v.x*6.));gl_FragColor=vec4(hue(v.y*.85+.02)*a,a);}`});
  const p = new THREE.Mesh(g, m); p.position.set(1.35, -.05, -.2); p.rotation.z = -.12; p.userData.fan = m;
  return p;
}

const gltf = new GLTFLoader();
const draco = new DRACOLoader(); draco.setDecoderPath('https://cdn.jsdelivr.net/npm/three@0.169.0/examples/jsm/libs/draco/');
gltf.setDRACOLoader(draco);
const glbCache = {};

// the bright edge a glass object shows where it catches the light
function rim(geo, G, f){
  const l = new THREE.LineSegments(new THREE.EdgesGeometry(geo, 25), new THREE.LineBasicMaterial({color:0x2c2823, transparent:true, opacity:.55}));
  if(f) f(l); G.add(l); return l;
}

/* Every object comes out centred and about two units across. */
export async function makeObject(kind){
  const G = new THREE.Group();
  const add = (geo, mat, f) => { const m = new THREE.Mesh(geo, mat); if(f) f(m); G.add(m); return m; };
  switch(kind){
    case 'torus':  add(new THREE.TorusGeometry(.66, .3, 96, 220), M.brushed(), m => m.rotation.x = .5); break;
    case 'sphere': add(new THREE.SphereGeometry(.82, 96, 64), M.chrome()); break;
    case 'ribbon': add(mobius(), (() => { const m = M.chrome(); m.side = THREE.DoubleSide; return m; })(), m => { m.rotation.x = -.9; }); break;
    case 'monolith': add(roundedSlab(1.0, 1.95, .3, .12), M.dark(), m => m.rotation.y = .35); break;
    case 'cards':
      for(let i = 0; i < 4; i++) add(roundedSlab(1.05, 1.45, .035, .08), i === 3 ? M.film() : M.bone(),
        m => { m.position.set(i * .09 - .14, i * .07 - .1, i * .12); m.rotation.set(-.12, .28, -.14 + i * .09); });
      break;
    case 'lens': {
      const pts = []; for(let i = 0; i <= 32; i++){ const t = i / 32, r = .8 * t; pts.push(new THREE.Vector2(r, .16 * Math.sqrt(Math.max(0, 1 - t * t)))); }
      const half = new THREE.LatheGeometry(pts, 96);
      add(half, M.glass(), m => m.rotation.x = Math.PI / 2);
      add(half, M.glass(), m => m.rotation.x = -Math.PI / 2);
      add(new THREE.TorusGeometry(.82, .055, 32, 160), M.chrome());
      G.rotation.y = .6; break; }
    case 'cube': {
      const g = new THREE.BoxGeometry(1.2, 1.2, 1.2);
      add(g, M.glass()); rim(g, G);
      add(new THREE.PlaneGeometry(1.5, 1.1), M.film(), m => { m.rotation.set(0, Math.PI / 4, 0); m.scale.set(.95, .95, 1); });
      G.rotation.set(.45, .6, 0); break; }
    case 'prism': {
      const g = new THREE.CylinderGeometry(.78, .78, 1.7, 3, 1), f = m => { m.rotation.z = Math.PI / 2; m.rotation.x = .35; };
      add(g, M.glass(), f); rim(g, G, f);
      G.add(spectrumFan()); break; }
    default:
      if(kind && kind.startsWith('glb:')){
        const f = kind.slice(4);
        const src = glbCache[f] || (glbCache[f] = new Promise((ok, no) => gltf.load('/media/desk/' + f + '.glb', g => ok(g.scene), undefined, no)));
        const root = (await src).clone(true);
        const box = new THREE.Box3().setFromObject(root), size = box.getSize(new THREE.Vector3());
        root.position.sub(box.getCenter(new THREE.Vector3()));
        const inner = new THREE.Group(); inner.add(root); inner.scale.setScalar(2 / Math.max(size.x, size.y, size.z));
        if(f === 'head') inner.rotation.y = -Math.PI / 2;
        G.add(inner);
      }
  }
  return G;
}

/* ── one studio, lit with the spectrum ────────────────────────────────
   Chrome is a mirror: it looks like whatever it reflects. A grey room makes
   grey chrome; seven coloured softboxes around the room make the prism's
   chrome, which is the whole brand in one reflection. */
let R, envTex;
function studio(){
  if(R) return R;
  R = new THREE.WebGLRenderer({antialias:true, alpha:true, powerPreference:'high-performance'});
  R.setPixelRatio(1); R.outputColorSpace = THREE.SRGBColorSpace;
  R.toneMapping = THREE.ACESFilmicToneMapping; R.toneMappingExposure = 1.05;
  R.setClearColor(0x000000, 0);
  const env = new RoomEnvironment();
  SPECTRUM.forEach((c, i) => {
    const a = i / SPECTRUM.length * Math.PI * 2;
    const box = new THREE.Mesh(new THREE.PlaneGeometry(1.6, 4), new THREE.MeshBasicMaterial({color:c}));
    box.material.color.multiplyScalar(2.2);
    box.position.set(Math.cos(a) * 9, 2 + (i % 2), Math.sin(a) * 9); box.lookAt(0, 2, 0); env.add(box);
  });
  envTex = new THREE.PMREMGenerator(R).fromScene(env, .03).texture;
  return R;
}

const views = [];
let pointer = {x:0, y:0}, bufW = 0, bufH = 0, raf = 0;
addEventListener('pointermove', e => { pointer.x = e.clientX / innerWidth - .5; pointer.y = e.clientY / innerHeight - .5; }, {passive:true});

function makeView(el){
  const c = document.createElement('canvas'); c.setAttribute('aria-hidden', 'true'); el.appendChild(c);
  const scene = new THREE.Scene(); scene.environment = envTex;
  const key = new THREE.DirectionalLight(0xffffff, 1.6); key.position.set(-2, 3, 4); scene.add(key);
  scene.add(new THREE.AmbientLight(0xffffff, .35));
  const cam = new THREE.PerspectiveCamera(32, 1, .1, 30); cam.position.set(0, 0, 5.2);
  const holder = new THREE.Group(); scene.add(holder);
  const v = {el, c, ctx:c.getContext('2d'), scene, cam, holder, obj:null, kind:null, vis:false, seed:Math.random() * 10, swapT:0, drawn:false};
  views.push(v); return v;
}

async function setKind(v, kind){
  if(v.kind === kind) return;
  v.kind = kind;
  const obj = await makeObject(kind);
  if(v.kind !== kind) return;          // superseded while loading
  if(v.obj) v.holder.remove(v.obj);
  v.obj = obj; v.holder.add(obj); v.swapT = performance.now(); wake();
  if(CALM) draw(performance.now());
}

function frameOf(v, now){
  const r = v.el.getBoundingClientRect();
  const w = Math.max(1, Math.round(r.width * DPR)), h = Math.max(1, Math.round(r.height * DPR));
  if(v.c.width !== w || v.c.height !== h){ v.c.width = w; v.c.height = h; }
  v.cam.aspect = w / h; v.cam.updateProjectionMatrix();
  // scroll: the object turns as it travels up the screen; float: it breathes
  const prog = (r.top + r.height / 2) / innerHeight - .5;        // -.5 top … .5 bottom
  const t = now / 1000 + v.seed, H = v.holder;
  const s = v.swapT ? Math.min(1, (now - v.swapT) / 700) : 1, ease = 1 - Math.pow(1 - s, 3);
  if(!CALM){
    H.position.y = Math.sin(t * .9) * .07;
    H.rotation.y = t * .22 + prog * -1.4 + pointer.x * .5 + (1 - ease) * 2.4;
    H.rotation.x = Math.sin(t * .6) * .06 + pointer.y * .3 + prog * .25;
    H.rotation.z = Math.sin(t * .4) * .03;
  } else { H.rotation.set(.1, .6, 0); }
  H.scale.setScalar(.72 + .28 * ease);
  v.obj && v.obj.traverse(o => { if(o.userData.fan) o.userData.fan.uniforms.t.value = t; });
  return [w, h];
}

function draw(now){
  const r = studio();
  for(const v of views){
    if(!v.vis || !v.obj) continue;
    const [w, h] = frameOf(v, now);
    if(w > bufW || h > bufH){ bufW = Math.max(bufW, w); bufH = Math.max(bufH, h); r.setSize(bufW, bufH, false); }
    r.setViewport(0, 0, w, h); r.setScissor(0, 0, w, h); r.setScissorTest(true);
    r.clear(); r.render(v.scene, v.cam);
    v.ctx.clearRect(0, 0, w, h);
    v.ctx.drawImage(r.domElement, 0, bufH - h, w, h, 0, 0, w, h);
    if(!v.drawn){ v.drawn = true; v.el.classList.add('live'); }
  }
}

function loop(now){
  raf = 0;
  if(document.hidden) return;
  draw(now);
  if(!CALM && views.some(v => v.vis)) raf = requestAnimationFrame(loop);
}
const wake = () => { if(!raf) raf = requestAnimationFrame(loop); };

export function mount(el){
  if(el.__obj) return el.__obj;
  studio();
  const v = makeView(el); el.__obj = v;
  setKind(v, el.dataset.obj);
  new MutationObserver(() => setKind(v, el.dataset.obj)).observe(el, {attributes:true, attributeFilter:['data-obj']});
  io.observe(el);
  return v;
}

const io = new IntersectionObserver(es => {
  for(const e of es){ const v = e.target.__obj; if(v){ v.vis = e.isIntersecting; } }
  if(CALM) draw(performance.now()); else wake();
}, {rootMargin:'120px 0px'});

addEventListener('resize', () => CALM ? draw(performance.now()) : wake());
addEventListener('scroll', () => { if(CALM) draw(performance.now()); }, {passive:true});
document.addEventListener('visibilitychange', wake);

// WebGL or a plain fallback colour (studio.css: .no-webgl .obj).
let ok = false;
try{ const p = document.createElement('canvas'); ok = !!(p.getContext('webgl2') || p.getContext('webgl')); }catch(e){}
if(!ok) document.documentElement.classList.add('no-webgl');
if(ok) document.querySelectorAll('[data-obj]').forEach(mount);
window.daemnObjects = {mount, makeObject, draw:() => draw(performance.now())};
