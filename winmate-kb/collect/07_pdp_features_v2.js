window.__parsePdp = (html) => {
  const d = new DOMParser().parseFromString(html,'text/html');
  d.querySelectorAll('br').forEach(b=>b.replaceWith(' '));
  const val=id=>{const e=d.getElementById(id); return e? (e.value||e.textContent||'').trim():null;};
  const meta=(n)=>{const e=d.querySelector(`meta[name="${n}"],meta[property="${n}"]`); return e?e.content:null;};
  const T = e => e ? e.textContent.replace(/\s+/g,' ').trim() : null;
  const imgOf = (root) => { const by = new Map(); const order=[];
    for (const i of root.querySelectorAll('img, source')) {
      let s = i.getAttribute('data-src') || i.getAttribute('data-srcset') || i.getAttribute('srcset') || i.getAttribute('src') || '';
      s = s.split(',')[0].trim().split(' ')[0];
      if (!s || s.startsWith('data:') || /img_baseimg_null|blank\.gif|spacer/.test(s)) continue;
      const pic = i.closest('picture'); const imgEl = i.tagName==='SOURCE' && pic ? pic.querySelector('img') : i;
      const alt = ((imgEl && imgEl.getAttribute('alt')) || '').trim();
      const media = i.getAttribute('media')||'';
      const mo = /_MO_|_MO\$|\$[A-Z_]*MO[A-Z_]*\$/.test(s) || /max-width/.test(media) || !!i.closest('.mo-ver, .mo-only');
      const key = alt ? (pic ? 'p:'+alt+'|'+[...root.querySelectorAll('picture')].indexOf(pic) : 'a:'+alt) : s;
      if (!by.has(key)) { by.set(key, {src:null, mo_src:null, alt}); order.push(key); }
      const o = by.get(key); if (mo) { o.mo_src = o.mo_src || s; } else { o.src = o.src || s; }
    }
    return order.map(k=>{const o=by.get(k); return {src:o.src||o.mo_src, mo_src:o.src?o.mo_src:null, alt:o.alt};}); };
  const vids = (root) => [...root.querySelectorAll('video source, video')].map(v=>v.getAttribute('data-src')||v.getAttribute('src')).filter(Boolean);
  let comps=[...d.querySelectorAll('.itm-component .wrap-component')]; if(!comps.length) comps=[...d.querySelectorAll('.itm-component > *')];
  const feats=[];
  for (const c0 of comps) {
    const c = c0.cloneNode(true);
    c.querySelectorAll('script,style,noscript,.mo-ver,.slider-controls,.blind').forEach(e=>e.remove());
    const type = ([...c0.classList].find(x=>x!=='wrap-component' && !/^(new-component|AATagging|pt-|pb-|w1440|img-|txt)/.test(x))) || null;
    const titles = [...c.querySelectorAll('.title, h2:not(.sub), h3:not(.sub)')].map(T).filter(x=>x && x.length>1);
    const subs = [...c.querySelectorAll('.sub')].map(T).filter(Boolean);
    const descs = [...c.querySelectorAll('.desc')].map(T).filter(Boolean);
    const discs = [...c.querySelectorAll('.disc, .disclaimer')].map(T).filter(Boolean);
    const imgs = imgOf(c0);
    const text = T(c).slice(0,2000);
    if (!text && !imgs.length) continue;
    const items = [];
    for (const s0 of c0.querySelectorAll('.visual, .swiper-slide, .slick-slide, .slide-item')) {
      const s = s0.cloneNode(true); s.querySelectorAll('script,style,.mo-ver,.blind').forEach(e=>e.remove());
      const h = T(s.querySelector('.title, h2, h3, h4, strong')); const ds = [...s.querySelectorAll('.desc')].map(T).filter(Boolean).join(' ');
      const im = imgOf(s0); if (h || ds || im.length) items.push({h, desc: ds.slice(0,400), imgs: im.slice(0,3)});
    }
    feats.push({type, h: titles[0]||subs[0]||null, h_all: [...new Set(titles)].slice(0,8), sub: subs[0]||null, desc: [...new Set(descs)].join(' ').slice(0,1500), disc: [...new Set(discs)].join(' ').slice(0,800), text, imgs, videos: vids(c0).slice(0,4), items: items.slice(0,12)});
  }
  return {title:T(d.querySelector('title')), desc:meta('description'), ogImage:meta('og:image'), ctg1:val('1depthCtgNm'), ctg2:val('2depthCtgNm'), feats, parser:'pdp_v2'};
};
window.__feat2 = {status:'running', done:0, items:{}, errors:[]};
(async()=>{ const W=window.__wkb, F=window.__feat2, sleep=ms=>new Promise(r=>setTimeout(r,ms));
  const ids=[...new Set(W.cardOrder)]; F.total=ids.length;
  for (const gid of ids) { const p=W.products[gid]; if(!p.goodsDetailUrl){F.done++; continue;}
    try { const html=await fetch('/sec/business/'+p.goodsDetailUrl).then(r=>r.text()); F.items[gid]=window.__parsePdp(html); } catch(e){ F.errors.push({gid,e:String(e)}); }
    F.done++; await sleep(250); }
  F.status='done'; F.finishedAt=new Date().toISOString(); })();
'started'