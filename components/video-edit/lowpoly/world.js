/* world.js — a blocky early-2000s console world, drawn entirely in code with three.js.
   Reads window.AD = {beats:[{t,e,scene,bumps,...}], dur}. draw(t) paints the frame at t. Same t, same frame. */
(function(){
const AD=window.AD, RW=AD.res?AD.res[0]:486, RH=AD.res?AD.res[1]:864;
const canvas=document.getElementById('gl');
const R=new THREE.WebGLRenderer({canvas,antialias:false,preserveDrawingBuffer:true});
R.setPixelRatio(1);R.setSize(RW,RH,false);
const scene=new THREE.Scene();
const SMOG=new THREE.Color('#d9cdb4');
scene.fog=new THREE.Fog(SMOG,9,34);scene.background=SMOG.clone();
const cam=new THREE.PerspectiveCamera(46,RW/RH,.02,80);
const hemi=new THREE.HemisphereLight('#ffe2b8','#2a1a10',.62);scene.add(hemi);
const sun=new THREE.DirectionalLight('#ffbe7a',3);sun.position.set(6,6,5);scene.add(sun);

let seed=7;const rnd=()=>{seed=(seed*16807)%2147483647;return seed/2147483647};
const mat=c=>new THREE.MeshLambertMaterial({color:c});
const box=(w,h,d,c)=>new THREE.Mesh(new THREE.BoxGeometry(w,h,d),mat(c));
const cyl=(a,b,h,s,c)=>new THREE.Mesh(new THREE.CylinderGeometry(a,b,h,s),mat(c));
const at=(m,x,y,z)=>{m.position.set(x,y,z);return m};
function tex(w,h,fn,rep){const c=document.createElement('canvas');c.width=w;c.height=h;fn(c.getContext('2d'),w,h);
 const t=new THREE.CanvasTexture(c);t.magFilter=THREE.LinearFilter;t.minFilter=THREE.LinearFilter;t.colorSpace=THREE.SRGBColorSpace;t.wrapS=t.wrapT=THREE.RepeatWrapping;if(rep)t.repeat.set(rep[0],rep[1]);return t}

/* the shop */
const shop=new THREE.Group();scene.add(shop);
const floorT=tex(64,64,(g,w)=>{for(let i=0;i<2;i++)for(let j=0;j<2;j++){g.fillStyle=(i+j)%2?'#a7a49c':'#b4b1a8';g.fillRect(i*w/2,j*w/2,w/2,w/2)}
 g.fillStyle='rgba(60,50,40,.12)';for(let k=0;k<60;k++)g.fillRect(Math.random()*w|0,Math.random()*w|0,2,2)},[9,12]);
const fl=new THREE.Mesh(new THREE.PlaneGeometry(18,24),new THREE.MeshLambertMaterial({map:floorT}));fl.rotation.x=-Math.PI/2;shop.add(fl);
const wallT=tex(64,64,(g,w,h)=>{g.fillStyle='#ece7da';g.fillRect(0,0,w,h);g.fillStyle='#dcd6c6';g.fillRect(0,0,w,2);g.fillStyle='#1a1a1c';g.fillRect(0,60,w,4)},[4,1]);
const wm=new THREE.MeshLambertMaterial({map:wallT});
const back=new THREE.Mesh(new THREE.PlaneGeometry(18,5.2),wm);at(back,0,2.6,-9);shop.add(back);
const left=new THREE.Mesh(new THREE.PlaneGeometry(24,5.2),wm);left.rotation.y=Math.PI/2;at(left,-7,2.6,0);shop.add(left);
const right=left.clone();right.rotation.y=-Math.PI/2;at(right,7,2.6,0);shop.add(right);
const front=back.clone();front.rotation.y=Math.PI;at(front,0,2.6,11);shop.add(front);
const ceil=at(box(18,.2,24,'#e5d7b6'),0,5.2,0);shop.add(ceil);
for(const z of[-6,-1,4]){const l=at(box(2.6,.08,.3,'#fff6d8'),0,5.06,z);l.material=new THREE.MeshBasicMaterial({color:'#fff6d8'});shop.add(l)}
/* mirrors, stations, posters: repeats like a game set */
const mirrorMat=new THREE.MeshBasicMaterial({color:'#9fc0c4'});
for(const z of[-6,-2.4,1.2]){
 const fr=at(box(.14,2.3,2.2,'#101012'),-6.9,2.9,z);shop.add(fr);
 const mr=at(box(.04,2,1.9,'#9fc0c4'),-6.8,2.9,z);mr.material=mirrorMat;shop.add(mr);
 const sh=at(box(.6,.12,2.6,'#f4f1ea'),-6.65,1.5,z);shop.add(sh);
 for(let i=0;i<3;i++)shop.add(at(cyl(.07,.09,.34,6,['#e0559a','#121214','#d9b45a'][i]),-6.6,1.72,z-.5+i*.5));
}
const posterT=tex(40,56,(g,w,h)=>{g.fillStyle='#e8dcc0';g.fillRect(0,0,w,h);for(let i=0;i<4;i++)for(let j=0;j<3;j++){g.fillStyle='#2b2018';g.beginPath();g.arc(8+i*8,12+j*16,3.4,0,7);g.fill();g.fillRect(5+i*8,16+j*16,6,5)}});
const po=new THREE.Mesh(new THREE.PlaneGeometry(2,2.8),new THREE.MeshLambertMaterial({map:posterT}));po.rotation.y=-Math.PI/2;at(po,6.9,3,-3);shop.add(po);
/* the barber pole, spinning like a loaded prop */
const poleT=tex(32,32,(g,w,h)=>{g.fillStyle='#f2ead8';g.fillRect(0,0,w,h);for(let i=-w;i<w*2;i+=11){g.strokeStyle=(i/11|0)%2?'#c23a2a':'#2d5fa8';g.lineWidth=5;g.beginPath();g.moveTo(i,0);g.lineTo(i+h,h);g.stroke()}},[2,2]);
const pole=new THREE.Mesh(new THREE.CylinderGeometry(.22,.22,1.9,8),new THREE.MeshLambertMaterial({map:poleT}));at(pole,3.1,2.4,-8.7);shop.add(pole);
const ring=new THREE.Mesh(new THREE.TorusGeometry(.5,.07,6,14),new THREE.MeshBasicMaterial({color:'#fffdf2'}));at(ring,-5.3,3,-.6);ring.rotation.y=Math.PI/2;shop.add(ring);shop.add(at(cyl(.03,.03,2.5,5,'#111'),-5.3,1.25,-.6));
const gold=new THREE.Group();for(let i=0;i<14;i++){const r=at(box(.03,1.1,.03,'#d9b45a'),0,0,0);r.geometry.translate(0,.55,0);r.rotation.set(i*.9,0,i*.45);gold.add(r)}at(gold,0,4,-5.5);shop.add(gold);
/* door + street outside, seen through it */
const sky=new THREE.Mesh(new THREE.PlaneGeometry(5,3.4),new THREE.MeshBasicMaterial({color:'#e8b873'}));at(sky,3.6,1.8,-8.95);shop.add(sky);
const door=new THREE.Group();const dl=at(box(1.1,3.2,.1,'#3c2a1c'),.55,1.6,0);door.add(dl);door.position.set(-1.8,0,10.9);shop.add(door);
/* the chair */
const chair=new THREE.Group();
chair.add(at(cyl(.5,.62,.14,8,'#555'),0,.07,0),at(cyl(.12,.12,.6,6,'#999'),0,.4,0),at(box(1.15,.26,1,'#a11f1f'),0,.82,0),at(box(1.15,1.5,.26,'#a11f1f'),0,1.5,-.44),at(box(.16,.14,.9,'#2c2c30'),-.56,1.2,0),at(box(.16,.14,.9,'#2c2c30'),.56,1.2,0),at(box(.8,.1,.34,'#333'),0,.3,.62));
at(chair,-3.4,0,-2.4);chair.rotation.y=Math.PI/2;shop.add(chair);

/* people: a painted face map, the way those games did it */
function faceTex(o){return tex(128,128,(g,w,h)=>{const sk=o.skin;g.fillStyle=sk;g.fillRect(0,0,w,h);
 const cx=32; /* the face sits at a quarter of the map */
 const sh=g.createRadialGradient(cx,66,6,cx,66,44);sh.addColorStop(0,'rgba(255,220,180,.16)');sh.addColorStop(1,'rgba(0,0,0,.42)');g.fillStyle=sh;g.fillRect(0,0,w,h);
 if(o.hairp){g.fillStyle='#0b0806';g.fillRect(0,0,w,34);for(let x=2;x<w;x+=7){g.fillStyle='#231810';g.fillRect(x,0,2,36)}}
 else if(o.bald){g.fillStyle='rgba(255,230,200,.1)';g.fillRect(0,0,w,24)}
 const dark='rgba(20,10,6,.85)';
 for(const s of[-1,1]){const ex=cx+s*11;g.fillStyle='rgba(0,0,0,.28)';g.fillRect(ex-7,48,14,9);g.fillStyle=dark;g.fillRect(ex-7,44,14,3);g.fillStyle='#e8dfcf';g.fillRect(ex-5,50,10,4);g.fillStyle='#160c08';g.fillRect(ex-2,50,4,4);g.fillStyle='rgba(0,0,0,.3)';g.fillRect(ex-6,55,12,1)}
 g.fillStyle='rgba(0,0,0,.3)';g.fillRect(cx-4,52,2,16);g.fillStyle='rgba(255,220,190,.14)';g.fillRect(cx-1,50,3,16);g.fillStyle='rgba(0,0,0,.4)';g.fillRect(cx-6,68,12,3);
 g.fillStyle='rgba(60,20,16,.9)';g.fillRect(cx-9,77,18,3);g.fillStyle='rgba(120,60,50,.8)';g.fillRect(cx-8,80,16,3);
 if(o.stache){g.fillStyle=dark;g.fillRect(cx-10,74,20,2);g.fillRect(cx-3,84,6,6)}
 if(o.bearded){g.fillStyle='rgba(12,8,6,.8)';g.fillRect(cx-22,74,44,30)}
 if(o.shades){g.fillStyle='#0c0c0e';g.fillRect(cx-19,47,16,9);g.fillRect(cx+3,47,16,9);g.fillRect(cx-3,49,6,2)}
 g.fillStyle='rgba(0,0,0,.25)';g.fillRect(cx-30,94,60,34)})}
function ribTex(c,lines){return tex(32,32,(g,w,h)=>{g.fillStyle=c;g.fillRect(0,0,w,h);g.fillStyle='rgba(0,0,0,.14)';for(let i=0;i<lines;i++)g.fillRect(0,(Math.random()*h)|0,w,1);g.fillStyle='rgba(255,255,255,.05)';for(let i=0;i<30;i++)g.fillRect((Math.random()*w)|0,(Math.random()*h)|0,2,1)})}
/* people: lofted bodies with shading painted into the texture, the way those games baked it */
function loft(rings,seg,tex_){const pos=[],uv=[],idx=[];const n=rings.length;
 for(let r=0;r<n;r++){const q=rings[r];for(let k=0;k<=seg;k++){const a=k/seg*Math.PI*2;
  const sx=Math.sin(a),cz=Math.cos(a);const fl=q.flat||0;
  pos.push((q.cx||0)+sx*q.rx*(1+fl*Math.abs(sx)),q.y,(q.cz||0)+cz*q.rz);uv.push(k/seg,r/(n-1))}}
 for(let r=0;r<n-1;r++)for(let k=0;k<seg;k++){const a=r*(seg+1)+k,b=a+1,c=a+seg+1,d=c+1;idx.push(a,c,b,b,c,d)}
 const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.setIndex(idx);g.computeVertexNormals();
 return new THREE.Mesh(g,new THREE.MeshLambertMaterial({map:tex_,side:THREE.DoubleSide}))}
function soft(c,w,h,fn){const t=tex(w,h,fn);t.magFilter=THREE.LinearFilter;t.minFilter=THREE.LinearMipmapLinearFilter;t.generateMipmaps=true;t.colorSpace=THREE.SRGBColorSpace;return t}
const hexa=(c,a)=>{const n=parseInt(c.slice(1),16);return 'rgba('+(n>>16)+','+((n>>8)&255)+','+(n&255)+','+a+')'};
function shade(hex,k){const n=parseInt(hex.slice(1),16),f=x=>Math.max(0,Math.min(255,Math.round(x*k)));return 'rgb('+f(n>>16)+','+f((n>>8)&255)+','+f(n&255)+')'}
function skinMap(o){return soft(0,128,128,(g,w,h)=>{const gr=g.createLinearGradient(0,0,w,0);const d=shade(o.skin,.52),m=o.skin,l=shade(o.skin,1.3);gr.addColorStop(0,d);gr.addColorStop(.25,m);gr.addColorStop(.5,l);gr.addColorStop(.75,m);gr.addColorStop(1,d);g.fillStyle=gr;g.fillRect(0,0,w,h);for(let i=0;i<500;i++){g.fillStyle='rgba(0,0,0,.05)';g.fillRect(Math.random()*w,Math.random()*h,2,2)}})}
function torsoMap(o){return soft(0,256,256,(g,w,h)=>{const sk=skinMap(o);const gr=g.createLinearGradient(0,0,w,0);const b=o.shirt,d=shade(b,.5),l=shade(b,1.12);gr.addColorStop(0,d);gr.addColorStop(.3,b);gr.addColorStop(.5,l);gr.addColorStop(.7,b);gr.addColorStop(1,d);g.fillStyle=gr;g.fillRect(0,0,w,h);
 if(!o.sleeve){g.fillStyle='rgba(0,0,0,.09)';for(let x=0;x<w;x+=5)g.fillRect(x,0,2,h)}
 for(let i=0;i<14;i++){g.strokeStyle='rgba(0,0,0,'+(.05+Math.random()*.1)+')';g.lineWidth=2+Math.random()*4;g.beginPath();const y=h*.25+Math.random()*h*.7,x=Math.random()*w;g.moveTo(x,y);g.quadraticCurveTo(x+40,y+Math.random()*20-10,x+90,y+Math.random()*30-15);g.stroke()}
 /* pecs and belly pushing through the cloth */
 g.fillStyle='rgba(0,0,0,.14)';g.fillRect(w*.495,h*.04,4,h*.3);const pc=g.createRadialGradient(w*.42,h*.2,4,w*.42,h*.2,44);pc.addColorStop(0,'rgba(255,255,255,.16)');pc.addColorStop(1,'rgba(255,255,255,0)');g.fillStyle=pc;g.fillRect(0,0,w,h);const pd=g.createRadialGradient(w*.58,h*.2,4,w*.58,h*.2,44);pd.addColorStop(0,'rgba(255,255,255,.16)');pd.addColorStop(1,'rgba(255,255,255,0)');g.fillStyle=pd;g.fillRect(0,0,w,h);
 if(!o.sleeve){/* shoulders and arm holes are skin: top of the map is the neck end */
  g.fillStyle=shade(o.skin,.95);g.fillRect(0,0,w,h*.07);g.fillRect(0,0,w*.2,h*.4);g.fillRect(w*.8,0,w*.2,h*.4);g.fillRect(w*.42,0,w*.16,h*.13)}
 g.fillStyle='rgba(0,0,0,.55)';g.fillRect(0,h*.97,w,h*.03)})}
function denimMap(c){return soft(0,128,128,(g,w,h)=>{const gr=g.createLinearGradient(0,0,w,0);gr.addColorStop(0,shade(c,.5));gr.addColorStop(.5,shade(c,1.25));gr.addColorStop(1,shade(c,.5));g.fillStyle=gr;g.fillRect(0,0,w,h);for(let i=0;i<1400;i++){g.fillStyle=Math.random()>.5?'rgba(255,255,255,.04)':'rgba(0,0,0,.06)';g.fillRect(Math.random()*w,Math.random()*h,1,3)}for(let i=0;i<9;i++){g.fillStyle='rgba(0,0,0,.13)';g.fillRect(0,Math.random()*h,w,3+Math.random()*5)}})}
function headGeo(){const g=new THREE.SphereGeometry(.2,22,18);const v=g.attributes.position;const bump=(x,y,cx,cy,sx,sy)=>Math.exp(-((x-cx)*(x-cx))/(2*sx*sx)-((y-cy)*(y-cy))/(2*sy*sy));
 for(let i=0;i<v.count;i++){let x=v.getX(i)/.2,y=v.getY(i)/.2,z=v.getZ(i)/.2;
  const jaw=y<0?1+.02*y:1-.1*y*y;let wx=jaw;if(y<-.45)wx*=1-.34*Math.pow((-y-.45)/.55,1.6);
  let yy=y*(y<0?1.2:1.06);let zz=z*.98;
  if(z>0){const f=z;zz+=f*(.17*bump(x,y,0,-.02,.1,.2)  /* nose */ +.1*bump(x,y,0,.27,.5,.05) /* brow */ -.1*bump(Math.abs(x),y,.33,.16,.14,.08) /* eye socket */ +.06*bump(Math.abs(x),y,.46,-.1,.16,.13) /* cheek */ +.07*bump(x,y,0,-.46,.2,.06) /* lips */ -.05*bump(x,y,0,-.58,.2,.03) +.07*bump(x,y,0,-.74,.2,.1) /* chin */)}
  v.setXYZ(i,x*wx*.2*.86,yy*.2,zz*.2)}
 g.computeVertexNormals();return g}
function faceMap(o){return soft(0,256,256,(g,w,h)=>{g.filter='blur(1.6px)';const sk=o.skin;const gr=g.createLinearGradient(0,0,w,0);gr.addColorStop(0,shade(sk,.42));gr.addColorStop(.25,shade(sk,1.12));gr.addColorStop(.5,shade(sk,.42));gr.addColorStop(.75,shade(sk,.42));gr.addColorStop(1,shade(sk,.42));g.fillStyle=gr;g.fillRect(0,0,w,h);
 const cx=64,S=1; /* three.js sphere: the front sits at a quarter of the map */
 g.fillStyle='rgba(0,0,0,.34)';g.fillRect(cx-26,96,20,12);g.fillRect(cx+6,96,20,12);
 for(const q of[-1,1]){const ex=cx+q*15;g.fillStyle='rgba(16,8,5,.85)';g.save();g.translate(ex,92);g.rotate(q*.1);g.fillRect(-11,-1,22,4);g.restore();g.fillStyle='#d8cdbb';g.fillRect(ex-8,100,16,5);g.fillStyle='#1b0f09';g.fillRect(ex-3,99,7,7);g.fillStyle='rgba(0,0,0,.5)';g.fillRect(ex-9,98,18,2);g.fillStyle='rgba(0,0,0,.2)';g.fillRect(ex-8,108,16,2)}
 g.fillStyle='rgba(255,225,190,.2)';g.fillRect(cx-2,100,4,28);g.fillStyle='rgba(0,0,0,.34)';g.fillRect(cx-5,104,2,24);g.fillRect(cx+4,104,2,24);g.fillStyle='rgba(0,0,0,.5)';g.fillRect(cx-9,130,18,4);
 g.fillStyle='#3a1610';g.fillRect(cx-13,149,26,3);g.fillStyle=shade(sk,.8);g.fillRect(cx-12,146,24,3);g.fillStyle=shade(sk,.9);g.fillRect(cx-11,152,22,4);
 if(o.stache){g.fillStyle='rgba(10,6,4,.6)';g.fillRect(cx-14,141,28,3);g.fillRect(cx-4,167,8,7)}
 if(o.hairp){g.fillStyle='#0b0705';g.fillRect(0,0,w,76);g.fillStyle='rgba(120,90,60,.2)';for(let x=-4;x<w;x+=13){g.fillRect(x,0,2,78)}g.fillStyle=shade(sk,.5);for(let x=0;x<w;x+=13)g.fillRect(x+6,62,2,14)}
 if(o.bald){const b=g.createRadialGradient(cx,30,4,cx,30,70);b.addColorStop(0,'rgba(255,230,200,.24)');b.addColorStop(1,'rgba(255,230,200,0)');g.fillStyle=b;g.fillRect(0,0,w,110)}})}
function person(o){const g=new THREE.Group(),p={g};const skin=o.skin,shirt=o.shirt,pant=o.pant;const sm=skinMap(o),dm=denimMap(pant);
 p.hip=at(new THREE.Group(),0,.98,0);g.add(p.hip);p.torso=at(new THREE.Group(),0,0,0);p.hip.add(p.torso);
 const tm=loft([{y:.02,rx:.245,rz:.17},{y:.3,rx:.25,rz:.17},{y:.52,rx:.31,rz:.2,cz:.012},{y:.72,rx:.37,rz:.225,cz:.02},{y:.86,rx:.41,rz:.2,flat:.12},{y:.97,rx:.26,rz:.15},{y:1.03,rx:.125,rz:.115}],14,(()=>{const t=torsoMap(o);t.flipY=true;t.needsUpdate=true;return t})());
 tm.geometry.attributes.uv.array.forEach(()=>0);{const u=tm.geometry.attributes.uv;for(let i=0;i<u.count;i++)u.setX(i,u.getX(i)+.5);u.needsUpdate=true}
 p.torso.add(tm);
 p.neck=at(new THREE.Group(),0,.98,0);p.torso.add(p.neck);
 const n=loft([{y:0,rx:.135,rz:.13},{y:.15,rx:.118,rz:.115},{y:.27,rx:.112,rz:.11}],10,sm);p.neck.add(n);n.material=n.material.clone();p.nk=n;
 p.head=at(new THREE.Group(),0,.4,.03);p.neck.add(p.head);
 const h=new THREE.Mesh(headGeo(),new THREE.MeshLambertMaterial({map:faceMap(o)}));h.scale.set(.98,1.06,1.02);p.head.add(h);
 for(const e of[-1,1]){const ear=at(new THREE.Mesh(new THREE.SphereGeometry(.04,6,6),new THREE.MeshLambertMaterial({map:sm})),e*.195,.0,-.01);ear.scale.set(.35,1,.7);p.head.add(ear)}
 p.mouth=new THREE.Mesh(new THREE.BoxGeometry(.06,.006,.01),new THREE.MeshBasicMaterial({color:'#1e0a08'}));at(p.mouth,0,-.102,.196);p.head.add(p.mouth);
 p.arms=[];p.legs=[];
 for(const s of[-1,1]){const a=at(new THREE.Group(),s*.47,.84,0);p.torso.add(a);const cm=o.sleeve?(()=>denimMap(shirt))():sm;
  a.add(loft([{y:.1,rx:.1,rz:.1},{y:0,rx:.145,rz:.145},{y:-.14,rx:.135,rz:.14},{y:-.26,rx:.115,rz:.12},{y:-.42,rx:.088,rz:.09}],10,cm));
  const fo=at(new THREE.Group(),0,-.42,0);a.add(fo);fo.add(loft([{y:0,rx:.088,rz:.09},{y:-.1,rx:.105,rz:.1},{y:-.28,rx:.075,rz:.07},{y:-.4,rx:.06,rz:.052}],10,sm));
  const hd=at(new THREE.Group(),0,-.42,0);fo.add(hd);hd.add(at(new THREE.Mesh(new THREE.BoxGeometry(.13,.14,.075),new THREE.MeshLambertMaterial({map:sm})),0,-.05,0));for(let f=0;f<4;f++)hd.add(at(new THREE.Mesh(new THREE.BoxGeometry(.024,.09,.03),new THREE.MeshLambertMaterial({map:sm})),-.05+f*.033,-.15,.005));hd.add(at(new THREE.Mesh(new THREE.BoxGeometry(.03,.08,.03),new THREE.MeshLambertMaterial({map:sm})),s*-.08,-.06,.02));
  p.arms.push({a,fo});
  const l=at(new THREE.Group(),s*.14,0,0);p.hip.add(l);l.add(loft([{y:.08,rx:.135,rz:.17},{y:-.1,rx:.16,rz:.175},{y:-.3,rx:.145,rz:.15},{y:-.47,rx:.125,rz:.13}],10,dm));
  const sh=at(new THREE.Group(),0,-.47,0);l.add(sh);sh.add(loft([{y:0,rx:.125,rz:.13},{y:-.2,rx:.125,rz:.135},{y:-.4,rx:.15,rz:.16}],10,dm));
  sh.add(at(box(.17,.1,.36,o.shoe||'#e8e2d6'),0,-.46,.07));p.legs.push({l,sh})}
 return p}
const K=person({skin:'#6e4228',shirt:'#e6e0d2',pant:'#3a4a68',hairp:1,stache:1});scene.add(K.g);
const B=person({skin:'#7a4c30',shirt:'#2b2b30',pant:'#1b1b1e',sleeve:1,shoe:'#111',bald:1});B.torso.scale.set(1.12,1.02,1.2);;scene.add(B.g);
const C=[];for(const[x,z,s]of[[-3.4,1.2,'#7e3a2a'],[-3.4,-6.2,'#3b6a4a']]){const c=chair.clone();at(c,x,0,z);shop.add(c);C.push(c)}
const blob=(r)=>{const m=new THREE.Mesh(new THREE.CircleGeometry(r,10),new THREE.MeshBasicMaterial({color:'#000',transparent:true,opacity:.34}));m.rotation.x=-Math.PI/2;m.position.y=.012;return m};
const ks=blob(.5),bs=blob(.5);scene.add(ks,bs);

/* the rigged lead: a loaded game body driven by the same pose joints the shots already use */
const RIG={ready:false,pairs:[],arm:new THREE.Quaternion()},RIG2={ready:false,pairs:[]};const b64=s=>{const b=atob(s),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);return u.buffer};const parse=s=>new Promise((ok,no)=>new window.GLTFLoader().parse(b64(s),'',ok,no));
const FL=new THREE.Group();FL.visible=false;scene.add(FL);
window.flexReady=new Promise(ok=>{if(!window.FLEX_GLB)return ok();const b=atob(window.FLEX_GLB),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);new window.GLTFLoader().parse(u.buffer,'',g=>{const m=g.scene;const bx=new THREE.Box3().setFromObject(m),c=bx.getCenter(new THREE.Vector3());m.position.sub(c);FL.add(m);m.traverse(o=>{if(o.isMesh){o.frustumCulled=false;if(o.material.color)o.material.color.setScalar(.8);o.material.roughness=.5}});ok()},()=>ok())});
window.ready=new Promise(ok=>{new window.GLTFLoader().parse(AD_GLB(),'',g=>{const root=g.scene;K.g.position.set(0,0,0);K.g.rotation.set(0,0,0);K.g.updateMatrixWorld(true);K.g.traverse(o=>{if(o.isMesh)o.visible=false});K.g.add(root);root.updateMatrixWorld(true);
 const bones={};root.traverse(o=>{if(o.isBone)bones[o.name]=o;if(o.isMesh){o.frustumCulled=false;o.material.side=THREE.DoubleSide;if(o.material.map){o.material.map.magFilter=THREE.LinearFilter;o.material.map.minFilter=THREE.LinearFilter}}});
 const wp=n=>bones[n].getWorldPosition(new THREE.Vector3());const tall=wp('Head').y-wp('LeftToeBase').y;const fit=1.72/tall;root.scale.multiplyScalar(fit);root.updateMatrixWorld(true);root.position.y-=wp('LeftToeBase').y;root.updateMatrixWorld(true);
 const lx=wp('LeftArm').x<0,side=i=>(i===0)===lx?'Left':'Right';
 const pair=(n,src,extra,conj)=>{const b=bones[n];RIG.pairs.push({b,src,rest:b.quaternion.clone(),w:b.getWorldQuaternion(new THREE.Quaternion()).premultiply(root.getWorldQuaternion(new THREE.Quaternion()).invert()),extra:extra||null,conj:conj||null})};
 pair('Spine',K.torso);pair('neck',K.neck);pair('Head',K.head);
 for(const i of[0,1]){const sg=i?-1:1,sd=side(i);pair(sd+'Arm',K.arms[i].a,new THREE.Euler(0,0,sg*.78));pair(sd+'ForeArm',K.arms[i].fo,null,new THREE.Euler(0,0,sg*.78));if(i===0){RIG.pairs[RIG.pairs.length-1].keep=1;RIG.pairs[RIG.pairs.length-2].keep=1}pair(sd+'UpLeg',K.legs[i].l);pair(sd+'Leg',K.legs[i].sh)}
 RIG.allB=Object.values(bones).map(b=>({b,q:b.quaternion.clone()}));
 const nb=bones['neck'];RIG.nb=nb;RIG.head=bones['Head'];bm.visible=false;dm.visible=false;
 /* find the skin of the neck and jaw on the model, by its rest position, and paint bumps into its texture */
 let skin=null;root.traverse(o=>{if(o.isSkinnedMesh)skin=o});root.updateMatrixWorld(true);
 const hb=bones['Head'].getWorldPosition(new THREE.Vector3()),nbp=nb.getWorldPosition(new THREE.Vector3());
 const uvA=skin.geometry.attributes.uv,V=new THREE.Vector3();RIG.uvs=[];
 for(let i=0;i<uvA.count;i++){skin.getVertexPosition(i,V);V.applyMatrix4(skin.matrixWorld);const up=V.y-nbp.y,span=hb.y-nbp.y;const dx=V.x-nbp.x,dz=V.z-(nbp.z+.02);
  if(up>.005&&up<span*1.0&&Math.hypot(dx,dz)<.14&&dz>-.03)RIG.uvs.push([uvA.getX(i),uvA.getY(i),up/span])}
 const im=skin.material.map.image,cv=document.createElement('canvas');cv.width=im.width;cv.height=im.height;RIG.ctx=cv.getContext('2d');RIG.base=im;RIG.tex=new THREE.CanvasTexture(cv);RIG.tex.flipY=false;RIG.tex.colorSpace=THREE.SRGBColorSpace;skin.material.map=RIG.tex;skin.material.needsUpdate=true;RIG.last=-1;
 seed=31;RIG.dots=[];for(let i=0;i<260;i++){const u=RIG.uvs[Math.floor(rnd()*RIG.uvs.length)];RIG.dots.push({x:(u[0]+(rnd()-.5)*.012)*cv.width,y:(u[1]+(rnd()-.5)*.012)*cv.height,r:(cv.width/1024)*(1.6+rnd()*2.6),k:rnd()})}
 paintBumps(0);
 addJaw(RIG,skin,bones,root);
 RIG.grip=bones[side(0)+'Hand'];RIG.B=bones;RIG.sL=side(1);RIG.sR=side(0);RIG.hips=bones['Hips'];RIG.hy=RIG.hips.position.y;RIG.fit=fit;RIG.root=root;RIG.ready=true;
 clipsFor(RIG,root);
 {const a=RIG.acts.scratch;if(a){a.play();const D=a.getClip().duration;let bestY=1e9,bestT=0,bone='LeftHand';for(let i=0;i<160;i++){a.time=D*i/160;RIG.mix.update(0);root.updateMatrixWorld(true);const nk=bones['neck'].getWorldPosition(new THREE.Vector3());for(const n of['LeftHand','RightHand']){const d=bones[n].getWorldPosition(new THREE.Vector3()).distanceTo(nk);if(d<bestY){bestY=d;bestT=a.time;bone=n}}}RIG.grip=bones[bone];RIG.upT=bestT;a.stop()}}
 Promise.all([window.DRE_GLB?parse(window.DRE_GLB):null]).then(([d])=>{if(d)rigDre(d);window.flexReady.then(ok)})},e=>{console.error('glb',e);ok()})});
function addJaw(rg,skin,bones,root){const V=new THREE.Vector3(),uvA=skin.geometry.attributes.uv,n=uvA.count,jaw=new Float32Array(n);root.updateMatrixWorld(true);const Hb=bones['Head'].getWorldPosition(new THREE.Vector3()),nbp=bones['neck'].getWorldPosition(new THREE.Vector3());let top=-1e9,chin=1e9;
 for(let i=0;i<n;i++){skin.getVertexPosition(i,V);V.applyMatrix4(skin.matrixWorld);if(V.y>Hb.y-.06&&V.y>top)top=V.y;if(Math.abs(V.x-Hb.x)<.03&&V.z>Hb.z&&V.y>nbp.y+.015&&V.y<Hb.y+.03&&V.y<chin)chin=V.y}
 const mouthY=top-.735*(top-chin);let ms=-1e9;
 for(let i=0;i<n;i++){skin.getVertexPosition(i,V);V.applyMatrix4(skin.matrixWorld);if(Math.abs(V.x-Hb.x)<.012&&Math.abs(V.y-mouthY)<.02&&V.z>ms)ms=V.z;const dx=Math.abs(V.x-Hb.x);if(V.z>Hb.z-.01&&V.y<mouthY&&V.y>chin-.035&&dx<.075){const a=Math.min(1,(mouthY-V.y)/.016),b=1-Math.pow(dx/.075,2);jaw[i]=a*b}}
 skin.geometry.setAttribute('aJaw',new THREE.BufferAttribute(jaw,1));
 let iT=0,iB=0,yT=-1e9,yB=1e9;for(let i=0;i<n;i++){skin.getVertexPosition(i,V);V.applyMatrix4(skin.matrixWorld);if(V.y>yT){yT=V.y;iT=i}if(V.y<yB){yB=V.y;iB=i}}
 const pa=skin.geometry.attributes.position,raw=new THREE.Vector3(pa.getX(iB)-pa.getX(iT),pa.getY(iB)-pa.getY(iT),pa.getZ(iB)-pa.getZ(iT));rg.uJaw={value:new THREE.Vector3()};rg.jawDir=raw.clone().multiplyScalar(1/(yT-yB));
 skin.material.onBeforeCompile=sh=>{sh.uniforms.uJaw=rg.uJaw;sh.vertexShader='attribute float aJaw;uniform vec3 uJaw;\n'+sh.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\n transformed+=uJaw*aJaw;')};skin.material.needsUpdate=true;
 const m=new THREE.Mesh(new THREE.SphereGeometry(1,10,6),new THREE.MeshBasicMaterial({color:'#160705'}));scene.add(m);m.position.set(Hb.x,mouthY+.017,ms-.012);bones['Head'].attach(m);rg.mouth=m;rg.mS=m.scale.x;m.scale.setScalar(rg.mS*.0001)}
function paintBumps(n,red,waves){if(!RIG.ctx)return;n=Math.round(n/4)*4;const key=n+(red?1000:0)+(waves?5000:0);if(key===RIG.bk)return;RIG.bk=key;const g=RIG.ctx,W=RIG.ctx.canvas.width;g.drawImage(RIG.base,0,0,W,RIG.ctx.canvas.height);
 const count=Math.min(RIG.dots.length,n*1.4|0);g.save();
 for(let i=0;i<count;i++){const d=RIG.dots[i];g.fillStyle=red?'rgba(120,36,24,.14)':'rgba(100,38,26,.1)';g.beginPath();g.arc(d.x,d.y,d.r*2.2,0,7);g.fill()}
 for(let i=0;i<count;i++){const d=RIG.dots[i];g.fillStyle=d.k>.55?'#2a1209':'#6a2a1c';g.beginPath();g.arc(d.x,d.y,d.r,0,7);g.fill();g.fillStyle='rgba(255,210,180,.5)';g.beginPath();g.arc(d.x-d.r*.3,d.y-d.r*.3,d.r*.32,0,7);g.fill()}
 if(waves&&RIG.waves){for(const d of RIG.waves){const k=Math.sin(d.r*170);g.fillStyle=k>0?'rgba(6,4,3,.95)':'rgba(70,56,48,.9)';g.beginPath();g.arc(d.x,d.y,W/170,0,7);g.fill()}}
 g.restore();RIG.tex.needsUpdate=true}
function open_(rg,o){rg.uJaw.value.copy(rg.jawDir).multiplyScalar(o*.03);const v=rg.mS;rg.mouth.visible=o>.04;rg.mouth.scale.set(v*.02,v*Math.max(.0002,o*.012),v*.006)}
function speak(t,b){if(!RIG.ready)return;open_(RIG,(AD.lips&&AD.lips[Math.floor(t*30)])||0);if(RIG2.ready)open_(RIG2,(AD.lipsB&&AD.lipsB[Math.floor(t*30)])||0)}
function rigDre(g){const root=g.scene;B2.g.position.set(0,0,0);B2.g.rotation.set(0,0,0);B2.g.updateMatrixWorld(true);B2.g.traverse(o=>{if(o.isMesh)o.visible=false});B2.g.add(root);root.updateMatrixWorld(true);const bones={};root.traverse(o=>{if(o.isBone)bones[o.name]=o;if(o.isMesh){o.frustumCulled=false;o.material.side=THREE.DoubleSide}});
 const wp=n=>bones[n].getWorldPosition(new THREE.Vector3()),fit=1.68/(wp('Head').y-wp('LeftToeBase').y);root.scale.multiplyScalar(fit);root.updateMatrixWorld(true);root.position.y-=wp('LeftToeBase').y;root.updateMatrixWorld(true);
 const lx=wp('LeftArm').x<0,side=i=>(i===0)===lx?'Left':'Right';const pair=(n,src,extra,conj)=>{const b=bones[n];RIG2.pairs.push({b,src,rest:b.quaternion.clone(),w:b.getWorldQuaternion(new THREE.Quaternion()).premultiply(root.getWorldQuaternion(new THREE.Quaternion()).invert()),extra:extra||null,conj:conj||null})};
 pair('Spine',B2.torso);pair('neck',B2.neck);pair('Head',B2.head);for(const i of[0,1]){const sg=i?-1:1,sd=side(i);pair(sd+'Arm',B2.arms[i].a,new THREE.Euler(0,0,sg*.78));pair(sd+'ForeArm',B2.arms[i].fo,null,new THREE.Euler(0,0,sg*.78));pair(sd+'UpLeg',B2.legs[i].l);pair(sd+'Leg',B2.legs[i].sh)}
 RIG2.allB=Object.values(bones).map(b=>({b,q:b.quaternion.clone()}));RIG2.B=bones;RIG2.sL=side(1);RIG2.sR=side(0);RIG2.root=root;clipsFor(RIG2,root);RIG2.grip=bones[side(1)+'Hand'];let skin;root.traverse(o=>{if(o.isSkinnedMesh)skin=o});addJaw(RIG2,skin,bones,root);RIG2.ready=true}
function AD_GLB(){const b=atob(window.TRE_GLB),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);return u.buffer}
const QA=new THREE.Quaternion(),QB=new THREE.Quaternion(),QC=new THREE.Quaternion();
const LOW=/Hips|UpLeg|Leg|Foot|ToeBase/;function layer(rg,n){const[a,b]=n.split('+'),k='L_'+n;if(rg.acts[k])return k;const all=window.CLIPS;const J=(name,keep)=>{const c=THREE.AnimationClip.parse(all[name]);c.tracks=c.tracks.filter(x=>keep(x.name.split('.')[0])&&(name==='sit'||!x.name.endsWith('.position')));return rg.mix.clipAction(c)};rg.acts[k]=[J(a,x=>LOW.test(x)),J(b,x=>!LOW.test(x))];return k}
function driveRig(){if(!RIG.ready)return;for(const rg of [RIG,RIG2]){if(!rg.ready)continue;const n0=rg===RIG?CLIP:CLIP2;const n=n0&&n0.includes('+')?layer(rg,n0):n0;if(Array.isArray(rg.acts&&rg.acts[n])){if(n!==rg.cur){if(rg.cur&&rg.acts[rg.cur]){[].concat(rg.acts[rg.cur]).forEach(a=>a.stop())}rg.acts[n].forEach(a=>{a.enabled=true;a.play()});rg.cur=n}rg.acts[n].forEach(a=>{a.time=(CLIP_T+(rg===RIG?0:3.3))%a.getClip().duration});rg.mix.update(0);continue}if(n!==rg.cur){if(rg.cur&&rg.acts[rg.cur]&&Array.isArray(rg.acts[rg.cur]))rg.acts[rg.cur].forEach(a=>a.stop());else if(rg.cur&&rg.acts[rg.cur])rg.acts[rg.cur].stop();if(!n)for(const b of rg.allB)b.b.quaternion.copy(b.q);if(n&&rg.acts[n]){rg.acts[n].enabled=true;rg.acts[n].play()}rg.cur=n;rg.last=-1}if(n&&rg.acts[n]){const a=rg.acts[n],tt=(n==='scratch'&&rg===RIG&&RIG.upT!=null)?RIG.upT+Math.sin(CLIP_T*5)*.1:CLIP_T%a.getClip().duration;if(tt!==rg.last){a.time=tt;rg.mix.update(0);rg.last=tt}}else drive1(rg,null)}}
let CLIP=null,CLIP2=null,CLIP_T=0;
function clipsFor(rg,root){rg.mix=new THREE.AnimationMixer(root);rg.acts={};const all=window.CLIPS||{};for(const k in all){const c=THREE.AnimationClip.parse(all[k]);if(k==='walk'||k==='idle'||k==='talk'||k==='passion'||k==='phone'||k==='scratch')c.tracks=c.tracks.filter(t=>!t.name.endsWith('.position'));rg.acts[k]=rg.mix.clipAction(c)}const hips=[];root.traverse(o=>{if(o.isBone&&o.name==='Hips')hips.push({b:o,p:o.position.clone()})});rg.hips=hips}
function drive1(rg,n){if(n)return;for(const p of rg.pairs){QA.setFromEuler(p.src.rotation);if(p.extra){QB.setFromEuler(p.extra);QA.multiply(QB)}if(p.conj){QC.setFromEuler(p.conj);QB.copy(QC).invert();QA.premultiply(QB).multiply(QC)}QB.copy(p.w).invert().multiply(QA).multiply(p.w);p.b.quaternion.copy(p.rest).multiply(QB)}}
/* bumps: grow out of the neck and jaw */
const MAXB=170,bg=new THREE.IcosahedronGeometry(.022,1);
const bm=new THREE.InstancedMesh(bg,new THREE.MeshLambertMaterial({color:'#6e3324',flatShading:true}),MAXB);
const dg=new THREE.CircleGeometry(.014,6),dm=new THREE.InstancedMesh(dg,new THREE.MeshBasicMaterial({color:'#2a160e'}),60);
K.neck.add(bm,dm);
const spots=[],marks=[];seed=11;
for(let i=0;i<MAXB;i++){const ang=-1.9+rnd()*3.8,h=rnd(),jaw=rnd()<.28;spots.push({ang,y:jaw?.22+rnd()*.04:.0+h*.24,r:jaw?.125:.128,s:.7+rnd()*1.3})}
for(let i=0;i<60;i++)marks.push({ang:-1.8+rnd()*3.6,y:.0+rnd()*.25});
const M=new THREE.Matrix4(),Q=new THREE.Quaternion(),P=new THREE.Vector3(),S3=new THREE.Vector3(),Eu=new THREE.Euler();
function setBumps(n,pop){n=Math.min(MAXB,Math.round(n));for(let i=0;i<MAXB;i++){const s=spots[i];
  const on=i<n?s.s*(i>n-14?pop:1):0.0001;P.set(Math.sin(s.ang)*s.r,s.y,Math.cos(s.ang)*s.r);Eu.set(0,s.ang,0);Q.setFromEuler(Eu);S3.set(on,on,on*.7);M.compose(P,Q,S3);bm.setMatrixAt(i,M)}bm.instanceMatrix.needsUpdate=true;
 const nm=Math.min(60,n*.45)|0;for(let i=0;i<60;i++){const s=marks[i],k=i<nm?1:.0001;P.set(Math.sin(s.ang)*.127,s.y,Math.cos(s.ang)*.127);Eu.set(0,s.ang,0);Q.setFromEuler(Eu);S3.set(k,k,k);M.compose(P,Q,S3);dm.setMatrixAt(i,M)}dm.instanceMatrix.needsUpdate=true}

/* the room: wallpaper, wood trim, a sunset window, a patterned sofa */
const room=new THREE.Group();room.visible=false;scene.add(room);
{const paper=soft(0,256,256,(g,w,h)=>{g.fillStyle='#8f6f4a';g.fillRect(0,0,w,h);for(let y=0;y<h;y+=32)for(let x=(y/32%2)*16;x<w;x+=32){g.fillStyle='rgba(60,30,14,.32)';g.beginPath();g.ellipse(x+8,y+12,5,9,0,0,7);g.fill();g.fillRect(x+7,y+18,2,10)}for(let x=0;x<w;x+=16){g.fillStyle='rgba(40,20,8,.08)';g.fillRect(x,0,3,h)}for(let i=0;i<300;i++){g.fillStyle='rgba(30,15,6,.05)';g.fillRect(Math.random()*w,Math.random()*h,5,3)}});paper.wrapS=paper.wrapT=THREE.RepeatWrapping;paper.repeat.set(5,2);
 const w=new THREE.MeshLambertMaterial({map:paper});const b=new THREE.Mesh(new THREE.PlaneGeometry(14,5),w);at(b,0,2.4,-3);room.add(b);const l=new THREE.Mesh(new THREE.PlaneGeometry(10,5),w);l.rotation.y=Math.PI/2;at(l,-6,2.4,0);room.add(l);
 room.add(at(box(14,.5,.1,'#3a2414'),0,.25,-2.94),at(box(14,.12,.1,'#3a2414'),0,3.5,-2.94));
 const glow=new THREE.Mesh(new THREE.PlaneGeometry(1.6,1.7),new THREE.MeshBasicMaterial({map:soft(0,64,64,(g,w,h)=>{const q=g.createLinearGradient(0,0,0,h);q.addColorStop(0,'#ffcf86');q.addColorStop(.7,'#f08a3c');q.addColorStop(1,'#7a3a20');g.fillStyle=q;g.fillRect(0,0,w,h);g.fillStyle='#2a1a10';g.fillRect(w/2-1,0,2,h);g.fillRect(0,h/2-1,w,2)}),fog:false}));at(glow,3,2.5,-2.92);room.add(glow);room.add(at(box(1.8,.1,.1,'#3a2414'),3,3.4,-2.9),at(box(1.8,.1,.1,'#3a2414'),3,1.6,-2.9));
 for(const[x,y,c]of[[-3.3,2.7,'#6a5a4a'],[-1.9,2.5,'#4a5a6a'],[.4,2.8,'#7a4a3a']]){room.add(at(box(.8,1,.05,'#20140c'),x,y,-2.93),at(box(.62,.82,.02,c),x,y,-2.9))}
 const fl=new THREE.Mesh(new THREE.PlaneGeometry(14,10),new THREE.MeshLambertMaterial({map:(()=>{const t=soft(0,128,128,(g,w,h)=>{g.fillStyle='#5a3e28';g.fillRect(0,0,w,h);for(let i=0;i<2500;i++){g.fillStyle=Math.random()>.5?'rgba(255,220,180,.05)':'rgba(0,0,0,.1)';g.fillRect(Math.random()*w,Math.random()*h,2,2)}});t.wrapS=t.wrapT=THREE.RepeatWrapping;t.repeat.set(6,4);return t})()}));fl.rotation.x=-Math.PI/2;room.add(fl);
 const sofa=new THREE.MeshLambertMaterial({map:(()=>{const t=soft(0,128,128,(g,w,h)=>{g.fillStyle='#5c3a2a';g.fillRect(0,0,w,h);for(let y=0;y<h;y+=16)for(let x=(y/16%2)*8;x<w;x+=16){g.fillStyle='#3e2418';g.beginPath();g.arc(x,y,4,0,7);g.fill()}for(let i=0;i<500;i++){g.fillStyle='rgba(0,0,0,.08)';g.fillRect(Math.random()*w,Math.random()*h,2,2)}});t.wrapS=t.wrapT=THREE.RepeatWrapping;t.repeat.set(3,1);return t})()});
 const bx=(w_,h_,d,x,y,z)=>{const m=new THREE.Mesh(new THREE.BoxGeometry(w_,h_,d),sofa);at(m,x,y,z);room.add(m)};bx(5.4,.8,1.3,0,.4,-1.9);bx(5.4,1.1,.4,0,1.15,-2.5);bx(.5,.9,1.3,-2.7,.65,-1.9);bx(.5,.9,1.3,2.7,.65,-1.9);
 room.add(at(cyl(.3,.22,.6,8,'#3b2a1c'),3.6,.3,-2.4));seed=23;for(let i=0;i<9;i++){const p=at(box(.1,1,.34,'#37552f'),3.6,1,-2.4);p.rotation.set(rnd()*.9-.45,i,rnd()*.9-.45);room.add(p)}
 const lamp=new THREE.PointLight('#ffb060',14,9);at(lamp,3,2.4,-1.6);room.add(lamp)}
const B2=person({skin:'#3e2519',shirt:'#3c5a3a',pant:'#26262b',hairp:1,stache:1,sleeve:1,shoe:'#eee'});scene.add(B2.g);B2.g.visible=false;
const phone=at(box(.1,.2,.012,'#111'),0,0,0);phone.visible=false;scene.add(phone);
const roadT=soft(0,128,128,(g,w,h)=>{g.fillStyle='#4b4640';g.fillRect(0,0,w,h);for(let i=0;i<2600;i++){g.fillStyle=Math.random()>.5?'rgba(255,240,220,.05)':'rgba(0,0,0,.12)';g.fillRect(Math.random()*w,Math.random()*h,2,2)}});roadT.wrapS=roadT.wrapT=THREE.RepeatWrapping;roadT.repeat.set(16,30);
/* the store: shelves far too tall, a pile of failed fixes behind him */
const aisle=new THREE.Group();aisle.visible=false;scene.add(aisle);const pile=[];
{const cols=['#9a4a38','#4a6a82','#a88a4a','#c9c2b0','#5e7a5a','#6a5a7a'];
 const sh=soft(0,128,256,(g,w,h)=>{g.fillStyle='#d8d3c6';g.fillRect(0,0,w,h);for(let y=0;y<h;y+=24){g.fillStyle='#6d6759';g.fillRect(0,y+21,w,3);for(let x=0;x<w;x+=11){g.fillStyle=cols[Math.floor(Math.random()*6)];g.fillRect(x+1,y+3+Math.random()*4,9,18)}}});sh.wrapS=sh.wrapT=THREE.RepeatWrapping;sh.repeat.set(2,6);
 for(const x of[-1,1])for(let z=30;z>-90;z-=16)aisle.add(at(new THREE.Mesh(new THREE.BoxGeometry(4,90,15),new THREE.MeshLambertMaterial({map:sh})),x*9,45,z));
 const fl=new THREE.Mesh(new THREE.PlaneGeometry(40,160),new THREE.MeshLambertMaterial({map:roadT}));fl.rotation.x=-Math.PI/2;at(fl,0,0,-30);aisle.add(fl);
 for(let z=30;z>-90;z-=7)aisle.add(at(box(.2,.02,3,'#d8c070'),0,.02,z));
 for(let i=0;i<40;i++){const p=at(box(.3+rnd()*.3,.3+rnd()*.4,.3+rnd()*.3,cols[i%6]),(rnd()>.5?1:-1)*(1.5+rnd()*.9),.2+Math.pow(rnd(),2)*2,2.6+rnd()*1.6);p.rotation.y=rnd()*3;p.visible=false;aisle.add(p);pile.push(p)}}
const city=new THREE.Group();city.visible=false;scene.add(city);
{const sky=new THREE.Mesh(new THREE.PlaneGeometry(90,36),new THREE.MeshBasicMaterial({map:soft(0,64,128,(g,w,h)=>{const q=g.createLinearGradient(0,0,0,h);q.addColorStop(0,'#5a4a7a');q.addColorStop(.42,'#e0784a');q.addColorStop(.72,'#ffc677');q.addColorStop(1,'#e8a765');g.fillStyle=q;g.fillRect(0,0,w,h)}),fog:false}));at(sky,0,14,-44);city.add(sky);
 const rd=soft(0,128,128,(g,w,h)=>{g.fillStyle='#4b4640';g.fillRect(0,0,w,h);for(let i=0;i<2600;i++){g.fillStyle=Math.random()>.5?'rgba(255,240,220,.05)':'rgba(0,0,0,.12)';g.fillRect(Math.random()*w,Math.random()*h,2,2)}});rd.wrapS=rd.wrapT=THREE.RepeatWrapping;rd.repeat.set(6,12);const road=new THREE.Mesh(new THREE.PlaneGeometry(50,90),new THREE.MeshLambertMaterial({map:rd}));road.rotation.x=-Math.PI/2;at(road,0,0,-20);city.add(road);
 for(const q of[-1,1]){city.add(at(box(3,.14,90,'#a79a84'),q*5.5,.07,-20));for(let i=0;i<7;i++){const z=4-i*7.5,x=q*(11+(i%2));const c=['#b98a5e','#8f9f8a','#c3a98a','#9a6a55'][(i+(q>0?1:0))&3];const wt=soft(0,64,64,(g,w,h)=>{g.fillStyle=c;g.fillRect(0,0,w,h);for(let k=0;k<200;k++){g.fillStyle='rgba(0,0,0,.05)';g.fillRect(Math.random()*w,Math.random()*h,3,2)}g.fillStyle='#2a2a30';g.fillRect(8,20,16,18);g.fillRect(40,20,16,18);g.fillStyle='#3a2414';g.fillRect(26,34,12,30)});const h=new THREE.Mesh(new THREE.BoxGeometry(7,3.6,6),new THREE.MeshLambertMaterial({map:wt}));at(h,x,1.8,z);city.add(h);const rf=new THREE.Mesh(new THREE.ConeGeometry(5.4,1.5,4),mat('#5a3a30'));rf.rotation.y=Math.PI/4;rf.scale.z=.85;at(rf,x,4.3,z);city.add(rf);
   if(i%2===0){const tx=q*7.3;city.add(at(cyl(.09,.16,8,6,'#5a4632'),tx,4,z));for(let f=0;f<9;f++){const l=at(box(.2,.05,2.6,'#3e5a32'),tx,8,z);l.geometry.translate(0,0,1.3);l.rotation.y=f*.7;l.rotation.x=.5;city.add(l)}}}
  for(let i=0;i<6;i++){const y=at(box(.5,.5,.5,'#333'),0,0,0);y.visible=false}}
 const pw=[];for(let i=0;i<5;i++)city.add(at(cyl(.07,.09,6.5,6,'#3a2c20'),-4.3,3.25,-6-i*9))}
const skyDome=new THREE.Mesh(new THREE.SphereGeometry(200,16,12),new THREE.MeshBasicMaterial({map:soft(0,8,256,(g,w,h)=>{const q=g.createLinearGradient(0,0,0,h);q.addColorStop(0,'#3a2a5a');q.addColorStop(.45,'#d9683e');q.addColorStop(.62,'#ffc677');q.addColorStop(1,'#e8a765');g.fillStyle=q;g.fillRect(0,0,w,h)}),side:THREE.BackSide,fog:false}));skyDome.visible=false;scene.add(skyDome);
/* the giant skin: he walks on it, the hair curls back under it, the razor flies over it */
const skinW=new THREE.Group();skinW.visible=false;scene.add(skinW);
{const st=soft(0,256,256,(g,w,h)=>{g.fillStyle='#6a3f27';g.fillRect(0,0,w,h);for(let i=0;i<5000;i++){g.fillStyle=Math.random()>.5?'rgba(255,200,160,.05)':'rgba(30,10,4,.14)';g.fillRect(Math.random()*w,Math.random()*h,3,2)}for(let i=0;i<200;i++){g.fillStyle='rgba(20,8,4,.45)';g.beginPath();g.arc(Math.random()*w,Math.random()*h,1.8,0,7);g.fill()}});st.wrapS=st.wrapT=THREE.RepeatWrapping;st.repeat.set(10,10);
 const gr=new THREE.Mesh(new THREE.PlaneGeometry(200,200),new THREE.MeshLambertMaterial({map:st}));gr.rotation.x=-Math.PI/2;skinW.add(gr);
 const hm=new THREE.MeshLambertMaterial({color:'#0e0907'});const mk=(pts,r)=>new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts.map(p=>new THREE.Vector3(...p))),24,r,8),hm);
 skinW.add(mk([[-6,-3,-14],[-5.5,4,-14],[-3,10,-14],[2,11,-14],[6,6,-14],[7,0,-14],[6,-3,-14]],.5));
 skinW.add(mk([[-18,-3,-26],[-17,5,-26],[-14,9,-26],[-10,8,-26],[-8,0,-26],[-8,-3,-26]],.42),mk([[13,-3,-24],[13,4,-24],[16,8,-24],[20,6,-24],[21,0,-24],[20,-3,-24]],.42));
 for(const[x,z,r]of[[6.6,-14,3.4],[-8.2,-26,2.8],[20.5,-24,2.8],[-11,-9,2],[10,-7,1.6]]){const m=new THREE.Mesh(new THREE.SphereGeometry(r,14,10,0,Math.PI*2,0,Math.PI/2),new THREE.MeshLambertMaterial({color:'#7a3a26'}));m.scale.y=.55;at(m,x,0,z);skinW.add(m)}
 window.bigRazor=new THREE.Group();const bz=window.bigRazor;bz.add(at(box(22,.5,3,'#dfe5e8'),0,0,0),at(box(3,1.4,2.2,'#26262b'),0,1,0),at(box(2,14,2,'#2d5fa8'),0,8,0));at(bz,0,14,-14);skinW.add(bz)}
/* the bathroom: tile, a shower head, running water */
const bath=new THREE.Group();bath.visible=false;scene.add(bath);const drops=[];
{const tl=soft(0,128,128,(g,w,h)=>{for(let y=0;y<h;y+=32)for(let x=0;x<w;x+=32){g.fillStyle=(x+y)%64?'#6f8f94':'#7f9ea2';g.fillRect(x,y,32,32);g.fillStyle='#3e4e50';g.fillRect(x,y,32,2);g.fillRect(x,y,2,32);g.fillStyle='rgba(255,255,255,.08)';g.fillRect(x+6,y+6,10,3)}});tl.wrapS=tl.wrapT=THREE.RepeatWrapping;tl.repeat.set(3,2);
 const w=new THREE.MeshLambertMaterial({map:tl,side:THREE.DoubleSide});const pl=(a,b,x,y,z,ry)=>{const m=new THREE.Mesh(new THREE.PlaneGeometry(a,b),w);at(m,x,y,z);m.rotation.y=ry;bath.add(m)};pl(6,4,0,2,-1.6,0);pl(5,4,-3,2,.8,Math.PI/2);pl(5,4,3,2,.8,Math.PI/2);
 const f=new THREE.Mesh(new THREE.PlaneGeometry(6,6),new THREE.MeshLambertMaterial({color:'#3e4e50'}));f.rotation.x=-Math.PI/2;at(f,0,.02,.8);bath.add(f);
 bath.add(at(box(.1,.1,1,'#cfd5d8'),.1,3.2,-1.1),at(new THREE.Mesh(new THREE.CylinderGeometry(.22,.1,.14,10),mat('#cfd5d8')),.1,3.14,-.6));
 const dg=new THREE.BoxGeometry(.012,.22,.012),dm_=new THREE.MeshBasicMaterial({color:'#d8eef2',transparent:true,opacity:.55});for(let i=0;i<90;i++){const d=new THREE.Mesh(dg,dm_);bath.add(d);drops.push({m:d,x:.1+Math.sin(i*2.4)*.55,z:-.6+Math.cos(i*5.1)*.55,p:i*.137})}
 const lb=new THREE.PointLight('#ffd9a0',10,9);at(lb,1.5,3.4,1.5);bath.add(lb)}
const beam=new THREE.Mesh(new THREE.CylinderGeometry(5,5,130,14,1,true),new THREE.MeshBasicMaterial({color:'#7dffa8',transparent:true,opacity:.13,side:THREE.DoubleSide,depthWrite:false,fog:false}));beam.visible=false;scene.add(beam);
const RN=60,rM=new THREE.InstancedMesh(new THREE.BoxGeometry(1.2,.12,.26),mat('#dfe5e8'),RN),rH=new THREE.InstancedMesh(new THREE.BoxGeometry(.18,1.5,.18),mat('#2d5fa8'),RN);rM.frustumCulled=rH.frustumCulled=false;scene.add(rM,rH);
function rainAt(t,b){rM.visible=rH.visible=!!b.rain;if(!b.rain)return;const M=new THREE.Matrix4(),Q_=new THREE.Quaternion(),E_=new THREE.Euler(),S_=new THREE.Vector3(),P_=new THREE.Vector3();const z0=K.g.position.z;for(let i=0;i<RN;i++){const per=1.6+(i%7)*.22,k=((t+i*.37)%per)/per,x=Math.sin(i*12.9)*(AD.skit?24:11),z=AD.skit?20+((i*7.3)%30):z0-3-((i*7.3)%30);const y=64*(1-k*k);E_.set(t*5+i,t*3+i,0);Q_.setFromEuler(E_);const s=1.2+(i%4)*.5;S_.set(s,s,s);P_.set(x,y,z);M.compose(P_,Q_,S_);rM.setMatrixAt(i,M);P_.y-=.7*s;M.compose(P_,Q_,S_);rH.setMatrixAt(i,M)}rM.instanceMatrix.needsUpdate=true;rH.instanceMatrix.needsUpdate=true}
/* the fixes he bought: each a small object carried at his hand */
const props={};{const P_=(n,f)=>{const g=new THREE.Group();f(g);g.visible=false;scene.add(g);props[n]=g};
 const steel='#cfd5d8',blk='#17171a',blu='#2d5fa8',red='#b0322a';
 const handle=(g,c)=>g.add(at(cyl(.016,.02,.3,8,c),0,.17,0));
 P_('five',g=>{handle(g,blu);g.add(at(box(.15,.05,.03,'#26262b'),0,.34,0));for(let i=0;i<5;i++)g.add(at(box(.14,.005,.034,steel),0,.324+i*.008,0))});
 P_('single',g=>{handle(g,steel);g.add(at(box(.13,.018,.05,steel),0,.33,0));g.add(at(box(.14,.006,.06,'#eef1f2'),0,.34,0))});
 P_('rotary',g=>{g.add(at(cyl(.042,.05,.2,10,blk),0,.1,0));for(const[x,z]of[[-.04,-.02],[.04,-.02],[0,.04]])g.add(at(cyl(.03,.03,.02,10,steel),x,.225,z))});
 P_('foil',g=>{g.add(at(box(.09,.2,.05,blk),0,.1,0));g.add(at(box(.1,.04,.05,steel),0,.23,0))});
 P_('clippers',g=>{g.add(at(box(.08,.22,.06,'#3a3a40'),0,.11,0));g.add(at(box(.09,.03,.03,steel),0,.235,0));for(let i=0;i<7;i++)g.add(at(box(.006,.02,.03,'#eef1f2'),-.036+i*.012,.258,0))});
 P_('scissors',g=>{for(const q of[-1,1]){const b=at(box(.016,.17,.008,steel),q*.012,.17,0);b.rotation.z=q*.18;g.add(b);const r=new THREE.Mesh(new THREE.TorusGeometry(.03,.008,6,12),mat(red));at(r,q*.04,.04,0);g.add(r)}});
 P_('cream',g=>{const c=at(cyl(.042,.028,.2,10,'#e8e2d6'),0,.11,0);g.add(c);g.add(at(cyl(.016,.016,.04,8,'#b0322a'),0,.23,0));g.add(at(box(.07,.08,.002,'#b0322a'),0,.11,.043))})}
/* a razor in his hand, for a beat that shows the swipe itself */
const razor=new THREE.Group();razor.add(at(box(.34,.05,.05,'#dfe5e8'),0,0,0),at(box(.05,.5,.05,'#2d2d33'),0,.27,0));razor.visible=false;scene.add(razor);
/* the skin cross-section: hair curling back under, as chunky props */
const cross=new THREE.Group();cross.visible=false;scene.add(cross);
cross.add(new THREE.Mesh(new THREE.BoxGeometry(7,.24,3),new THREE.MeshLambertMaterial({map:ribTex('#6a3f27',20)})),at(new THREE.Mesh(new THREE.BoxGeometry(7,1.9,3),new THREE.MeshLambertMaterial({map:ribTex('#8f4638',40)})),0,-1.07,0),at(new THREE.Mesh(new THREE.BoxGeometry(7,.8,3),new THREE.MeshLambertMaterial({map:ribTex('#b89466',30)})),0,-2.4,0));
const hairMat=mat('#120c08');const hp=[];for(let i=0;i<9;i++){const a=-.3+i*.62;hp.push(new THREE.Vector3(1.6*Math.cos(a)-.4,-.9-.7*Math.sin(a)+(.08*i),0))}
const hairCurve=new THREE.CatmullRomCurve3([new THREE.Vector3(-1.5,-1.75,1.52),new THREE.Vector3(-1.3,-.7,1.52),new THREE.Vector3(-.95,.34,1.52),new THREE.Vector3(-.3,.5,1.52),new THREE.Vector3(.35,.1,1.52),new THREE.Vector3(.75,-.7,1.52),new THREE.Vector3(.5,-1.25,1.52)]);
const hairTube=new THREE.Mesh(new THREE.TubeGeometry(hairCurve,18,.09,5),hairMat);cross.add(hairTube);
const bl=new THREE.Group();cross.add(bl);bl.add(at(box(2.4,.09,.5,'#dfe5e8'),0,.74,1.52),at(box(.4,1.1,.3,'#8a97a8'),.2,1.3,1.52));

const rings=[];for(let i=0;i<3;i++){const r=new THREE.Mesh(new THREE.TorusGeometry(.9,.05,6,18),new THREE.MeshBasicMaterial({color:'#7dffa8',transparent:true}));r.rotation.x=Math.PI/2;r.visible=false;cross.add(r);rings.push(r)}
/* the real product: its real photo, never a drawn one */
const loader=new THREE.TextureLoader();
function photo(src,w){const t=loader.load(src);t.colorSpace=THREE.SRGBColorSpace;t.magFilter=THREE.LinearFilter;const m=new THREE.Mesh(new THREE.PlaneGeometry(w,.825),new THREE.MeshBasicMaterial({map:t,transparent:true,alphaTest:.04,side:THREE.DoubleSide,fog:false}));m.visible=false;scene.add(m);return m}
const TURN=AD.product_turn.map(x=>photo(x.src,.66*x.w)),FX=TURN[0];
const halo=new THREE.Mesh(new THREE.CylinderGeometry(.34,.34,4,10,1,true),new THREE.MeshBasicMaterial({color:'#7dffa8',transparent:true,opacity:.1,side:THREE.DoubleSide,depthWrite:false}));halo.visible=false;scene.add(halo);

const clamp=(x,a=0,b=1)=>Math.min(b,Math.max(a,x));const ease=x=>x*x*(3-2*x);const lerp=(a,b,k)=>a+(b-a)*k;
function idle(p,t,o=0){p.torso.rotation.z=Math.sin(t*2.1+o)*.012;p.head.rotation.y=Math.sin(t*.9+o)*.08;for(const[i,x]of p.arms.entries()){x.a.rotation.set(0,0,(i?-1:1)*.09);x.fo.rotation.x=-.08}for(const x of p.legs){x.l.rotation.x=0;x.sh.rotation.x=0}p.hip.position.y=.98;p.hip.rotation.x=0;p.torso.rotation.x=0}
function walk(p,t,sp=8){idle(p,t);const w=Math.sin(t*sp);p.legs[0].l.rotation.x=w*.62;p.legs[1].l.rotation.x=-w*.62;p.legs[0].sh.rotation.x=Math.max(0,-w)*.9;p.legs[1].sh.rotation.x=Math.max(0,w)*.9;p.arms[0].a.rotation.x=-w*.55;p.arms[1].a.rotation.x=w*.55;p.arms[0].fo.rotation.x=-.18;p.arms[1].fo.rotation.x=-.18;p.hip.position.y=.98+Math.abs(Math.cos(t*sp))*.045}
function sit(p,t){idle(p,t);p.hip.position.y=.98;p.legs.forEach(x=>{x.l.rotation.x=-1.42;x.sh.rotation.x=1.42});p.arms.forEach(x=>{x.a.rotation.x=-.5;x.fo.rotation.x=-.7})}
function sitK(){K.g.position.set(-3.4,.04,-2.4);K.g.rotation.y=Math.PI/2}
function chop(p,t){p.arms[1].a.rotation.x=-1.2+Math.sin(t*16)*.28;p.arms[1].fo.rotation.x=-.9;p.arms[0].a.rotation.x=-.6;p.arms[0].fo.rotation.x=-.7}
function setCam(x,y,z,lx,ly,lz,sh=0,t=0){cam.position.set(x+Math.sin(t*23)*sh,y+Math.cos(t*19)*sh,z);cam.lookAt(lx,ly,lz)}
function handAt(b){if(!RIG.ready)return null;driveRig();scene.updateMatrixWorld(true);const v=new THREE.Vector3();RIG.grip.getWorldPosition(v);return v}
function neckTarget(){if(RIG.ready){driveRig();scene.updateMatrixWorld(true);const v=new THREE.Vector3();RIG.nb.getWorldPosition(v);v.y+=.04;return v}const v=new THREE.Vector3(0,.2,0);K.neck.localToWorld(v);return v}

/* scenes: each sets the world for t inside its beat */
const SC={
 walk(u,t,b){shop.visible=true;const z=lerp(9.4,-.4,clamp(u*1.05)),x=lerp(-1.8,-1.3,u);K.g.position.set(x,0,z);K.g.rotation.y=Math.PI;K.g.rotation.x=0;walk(K,t);
  door.rotation.y=-ease(clamp(u*5))*1.6;B.g.position.set(-2.1,0,-3.6);B.g.rotation.y=.4;idle(B,t);
  setCam(x+.4,2.1,z+3.2,x,1.5,z-.8,.006,t)},
 neck(u,t,b){sitK();sit(K,t);K.head.rotation.x=-.24;K.head.rotation.y=.05+Math.sin(t*1.2)*.07;K.neck.rotation.x=-.04;
  B.g.position.set(-3.4,0,-.9);B.g.rotation.y=Math.PI;idle(B,t);chop(B,t);
  K.g.updateMatrixWorld(true);const n=neckTarget(),d=lerp(2.1,1.55,ease(clamp(u*1.6)));
  setCam(n.x+d*.95,n.y-.1,n.z+d*.42,n.x,n.y+.08,n.z,.003,t)},
 chair(u,t,b){sitK();sit(K,t);K.head.rotation.y=.35+Math.sin(t)*.1;B.g.position.set(-3.5,0,-1.1);B.g.rotation.y=Math.PI;idle(B,t);chop(B,t);
  K.g.updateMatrixWorld(true);setCam(lerp(-.2,-.7,u),2.1,lerp(-.8,-1.2,u),-3.3,1.75,-2.1,.004,t)},
 talk(u,t,b){sitK();sit(K,t);B.g.position.set(-2.5,0,-1.3);B.g.rotation.y=1.05+Math.sin(t*5)*.05;idle(B,t);B.head.rotation.y=Math.sin(t*9)*.16;B.head.rotation.x=Math.sin(t*14)*.07;B.mouth.scale.y=1+Math.abs(Math.sin(t*17))*5;B.arms[0].a.rotation.x=-1+Math.sin(t*7)*.3;
  B.g.updateMatrixWorld(true);setCam(lerp(.6,.35,u),2.15,lerp(.5,.3,u),-2.9,1.75,-1.75,.003,t)},
 cross(u,t,b){shop.visible=false;skinW.visible=true;skyDome.visible=true;B.g.visible=false;scene.fog.near=30;scene.fog.far=120;scene.fog.color.set('#d98a4a');K.g.position.set(0,0,lerp(1,-1.6,u));K.g.rotation.y=Math.PI;CLIP='walk';window.bigRazor.position.x=Math.sin(t*1.6)*16;setCam(1.6,1.1,K.g.position.z+7.5,.6,3,-14,.006,t)},
 pickup(u,t,b){sitK();sit(K,t);K.head.rotation.y=-.2;B.g.position.set(-2.9,0,-1.2);B.g.rotation.y=-1.2;idle(B,t);
  const p=new THREE.Vector3(-1.8,1.7+Math.sin(t*3)*.07,-1.7);FL.visible=true;FL.position.copy(p);FL.rotation.set(.15,t*2.4,0);FL.scale.setScalar(lerp(.5,6,ease(clamp(u*5))));
  halo.visible=true;halo.position.set(-1.8,3,-1.7);setCam(.2,1.9,lerp(-.1,-.6,u),-2,1.7,-1.75,.002,t)},
 use(u,t,b){sitK();sit(K,t);K.head.rotation.x=-.24;K.head.rotation.y=.05;K.neck.rotation.x=-.04;B.g.position.set(-5.2,0,-1);B.g.rotation.y=1;idle(B,t);
  K.g.updateMatrixWorld(true);const n=neckTarget();setCam(n.x+1.3,n.y+.02,n.z+.68,n.x,n.y+.02,n.z,.002,t);
  const a=FX;a.visible=true;a.scale.setScalar(.5);a.position.set(n.x+.14+Math.sin(t*5)*.03+Math.sin(t*71)*.004,n.y+.02+Math.cos(t*3)*.06,n.z+.13);a.lookAt(cam.position);
  K.arms[0].a.rotation.x=-2.1;K.arms[0].fo.rotation.x=-1.7},
 clock(u,t,b){sitK();sit(K,t);const k=Math.sin(u*Math.PI*8)*.5+.5;scene.background.set('#c9b48a').lerp(new THREE.Color('#141b3a'),k);sky.material.color.set('#e8b873').lerp(new THREE.Color('#10183a'),k);hemi.intensity=lerp(1.15,.45,k);B.g.position.set(-3.5+Math.sin(t*9)*.9,0,-1.2+Math.cos(t*7)*.5);B.g.rotation.y=t*6;walk(B,t,14);K.head.rotation.y=Math.sin(t*6)*.6;
  K.g.updateMatrixWorld(true);setCam(-.6,2.1,-1,-3.3,1.75,-2.1,.004,t)},
 reveal(u,t,b){sitK();sit(K,t);K.head.rotation.x=-.24;K.head.rotation.y=.05+Math.sin(t*1.8)*.12;K.neck.rotation.x=-.04;B.g.position.set(-2.7,0,-.8);B.g.rotation.y=-.7+Math.sin(t*4)*.04;idle(B,t);B.head.rotation.x=.1;
  K.g.updateMatrixWorld(true);const n=neckTarget(),d=lerp(1.55,2.2,ease(u));setCam(n.x+d*.95,n.y-.1,n.z+d*.42,n.x,n.y+.08,n.z,.002,t)},
 selfie(u,t,b){shop.visible=false;room.visible=true;scene.background.set('#6b4a2a');scene.fog.near=4;scene.fog.far=14;scene.fog.color.set('#a8743f');hemi.intensity=.7;B.g.visible=false;
  const sat=b.seat;K.g.position.set(-.55,sat?.42:0,sat?-1.75:-.6);K.g.rotation.y=sat?.18:.32;B2.g.visible=true;B2.g.position.set(.75,sat?.42:0,sat?-1.75:-.9);B2.g.rotation.y=sat?-.18:-.42;
  K.g.updateMatrixWorld(true);B2.g.updateMatrixWorld(true);const hx=neckTarget();setCam(.1+Math.sin(t*3.1)*.03,sat?1.25:1.45+Math.sin(t*4.3)*.02,sat?2.4:3.1,.1,sat?1.05:1.1,-1,.004,t)},
 street(u,t,b){shop.visible=false;city.visible=true;skyDome.visible=true;B.g.visible=false;scene.fog.near=9;scene.fog.far=70;scene.fog.color.set('#d98a4a');sun.intensity=3.4;
  const z=lerp(-3,1.2,u);K.g.position.set(0,0,z);K.g.rotation.y=0;CLIP='walk';
  K.g.updateMatrixWorld(true);setCam(1.1-u*.3,.5,z+3.6-u*.5,.15,1.35,z,.006,t)},
 store(u,t,b){shop.visible=false;aisle.visible=true;skyDome.visible=true;B.g.visible=false;scene.fog.near=14;scene.fog.far=70;scene.fog.color.set('#d98a4a');K.g.position.set(0,0,lerp(1.6,-1.2,u));K.g.rotation.y=Math.PI;CLIP='walk';setCam(.7,1.0,K.g.position.z+3.9,0,3.2,K.g.position.z-10,.008,t)},
 bigflex(u,t,b){shop.visible=false;aisle.visible=true;skyDome.visible=true;B.g.visible=false;scene.fog.near=30;scene.fog.far=120;scene.fog.color.set('#d98a4a');K.g.position.set(0,0,lerp(2,0,u));K.g.rotation.y=Math.PI;CLIP='walk';FL.visible=true;FL.scale.setScalar(260);FL.position.set(0,17+Math.sin(t*2)*1.2,-34);FL.rotation.set(0,t*.45,0);beam.visible=true;beam.position.set(0,60,-34);setCam(1.5,.34,K.g.position.z+5.4,.5,7.2,-20,.006,t)},
 fix(u,t,b){shop.visible=false;aisle.visible=true;skyDome.visible=true;B.g.visible=false;scene.fog.near=14;scene.fog.far=70;scene.fog.color.set('#d98a4a');K.g.position.set(0,0,1);K.g.rotation.y=.12;CLIP='scratch';pile.forEach((p,i)=>p.visible=i<(b.pile||0));
  const n=neckTarget(),st=b.step||0;setCam(n.x+[.5,-.45,.6,-.5,.3,-.6,.55][st%7],n.y-.05,n.z+1.7,n.x,n.y-.08,n.z,.008,t);
  if(b.prop&&props[b.prop]){const g=props[b.prop],h=handAt(b);g.visible=true;g.position.copy(h);g.lookAt(cam.position);g.rotateX(-.2);g.rotateZ(-.9);g.position.y+=.0}},
 end(u,t,b){shop.visible=false;aisle.visible=true;B.g.visible=false;scene.background.set('#c9a878');scene.fog.near=11;scene.fog.far=34;scene.fog.color.set('#c9a878');K.g.position.set(0,0,lerp(1.6,.8,u)-(b.step||0)*.5);K.g.rotation.y=Math.PI;walk(K,t,13);pile.forEach((p,i)=>p.visible=i<(b.pile||0));
  setCam(Math.sin((b.step||0)*2)*.7,.7,K.g.position.z+5.2,0,3.6,K.g.position.z-8,.012,t)},
 shower(u,t,b){shop.visible=false;bath.visible=true;B.g.visible=false;scene.background.set('#20282a');scene.fog.near=20;scene.fog.far=60;K.g.position.set(0,0,0);K.g.rotation.y=.3;CLIP='scratch';K.g.updateMatrixWorld(true);const n=neckTarget();setCam(n.x+.5,n.y-.05,n.z+1.65,n.x,n.y-.12,n.z,.004,t);
  for(const d of drops){const k=((t*1.5+d.p)%1);d.m.position.set(d.x,3.1-k*3.1,d.z)}
  const h=handAt(b);FL.visible=true;FL.scale.setScalar(1.7);FL.position.set(n.x+.13+Math.sin(t*90)*.0015,n.y-.03+Math.sin(t*5)*.03,n.z+.14);FL.lookAt(cam.position);FL.rotateY(.45)},
 end(u,t,b){shop.visible=false;K.g.visible=false;B.g.visible=false;scene.background.set('#050505');FL.visible=true;FL.scale.setScalar(2.4);FL.position.set(0,.1,0);FL.rotation.set(.08,t*1.1,0);sun.intensity=4.2;hemi.intensity=2;setCam(0,0,1.1,0,-.03,0,0,t)}
};
function reset(){shop.visible=true;K.g.visible=true;B.g.visible=true;cross.visible=false;room.visible=false;aisle.visible=false;B2.g.visible=false;bl.visible=true;city.visible=false;Object.values(props).forEach(p=>p.visible=false);pile.forEach(p=>p.visible=false);FL.visible=false;beam.visible=false;skyDome.visible=false;skinW.visible=false;bath.visible=false;phone.visible=false;sun.intensity=3;rings.forEach(r=>r.visible=false);K.head.position.y=.4;K.arms.forEach(x=>x.a.rotation.z=0);TURN.forEach(m=>m.visible=false);halo.visible=false;scene.background.copy(SMOG);scene.fog.near=9;scene.fog.far=34;scene.fog.color.copy(SMOG);sky.material.color.set('#e8b873');hemi.intensity=.62;K.head.rotation.set(0,0,0);K.neck.rotation.set(0,0,0);K.mouth.scale.set(1,1,1);B.mouth.scale.set(1,1,1);B2.mouth.scale.set(1,1,1);B.head.rotation.set(0,0,0);K.g.rotation.set(0,0,0)}

/* the barber's body swings across the lens: the swipe's own move. Drawn in the world, close to camera. */
const wipe=box(1.4,3,.5,'#3a3b40');wipe.visible=false;scene.add(wipe);
let POST=null,AFTER=null;const S_={};
/*SKIT*/
window.RIGDBG=()=>{const a=RIG.acts||{};return JSON.stringify({keys:Object.keys(a),clips:Object.keys(window.CLIPS||{}),dur:a.scratch&&a.scratch.getClip().duration,tracks:a.scratch&&a.scratch.getClip().tracks.slice(0,3).map(t=>[t.name,t.times.length,t.ValueTypeName]),en:a.scratch&&a.scratch.enabled,w:a.scratch&&a.scratch.getEffectiveWeight(),run:a.scratch&&a.scratch.isRunning(),t:a.scratch&&a.scratch.time,q:RIG.allB[8].b.name,qv:RIG.allB[8].b.quaternion.toArray(),rest:RIG.allB[8].q.toArray()})};
window.draw=function(t){
 const b=AD.beats.find(x=>t>=x.t&&t<x.e)||AD.beats[AD.beats.length-1],u=clamp((t-b.t)/(b.e-b.t));
 reset();CLIP=b.clip||null;CLIP2=b.clip2||null;CLIP_T=t;(SC[b.scene]||SC.chair)(u,t,b);rainAt(t,b);
 const prev=b.from!=null?b.from:(b.bumps||0),n=lerp(prev,b.bumps||0,ease(clamp(u*2.4)));setBumps(n,lerp(.2,1,ease(clamp(u*3))));if(RIG.ready)paintBumps(n,b.red);
 razor.visible=false;if(b.razor&&b.scene==='neck'&&u<.62){const n=neckTarget(),k=clamp(u/.62);razor.visible=true;razor.position.set(n.x+.2,n.y+lerp(.26,-.14,ease(k)),n.z+.12);razor.lookAt(cam.position)}
 pole.rotation.y=t*2.4;poleT.offset.y=(t*.8)%1;
 /* wipe at any beat with swing: first 0.34 s */
 let w=-1;const SW=.17;
 if(b.swing&&t-b.t<SW)w=1-(t-b.t)/SW; /* leaving */
 const nx=AD.beats[AD.beats.indexOf(b)+1];if(nx&&nx.swing&&b.e-t<SW)w=1+(b.e-t)/SW*-1+1-1;
 wipe.visible=false;
 if(nx&&nx.swing&&b.e-t<SW){const k=1-(b.e-t)/SW;place(lerp(1.6,0,k))}
 else if(b.swing&&t-b.t<SW){const k=(t-b.t)/SW;place(lerp(0,-1.6,k))}
 skyDome.position.copy(cam.position);speak(t,b);driveRig();const snap=AFTER&&[RIG,RIG2].filter(r=>r.ready).flatMap(r=>r.allB.map(x=>[x.b,x.b.quaternion.clone()]));if(AFTER)AFTER(t,b);if(POST)POST(b,t);else R.render(scene,cam);if(snap)for(const[x,q]of snap)x.quaternion.copy(q);
 if(window.hud)window.hud(t,b,u);
};
function place(x){cam.updateMatrixWorld(true);const v=new THREE.Vector3(x,0,-.55).applyMatrix4(cam.matrixWorld);wipe.position.copy(v);wipe.quaternion.copy(cam.quaternion);wipe.visible=true}
})();