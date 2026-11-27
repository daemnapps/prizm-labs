/* skit.js: a porch comedy skit shot like a film. Read into world.js at its SKIT mark, so it shares that scope.
   Adds: sun shadows, a lens pass (focus, bloom, grain, grade), hands placed by reach (two-bone IK), layered clips,
   the porch and street, falling objects, smoke, and the shot grammar in ad.json (cam, cam2, hand, snap, tL tR dL dR). */
if(AD.skit){
document.body.className='skit';cam.far=320;cam.updateProjectionMatrix();
const V3=(x,y,z)=>new THREE.Vector3(x,y,z);
/* light */
R.shadowMap.enabled=true;R.shadowMap.type=THREE.PCFSoftShadowMap;
sun.castShadow=true;sun.shadow.mapSize.set(1536,1536);{const c=sun.shadow.camera;c.left=-10;c.right=10;c.top=10;c.bottom=-10;c.near=1;c.far=60}sun.shadow.bias=-.0005;sun.shadow.normalBias=.03;
function smooth(root){root.traverse(o=>{if(!o.isSkinnedMesh)return;const g=o.geometry,P=g.attributes.position,N=g.attributes.normal,m=new Map();for(let i=0;i<P.count;i++){const k=Math.round(P.getX(i)*2e3)+'_'+Math.round(P.getY(i)*2e3)+'_'+Math.round(P.getZ(i)*2e3);let e=m.get(k);if(!e){e={x:0,y:0,z:0,i:[]};m.set(k,e)}e.x+=N.getX(i);e.y+=N.getY(i);e.z+=N.getZ(i);e.i.push(i)}for(const e of m.values()){const l=Math.hypot(e.x,e.y,e.z)||1;for(const i of e.i)N.setXYZ(i,e.x/l,e.y/l,e.z/l)}N.needsUpdate=true;o.material.flatShading=false;o.material.needsUpdate=true})}
window.ready.then(()=>{smooth(RIG.root);if(RIG2.root)smooth(RIG2.root);for(const g of[K.g,B2.g,FL])g.traverse(o=>{if(o.isMesh&&o.visible!==false)o.castShadow=true});if(RIG.root)RIG.root.traverse(o=>{if(o.isMesh)o.castShadow=true});if(RIG2.root)RIG2.root.traverse(o=>{if(o.isMesh)o.castShadow=true})});
const mk=(g,c,x,y,z,sh=1)=>{const m=c;at(m,x,y,z);m.castShadow=!!sh;m.receiveShadow=true;g.add(m);return m};
const skyM=new THREE.Mesh(new THREE.SphereGeometry(200,16,12),new THREE.MeshBasicMaterial({map:soft(0,8,256,(g,w,h)=>{const q=g.createLinearGradient(0,0,0,h);q.addColorStop(0,'#5f8fc4');q.addColorStop(.38,'#a9c8dc');q.addColorStop(.5,'#f4dcae');q.addColorStop(.56,'#ffd9a0');q.addColorStop(1,'#caa97a');g.fillStyle=q;g.fillRect(0,0,w,h)}),side:THREE.BackSide,fog:false}));skyM.visible=false;scene.add(skyM);
const PORCH=new THREE.Group();PORCH.visible=false;scene.add(PORCH);const YARD=new THREE.Group();YARD.visible=false;scene.add(YARD);
const wood=(c,rep)=>{const t=soft(0,128,128,(g,w,h)=>{g.fillStyle=c;g.fillRect(0,0,w,h);for(let y=0;y<h;y+=18){g.fillStyle='rgba(20,10,4,.6)';g.fillRect(0,y,w,2);for(let i=0;i<30;i++){g.fillStyle=Math.random()>.5?'rgba(255,230,190,.05)':'rgba(30,14,6,.09)';g.fillRect(Math.random()*w,y+2+Math.random()*15,20+Math.random()*50,1)}}});t.wrapS=t.wrapT=THREE.RepeatWrapping;t.repeat.set(rep[0],rep[1]);return new THREE.MeshLambertMaterial({map:t})};
const deckM=wood('#7d5a3c',[3,3]),sideM=wood('#b9a78c',[2,2]),trimM=mat('#e6dcc6'),railM=mat('#d9cfb8'),roofM=mat('#4a3a30');
const bx=(w,h,d,m)=>new THREE.Mesh(new THREE.BoxGeometry(w,h,d),m);
const paintable=[sideM];
{mk(PORCH,bx(9,.5,4,deckM),0,.25,-.3);
 mk(PORCH,bx(14,4.4,.3,sideM),0,2.4,-2.4);mk(PORCH,bx(14,1.8,5,roofM),0,5.3,-4.4,1);
 mk(PORCH,bx(9.6,.22,4.8,roofM),0,3.6,-.3);mk(PORCH,bx(9.4,.3,.2,trimM),0,3.36,1.55);
 for(const x of[-4.2,-1.3,1.3,4.2])mk(PORCH,bx(.2,3,.2,trimM),x,2,1.5);
 /* screen door and two windows */
 mk(PORCH,bx(1.1,2.3,.08,mat('#5a4636')),0,1.65,-2.22);mk(PORCH,bx(1.24,2.44,.05,trimM),0,1.65,-2.24);
 for(const x of[-2.7,2.7]){mk(PORCH,bx(1.5,1.3,.06,new THREE.MeshBasicMaterial({color:'#2c3238'})),x,2.1,-2.22,0);mk(PORCH,bx(1.66,1.46,.04,trimM),x,2.1,-2.24,0);mk(PORCH,bx(.7,1.2,.03,mat('#c9b58a')),x-.36,2.1,-2.18,0);mk(PORCH,bx(.08,1.3,.03,trimM),x,2.1,-2.17,0)}
 /* the rail, open at the steps */
 for(const q of[-1,1]){mk(PORCH,bx(2.9,.09,.09,railM),q*2.75,1.42,1.5);mk(PORCH,bx(2.9,.07,.07,railM),q*2.75,.66,1.5);for(let i=0;i<14;i++)mk(PORCH,bx(.045,.76,.045,railM),q*(1.4+i*.21),1.04,1.5)}
 for(let i=0;i<3;i++)mk(PORCH,bx(2.4,.17,.42,deckM),0,.42-i*.17,1.9+i*.42);
 /* a chair each, a crate between them */
 const chairM=mat('#5a4230'),leg=mat('#c9c5ba');
 for(const[x,r]of[[-.45,.2],[.45,-.2]]){const c=new THREE.Group();mk(c,bx(.66,.06,.42,chairM),0,.5,-.12);for(let q=0;q<3;q++)mk(c,bx(.66,.09,.04,chairM),0,.72+q*.16,-.32);mk(c,bx(.05,.5,.05,leg),-.3,.84,-.33);mk(c,bx(.05,.5,.05,leg),.3,.84,-.33);for(const[a,b]of[[-.3,-.28],[.3,-.28],[-.3,.06],[.3,.06]])mk(c,bx(.05,.5,.05,leg),a,.25,b);at(c,x,.5,.05);c.scale.y=1.4;c.rotation.y=r;PORCH.add(c)}
 mk(PORCH,bx(.3,.3,.3,wood('#6b4a30',[1,1])),-1.7,.65,.2);mk(PORCH,new THREE.Mesh(new THREE.CylinderGeometry(.09,.07,.03,12),mat('#3a3a3e')),-1.7,.815,.2);
 /* the razor that has been stuck in the rail for years */
 const r=new THREE.Group();mk(r,bx(.34,.05,.07,mat('#dfe5e8')),0,0,0);mk(r,bx(.05,.42,.05,mat('#2d5fa8')),0,.23,0);r.visible=false;PORCH.add(r)
}
/* the yard and the block */
{const gt=soft(0,256,256,(g,w,h)=>{g.fillStyle='#5f7a3a';g.fillRect(0,0,w,h);for(let i=0;i<9000;i++){g.fillStyle=['#4b6a2e','#78924a','#3d5a2a','#8a9a52'][i&3];g.fillRect(Math.random()*w,Math.random()*h,1.5,5)}for(let i=0;i<30;i++){g.fillStyle='rgba(120,90,50,.35)';g.beginPath();g.arc(Math.random()*w,Math.random()*h,8+Math.random()*16,0,7);g.fill()}});gt.wrapS=gt.wrapT=THREE.RepeatWrapping;gt.repeat.set(14,14);
 const gr=new THREE.Mesh(new THREE.PlaneGeometry(90,90),new THREE.MeshLambertMaterial({map:gt}));gr.rotation.x=-Math.PI/2;gr.position.z=4;gr.receiveShadow=true;YARD.add(gr);
 const tuft=new THREE.InstancedMesh(new THREE.ConeGeometry(.035,.3,3),mat('#6f8a42'),1500);seed=91;const M_=new THREE.Matrix4();for(let i=0;i<1500;i++){const s=.6+rnd();M_.makeRotationFromEuler(new THREE.Euler((rnd()-.5)*.5,rnd()*6,(rnd()-.5)*.5));M_.setPosition(-9+rnd()*18,.12*s,1.9+rnd()*7);M_.scale(V3(s,s,s));tuft.setMatrixAt(i,M_)}tuft.receiveShadow=true;tuft.frustumCulled=false;YARD.add(tuft);
 const walk_=mk(YARD,bx(1.5,.05,6,mat('#a8a294')),0,.025,6.2,0);
 const rd=new THREE.Mesh(new THREE.PlaneGeometry(90,8),new THREE.MeshLambertMaterial({map:(()=>{const t=soft(0,128,128,(g,w,h)=>{g.fillStyle='#4b4a48';g.fillRect(0,0,w,h);for(let i=0;i<2600;i++){g.fillStyle=Math.random()>.5?'rgba(255,240,220,.05)':'rgba(0,0,0,.12)';g.fillRect(Math.random()*w,Math.random()*h,2,2)}});t.wrapS=t.wrapT=THREE.RepeatWrapping;t.repeat.set(12,1);return t})()}));rd.rotation.x=-Math.PI/2;at(rd,0,.03,14);rd.receiveShadow=true;YARD.add(rd);
 mk(YARD,bx(90,.14,1.6,mat('#a8a294')),0,.07,9.4,0);mk(YARD,bx(90,.14,1.6,mat('#a8a294')),0,.07,18.6,0);
 for(let x=-40;x<40;x+=6)mk(YARD,bx(2.6,.01,.2,mat('#d8c070')),x,.05,14,0);
 /* chain fence with a gate gap */
 for(const q of[-1,1]){mk(YARD,bx(6,.9,.04,new THREE.MeshLambertMaterial({color:'#8c9296',transparent:true,opacity:.35})),q*4.3,.45,8.4,0);mk(YARD,bx(6,.04,.04,mat('#b0b4b8')),q*4.3,.92,8.4,0)}
 for(let i=-1;i<2;i+=2){mk(YARD,bx(.8,3,5,sideM.clone()),i*11,1.5,-3)}
 /* the houses across the street */
 const cs=['#c7a57e','#9fb09a','#d0bfa0','#a97a62','#b9b4ac'];for(let i=0;i<7;i++){const x=-27+i*9,h=new THREE.Group();mk(h,bx(7.5,3.6,6,mat(cs[i%5])),0,1.8,0);const rf=mk(h,new THREE.Mesh(new THREE.ConeGeometry(5.6,1.5,4),mat('#5a3a30')),0,4.3,0);rf.rotation.y=Math.PI/4;rf.scale.z=.85;mk(h,bx(1,2,.1,mat('#3a2414')),0,1,-3.05,0);for(const q of[-1,1])mk(h,bx(1.2,1,.1,new THREE.MeshBasicMaterial({color:'#2a3238'})),q*2.3,2,-3.05,0);at(h,x,0,24);YARD.add(h)}
 /* palms and wires */
 S_.palms=[];const palm=(x,z,h_)=>{const p=new THREE.Group();const tr=cyl(.1,.2,h_,7,'#6a543c');tr.position.y=h_/2;tr.castShadow=true;p.add(tr);const cr=new THREE.Group();cr.position.y=h_;for(let f=0;f<10;f++){const l=bx(.32,.05,2.8,mat(f%2?'#3e6a32':'#4c7a3a'));l.geometry.translate(0,0,1.4);l.rotation.y=f*.63;l.rotation.x=.45;l.castShadow=true;cr.add(l)}p.add(cr);at(p,x,0,z);YARD.add(p);S_.palms.push(cr);return p};
 palm(-13,20,11);palm(4,21,12.5);palm(16,20,10);palm(-24,21,12);
 S_.tree=palm(3.4,3.2,5);S_.tree.visible=false;
 for(let i=0;i<8;i++)mk(YARD,cyl(.09,.12,8,6,'#3a2c20'),-28+i*8,4,10.2,0);
 for(let i=0;i<7;i++){for(const dy of[0,.28]){const w=bx(8.1,.018,.018,new THREE.MeshBasicMaterial({color:'#20201e'}));at(w,-24+i*8,7.7+dy,10.2);YARD.add(w)}}
 /* a parked car and one that rolls past */
 const car=c=>{const g=new THREE.Group();mk(g,bx(4.6,.62,1.8,mat(c)),0,.62,0);mk(g,bx(2.3,.55,1.6,mat(c)),-.2,1.2,0);mk(g,bx(2.1,.46,1.64,new THREE.MeshBasicMaterial({color:'#222830'})),-.2,1.2,0,0);for(const[x,z]of[[-1.5,.9],[1.5,.9],[-1.5,-.9],[1.5,-.9]]){const w=mk(g,cyl(.32,.32,.22,14,'#141414'),x,.32,z);w.rotation.x=Math.PI/2}mk(g,bx(.06,.14,1.4,new THREE.MeshBasicMaterial({color:'#ffe9b0'})),2.31,.7,0,0);return g};
 const parked=car('#7a2a30');at(parked,-5,0,11.4);YARD.add(parked);S_.car=car('#2c3f6a');YARD.add(S_.car);
 /* birds */
 S_.birds=[];for(let i=0;i<7;i++){const b=bx(.26,.03,.09,new THREE.MeshBasicMaterial({color:'#25231f'}));YARD.add(b);S_.birds.push(b)}
}
/* things that land: razors and the rest of the graveyard */
const junk=[['five','#2d5fa8'],['single','#cfd5d8'],['rotary','#17171a'],['foil','#3a3a40']];
function bigThing(c){const g=new THREE.Group();mk(g,bx(.08,.75,.08,mat(c)),0,.37,0);mk(g,bx(.62,.09,.16,mat('#dfe5e8')),0,.78,0);return g}
S_.drops=(AD.drops||[]).map(d=>{const g=bigThing(junk[d.k%4][1]);g.scale.setScalar(d.s||3.5);g.visible=false;scene.add(g);return{d,g}});
const heapN=420,hA=new THREE.InstancedMesh(new THREE.BoxGeometry(.9,.14,.3),mat('#cfd5d8'),heapN),hB=new THREE.InstancedMesh(new THREE.BoxGeometry(.2,1.2,.2),mat('#2d5fa8'),heapN);hA.frustumCulled=hB.frustumCulled=false;hA.castShadow=hB.castShadow=true;hA.visible=hB.visible=false;scene.add(hA,hB);
{seed=55;const M_=new THREE.Matrix4(),P_=new THREE.Vector3(),Q_=new THREE.Quaternion(),E_=new THREE.Euler(),S1=new THREE.Vector3(1,1,1),cols=['#2d5fa8','#17171a','#a02a26','#3a3a40','#6a6e74'],C_=new THREE.Color();for(let i=0;i<heapN;i++){const k=i/heapN,y=k*9.5,r=(1-k)*5.4*Math.sqrt(rnd());const a=rnd()*7;P_.set(2.8+Math.cos(a)*r,y,5.4+Math.sin(a)*r*.7);E_.set(rnd()*6,rnd()*6,rnd()*6);Q_.setFromEuler(E_);M_.compose(P_,Q_,S1);hA.setMatrixAt(i,M_);P_.add(V3(.1,-.4,0));M_.compose(P_,Q_,S1);hB.setMatrixAt(i,M_);hB.setColorAt(i,C_.set(cols[i%5]))}}
/* props in the hands */
const bowl=new THREE.Group();{const pts=[];for(let i=0;i<=8;i++){const a=i/8*1.45;pts.push(new THREE.Vector2(Math.sin(a)*.2,-Math.cos(a)*.13))}const b=new THREE.Mesh(new THREE.LatheGeometry(pts,18),new THREE.MeshStandardMaterial({color:'#c8ccd0',metalness:.85,roughness:.32,side:THREE.DoubleSide}));b.castShadow=true;bowl.add(b);const m=new THREE.Mesh(new THREE.CircleGeometry(.185,18),new THREE.MeshLambertMaterial({map:soft(0,64,64,(g,w,h)=>{g.fillStyle='#f4efe4';g.fillRect(0,0,w,h);for(let i=0;i<70;i++){g.fillStyle=['#d9a441','#c9782a','#e6c35a','#b5452c'][i&3];g.beginPath();g.arc(Math.random()*w,Math.random()*h,3.2,0,7);g.fill()}})}));m.rotation.x=-Math.PI/2;m.position.y=-.015;bowl.add(m)}bowl.visible=false;scene.add(bowl);
const spoon=new THREE.Group();{const s=at(bx(.01,.17,.005,mat('#d6dadf')),0,.09,0);const h=new THREE.Mesh(new THREE.SphereGeometry(.015,8,6),mat('#d6dadf'));h.scale.set(.8,.25,1.2);at(h,0,.18,0);spoon.add(s,h)}spoon.visible=false;scene.add(spoon);
const mirror=new THREE.Group();{const f=new THREE.Mesh(new THREE.CylinderGeometry(.11,.11,.02,20),mat('#7a3a4a'));f.rotation.x=Math.PI/2;const g=new THREE.Mesh(new THREE.CircleGeometry(.095,20),new THREE.MeshBasicMaterial({color:'#c6dbe2'}));g.position.z=-.012;g.rotation.y=Math.PI;mirror.add(f,g,at(bx(.03,.16,.02,mat('#7a3a4a')),0,-.18,0))}mirror.visible=false;scene.add(mirror);
const cig=new THREE.Group();cig.add(at(cyl(.006,.006,.08,6,'#efe9dd'),0,0,0),at(cyl(.0065,.0065,.012,6,'#d9662a'),0,.045,0));cig.visible=false;scene.add(cig);
const smokeT=soft(0,64,64,(g,w,h)=>{const q=g.createRadialGradient(w/2,h/2,2,w/2,h/2,w/2);q.addColorStop(0,'rgba(235,232,226,.5)');q.addColorStop(1,'rgba(235,232,226,0)');g.fillStyle=q;g.fillRect(0,0,w,h)});
const puffs=[];for(let i=0;i<16;i++){const s=new THREE.Sprite(new THREE.SpriteMaterial({map:smokeT,transparent:true,depthWrite:false}));s.visible=false;scene.add(s);puffs.push(s)}
const dustM=new THREE.Points(new THREE.BufferGeometry(),new THREE.PointsMaterial({color:'#fff3cc',size:.009,transparent:true,opacity:.35,depthWrite:false}));{seed=17;const a=[];for(let i=0;i<260;i++)a.push(-3+rnd()*6,.6+rnd()*3,-1+rnd()*4);dustM.geometry.setAttribute('position',new THREE.Float32BufferAttribute(a,3));dustM.frustumCulled=false}dustM.visible=false;scene.add(dustM);
const giantBlade=window.bigRazor;
{const P=(n,f)=>{const g=new THREE.Group();f(g);g.visible=false;scene.add(g);props[n]=g};P('sander',g=>{g.add(at(box(.3,.13,.16,'#d9651e'),0,.12,0),at(box(.32,.05,.17,'#1c1c1e'),0,.04,0),at(box(.1,.14,.05,'#26262b'),0,.24,0))});P('armful',g=>{const c=['#b0322a','#2d5fa8','#e8e2d6','#e6b83e','#3a7a4a','#7a3a8a'];seed=5;for(let i=0;i<16;i++){const m=at(box(.13+rnd()*.1,.2+rnd()*.12,.1,c[i%6]),(i%4-1.5)*.15,(Math.floor(i/4))*.22,rnd()*.05);m.rotation.z=(rnd()-.5)*.5;g.add(m)}})}
{const steel=new THREE.MeshLambertMaterial({color:'#f2f5f8'}),blk=new THREE.MeshStandardMaterial({color:'#17171a',metalness:.3,roughness:.5});
 const headT=soft(0,128,128,(g,w,h)=>{g.fillStyle='#c9ced4';g.fillRect(0,0,w,h);g.translate(w/2,h/2);g.strokeStyle='#30343a';g.lineWidth=2;for(let i=0;i<36;i++){g.rotate(Math.PI/18);g.beginPath();g.moveTo(26,0);g.lineTo(58,0);g.stroke()}g.beginPath();g.arc(0,0,20,0,7);g.fillStyle='#8c9198';g.fill()});
 const P=(n,f)=>{const g=new THREE.Group();f(g);g.visible=false;scene.add(g);props[n]=g};
 P('rotary2',g=>{const b=new THREE.Mesh(new THREE.CylinderGeometry(.036,.045,.17,16),blk);b.position.y=.085;g.add(b);const pl=new THREE.Mesh(new THREE.CylinderGeometry(.062,.05,.03,20),blk);pl.position.y=.18;g.add(pl);g.userData.spin=[];for(const[x,y]of[[-.03,.205],[.03,.205],[0,.155]]){const d=new THREE.Mesh(new THREE.CircleGeometry(.027,20),new THREE.MeshStandardMaterial({map:headT,metalness:.6,roughness:.35}));d.position.set(x,y,.052);g.add(d);g.userData.spin.push(d)}g.add(at(new THREE.Mesh(new THREE.BoxGeometry(.095,.11,.02),blk),0,.18,.04))});
 P('foil2',g=>{g.add(at(new THREE.Mesh(new THREE.BoxGeometry(.065,.17,.04),blk),0,.085,0));g.add(at(new THREE.Mesh(new THREE.BoxGeometry(.075,.03,.05),blk),0,.18,0));const f=new THREE.Mesh(new THREE.CylinderGeometry(.018,.018,.07,16,1,false,0,Math.PI),steel);f.rotation.z=Math.PI/2;f.position.set(0,.2,0);g.add(f);const m=at(new THREE.Mesh(new THREE.BoxGeometry(.07,.02,.03),steel),0,.2,.012);g.add(m);g.add(at(box(.02,.04,.004,'#c23a2a'),0,.1,.021))});
 P('scissors2',g=>{g.userData.blades=[];for(const q of[-1,1]){const a=new THREE.Group();a.add(at(new THREE.Mesh(new THREE.BoxGeometry(.012,.09,.003),steel),0,.045,0));const r=new THREE.Mesh(new THREE.TorusGeometry(.016,.0045,8,16),mat('#c23a2a'));r.position.set(q*.014,-.022,0);a.add(r);a.position.y=.05;g.add(a);g.userData.blades.push([a,q])}})}
props.single.children.forEach((c,i)=>{if(i===0)c.material=new THREE.MeshLambertMaterial({color:'#b5262a'});else c.material=new THREE.MeshLambertMaterial({color:'#3a3d42'})});props.single.add(at(box(.145,.004,.05,'#f4f6f8'),0,.348,.012));
const SP=new THREE.InstancedMesh(new THREE.BoxGeometry(.006,.006,.018),new THREE.MeshBasicMaterial({color:'#ffc25a',fog:false}),60);SP.frustumCulled=false;SP.visible=false;scene.add(SP);
const tag=at(box(.1,.06,.01,'#f4d23c'),0,0,0);tag.visible=false;scene.add(tag);
const cap=new THREE.Group();cap.add(at(cyl(.115,.12,.07,16,'#1d4f9a'),0,.03,0),at(box(.2,.016,.12,'#1d4f9a'),0,0,.12));cap.visible=false;scene.add(cap);
const chain=new THREE.Mesh(new THREE.TorusGeometry(.115,.012,8,28),new THREE.MeshStandardMaterial({color:'#e8b94a',metalness:.9,roughness:.25,emissive:'#5a3a08'}));chain.visible=false;scene.add(chain);
{const r=bigThing('#2d5fa8');r.scale.setScalar(3);r.visible=false;scene.add(r);S_.ru=r;const q=new THREE.Group();q.visible=false;bath.add(q);S_.shelf=q}

/* hands by reach */
const Qa=new THREE.Quaternion(),Qb=new THREE.Quaternion(),Qc=new THREE.Quaternion(),Va=new THREE.Vector3(),Vb=new THREE.Vector3(),Vc=new THREE.Vector3(),Vd=new THREE.Vector3(),Ve=new THREE.Vector3();
function aim(bone,from,to){Qa.setFromUnitVectors(from,to);bone.getWorldQuaternion(Qb);Qb.premultiply(Qa);bone.parent.getWorldQuaternion(Qc).invert();bone.quaternion.copy(Qc.multiply(Qb)).normalize();bone.updateWorldMatrix(true,true)}
function ik(up,lo,ha,T,pole){up.updateWorldMatrix(true,true);const S=up.getWorldPosition(new THREE.Vector3()),E=lo.getWorldPosition(new THREE.Vector3()),W=ha.getWorldPosition(new THREE.Vector3());const a=S.distanceTo(E),b=E.distanceTo(W);const D=T.clone().sub(S),d=Math.min(D.length(),(a+b)*.995),dir=D.clone().normalize();const c=clamp((a*a+d*d-b*b)/(2*a*d),-1,1),s=Math.sqrt(1-c*c);const perp=pole.clone().sub(dir.clone().multiplyScalar(pole.dot(dir))).normalize();const E2=S.clone().add(dir.clone().multiplyScalar(a*c)).add(perp.multiplyScalar(a*s));aim(up,E.clone().sub(S).normalize(),E2.clone().sub(S).normalize());const E3=lo.getWorldPosition(new THREE.Vector3()),W3=ha.getWorldPosition(new THREE.Vector3());aim(lo,W3.clone().sub(E3).normalize(),T.clone().sub(E3).normalize())}
function turn(bone,ax,ang){bone.parent.getWorldQuaternion(Qc).invert();const l=ax.clone().applyQuaternion(Qc).normalize();Qa.setFromAxisAngle(l,ang);bone.quaternion.premultiply(Qa);bone.updateWorldMatrix(true,true)}
const Y=V3(0,1,0),X=V3(1,0,0),Z=V3(0,0,1);
function loc(rg,g,x,y,z){const n=rg.B.neck.getWorldPosition(new THREE.Vector3());return n.add(V3(x,y,z).applyAxisAngle(Y,g.rotation.y))}
function poseT(who,name,t,b){const tre=who==='t',rg=tre?RIG:RIG2,g=tre?K.g:B2.g;switch(name){
 case'shave':return loc(rg,g,-.03+Math.sin(t*(b&&b.fast||9))*.03,-.09+Math.sin(t*(b&&b.fast||9)*1.7)*.05,.18);
 case'low':return loc(rg,g,-.3,-.42,.3);
 case'carryL':return loc(rg,g,.2,-.42,.26);case'carryR':return loc(rg,g,-.2,-.42,.26);
 case'brush':return loc(rg,g,.12+Math.sin(t*7)*.04,-.26+Math.cos(t*5)*.04,.2);
 case'show':return loc(rg,g,-.22,-.28,.4);
 case'rub':return loc(rg,g,.3,-.34+Math.sin(t*4.5)*.04,.2);
 case'rub2':return loc(rg,g,-.17,-.06+Math.sin(t*4.5)*.04,.1);
 case'mirror':return loc(rg,g,-.34,-.02,.42);
 case'drag':{const k=Math.pow(Math.max(0,Math.sin(t*.8)),6);return lerpV(loc(rg,g,-.34,-.5,.3),loc(rg,g,-.06,.13,.17),k)}
 case'cig':return loc(rg,g,-.34,-.5,.3);
 case'point':return loc(rg,g,-.62,-.02,.38);
 case'shrug':return loc(rg,g,(b&&b.q||1)*.4,-.28+Math.abs(Math.sin(t*5))*.1,.34);
 case'hold':return loc(rg,g,.0,-.32,.34);
 case'bowl':return loc(rg,g,.08,-.56,.3);
 case'eat':{const c=(t%2.8)/2.8,k=c<.2?ease(c/.2):c<.34?1:c<.5?1-ease((c-.34)/.16):0;return lerpV(loc(rg,g,.02,-.42,.33),loc(rg,g,.0,-.05,.27),k)}
 case'shoulder':{const n=RIG.B.neck.getWorldPosition(new THREE.Vector3());return n.add(V3(.14,-.13,.02))}
 case'slide':return loc(rg,g,-.2,-.82,.52);
 case'whisper':return loc(rg,g,-.1,.1,.2);
 case'gesture':return loc(rg,g,-.34,-.2+Math.sin(t*6)*.08,.42);
 default:return null}}
const lerpV=(a,b,k)=>a.clone().lerp(b,k);
function hand(rg,who,side,g,cur,prev,k,t,b,flip){const up=rg.B[side+'Arm'],lo=rg.B[side+'ForeArm'],ha=rg.B[side+'Hand'];const A=poseT(who,prev,t,b),C=poseT(who,cur,t,b);if(!A&&!C)return;up.updateWorldMatrix(true,true);const W=ha.getWorldPosition(new THREE.Vector3());const T=lerpV(A||W,C||W,k);const s=flip?1:-1;ik(up,lo,ha,T,V3(s*.4,-1,-.25).applyAxisAngle(Y,g.rotation.y))}
function gaze(rg,yaw,tilt,lean,side){const N=rg.B.neck,H=rg.B.Head,Sp=rg.B.Spine;if(lean)turn(Sp,Z,lean);if(side)turn(Sp,X,side);turn(N,Y,yaw*.45);turn(H,Y,yaw*.55);if(tilt)turn(H,X,tilt)}
AFTER=function(t,b){if(!AD.skit||!RIG.ready||b.scene==='cast')return;
 const i=AD.beats.indexOf(b),p=AD.beats[i-1]||b,k=b.scene===p.scene?ease(clamp((t-b.t)/.3)):1,ky=ease(clamp((t-b.t)/.22));
 if(b.tre!==0){gaze(RIG,lerp(p.tY||0,b.tY||0,ky)+Math.sin(t*.7)*.04,lerp(p.tT||0,b.tT||0,ky)+Math.sin(t*1.1)*.012,0,0);
  hand(RIG,'t',RIG.sL,K.g,b.tL,p.tL,k,t,b,true);hand(RIG,'t',RIG.sR,K.g,b.tR,p.tR,k,t,b,false)}
 if(b.dre!==0&&!b.dreFree){gaze(RIG2,lerp(p.dY||0,b.dY||0,ky)+Math.sin(t*.9+1)*.05,lerp(p.dT||0,b.dT||0,ky)+Math.sin(t*1.3)*.012,lerp(p.dLean||0,b.dLean||0,ky),0);
  hand(RIG2,'d',RIG2.sL,B2.g,b.dL,p.dL,k,t,b,true);hand(RIG2,'d',RIG2.sR,B2.g,b.dR,p.dR,k,t,b,false)}
 scene.updateMatrixWorld(true);
 const at_=(rg,s)=>rg.B[s+'Hand'].getWorldPosition(new THREE.Vector3());
 bowl.visible=b.bowl!==0&&b.scene==='porch'&&b.dL==='bowl';if(bowl.visible){bowl.position.copy(at_(RIG2,RIG2.sL)).add(V3(.03,.1,.05));bowl.rotation.set(.12,0,-.06)}
 spoon.visible=bowl.visible&&b.dR==='eat';if(spoon.visible){const h=at_(RIG2,RIG2.sR);spoon.position.copy(h);spoon.lookAt(cam.position);spoon.rotateX(1.2)}
 chain.visible=false;if(chain.visible){chain.position.copy(RIG.B.neck.getWorldPosition(new THREE.Vector3())).add(V3(0,-.1,.06));chain.rotation.set(Math.PI/2-.42,0,0)}
 mirror.visible=b.tR==='mirror';if(mirror.visible){mirror.position.copy(at_(RIG,RIG.sR)).add(V3(.02,.14,.03));mirror.lookAt(RIG.B.Head.getWorldPosition(new THREE.Vector3()))}
 cig.visible=(b.tR==='cig'||b.tR==='drag')&&b.scene==='porch';let em=null;if(cig.visible){em=at_(RIG,RIG.sR);cig.position.copy(em).add(V3(.03,.03,.05));cig.rotation.set(.3,0,-.9);em=cig.position.clone().add(V3(-.03,.05,0))}
 if(b.scene==='porch'&&!em)em=V3(-1.7,.85,.2);
 phone.visible=b.dR==='show'&&b.scene==='porch';if(phone.visible){phone.position.copy(at_(RIG2,RIG2.sR)).add(V3(0,.1,.04));phone.scale.setScalar(1.5);phone.lookAt(cam.position)}
 if(b.prop&&props[b.prop]){const g=props[b.prop],h=b.propD?at_(RIG2,RIG2.sR):at_(RIG,b.propL?RIG.sL:RIG.sR);g.visible=true;g.scale.setScalar(b.ps||1.7);g.position.copy(h);if(b.prop==='armful'){const n=RIG.B.neck.getWorldPosition(new THREE.Vector3());g.position.set(n.x,n.y-.95,n.z+.34);g.rotation.set(0,K.g.rotation.y,0)}else if(b.nk){const n=RIG.B.neck.getWorldPosition(new THREE.Vector3()),L=(b.pl||.34)*(b.ps||1.7),r=(b.pl&&b.pl<.3)?.55:.75,st=Math.sin(t*(b.fast||9))*.04;g.position.set(n.x+.03+Math.sin(r)*L,n.y-.03+st-Math.cos(r)*L,n.z+(r<.7?.17:.15));g.rotation.set(r<.7?0:.25,r<.7?0:.2,r);if(g.userData.spin)g.userData.spin.forEach((d,i)=>d.rotation.z=t*(26+i*5));if(g.userData.blades)g.userData.blades.forEach(([a,q])=>a.rotation.z=q*(.12+Math.abs(Math.sin(t*14))*.28))}else{g.lookAt(cam.position);g.rotateX(-1.1);g.rotateZ(-.5)}}
 SP.visible=!!b.sparks;if(b.sparks){const n=RIG.B.neck.getWorldPosition(new THREE.Vector3()).add(V3(0,-.05,.12)),M_=new THREE.Matrix4();for(let i=0;i<60;i++){const a=((t*(1+i%3*.3)+i*.073)%.5),vx=Math.sin(i*12.9)*1.3,vy=.6+Math.abs(Math.sin(i*7.1))*1.4,vz=.12+Math.abs(Math.cos(i*3.3))*.25;M_.makeRotationFromEuler(new THREE.Euler(i,i*2,t*9));M_.setPosition(n.x+vx*a,n.y+vy*a-4*a*a,n.z+vz*a);SP.setMatrixAt(i,M_)}SP.instanceMatrix.needsUpdate=true}
 tag.visible=cap.visible=!!b.vest;if(b.vest){const n=RIG2.B.neck.getWorldPosition(new THREE.Vector3()),h=RIG2.B.Head.getWorldPosition(new THREE.Vector3());tag.position.copy(n).add(V3(.06,-.22,.13));tag.scale.setScalar(.7);cap.position.copy(h).add(V3(0,.15,.01));cap.rotation.y=B2.g.rotation.y}
 puffs.forEach((s,n)=>{s.visible=!!em;if(!em)return;const a=((t+n*.34)%5.4)/5.4;s.position.set(em.x+Math.sin(n*3+t*.5)*.06+a*.5,em.y+a*1.3,em.z+a*.2);const q=.06+a*.5;s.scale.set(q,q,q);s.material.opacity=(1-a)*.09});
 if(b.flex&&b.scene==='bathw'){FL.visible=true;{const n=RIG.B.neck.getWorldPosition(new THREE.Vector3());FL.scale.setScalar(1.15);FL.position.copy(n).add(V3(.07+Math.sin(t*7)*.03,-.04+Math.cos(t*5)*.03,.13));FL.rotation.set(.3,.95,Math.sin(t*90)*.02)}}
 else if(b.flex&&b.scene==='porch'){FL.visible=true;const d=b.flex;FL.scale.setScalar(d.s||1.25);if(d.hand){FL.position.copy(at_(RIG,RIG.sL)).add(V3(.02,.1,.05));FL.rotation.set(.2,t*.5,.1)}else{const q=clamp((t-b.t)/.8);FL.position.set(lerp(.5,-.2,ease(q)),.56,lerp(.55,.75,ease(q)));FL.rotation.set(Math.PI/2,0,1.2)}}
};
/* the lens: focus, bloom, grain, vignette, grade */
{const dt=new THREE.DepthTexture(RW,RH);dt.type=THREE.UnsignedIntType;const rt=new THREE.WebGLRenderTarget(RW,RH,{type:THREE.HalfFloatType,depthTexture:dt,minFilter:THREE.LinearFilter,magFilter:THREE.LinearFilter});
 const u={c:{value:rt.texture},d:{value:dt},t:{value:0},focus:{value:2.5},ap:{value:1},px:{value:new THREE.Vector2(1/RW,1/RH)},n:{value:.02},f:{value:80},flash:{value:0},tint:{value:new THREE.Vector3(1,1,1)},fade:{value:0}};
 const qs=new THREE.Scene(),qc=new THREE.OrthographicCamera(-1,1,1,-1,0,1);
 const q=new THREE.Mesh(new THREE.PlaneGeometry(2,2),new THREE.ShaderMaterial({uniforms:u,depthTest:false,depthWrite:false,vertexShader:'varying vec2 v;void main(){v=uv;gl_Position=vec4(position.xy,0.,1.);}',fragmentShader:`precision highp float;varying vec2 v;uniform sampler2D c,d;uniform float t,focus,ap,n,f,flash,fade;uniform vec2 px;uniform vec3 tint;
 float lin(vec2 p){float z=texture2D(d,p).x*2.-1.;return 2.*n*f/(f+n-z*(f-n));}
 float rnd(vec2 p){return fract(sin(dot(p,vec2(12.9898,78.233))+t*7.)*43758.5453);}
 vec3 aces(vec3 x){return clamp((x*(2.51*x+.03))/(x*(2.43*x+.59)+.14),0.,1.);}
 const int N=12;void main(){float z=lin(v);float coc=clamp(abs(z-focus)/max(z,.01)*ap,0.,1.)*7.;vec3 s=texture2D(c,v).rgb;vec3 b=vec3(0.);float w=1.;float a=rnd(v)*6.28;
 for(int i=0;i<N;i++){float q=float(i)+.5;float r=sqrt(q/float(N));float th=q*2.399+a;vec2 o=vec2(cos(th),sin(th))*r;vec3 x=texture2D(c,v+o*px*coc).rgb;s+=x;w+=1.;vec3 y=texture2D(c,v+o*px*22.).rgb;b+=max(y-vec3(.9),vec3(0.));}
 s/=w;b/=float(N);s+=b*.9;
 vec2 ca=(v-.5)*.0026;s.r=mix(s.r,texture2D(c,v+ca).r,.45);s.b=mix(s.b,texture2D(c,v-ca).b,.45);
 s*=tint;s=aces(s*1.05);s=pow(s,vec3(1./2.2));
 float l=dot(s,vec3(.3,.59,.11));s=mix(vec3(l),s,1.14);s=mix(s,s*vec3(.93,.97,1.07),smoothstep(.5,0.,l)*.55);s=mix(s,s*vec3(1.05,1.0,.92),smoothstep(.45,1.,l)*.5);
 float vg=smoothstep(.95,.28,length((v-.5)*vec2(.95,1.1)));s*=mix(.62,1.,vg);
 s+=(rnd(v+.3)-.5)*.045;s=mix(s,vec3(1.),flash);s*=1.-fade;gl_FragColor=vec4(s,1.);}`}));qs.add(q);
 POST=function(b,t){R.setRenderTarget(rt);R.render(scene,cam);R.setRenderTarget(null);u.t.value=t%10;u.n.value=cam.near;u.f.value=cam.far;u.focus.value=b.focus||2.2;u.ap.value=b.ap==null?1.1:b.ap;const dt_=t-b.t;u.flash.value=(b.flash?Math.max(0,1-dt_/ (b.flash)):0);u.fade.value=b.fadein?Math.max(0,1-dt_/b.fadein):0;const ti=b.tint||[1,1,1];u.tint.value.set(ti[0],ti[1],ti[2]);if(b.siren){if(Math.floor(t*5)%2)u.tint.value.set(1.15,.72,.72);else u.tint.value.set(.72,.8,1.2)}R.render(qs,qc)}}
{const r0=reset;reset=function(){r0();PORCH.visible=YARD.visible=skyM.visible=dustM.visible=false;PORCH.position.y=YARD.position.y=0;crossBg.visible=false;hA.visible=hB.visible=false;SP.visible=tag.visible=cap.visible=false;B2.g.rotation.set(0,0,0);S_.ru.visible=false;S_.shelf.visible=false;for(const o of S_.drops)o.g.visible=false;bowl.visible=spoon.visible=mirror.visible=cig.visible=false;puffs.forEach(p=>p.visible=false);B.g.visible=false}}
window.MEAS=t=>{draw(t);const f=(rg,g)=>{const h=rg.B.Hips.getWorldPosition(new THREE.Vector3()),n=rg.B.Head.getWorldPosition(new THREE.Vector3()),l=rg.B[rg.sL+'Foot'].getWorldPosition(new THREE.Vector3());return{g:g.position.toArray(),hips:h.toArray(),head:n.toArray(),foot:l.toArray()}};return JSON.stringify({t:f(RIG,K.g),d:f(RIG2,B2.g)})};
/* the shot grammar */
function hand_(t,a){return[a*(Math.sin(t*1.7)+.5*Math.sin(t*4.3+1)+.25*Math.sin(t*9.1)),a*(Math.cos(t*1.3+2)+.5*Math.sin(t*3.7)+.25*Math.cos(t*8.3)),a*.6*Math.sin(t*2.1+.5)]}
function shoot(b,u,t){const A=b.cam,Bm=b.cam2||A;const k=b.snap?ease(clamp((t-b.t)/b.snap)):ease(u);const n=hand_(t,b.hand==null?.012:b.hand);const shake=b.shake&&t-b.t<b.shake[1]?b.shake[0]*(1-(t-b.t)/b.shake[1]):0;
 cam.position.set(lerp(A[0],Bm[0],k)+n[0]+Math.sin(t*61)*shake,lerp(A[1],Bm[1],k)+n[1]+Math.cos(t*53)*shake,lerp(A[2],Bm[2],k)+n[2]);
 const wh=b.whip?Math.pow(Math.max(0,1-(t-b.t)/.16),2)*1.4:0;cam.lookAt(lerp(A[3],Bm[3],k)+n[0]*.4+wh,lerp(A[4],Bm[4],k)+n[1]*.4,lerp(A[5],Bm[5],k));
 const f=lerp(A[6]||38,Bm[6]||A[6]||38,k);if(cam.fov!==f){cam.fov=f;cam.updateProjectionMatrix()}}
function world(t,after){shop.visible=false;B.g.visible=false;PORCH.visible=YARD.visible=true;skyM.visible=true;skyM.position.copy(cam.position);dustM.visible=true;scene.background.set('#d9c9a4');scene.fog.color.set('#e8d6b0');scene.fog.near=14;scene.fog.far=75;
 sun.position.set(-6.5,4.6,13);sun.target.position.set(0,0,2);scene.add(sun.target);sun.color.set('#ffd9a8');sun.intensity=4.2;hemi.color.set('#dcebf7');hemi.groundColor.set('#a08a5a');hemi.intensity=2.1;
 S_.palms.forEach((c,i)=>{c.rotation.z=Math.sin(t*.9+i)*.05;c.rotation.x=Math.cos(t*.7+i)*.04});S_.tree.visible=!!after;
 sideM.color.set(after?'#ffffff':'#d8cdb8');
 const pc=((t+9)%17)/17;S_.car.position.set(-48+pc*96,0,15.6);
 S_.birds.forEach((m,i)=>{const a=t*.34+i*.8;m.position.set(Math.cos(a)*(12+i)+1,9+Math.sin(a*2)*1.2+i*.3,16+Math.sin(a)*5);m.rotation.z=Math.sin(t*9+i)*.5});
 dustM.rotation.y=t*.02;dustM.position.y=Math.sin(t*.3)*.08}
function seat(){K.g.position.set(-.59,.62,.44);K.g.rotation.y=.2;B2.g.visible=true;B2.g.position.set(.17,.62,.35);B2.g.rotation.y=-.2}
function groundDrops(t,b){for(const o of S_.drops){const d=o.d;const fall=.42;if(t<d.t-fall||b.after||b.flexrise){o.g.visible=false;continue}o.g.visible=b.scene==='porch';const k=clamp((t-(d.t-fall))/fall);o.g.position.set(d.x,(1-k*k)*30+(k>=1?0:0),d.z);const hit=t-d.t;o.g.rotation.set(d.rx||.3,d.ry||0,(d.rz||.25)+(k>=1&&hit<.35?Math.sin(hit*50)*(.35-hit)*.25:0))}}
const H0=hairCurve.points.map(v=>v.clone()),H1=H0.map((v,i)=>new THREE.Vector3(-1.5+.1*i/6,-1.75+3.4*i/6,1.52));
const lump=new THREE.Mesh(new THREE.SphereGeometry(.62,16,12),new THREE.MeshLambertMaterial({color:'#c23a2a',transparent:true,opacity:.75}));lump.scale.set(1.3,.75,.5);at(lump,0,-.25,1.3);cross.add(lump);
const crossBg=new THREE.Mesh(new THREE.PlaneGeometry(30,16),new THREE.MeshBasicMaterial({color:'#e9d9bd',fog:false}));crossBg.position.set(0,4,-2);crossBg.visible=false;scene.add(crossBg);
function room_(t,water){shop.visible=false;B.g.visible=false;bath.visible=true;scene.background.set('#20282a');scene.fog.near=30;scene.fog.far=60;sun.position.set(2,5,6);sun.color.set('#ffe6c8');sun.intensity=2.2;hemi.color.set('#fff0dc');hemi.groundColor.set('#6a7a7c');hemi.intensity=2.2;for(const d of drops){d.m.visible=!!water;if(water){const k=(t*1.5+d.p)%1;d.m.position.set(d.x,3.1-k*3.1,d.z+.9)}}}
Object.assign(SC,{
 crossw(u,t,b){shop.visible=false;K.g.visible=false;B.g.visible=false;cross.visible=true;crossBg.visible=true;scene.background.set('#e9d9bd');scene.fog.near=40;scene.fog.far=90;sun.position.set(2,6,8);sun.color.set('#fff4e0');sun.intensity=2.4;hemi.color.set('#ffffff');hemi.groundColor.set('#a08a7a');hemi.intensity=2.2;
  const k=ease(clamp(lerp(b.uc?b.uc[0]:0,b.uc?b.uc[1]:0,u)));const pts=H0.map((v,i)=>v.clone().lerp(H1[i],k));hairTube.geometry.dispose();hairTube.geometry=new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts),24,.09,6);
  lump.scale.set(1.3*(1-k*.9),.75*(1-k*.9),.5);lump.material.opacity=.75*(1-k);
  bl.visible=!!b.bl;if(b.bl){bl.position.set(lerp(-4,4,u),-.85,0);bl.scale.setScalar(1.5)}
  cross.position.x=b.shake2?Math.sin(t*70)*.03:0;
  if(b.fx){FL.visible=true;FL.scale.setScalar(10);FL.position.set(Math.sin(t*70)*.05-.2,lerp(4,.5,ease(clamp(u*3))),1.55);FL.rotation.set(Math.PI,.5,.1)}
  rings.forEach((r,i)=>{r.visible=!!b.rg;if(b.rg){const a=((t*1.2+i/3)%1);r.position.set(-.3,.2-a*2.1,1.53);r.rotation.x=0;r.scale.setScalar(.6+a*1.6);r.material.opacity=(1-a)*.6}});
  shoot(b,u,t)},
 prodw(u,t,b){shop.visible=false;K.g.visible=false;B.g.visible=false;scene.background.set('#0d0d0f');scene.fog.near=30;scene.fog.far=80;FL.visible=true;FL.scale.setScalar(4.4);FL.position.set(0,.36,0);FL.rotation.set(.08,t*1.3,0);sun.position.set(2,4,6);sun.color.set('#ffffff');sun.intensity=4;hemi.color.set('#ffffff');hemi.intensity=2;shoot(b,u,t)},
 bathw(u,t,b){room_(t,b.water);S_.shelf.visible=!!b.shelf;K.g.position.set(0,0,.5);K.g.rotation.y=0;if(b.nk){const n=neckTarget();const[a,c,f]=b.nk;b=Object.assign({},b,{cam:[n.x+.22,n.y+.02,n.z+a,n.x+.02,n.y-.04,n.z,f],cam2:[n.x+.2,n.y+.02,n.z+c,n.x+.02,n.y-.04,n.z,f]})}shoot(b,u,t)},
 storew(u,t,b){shop.visible=false;B.g.visible=false;aisle.visible=true;skyDome.visible=true;skyDome.position.copy(cam.position);scene.fog.color.set('#e8d6b0');scene.fog.near=20;scene.fog.far=90;scene.background.set('#d9c9a4');sun.position.set(-3,10,8);sun.color.set('#fff4e0');sun.intensity=2.6;hemi.color.set('#ffffff');hemi.groundColor.set('#8a8578');hemi.intensity=2.2;K.g.position.set(-.42,0,1);K.g.rotation.y=.6;B2.g.visible=true;B2.g.position.set(.42,0,1);B2.g.rotation.y=-.6;shoot(b,u,t)},
 runw(u,t,b){shop.visible=false;B.g.visible=false;city.visible=true;skyDome.visible=true;skyDome.position.copy(cam.position);scene.fog.color.set('#d98a4a');scene.fog.near=12;scene.fog.far=75;sun.position.set(-6,7,8);sun.color.set('#ffd9a8');sun.intensity=3.4;hemi.color.set('#ffe6c8');hemi.groundColor.set('#5a4a3a');hemi.intensity=1.8;const z=-6+u*7;K.g.position.set(0,0,z);K.g.rotation.y=0;CLIP_T=t*2.1;shoot({...b,cam:[b.cam[0],b.cam[1],z+b.cam[2],b.cam[3],b.cam[4],z+b.cam[5],b.cam[6]],cam2:[b.cam2[0],b.cam2[1],z+b.cam2[2],b.cam2[3],b.cam2[4],z+b.cam2[5],b.cam2[6]]},u,t)},
 black(u,t,b){shop.visible=false;K.g.visible=false;B.g.visible=false;scene.background.set('#000000');scene.fog.near=1;scene.fog.far=2;shoot(b,u,t)},
 cast(u,t,b){shop.visible=false;B.g.visible=false;B2.g.visible=true;scene.background.set('#8d8f94');scene.fog.near=60;scene.fog.far=200;K.g.position.set(-.75,0,0);K.g.rotation.y=0;B2.g.position.set(.75,0,0);B2.g.rotation.y=0;sun.position.set(-4,6,8);sun.color.set('#ffffff');sun.intensity=2.6;hemi.color.set('#ffffff');hemi.groundColor.set('#8a8a8a');hemi.intensity=2.2;shoot(b,u,t);if(RIG.ready){open_(RIG,window.__j||0);if(RIG2.ready)open_(RIG2,window.__j||0)}},
 porch(u,t,b){world(t,b.after);seat();if(b.freeze!=null)CLIP_T=b.freeze;if(b.dreFly!=null){const q=clamp((t-b.t)/b.dreFly),s=[.17,.62,.35],e=[1.5,.05,4.2];B2.g.position.set(lerp(s[0],e[0],q),lerp(s[1],e[1],q)+Math.sin(q*Math.PI)*1.5,lerp(s[2],e[2],q));B2.g.rotation.set(-q*7.8,0,0)}
  if(b.dreDown){B2.g.position.set(1.5,.16,4.2+Math.sin(t*11)*.012);B2.g.rotation.set(-Math.PI/2+Math.sin(t*13)*.05,0,0)}
  hA.visible=hB.visible=!!b.heap;if(b.heap){const n=Math.floor(lerp(b.heap[0],b.heap[1],ease(u))*heapN);hA.count=hB.count=n}
  groundDrops(t,b);if(b.spit){}shoot(b,u,t);
  if(b.flexrise){scene.fog.near=120;scene.fog.far=320;FL.visible=true;FL.traverse(o=>{if(o.isMesh)o.frustumCulled=false});FL.scale.setScalar(260);const q=ease(clamp(u*1.3));FL.position.set(-1,lerp(-16,21,q),-40);FL.rotation.set(0,t*.2,0);beam.visible=true;beam.position.set(-2,60,-48);beam.material.opacity=.1*q}
  if(b.razorup){const q=clamp((t-b.t)/ (b.e-b.t)),r=S_.ru;r.visible=true;const hold=b.razorup;const y=t-b.t<hold?lerp(11,2.9,ease((t-b.t)/hold)):2.9+Math.pow((t-b.t-hold)*2.4,2);r.position.set(.6,y,3.6);r.rotation.set(.3,t*.4,0.2)}},
 neckw(u,t,b){shop.visible=false;B.g.visible=false;skinW.visible=true;skyDome.visible=true;skyDome.position.copy(cam.position);scene.background.set('#2a1016');scene.fog.color.set('#7a3528');scene.fog.near=12;scene.fog.far=95;sun.position.set(-8,18,8);sun.color.set('#ffb48a');sun.intensity=3;hemi.color.set('#ffb48a');hemi.groundColor.set('#7a3020');hemi.intensity=2.4;
  B2.g.visible=true;K.g.position.set(-.9,0,0);K.g.rotation.y=.25;B2.g.position.set(.9,0,.1);B2.g.rotation.y=-.3;
  giantBlade.position.set(b.bladeX?lerp(b.bladeX[0],b.bladeX[1],u):60,b.bladeY||8.6,-9);shoot(b,u,t)},
 drop(u,t,b){world(t);seat();PORCH.position.y=-ease(u)*40;YARD.position.y=-ease(u)*40;skinW.visible=u>.4;skyDome.visible=false;shoot(b,u,t)},
 bathcut(u,t,b){shop.visible=false;B.g.visible=false;K.g.visible=false;bath.visible=true;S_.shelf.visible=true;scene.background.set('#20282a');scene.fog.near=30;scene.fog.far=60;for(const d of drops)d.m.visible=false;sun.intensity=1.2;hemi.intensity=1.1;shoot(b,u,t)}
});
{const s=new THREE.Group();const cols=['#9a4a38','#4a6a82','#a88a4a','#c9c2b0','#5e7a5a','#6a5a7a','#2d5fa8','#e0559a'];seed=8;for(let i=0;i<150;i++){const m=bx(.16+rnd()*.14,.2+rnd()*.34,.14,mat(cols[i%8]));m.position.set(-2.8+(i%15)*.4+rnd()*.1,.2+Math.floor(i/15)*.5+rnd()*.05,-1.4+rnd()*.35);m.rotation.y=(rnd()-.5)*.6;m.rotation.z=(rnd()-.5)*.14;s.add(m)}for(let i=0;i<70;i++){const m=bigThing(junk[i%4][1]);m.scale.setScalar(.5);m.position.set(-2.6+rnd()*5.2,.05,-.2+rnd()*2.4);m.rotation.set(1.4+rnd(),rnd()*6,rnd());s.add(m)}S_.shelf.add(s)}
/* the after: waves and a sharp line painted into his scalp */
window.ready.then(()=>{if(!RIG.ready)return;{const c=RIG.ctx,W=c.canvas.width,H_=c.canvas.height;c.drawImage(RIG.base,0,0,W,H_);RIG.dots=RIG.dots.filter(d=>{const p=c.getImageData(d.x|0,d.y|0,1,1).data;return p[0]+p[1]+p[2]<380});RIG.dots.forEach(d=>d.r*=.55);RIG.bk=-1}let skin;RIG.root.traverse(o=>{if(o.isSkinnedMesh)skin=o});const Hb=RIG.B.Head.getWorldPosition(new THREE.Vector3()),V=new THREE.Vector3(),uv=skin.geometry.attributes.uv,W=RIG.ctx.canvas.width;RIG.waves=[];let top=-9;for(let i=0;i<uv.count;i++){skin.getVertexPosition(i,V);V.applyMatrix4(skin.matrixWorld);if(V.y>top)top=V.y}for(let i=0;i<uv.count;i++){skin.getVertexPosition(i,V);V.applyMatrix4(skin.matrixWorld);const dy=top-V.y;if(dy<.13&&Math.hypot(V.x-Hb.x,V.z-Hb.z)<.13)RIG.waves.push({x:uv.getX(i)*W,y:uv.getY(i)*W,r:dy})}});
}
