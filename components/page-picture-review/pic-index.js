/* Picture index overlay for a numbered page demo.
   Numbers every picture slot and colours it by the decision recorded in pic-state.json.
   Numbers come from slots.json (filename -> number), NOT from DOM position, so they
   survive edits to the page. A file the index does not know gets "?" and a console warning. */
(function(){
  const LAYER=document.createElement('div');
  LAYER.id='pic-index-layer';
  LAYER.style.cssText='position:absolute;top:0;left:0;width:0;height:0;z-index:99998;pointer-events:none';
  document.body.appendChild(LAYER);
  const BADGES=document.createElement('div'), NOTES=document.createElement('div');
  [BADGES,NOTES].forEach(l=>{l.style.cssText='position:absolute;top:0;left:0';LAYER.appendChild(l);});

  /* Colour answers ONE question: does this slot need a person? Green means no.
     Ruled by email_lead 2026-09-23, see the page's PROPOSAL-slot-states.md. `keep`
     and `updated` shared one green until then, so a slot nobody had judged
     looked exactly like a slot that was right.
     The two greens are not the same green, on her second look: `accepted` is
     the confident one because somebody signed it, `keep` is muted because it
     only ever meant "inherited, and nothing about this page makes it wrong". */
  const STYLES={
    undecided:{bg:'#ffd600',fg:'#111',ring:'rgba(255,214,0,.95)',label:''},
    replace  :{bg:'#e53935',fg:'#fff',ring:'rgba(229,57,53,.95)',label:' · replace'},
    redo     :{bg:'#e8730c',fg:'#fff',ring:'rgba(232,115,12,.95)',label:' · redo'},
    updated  :{bg:'#55606b',fg:'#fff',ring:'rgba(85,96,107,.95)',label:' · updated'},
    keep     :{bg:'#6b8f71',fg:'#fff',ring:'rgba(107,143,113,.95)',label:' · keep'},
    accepted :{bg:'#2e7d32',fg:'#fff',ring:'rgba(46,125,50,.95)',label:' · accepted ✓'}
  };

  function collect(root){
    const out=[];
    root.querySelectorAll('img, video[poster], [style*="url("]').forEach(el=>{
      if(el.tagName==='VIDEO') out.push({el,src:base(el.getAttribute('poster'))});
      else if(el.tagName==='IMG') out.push({el,src:base(el.currentSrc||el.src)});
      else{
        const m=/url\((['"]?)([^'")]+)\1\)/.exec(el.getAttribute('style')||'');
        // base() drops any ?cache-buster before the extension is tested
        if(m){ const f=base(m[2]); if(/\.(jpg|jpeg|png|webp|svg|gif)$/i.test(f)) out.push({el,src:f}); }
      }
    });
    return out;
  }
  const base=s=>(s||'').split('/').pop().split('?')[0];

  let boxes=[];
  function build(slots){
    const byFile={D:{},M:{}};
    Object.entries(slots).forEach(([n,s])=>{
      (byFile.D[s.desktop]=byFile.D[s.desktop]||[]).push(+n);
      (byFile.M[s.mobile] =byFile.M[s.mobile] ||[]).push(+n);
    });
    Object.values(byFile).forEach(m=>Object.values(m).forEach(a=>a.sort((x,y)=>x-y)));
    const used={D:{},M:{}};
    const items=[];
    [['D','.pas-bp-desktop'],['M','.pas-bp-mobile']].forEach(([p,sel])=>{
      const root=document.querySelector(sel); if(!root) return;
      collect(root).forEach(t=>{
        /* An <img> with a srcset resolves currentSrc to whichever variant the
           browser picked — `carousel-1-800.jpg` for an 85px thumbnail at DPR 2,
           the base file for the 610px slide. Only the base file is in slots.json,
           so a variant used to fall through to "?" depending on viewport, DPR and
           whether a lazy image had loaded yet. Strip a trailing -<width> and try
           again before giving up. */
        let list=byFile[p][t.src]||[];
        if(!list.length){
          const stem=t.src.replace(/-\d+(\.[a-z0-9]+)$/i,'$1');
          if(stem!==t.src && byFile[p][stem]){ t.src=stem; list=byFile[p][stem]; }
        }
        const k=used[p][t.src]=(used[p][t.src]||0);
        const n=list[k]; used[p][t.src]=k+1;
        if(n===undefined) console.warn('picture index: no slot for '+p+' '+t.src);
        items.push({id:p+(n===undefined?'?':n), n:n===undefined?null:String(n), ...t});
      });
    });
    window.PIC_INDEX=items.map(x=>({id:x.id,file:x.src}));
    boxes=items.map(it=>{
      const b=document.createElement('div');
      b.style.cssText='position:absolute;outline:2px dashed;outline-offset:-2px;display:none';
      const tag=document.createElement('span');
      tag.style.cssText='position:absolute;top:0;left:0;border:2px solid #111;font:700 13px/1.1 ui-monospace,Menlo,monospace;'+
        'padding:3px 7px;border-radius:0 0 6px 0;box-shadow:0 2px 6px rgba(0,0,0,.45);white-space:nowrap';
      b.appendChild(tag); BADGES.appendChild(b);
      return {b,it};
    });
  }

  function place(){
    const sx=window.scrollX, sy=window.scrollY;
    boxes.forEach(({b,it})=>{
      const r=it.el.getBoundingClientRect();
      if(!r.width||!r.height){ b.style.display='none'; return; }
      b.style.display='block';
      b.style.left=(r.left+sx)+'px'; b.style.top=(r.top+sy)+'px';
      b.style.width=r.width+'px'; b.style.height=r.height+'px';
    });
  }
  /* The baked state file is the BASELINE. An override map may sit on top of it,
     set by whatever is layered over this engine (pic-marks.js writes the ones a
     reviewer makes on the page). Keeping them apart means the 2s re-read of
     pic-state.json cannot wipe a decision made in the browser. */
  let baseState={}, overrides={};
  function paintAll(){ paint(Object.assign({}, baseState, overrides)); }

  function paint(state){
    let decided=0;
    boxes.forEach(({b,it})=>{
      // a decision can be recorded for the slot ("12") or for one tree ("D12"),
      // which is what the split slots need — #1 and #12-#23 are different pictures
      const val=state[it.id]||state[it.n];
      const st=STYLES[val]||STYLES.undecided;
      if(val) decided++;
      b.style.outlineColor=st.ring;
      const tag=b.firstChild;
      tag.textContent=it.id+st.label;
      tag.style.background=st.bg; tag.style.color=st.fg;
    });
    const c=document.getElementById('pic-count');
    if(c){
      const slots=new Set(boxes.filter(({it})=>state[it.id]||state[it.n]).map(({it})=>it.n));
      c.textContent=slots.size+' of '+Object.keys(window.PIC_SLOTS||{}).length+' decided';
    }
  }
  // ---- notes: review comments pinned to a slot, or to a region inside it ----
  const NOTE={fix:{c:'#e53935',t:'FIX'},ok:{c:'#2e7d32',t:'GOOD'},spec:{c:'#1565c0',t:'SPEC'},
              hold:{c:'#b26a00',t:'HOLD'}};
  let noteEls=[], baseNotes={}, liveNotes={};

  /* Notes come from two places: the state folder's notes.json, baked in when the
     demo is built, and whatever a layer over this engine adds at run time (a
     reason typed on the page). Same drawing, same collapse, merged per slot. */
  function allNotes(){
    const out={};
    [baseNotes, liveNotes].forEach(src=>Object.entries(src||{}).forEach(([k,v])=>{
      out[k]=(out[k]||[]).concat(v||[]);
    }));
    return out;
  }
  function rebuildNotes(){
    while(NOTES.firstChild) NOTES.removeChild(NOTES.firstChild);
    buildNotes(allNotes()); placeNotes();
  }

  /* A note starts COLLAPSED: one chip with its kind and its slot, so the picture
     underneath can be judged. Click the chip and the reason opens; click again
     and it closes. The `notes` button still hides every note outright — that is
     a different thing from collapsing them, and both are worth having. */
  function noteCard(style, label, n){
    const card=document.createElement('div');
    const head=document.createElement('div');
    head.style.cssText='font:700 11px/1.3 ui-monospace,Menlo,monospace;color:'+style.c+
      ';letter-spacing:.06em;display:flex;gap:8px;align-items:center;white-space:nowrap';
    const chev=document.createElement('span');
    chev.textContent='+'; chev.style.cssText='color:#8a8a8a;font-size:13px;line-height:1';
    head.appendChild(document.createTextNode(style.t+' \u00b7 '+label)); head.appendChild(chev);
    const body=document.createElement('div');
    body.style.cssText='display:none;margin-top:6px';
    body.innerHTML='<div style="font-weight:600;margin-bottom:5px">'+n.title+'</div>'+
                   '<div>'+n.body+'</div>';
    card.appendChild(head); card.appendChild(body);
    const shut='width:auto;';
    const open='width:330px;';
    const skin='background:rgba(17,17,17,.94);color:#fff;cursor:pointer;'+
      'font:400 12.5px/1.5 system-ui,-apple-system,sans-serif;padding:8px 11px;border-radius:8px;'+
      'border-left:5px solid '+style.c+';box-shadow:0 6px 20px rgba(0,0,0,.45);pointer-events:auto;';
    card.dataset.open='0';
    card.setAttribute('role','button'); card.setAttribute('tabindex','0');
    /* Only width and the body toggle here. placeNotes owns left/top and runs on a
       1.2s tick, so rewriting cssText would throw the card back to its origin
       until the next tick and make every expand visibly jump. */
    let base=false;
    const paint=()=>{
      if(!base){ card.style.cssText=card.dataset.pos+skin+shut; base=true; }
      const isOpen=card.dataset.open==='1';
      body.style.display=isOpen?'block':'none';
      chev.textContent=isOpen?'\u2212':'+';
      card.style.width=isOpen?open.slice(6,-1):shut.slice(6,-1);
    };
    const toggle=e=>{ e.stopPropagation(); card.dataset.open=card.dataset.open==='1'?'0':'1'; paint(); };
    card.addEventListener('click',toggle);
    card.addEventListener('keydown',e=>{ if(e.key==='Enter'||e.key===' ') toggle(e); });
    card._paint=paint;
    return card;
  }

  function buildNotes(notes){
    noteEls=[];
    /* `_page` is a note about the page, not about a slot: one chip fixed under the
       top bar instead of sixteen identical ones pinned to sixteen pictures. It
       lives in the NOTES layer, so the `notes` toggle hides it with the rest. */
    (notes && notes._page || []).forEach(n=>{
      const style=NOTE[n.kind]||NOTE.spec;
      const card=noteCard(style,'THIS PAGE',n);
      card.dataset.pos='position:fixed;z-index:99997;top:40px;left:12px;';
      card._paint();
      NOTES.appendChild(card);
    });
    Object.entries(notes||{}).forEach(([id,list])=>{
      if(id==='_page') return;
      const item=boxes.find(({it})=>it.id===id);
      if(!item) return;
      list.forEach((n,i)=>{
        const style=NOTE[n.kind]||NOTE.spec;
        const box=document.createElement('div');
        box.style.cssText='position:absolute;pointer-events:none;'+
          (n.rect?`border:3px solid ${style.c};box-shadow:0 0 0 2px rgba(0,0,0,.35) inset;`:'');
        const card=noteCard(style,id,n);
        card.dataset.pos='position:absolute;';
        card._paint();
        NOTES.appendChild(box); NOTES.appendChild(card);
        noteEls.push({box,card,it:item.it,n,i});
      });
    });
  }
  function placeNotes(){
    const sx=window.scrollX, sy=window.scrollY;
    noteEls.forEach(({box,card,it,n,i})=>{
      const r=it.el.getBoundingClientRect();
      if(!r.width||!r.height){ box.style.display='none'; card.style.display='none'; return; }
      box.style.display='block'; card.style.display='block';
      let x=r.left+sx, y=r.top+sy, w=r.width, h=r.height;
      if(n.rect){ x+=n.rect[0]*r.width; y+=n.rect[1]*r.height; w=n.rect[2]*r.width; h=n.rect[3]*r.height; }
      box.style.left=x+'px'; box.style.top=y+'px'; box.style.width=w+'px'; box.style.height=h+'px';
      let cx, cy;
      if(n.rect){                       // beside the region it marks, flipped if it would run off
        cx=x+w+14; cy=y;
        if(cx+330>document.documentElement.scrollWidth-10) cx=Math.max(10,x-344);
      }else{                            // slot-wide note: inside the slot's right edge, stacked
        cx=Math.max(10, r.left+sx+r.width-344);
        cy=r.top+sy+14+i*104;
      }
      card.style.left=cx+'px'; card.style.top=cy+'px';
    });
  }

  // ---- show/hide, so the picture can be judged without anything on top of it ----
  const PREF={badges:true,notes:true};
  function load(k){ try{ const v=localStorage.getItem('picIndex.'+k); return v===null?true:v==='1'; }catch(e){ return true; } }
  function save(k,v){ try{ localStorage.setItem('picIndex.'+k, v?'1':'0'); }catch(e){} }
  function apply(){
    BADGES.style.display=PREF.badges?'block':'none';
    NOTES.style.display=PREF.notes?'block':'none';
    [['badges',bBtn],['notes',nBtn]].forEach(([k,btn])=>{
      if(!btn) return;
      btn.style.background=PREF[k]?'#ffd600':'transparent';
      btn.style.color=PREF[k]?'#111':'#9a9a9a';
      btn.style.borderColor=PREF[k]?'#ffd600':'#555';
    });
  }
  function set(k,v){ PREF[k]=v; save(k,v); apply(); }
  let bBtn,nBtn;
  function controls(){
    const host=document.getElementById('pic-count');
    if(!host) return;
    const wrap=document.createElement('span');
    wrap.style.cssText='margin-left:14px;display:inline-flex;gap:6px;vertical-align:middle';
    const mk=(label,key)=>{
      const b=document.createElement('button');
      b.textContent=label;
      b.style.cssText='font:600 11px/1 system-ui;padding:4px 9px;border-radius:12px;border:1px solid;'+
        'cursor:pointer;background:transparent';
      b.onclick=()=>set(key,!PREF[key]);
      wrap.appendChild(b); return b;
    };
    bBtn=mk('numbers','badges'); nBtn=mk('notes','notes');
    const hint=document.createElement('span');
    hint.textContent='(press A)';
    hint.style.cssText='font:400 11px/1 system-ui;color:#8a8a8a;align-self:center';
    wrap.appendChild(hint);
    host.parentNode.appendChild(wrap);
    PREF.badges=load('badges'); PREF.notes=load('notes'); apply();
  }
  document.addEventListener('keydown',e=>{
    if(e.key!=='a'&&e.key!=='A') return;
    if(/^(INPUT|TEXTAREA)$/.test((e.target||{}).tagName)) return;
    const on=PREF.badges||PREF.notes;          // A hides everything, then brings it all back
    set('badges',!on); set('notes',!on);
  });

  const get=u=>fetch(u+'?ts='+Date.now()).then(r=>r.json());
  const served=/^https?:$/.test(location.protocol);

  function start(slots,state,notes){
    window.PIC_SLOTS=slots; build(slots); place(); baseState=state||{}; paintAll();
    baseNotes=notes||window.PIC_NOTES_INLINE||{}; buildNotes(allNotes()); placeNotes(); controls();
    setInterval(()=>{place();placeNotes();},1200);
    window.addEventListener('load',()=>{place();placeNotes();});
    window.addEventListener('resize',()=>{place();placeNotes();});
    if(served){                       // live updates only when a server is serving the files
      const tick=()=>get('pic-state.json').then(st=>{baseState=st;paintAll();}).catch(()=>{});
      setInterval(tick,2000);
    }
    window.PIC_INDEX_API={
      badges:()=>boxes.map(({b,it})=>({id:it.id,n:it.n,box:b,tag:b.firstChild})),
      setOverrides(m){ overrides=m||{}; paintAll(); },
      setLiveNotes(m){ liveNotes=m||{}; rebuildNotes(); },
      state(){ return Object.assign({}, baseState, overrides); },
      styles:STYLES
    };
    document.dispatchEvent(new CustomEvent('pic-index:ready'));
    console.log('picture index: '+boxes.length+' badges over '+Object.keys(slots).length+
                ' slots'+(served?'':' (opened from a file — decisions are frozen at build time)'));
  }

  function fail(why){
    const b=document.createElement('div');
    b.style.cssText='position:fixed;z-index:100001;top:0;left:0;right:0;background:#e53935;color:#fff;'+
      'font:600 13px/1.5 system-ui;padding:8px 12px;text-align:center';
    b.textContent='Picture index did not load ('+why+') — no numbers on this page. '+
      'Rebuild it with make_demo.py, or serve the folder over http.';
    document.body.appendChild(b);
    console.error('picture index failed: '+why);
  }

  // inline data first (works when the file is opened directly), fetch as the fallback
  if(window.PIC_SLOTS_INLINE) start(window.PIC_SLOTS_INLINE, window.PIC_STATE_INLINE||{}, window.PIC_NOTES_INLINE||{});
  else if(served) get('slots.json').then(s=>get('pic-state.json').catch(()=>({})).then(st=>start(s,st)))
                  .catch(e=>fail('slots.json could not be read: '+e.message));
  else fail('this page has no inline slot data and fetch is blocked on file:// URLs');
})();
