/* carousel.js — the objects from the trip, riding one carousel.

   The piece ends on a tiny carousel spinning by a phone that glows Goja purple.
   This is that carousel, big enough to ride: every object is a seat, bobbing on
   its pole like a carousel horse and turning on its own axis. Drag sideways
   (thumb or mouse) and it spins with weight, then settles an object front and
   centre. Leave it alone and it turns on its own, slowly, like a music box.

   Markup:   <div class="carousel" id="carousel"></div>
             <p class="label" id="carousel-label"></p>
   Needs the three.js import map (same CDN build as /objects3d.js).

   The look is the video's (edit/pullback_shot.py + edit/lifelike.py): a real
   light map for light and reflections (interior.hdr — Blender's own warm
   interior map, CC0 Poly Haven, lamps capped at 8), a warm key with soft
   shadows, ACES tone mapping, bloom on the bulbs and the neon only, and each
   object's lifelike recipe (clear coat, sheen, glass, mirror metal, neon)
   re-applied on load. The page stays the site's bone: the canvas is
   transparent, the light map only lights and reflects.

   The stripes are the system's --bone and --coral (the video's cream-and-red
   canopy); gold, brass, mirror and walnut are physical materials, not page
   colours. Loads when the section scrolls near, renders only while on screen,
   pixel ratio capped at 2, and steps its quality down if the frame rate drops.
*/
import * as THREE from 'three';
import {RGBELoader} from 'three/addons/loaders/RGBELoader.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {MeshoptDecoder} from 'three/addons/libs/meshopt_decoder.module.js';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {UnrealBloomPass} from 'three/addons/postprocessing/UnrealBloomPass.js';
import {OutputPass} from 'three/addons/postprocessing/OutputPass.js';
import {ShaderPass} from 'three/addons/postprocessing/ShaderPass.js';

const SEATS = [
  ['koi', 'Koi', 'swims through the iris'],
  ['goja-sign', 'Goja sign', 'the neon that opens the loop'],
  ['chicken-heart-skewer', 'Chicken-heart skewer', 'pops in on the street-food burst'],
  ['beerlao', 'Beerlao', 'pops in on the night-out burst'],
  ['disco-ball', 'Disco ball', 'pops in on the dance-floor burst'],
  ['longtail-boat', 'Longtail boat', 'pops in on the river burst'],
  ['el-headphones', 'Headphones', 'his dark space-grey pair, in the opener and the selfie'],
  ['helmet', 'Helmet', 'the motorbike selfie'],
  ['temple', 'Temple', 'circles Patuxai'],
  ['padel-racket', 'Padel racket', 'swings with every shot'],
  ['padel-ball', 'Padel ball', 'hits the lens'],
  ['sticky-rice-basket', 'Sticky-rice basket', 'crosses the footbridge'],
  ['bag-cream-strap', 'Cream-strap bag', 'runs in reverse'],
  ['bag-black-pouch', 'Black pouch', 'packed for the trip'],
  ['turntable', 'Turntable', 'rides the carousel at the end'],
  ['vinyl', 'Vinyl', 'the record the loop spins on'],
  ['gold-glasses', 'Gold glasses', 'worn on the trip'],
  ['monk', 'Monk', 'sits in the corner the whole piece'],
];

/* The lifelike recipe (edit/lifelike.py R), the parts the glb cannot carry:
   clear coat, sheen, glass, neon. Roughness and metal per pixel are baked into
   the glb by edit/export_web_objects.py. */
const LIFE = {
  'koi':                  {coat:.7, coatRough:.08},
  'goja-sign':            {coat:.6, coatRough:.03, neon:5},
  'chicken-heart-skewer': {coat:.35, sheen:.3},
  'beerlao':              {coat:.6, glass:true},
  'disco-ball':           {env:1.35},
  'longtail-boat':        {coat:.15},
  'el-headphones':        {sheen:.4, coat:.2},
  'helmet':               {coat:1, coatRough:.04},
  'temple':               {coat:.1},
  'padel-racket':         {coat:.8, coatRough:.12},
  'padel-ball':           {sheen:.9, sheenRough:.35},
  'sticky-rice-basket':   {sheen:.2},
  'bag-cream-strap':      {sheen:.35},
  'bag-black-pouch':      {sheen:.3, coat:.2},
  'turntable':            {coat:.3},
  'vinyl':                {coat:.6},
  'gold-glasses':         {coat:.3},
  'monk':                 {sheen:.5, sheenRough:.6},
};

const CALM = matchMedia('(prefers-reduced-motion:reduce)').matches;
const COARSE = matchMedia('(pointer:coarse)').matches;
const N = SEATS.length, STEP = Math.PI * 2 / N;
const R = 2.6;                 // ring radius (seat poles)
const DECK = R + .55;          // platform radius
const TOP = 2.05;              // where the canopy starts
const RIM = DECK + .2;         // canopy rim radius
const HC = 1.05;               // canopy height
const SIZE = 1.0;              // an object's biggest side on its seat
const IDLE = .16;              // music-box spin, radians a second

const tok = (n, f) => (getComputedStyle(document.documentElement).getPropertyValue(n).trim() || f);
const canopyY = r => TOP + HC * Math.pow(Math.max(0, 1 - r / RIM), .85);   // a slightly domed cone

export function mountCarousel(el, label){
  const C = {bone: tok('--bone', '#EFE9E1'), paper: tok('--paper', '#F7F4EF'), ink: tok('--ink', '#171512'),
             violet: tok('--violet', '#6D3BF5'), coral: tok('--coral', '#F04A2E'), amber: tok('--amber', '#F09000')};
  const col = c => new THREE.Color(c);
  // physical metals, in linear light (not page colours)
  const GOLD = new THREE.Color().setRGB(1.0, .74, .36), BRASS = new THREE.Color().setRGB(.9, .66, .34);
  const WARM = new THREE.Color().setRGB(1, .72, .44);                     // tungsten bulb / golden-hour key

  /* ── renderer ─────────────────────────────────────────────────────── */
  const renderer = new THREE.WebGLRenderer({antialias:true, alpha:true, powerPreference:'high-performance'});
  const DPR = Math.min(2, devicePixelRatio || 1);
  renderer.setPixelRatio(DPR);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = .9;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap; renderer.shadowMap.autoUpdate = false;
  renderer.setClearColor(0x000000, 0);
  const cv = renderer.domElement; cv.setAttribute('aria-hidden', 'true'); el.appendChild(cv);
  const maxAniso = Math.min(8, renderer.capabilities.getMaxAnisotropy());

  const scene = new THREE.Scene();
  scene.environmentIntensity = .8;
  scene.environmentRotation = new THREE.Euler(0, 0, 0);
  scene.backgroundRotation = scene.environmentRotation;
  const pmrem = new THREE.PMREMGenerator(renderer);
  new RGBELoader().load(new URL('interior.hdr', import.meta.url).href, hdr => {
    hdr.mapping = THREE.EquirectangularReflectionMapping;
    scene.environment = pmrem.fromEquirectangular(hdr).texture; hdr.dispose(); pmrem.dispose(); wake();
  }, undefined, e => console.warn('carousel: no light map', e));

  // the key: warm, high front-left, soft shadows onto the deck and the page
  const key = new THREE.DirectionalLight(WARM, 2.6); key.position.set(-5, 8.5, 7);
  key.castShadow = true;
  const sc = key.shadow; sc.mapSize.setScalar(COARSE ? 1024 : 2048); sc.radius = 4; sc.bias = -.0004; sc.normalBias = .02;
  Object.assign(sc.camera, {left:-5.2, right:5.2, top:5.2, bottom:-5.2, near:1, far:26}); sc.camera.updateProjectionMatrix();
  scene.add(key, key.target);
  // a cool back light for a rim on the canopy and the riders
  const back = new THREE.DirectionalLight(col(C.paper), .9); back.position.set(4, 5, -6); scene.add(back);
  // the bulbs' own warm light under the canopy, and a breath of Goja purple from the centre
  const under = new THREE.PointLight(WARM, 9, 9, 2); under.position.set(0, TOP - .25, 0); scene.add(under);
  const glow = new THREE.PointLight(col(C.violet), 2.2, 5, 2); glow.position.set(0, .9, 0); scene.add(glow);

  const cam = new THREE.PerspectiveCamera(32, 1, .1, 60);

  /* ── post: bloom on the bulbs and the neon only ───────────────────── */
  // Selective, as in the three.js example: the glow is drawn from a pass where everything that should not glow is
  // painted black (it still hides what is behind it), then added over the full render. A plain luminance threshold
  // would also catch the key light's glints on the gold and the mirrors.
  const bloomComposer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(1, 1, {type:THREE.HalfFloatType}));
  bloomComposer.renderToScreen = false;
  bloomComposer.addPass(new RenderPass(scene, cam));
  const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), .45, .05, 0);
  bloomComposer.addPass(bloom);
  const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(1, 1, {type:THREE.HalfFloatType, samples:4}));
  composer.addPass(new RenderPass(scene, cam));
  const mix = new ShaderPass(new THREE.ShaderMaterial({
    uniforms:{tDiffuse:{value:null}, tBloom:{value:bloomComposer.renderTarget2.texture}},
    vertexShader:'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    // the glow is light: it adds to the colour and leaves the alpha; over the page it is kept faint and fades before the canvas edge
    fragmentShader:'uniform sampler2D tDiffuse, tBloom; varying vec2 vUv; void main(){ vec4 c = texture2D(tDiffuse, vUv); vec2 e = smoothstep(0.0, 0.12, vUv) * smoothstep(0.0, 0.12, 1.0 - vUv); gl_FragColor = vec4(c.rgb + texture2D(tBloom, vUv).rgb * mix(0.3, 1.0, c.a) * e.x * e.y, c.a); }',
  }), 'tDiffuse');
  composer.addPass(mix);
  composer.addPass(new OutputPass());
  const BLACK = new THREE.MeshBasicMaterial({color:0x000000}), glows = new Set(), saved = new Map();
  function renderBloom(){
    scene.traverse(m => { if(m.material && !glows.has(m)){ saved.set(m, m.material); m.material = BLACK; } });
    const v = [catcher.visible, under2.visible, blobs.visible]; catcher.visible = under2.visible = blobs.visible = false;
    bloomComposer.render();
    saved.forEach((mt, m) => { m.material = mt; }); saved.clear();
    [catcher.visible, under2.visible, blobs.visible] = v;
  }

  /* ── materials ────────────────────────────────────────────────────── */
  const tex = (c, srgb = true, rep = 1) => { const t = new THREE.CanvasTexture(c);
    if(srgb) t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = maxAniso;
    if(rep !== 1){ t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(rep, rep); } return t; };
  const gold = new THREE.MeshPhysicalMaterial({color:GOLD, metalness:1, roughness:.2, clearcoat:.4, clearcoatRoughness:.1});
  const brass = new THREE.MeshPhysicalMaterial({color:BRASS, metalness:1, roughness:.26});
  const mirror = new THREE.MeshPhysicalMaterial({color:col(C.paper), metalness:1, roughness:.035, envMapIntensity:1.15});
  const enamel = new THREE.MeshPhysicalMaterial({color:col(C.coral), roughness:.34, clearcoat:1, clearcoatRoughness:.06});
  const creme = new THREE.MeshPhysicalMaterial({color:col(C.bone), roughness:.4, clearcoat:.8, clearcoatRoughness:.1});

  // walnut: planks with grain, polished
  const wood = document.createElement('canvas'); wood.width = wood.height = 1024;
  { const g = wood.getContext('2d'), PW = 64, rnd = mulberry(7);
    for(let x = 0; x < 1024; x += PW){
      const k = rnd(), base = [96 + k * 34, 58 + k * 22, 34 + k * 14];
      g.fillStyle = `rgb(${base.map(Math.round)})`; g.fillRect(x, 0, PW, 1024);
      for(let i = 0; i < 26; i++){                                 // grain: long wavy lines
        const gx = x + rnd() * PW, a = .05 + rnd() * .12, dark = rnd() < .6;
        g.strokeStyle = dark ? `rgba(30,16,8,${a})` : `rgba(190,130,80,${a * .7})`; g.lineWidth = .6 + rnd() * 1.6;
        g.beginPath(); const f = .004 + rnd() * .01, ph = rnd() * 6, amp = 1 + rnd() * 3;
        for(let y = 0; y <= 1024; y += 16) g.lineTo(gx + Math.sin(y * f + ph) * amp, y);
        g.stroke();
      }
      const off = rnd() * 1024;                                    // plank ends
      g.fillStyle = 'rgba(20,10,5,.55)'; g.fillRect(x, off, PW, 2);
      g.fillStyle = 'rgba(20,10,5,.7)'; g.fillRect(x, 0, 2, 1024); // seams
    }
  }
  const woodTex = tex(wood);
  const deckMat = new THREE.MeshPhysicalMaterial({map:woodTex, roughness:.32, clearcoat:1, clearcoatRoughness:.05,
    bumpMap:woodTex, bumpScale:.6});

  // canopy stripes, bone and coral, a fine seam between them and a faint painted sheen
  const stripes = document.createElement('canvas'); stripes.width = N * 64; stripes.height = 512;
  { const g = stripes.getContext('2d');
    for(let i = 0; i < N; i++){
      g.fillStyle = i % 2 ? C.coral : C.bone; g.fillRect(i * 64, 0, 64, 512);
      const sh = g.createLinearGradient(i * 64, 0, i * 64 + 64, 0);         // each panel bows a little
      sh.addColorStop(0, 'rgba(0,0,0,.10)'); sh.addColorStop(.5, 'rgba(255,255,255,.06)'); sh.addColorStop(1, 'rgba(0,0,0,.10)');
      g.fillStyle = sh; g.fillRect(i * 64, 0, 64, 512);
      g.fillStyle = 'rgba(40,20,10,.35)'; g.fillRect(i * 64, 0, 1.5, 512);
    }
  }
  const sTex = tex(stripes);
  const canopyMat = new THREE.MeshPhysicalMaterial({map:sTex, roughness:.36, clearcoat:.7, clearcoatRoughness:.12,
    side:THREE.DoubleSide});

  /* ── the carousel itself ──────────────────────────────────────────── */
  const ride = new THREE.Group(); scene.add(ride);          // everything that turns
  const cast = m => { m.castShadow = true; m.receiveShadow = true; return m; };

  // the platform: polished walnut on a coral enamel drum, gold rings, gold studs
  ride.add(cast(mesh(new THREE.CylinderGeometry(DECK, DECK, .1, 128), [gold, deckMat, deckMat], 0, -.05)));
  ride.add(cast(mesh(new THREE.CylinderGeometry(DECK + .1, DECK + .16, .34, 128, 1, true), enamel, 0, -.27)));
  ride.add(cast(mesh(new THREE.CylinderGeometry(DECK + .16, DECK + .16, .02, 128), creme, 0, -.44)));
  for(const [y, r, t] of [[-.1, DECK + .1, .03], [-.43, DECK + .16, .035], [.002, DECK - .02, .018]])
    ride.add(cast(mesh(new THREE.TorusGeometry(r, t, 12, 180), gold, 0, y, m => m.rotation.x = Math.PI / 2)));
  // cream plaques in gold rims round the drum, like the music box's
  { const n = N * 2, plq = new THREE.InstancedMesh(new THREE.CylinderGeometry(.075, .075, .02, 28), creme, n),
      rim = new THREE.InstancedMesh(new THREE.TorusGeometry(.08, .016, 8, 28), gold, n), o = new THREE.Object3D();
    for(let i = 0; i < n; i++){
      const a = (i + .5) / n * Math.PI * 2, r = DECK + .14;
      o.position.set(Math.sin(a) * r, -.27, Math.cos(a) * r); o.rotation.set(0, a, 0); o.rotateX(Math.PI / 2);
      o.scale.set(1.25, 1, .8); o.updateMatrix(); plq.setMatrixAt(i, o.matrix);
      o.rotation.set(0, a, 0); o.scale.set(1.25, .8, 1); o.updateMatrix(); rim.setMatrixAt(i, o.matrix);
    }
    ride.add(plq, rim);
  }

  // the centre: mirrored panels framed in gold between two gold collars
  { const P = 12, cr = .46, h = canopyY(cr) - .05, pw = 2 * cr * Math.tan(Math.PI / P) * .86;
    const pan = new THREE.InstancedMesh(new THREE.BoxGeometry(pw, h - .5, .02), mirror, P);
    const bar = new THREE.InstancedMesh(new THREE.BoxGeometry(.045, h - .3, .05), gold, P), o = new THREE.Object3D();
    for(let i = 0; i < P; i++){
      const a = i / P * Math.PI * 2;
      o.position.set(Math.sin(a) * cr, h / 2, Math.cos(a) * cr); o.rotation.set(0, a, 0); o.updateMatrix(); pan.setMatrixAt(i, o.matrix);
      const b = a + Math.PI / P;
      o.position.set(Math.sin(b) * (cr + .005), h / 2, Math.cos(b) * (cr + .005)); o.rotation.set(0, b, 0); o.updateMatrix();
      bar.setMatrixAt(i, o.matrix);
    }
    const core = mesh(new THREE.CylinderGeometry(cr - .02, cr - .02, h, P), enamel, 0, h / 2);
    ride.add(cast(pan), cast(bar), cast(core));
    ride.add(cast(mesh(new THREE.CylinderGeometry(cr + .1, cr + .14, .24, 48), gold, 0, .12)));
    ride.add(cast(mesh(new THREE.CylinderGeometry(cr + .12, cr + .06, .2, 48), gold, 0, h - .12)));
    for(const y of [.25, h - .23]) ride.add(mesh(new THREE.TorusGeometry(cr + .08, .025, 10, 64), gold, 0, y, m => m.rotation.x = Math.PI / 2));
  }

  // the canopy: a domed cone of stripes, a scalloped valance with gold trim and mirror medallions
  { const prof = [];
    for(let i = 0; i <= 24; i++){ const r = RIM * (1 - i / 24) + .06 * (i / 24); prof.push(new THREE.Vector2(r, canopyY(r))); }
    const roof = mesh(new THREE.LatheGeometry(prof, N * 8), canopyMat); roof.receiveShadow = true; ride.add(roof);
    // valance: one scallop per stripe, cusps on the seams
    const VH = .2, VD = .13, SEG = N * 24, pos = [], uv = [], nor = [], idx = [], edge = [];
    for(let j = 0; j <= SEG; j++){
      const a = j / SEG * Math.PI * 2, f = (a / STEP) % 1, sx = Math.sin(a), cz = Math.cos(a);
      const yb = TOP - VH - VD * Math.sin(Math.PI * f);
      pos.push(sx * RIM, TOP + .01, cz * RIM, sx * RIM, yb, cz * RIM);
      uv.push(j / SEG, .98, j / SEG, .9); nor.push(sx, 0, cz, sx, 0, cz);
      if(j < SEG){ const k = j * 2; idx.push(k, k + 1, k + 2, k + 1, k + 3, k + 2); edge.push(new THREE.Vector3(sx * (RIM + .004), yb, cz * (RIM + .004))); }
    }
    const vg = new THREE.BufferGeometry(); vg.setIndex(idx);
    vg.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    vg.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3)); vg.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
    ride.add(mesh(vg, canopyMat));
    ride.add(mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(edge, true), SEG, .016, 6, true), gold));
    for(const [y, t] of [[TOP + .01, .045], [TOP - .07, .014]])
      ride.add(mesh(new THREE.TorusGeometry(RIM + .01, t, 12, 200), gold, 0, y, m => m.rotation.x = Math.PI / 2));
    const med = new THREE.InstancedMesh(new THREE.CylinderGeometry(.06, .06, .015, 24), creme, N);
    const mr = new THREE.InstancedMesh(new THREE.TorusGeometry(.064, .013, 8, 24), gold, N), o = new THREE.Object3D();
    for(let i = 0; i < N; i++){
      const a = (i + .5) * STEP, r = RIM + .012;
      o.position.set(Math.sin(a) * r, TOP - VH * .5 - VD * .45, Math.cos(a) * r); o.rotation.set(0, a, 0); o.rotateX(Math.PI / 2);
      o.scale.set(1, 1, 1.3); o.updateMatrix(); med.setMatrixAt(i, o.matrix);
      o.rotation.set(0, a, 0); o.scale.set(1, 1.3, 1); o.updateMatrix(); mr.setMatrixAt(i, o.matrix);
    }
    ride.add(med, mr);
    // gold ribs down the seams
    const rib = [];
    for(let i = 0; i <= 12; i++){ const r = RIM * (1 - i / 12) + .08 * (i / 12); rib.push(new THREE.Vector3(0, canopyY(r) + .012, r)); }
    const ribGeo = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(rib), 24, .014, 6);
    const ribs = new THREE.InstancedMesh(ribGeo, gold, N);
    for(let i = 0; i < N; i++){ o.position.set(0, 0, 0); o.rotation.set(0, i * STEP, 0); o.scale.setScalar(1); o.updateMatrix(); ribs.setMatrixAt(i, o.matrix); }
    ride.add(ribs);
    // the finial
    const ty = canopyY(0);
    ride.add(mesh(new THREE.CylinderGeometry(.16, .22, .1, 32), gold, 0, ty - .02));
    ride.add(mesh(new THREE.SphereGeometry(.14, 40, 20), gold, 0, ty + .15));
    ride.add(mesh(new THREE.TorusGeometry(.1, .02, 10, 40), gold, 0, ty + .27, m => m.rotation.x = Math.PI / 2));
    ride.add(mesh(new THREE.ConeGeometry(.045, .34, 20), gold, 0, ty + .45));
  }

  // the bulbs: warm, round the rim, up the seams and round the crown; they chase softly
  const bulbPos = [];
  for(let i = 0; i < N * 2; i++){ const a = i / (N * 2) * Math.PI * 2; bulbPos.push([a, RIM + .05, TOP + .045, 0]); }
  for(let i = 0; i < N; i++) for(const t of [.3, .55, .78]){ const r = RIM * (1 - t); bulbPos.push([i * STEP, r, canopyY(r) + .05, 1]); }
  for(let i = 0; i < N; i++){ const r = .3; bulbPos.push([(i + .5) * STEP, r, canopyY(r) + .05, 2]); }
  const bulbs = new THREE.InstancedMesh(new THREE.SphereGeometry(.042, 16, 10), new THREE.MeshBasicMaterial({color:0xffffff}), bulbPos.length);
  const sockets = new THREE.InstancedMesh(new THREE.CylinderGeometry(.03, .035, .045, 12), brass, bulbPos.length);
  { const o = new THREE.Object3D();
    bulbPos.forEach(([a, r, y], i) => {
      o.position.set(Math.sin(a) * r, y, Math.cos(a) * r); o.rotation.set(0, 0, 0); o.updateMatrix(); bulbs.setMatrixAt(i, o.matrix);
      o.position.y = y - .04; o.updateMatrix(); sockets.setMatrixAt(i, o.matrix);
    }); }
  const BULB = new THREE.Color().setRGB(1, .6, .28).multiplyScalar(7), bc = new THREE.Color();
  ride.add(bulbs, sockets); glows.add(bulbs);

  // the poles: barley-twist brass, one per seat
  { const len = canopyY(R) + .05, g = new THREE.CylinderGeometry(.032, .032, len, 20, 220, true), p = g.attributes.position;
    for(let i = 0; i < p.count; i++){
      const x = p.getX(i), y = p.getY(i), z = p.getZ(i), th = Math.atan2(z, x);
      const k = 1 + .26 * Math.cos(3 * (th - (y / .16) * Math.PI * 2 / 3));
      p.setX(i, x * k); p.setZ(i, z * k); p.setY(i, y + len / 2);
    }
    g.computeVertexNormals();
    const poles = new THREE.InstancedMesh(g, brass, N);
    const caps = new THREE.InstancedMesh(new THREE.CylinderGeometry(.06, .075, .08, 24), gold, N * 2), o = new THREE.Object3D();
    for(let i = 0; i < N; i++){
      const a = i * STEP, x = Math.sin(a) * R, z = Math.cos(a) * R;
      o.position.set(x, 0, z); o.rotation.set(0, 0, 0); o.scale.setScalar(1); o.updateMatrix(); poles.setMatrixAt(i, o.matrix);
      o.position.set(x, .04, z); o.updateMatrix(); caps.setMatrixAt(i * 2, o.matrix);
      o.position.set(x, len - .12, z); o.rotation.x = Math.PI; o.updateMatrix(); caps.setMatrixAt(i * 2 + 1, o.matrix);
    }
    ride.add(cast(poles), cast(caps));
  }

  // soft contact shadows: one under each rider on the deck (grows and fades as it rises), and one under the ride
  const blob = document.createElement('canvas'); blob.width = blob.height = 128;
  { const g = blob.getContext('2d'), r = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    r.addColorStop(0, 'rgba(0,0,0,1)'); r.addColorStop(.45, 'rgba(0,0,0,.45)'); r.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = r; g.fillRect(0, 0, 128, 128); }
  const blobTex = new THREE.CanvasTexture(blob);
  const blobs = new THREE.InstancedMesh(new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2),
    new THREE.MeshBasicMaterial({map:blobTex, color:col(C.ink), transparent:true, opacity:.3, depthWrite:false}), N);
  blobs.position.y = .004; blobs.renderOrder = 1; ride.add(blobs);
  const under2 = mesh(new THREE.PlaneGeometry((DECK + .8) * 2.4, (DECK + .8) * 2.4),
    new THREE.MeshBasicMaterial({map:blobTex, color:col(C.ink), transparent:true, opacity:.32, depthWrite:false}), 0, -.445,
    m => m.rotation.x = -Math.PI / 2);
  scene.add(under2);
  // the key light's shadow on the page itself
  const catcher = mesh(new THREE.PlaneGeometry(30, 30), new THREE.ShadowMaterial({color:col(C.ink), opacity:.2}), 0, -.44,
    m => { m.rotation.x = -Math.PI / 2; m.receiveShadow = true; });
  scene.add(catcher);

  // the seats: an object riding each pole
  const seats = SEATS.map(([id], i) => {
    const a = i * STEP, seat = new THREE.Group();
    seat.position.set(Math.sin(a) * R, 0, Math.cos(a) * R);
    const rider = new THREE.Group(); seat.add(rider);
    ride.add(seat);
    return {id, seat, rider, obj:null, born:0, phase:i * STEP * 3};
  });

  /* ── load the riders, front seats first, and give each its lifelike finish ── */
  const loader = new GLTFLoader(); loader.setMeshoptDecoder(MeshoptDecoder);
  const base = new URL('objects/', import.meta.url);
  const order = seats.map((s, i) => [Math.min(i, N - i), s]).sort((a, b) => a[0] - b[0]).map(x => x[1]);
  let q = 0, done = 0, doneAt = 0;
  const next = () => {
    const s = order[q++]; if(!s) return;
    loader.load(new URL(s.id + '.glb', base).href, gl => {
      const o = gl.scene, box = new THREE.Box3().setFromObject(o), size = box.getSize(new THREE.Vector3());
      o.position.sub(box.getCenter(new THREE.Vector3()));
      const holder = new THREE.Group(); holder.add(o); holder.scale.setScalar(SIZE / Math.max(size.x, size.y, size.z));
      o.traverse(m => { if(m.isMesh && m.material){ m.material = lifelike(m.material, s.id); m.castShadow = true; m.receiveShadow = true;
        if(LIFE[s.id] && LIFE[s.id].neon) glows.add(m); } });
      s.rider.add(holder); s.obj = holder; s.born = performance.now(); s.rider.scale.setScalar(.001);
      done++; doneAt = performance.now(); next(); wake();
    }, undefined, e => { console.warn('carousel: could not load', s.id, e); done++; doneAt = performance.now(); next(); });
  };
  for(let i = 0; i < 4; i++) next();

  function lifelike(m0, id){
    const r = LIFE[id] || {};
    const m = m0.isMeshPhysicalMaterial ? m0 : Object.assign(new THREE.MeshPhysicalMaterial(), {name:m0.name});
    if(m !== m0){
      for(const k of ['color', 'map', 'normalMap', 'normalScale', 'roughness', 'metalness', 'roughnessMap', 'metalnessMap',
        'emissive', 'emissiveMap', 'emissiveIntensity', 'aoMap', 'side', 'transparent', 'opacity', 'alphaTest'])
        if(m0[k] !== undefined) m[k] = m0[k] && m0[k].clone && !m0[k].isTexture ? m0[k].clone() : m0[k];
      m0.dispose();
    }
    for(const t of [m.map, m.normalMap, m.roughnessMap, m.emissiveMap]) if(t){ t.anisotropy = maxAniso; t.needsUpdate = true; }
    m.side = THREE.FrontSide;
    if(r.coat !== undefined){ m.clearcoat = r.coat; m.clearcoatRoughness = r.coatRough ?? .1; }
    if(r.sheen){ m.sheen = r.sheen; m.sheenRoughness = r.sheenRough ?? .5; m.sheenColor = new THREE.Color(1, 1, 1); }
    if(!m.normalMap && m.map){ m.bumpMap = m.map; m.bumpScale = .5; }    // micro-bump from the texture, as in the renders
    if(r.env) m.envMapIntensity = r.env;
    if(r.glass){                                                        // the green bottle: real glass
      m.transmission = m.transmission || 1; m.thickness = .35; m.ior = 1.5;
      m.attenuationColor = new THREE.Color().setRGB(.25, .6, .2); m.attenuationDistance = .6; m.specularIntensity = 1;
    }
    if(r.neon){                                                         // the Goja tubes: lit neon
      m.emissive = new THREE.Color(1, 1, 1); m.emissiveMap = m.emissiveMap || m.map; m.emissiveIntensity = r.neon;
      m.toneMapped = true;
    }
    m.needsUpdate = true;
    return m;
  }

  /* ── motion: drag with weight, snap to a seat, music-box idle ─────── */
  let rot = 0, vel = 0, mode = CALM ? 'rest' : 'idle', target = 0, restAt = 0, front = -1;
  let ppu = 100;                                           // screen px per world unit at the front seat
  let drag = null;

  const nearest = r => Math.round(r / STEP) * STEP;
  cv.style.touchAction = 'pan-y'; el.style.touchAction = 'pan-y';
  el.addEventListener('pointerdown', e => {
    if(e.button > 0) return;
    drag = {id:e.pointerId, x0:e.clientX, y0:e.clientY, x:e.clientX, t:performance.now(), h:null};
  });
  el.addEventListener('pointermove', e => {
    if(!drag || e.pointerId !== drag.id) return;
    const dx = e.clientX - drag.x0, dy = e.clientY - drag.y0;
    if(drag.h === null){
      if(Math.hypot(dx, dy) < 6) return;
      drag.h = Math.abs(dx) > Math.abs(dy);
      if(!drag.h){ drag = null; return; }                  // a vertical swipe is the page's, not ours
      try{ el.setPointerCapture(e.pointerId); }catch(_){}
      mode = 'drag'; vel = 0; el.classList.add('grabbing');
    }
    const now = performance.now(), d = (e.clientX - drag.x) / (R * ppu), dt = Math.max(1, now - drag.t) / 1000;
    rot += d; vel = vel * .6 + (d / dt) * .4;
    drag.x = e.clientX; drag.t = now; e.preventDefault(); wake();
  });
  const up = e => {
    if(!drag || e.pointerId !== drag.id) return;
    if(drag.h){
      if(performance.now() - drag.t > 90) vel = 0;           // held still before letting go: no fling
      vel = Math.max(-9, Math.min(9, vel)); mode = 'free'; el.classList.remove('grabbing');
    }
    drag = null; wake();
  };
  el.addEventListener('pointerup', up); el.addEventListener('pointercancel', up);
  el.tabIndex = 0;
  el.addEventListener('keydown', e => {
    if(e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    e.preventDefault(); target = nearest(rot) + (e.key === 'ArrowRight' ? STEP : -STEP); mode = 'snap'; wake();
  });

  const o3 = new THREE.Object3D();
  function step(dt, now){
    if(mode === 'free'){
      vel *= Math.exp(-1.6 * dt); rot += vel * dt;
      if(Math.abs(vel) < .9){ target = nearest(rot + vel * .35); mode = 'snap'; }
    } else if(mode === 'snap'){
      const k = 26, c = 2 * Math.sqrt(k) * .85;
      vel += (k * (target - rot) - c * vel) * dt; rot += vel * dt;
      if(Math.abs(target - rot) < 1e-3 && Math.abs(vel) < 2e-3){ rot = target; vel = 0; mode = 'rest'; restAt = now; }
    } else if(mode === 'rest'){
      if(!CALM && now - restAt > 3200) mode = 'idle';
    } else if(mode === 'idle'){
      vel += (IDLE - vel) * Math.min(1, dt * .7); rot += vel * dt;
    }
    ride.rotation.y = rot;
    const t = now / 1000;
    seats.forEach((s, i) => {
      const bob = CALM ? 0 : Math.sin(t * 1.5 + s.phase);
      s.rider.position.y = 1.0 + bob * .13;
      s.rider.rotation.y = (CALM ? 0 : t * .35) - rot + s.phase * .2;   // turns on its own, not with the ride
      if(s.obj){ const k = Math.min(1, (now - s.born) / 600); s.rider.scale.setScalar(.001 + (1 - Math.pow(1 - k, 3)) * .999); }
      const a = i * STEP, sc = s.obj ? .95 + bob * .12 : .001;
      o3.position.set(Math.sin(a) * R, 0, Math.cos(a) * R); o3.scale.set(sc, 1, sc); o3.updateMatrix(); blobs.setMatrixAt(i, o3.matrix);
    });
    blobs.instanceMatrix.needsUpdate = true;
    // the bulbs chase round the rim, softly
    bulbPos.forEach(([a, , , ring], i) => {
      const k = CALM ? .85 : .72 + .28 * (.5 + .5 * Math.sin(t * 3 - a * 6 - ring * 1.2));
      bulbs.setColorAt(i, bc.copy(BULB).multiplyScalar(k));
    });
    bulbs.instanceColor.needsUpdate = true;
    const f = ((Math.round(-rot / STEP) % N) + N) % N;
    if(f !== front){ front = f; const [, name, cap] = SEATS[f]; if(label) label.textContent = `${name} — ${cap}`; }
  }

  /* ── quality: full on desktop; steps down if the frame rate drops ── */
  let tier = 2, pr = DPR;                                      // 2 bloom + shadows, 1 shadows, 0 neither and a lower pixel ratio
  function setTier(n){
    tier = n;
    if(n < 1){ key.castShadow = false; renderer.shadowMap.enabled = false; catcher.visible = false; pr = Math.min(DPR, 1.25);
      scene.traverse(m => { if(m.material) (Array.isArray(m.material) ? m.material : [m.material]).forEach(x => x.needsUpdate = true); }); }
    fit();
  }
  const perf = {frames:0, time:0, fps:0};

  /* ── size, camera, render only while seen ─────────────────────────────
     The camera is fitted to the whole ride on every size: the carousel's
     bounds (measured once from the built geometry: deck, canopy rim, finial)
     are sampled as a hull, and the camera backs off along its fixed viewing
     angle until every hull point sits inside the frame with a margin. So a
     phone sees the whole carousel with room round it, and a wide desktop
     canvas sees it at full height. */
  const bb = new THREE.Box3().setFromObject(ride);
  // never smaller than the parts we know are there (instanced parts can measure short)
  const rad = Math.max(-bb.min.x, bb.max.x, -bb.min.z, bb.max.z, RIM + .12),
        yLo = Math.min(bb.min.y, -.46), yHi = Math.max(bb.max.y, TOP + HC + .62);
  const hull = [new THREE.Vector3(0, yHi, 0)];
  for(let i = 0; i < 32; i++){ const a = i / 32 * Math.PI * 2, cx = Math.sin(a) * rad, cz = Math.cos(a) * rad;
    hull.push(new THREE.Vector3(cx, yLo, cz), new THREE.Vector3(cx, TOP + .1, cz)); }
  const centreY = (yLo + yHi) / 2, ELEV = .21, pv = new THREE.Vector3();
  function spread(dist){                                   // how far the hull reaches across the frame, 1 = the edge
    cam.position.set(0, centreY + Math.sin(ELEV) * dist, Math.cos(ELEV) * dist);
    cam.lookAt(0, centreY, 0); cam.updateMatrixWorld(); cam.updateProjectionMatrix();
    let m = 0; for(const p of hull){ pv.copy(p).project(cam); m = Math.max(m, Math.abs(pv.x), Math.abs(pv.y)); }
    return m;
  }
  function fit(){
    const w = el.clientWidth, h = el.clientHeight; if(!w || !h) return;
    renderer.setPixelRatio(pr); renderer.setSize(w, h, false);
    composer.setPixelRatio(pr); composer.setSize(w, h);
    bloomComposer.setPixelRatio(pr / 2); bloomComposer.setSize(w, h);
    const aspect = w / h, narrow = aspect < 1.2;
    cam.fov = narrow ? 36 : 30; cam.aspect = aspect;
    const fill = narrow ? .9 : .92;                        // the margin: the hull fills 90% of the frame
    let lo = 2, hi = 80;
    for(let i = 0; i < 30; i++){ const mid = (lo + hi) / 2; if(spread(mid) > fill) lo = mid; else hi = mid; }
    const dist = hi; spread(dist);
    const vt = Math.tan(THREE.MathUtils.degToRad(cam.fov / 2));
    ppu = h / (2 * (dist - R) * vt);
  }
  new ResizeObserver(() => { fit(); wake(); }).observe(el);
  fit();

  let seen = true, raf = 0, last = performance.now();
  function loop(now){
    raf = 0;
    const raw = (now - last) / 1000, dt = Math.min(.05, raw); last = now;
    step(dt, now);
    if(tier === 2){ renderBloom(); renderer.shadowMap.needsUpdate = true; composer.render(); }
    else { renderer.shadowMap.needsUpdate = true; renderer.render(scene, cam); }
    // judge the frame rate once everything has loaded; step down at most twice
    if(done === N && now - doneAt > 1500 && raw < .5){      // settled: every rider loaded and uploaded
      perf.frames++; perf.time += raw;
      if(perf.frames >= 120){
        perf.fps = perf.frames / perf.time; perf.frames = 0; perf.time = 0;
        perf.low = perf.fps < 40 ? (perf.low || 0) + 1 : 0;
        if(perf.low >= 2 && tier > 0){ perf.low = 0; setTier(tier - 1); }   // two slow seconds running, not one hitch
      }
    }
    if(seen && !document.hidden) raf = requestAnimationFrame(loop);
  }
  function wake(){ if(!raf && seen){ last = performance.now(); raf = requestAnimationFrame(loop); } }
  new IntersectionObserver(es => { seen = es[0].isIntersecting; wake(); }).observe(el);
  document.addEventListener('visibilitychange', wake);
  wake();
  return {spin:v => { vel = v; mode = 'free'; wake(); }, get front(){ return SEATS[front] && SEATS[front][0]; },
          get fps(){ return perf.fps; }, get tier(){ return tier; }, setTier};
}

function mesh(geo, mat, x = 0, y = 0, f){
  const m = new THREE.Mesh(geo, mat); m.position.set(x, y, 0); if(f) f(m); return m;
}

function mulberry(a){ return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a);
  t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

/* start loading only when the section is near */
const el = document.getElementById('carousel');
if(el){
  let ok = false;
  try{ const p = document.createElement('canvas'); ok = !!(p.getContext('webgl2') || p.getContext('webgl')); }catch(_){}
  if(ok){
    const near = new IntersectionObserver(es => {
      if(!es.some(e => e.isIntersecting)) return;
      near.disconnect();
      window.daemnCarousel = mountCarousel(el, document.getElementById('carousel-label'));
    }, {rootMargin:'600px 0px'});
    near.observe(el);
  }
}
