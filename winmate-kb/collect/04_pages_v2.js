window.__runPages2 = async function(){
window.__pages2={status:'running', done:0, total:window.__pagesQueue.length, items:{}, errors:[]};
const P=window.__pages2, sleep=ms=>new Promise(r=>setTimeout(r,ms));
const SKIP=/^(SCRIPT|STYLE|NOSCRIPT|SVG|HEADER|FOOTER|NAV|IFRAME|TEMPLATE|BUTTON|SELECT|OPTION|FORM)$/;
const SKIPCLS=/(gnb|footer|popup|layer-pop|layerpop|breadcrumb|skip|header-|cookie|sns|share|quick-menu|floating|latest-item|login|lnb)/i;
const BLOCK=/^(P|DIV|LI|DD|DT|TD|TH|SECTION|ARTICLE|FIGCAPTION|BLOCKQUOTE|H1|H2|H3|H4|H5|H6|UL|OL|DL|TABLE|TR|FIGURE|ASIDE|MAIN)$/;
const imgAttrs=['src','data-src','data-desktop-src','data-pc-src','data-lazy','data-original','data-srcset','srcset','data-mobile-src','data-mo-src'];
const abs=u=>{ if(!u) return u; u=u.trim().split(/\s+/)[0]; if(u.startsWith('//')) return 'https:'+u; if(u.startsWith('/')) return 'https://www.samsung.com'+u; return u; };
function lin(root){
  const out=[]; const seenImg=new Set(); let buf='', bufEl=null, last='';
  const flush=()=>{ const t=buf.replace(/\s+/g,' ').trim(); if(t && t!==last){ out.push({t:'p',x:t}); last=t;} buf=''; bufEl=null; };
  const walk=(el)=>{
    for(const n of el.childNodes){
      if(n.nodeType===3){ const tx=n.textContent; if(tx.trim()){ let b=n.parentElement; while(b && !BLOCK.test(b.tagName)) b=b.parentElement; if(b!==bufEl){ flush(); bufEl=b;} buf+=' '+tx; } continue; }
      if(n.nodeType!==1) continue;
      const tag=n.tagName; const cls=(n.className&&n.className.baseVal!==undefined)? n.className.baseVal : (n.className||'');
      if(SKIP.test(tag) || SKIPCLS.test(cls) || SKIPCLS.test(n.id||'')) continue;
      if(/^H[1-6]$/.test(tag)){ flush(); const t=n.textContent.replace(/\s+/g,' ').trim(); if(t){ out.push({t:'h',l:+tag[1],x:t}); last=t;} continue; }
      if(tag==='IMG' || tag==='SOURCE'){ let s=null; for(const a of imgAttrs){ const v=n.getAttribute(a); if(v && !v.startsWith('data:')){ s=abs(v); break; } } if(s && !seenImg.has(s)){ seenImg.add(s); flush(); out.push({t:'img',src:s,alt:n.getAttribute('alt')||null}); } continue; }
      if(tag==='A'){ const h=n.getAttribute('href'); if(h && !h.startsWith('javascript') && !h.startsWith('#')){ flush(); out.push({t:'a',href:abs(h),x:n.textContent.replace(/\s+/g,' ').trim().slice(0,200)}); } }
      const st=n.getAttribute && n.getAttribute('style'); if(st && /background(-image)?\s*:[^;]*url\(/.test(st)){ const m=st.match(/url\(['"]?([^'")]+)/); if(m){ const s=abs(m[1]); if(!seenImg.has(s)){ seenImg.add(s); flush(); out.push({t:'img',src:s,alt:null,bg:true}); } } }
      if(BLOCK.test(tag)) flush();
      walk(n);
      if(BLOCK.test(tag)) flush();
    }
  };
  walk(root); flush();
  return out.slice(0,3000);
}
for(const q of window.__pagesQueue){
  try{
    const r=await fetch(q.u); const html=await r.text();
    const d=new DOMParser().parseFromString(html,'text/html');
    const meta=n=>{const e=d.querySelector(`meta[name="${n}"],meta[property="${n}"]`); return e?e.content:null;};
    const root=d.getElementById('content')||d.getElementById('container')||d.querySelector('main')||d.body;
    P.items[q.u]={kind:q.kind, url:'https://www.samsung.com'+q.u, status:r.status, title:(d.querySelector('title')||{}).textContent||null, desc:meta('description'), ogImage:meta('og:image'), ogTitle:meta('og:title'), pubDate:meta('article:published_time')||null, fetchedAt:new Date().toISOString(), rootId:root.id||root.tagName, blocks:lin(root)};
  }catch(e){ P.errors.push({u:q.u,e:String(e)}); }
  P.done++; await sleep(500);
}
P.status='done';
};
(async()=>{ while(window.__pages.status!=='done') await new Promise(r=>setTimeout(r,3000)); window.__runPages2(); })();
({p1:window.__pages.done, total:window.__pages.total})