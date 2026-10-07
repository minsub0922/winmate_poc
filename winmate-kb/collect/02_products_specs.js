window.__wkb = {status:'running', phase:'lists', startedAt:new Date().toISOString(), cats:(window.__cats||[]).filter(c=>c.no), products:{}, cardOrder:[], filters:{}, variants:{}, specs:{}, features:{}, errors:[], n:{lists:0,filters:0,specs:0,features:0}};
(async()=>{
const W=window.__wkb, sleep=ms=>new Promise(r=>setTimeout(r,ms));
const LIST=(no,f='',rows=400)=>`/sec/business/cxhr/pf/goodsList?searchFilter=${encodeURIComponent(f)}&dispClsfNo=${no}&sortType=10&page=1&rows=${rows}&ehcacheYn=Y&soldOutExceptYn=N&pfFasterUseYn=N&secApp=false&secIos=false&aiscCtgYn=N&tcPlantCode=`;
const KEEP=['goodsId','goodsNm','mdlCode','mdlNm','grpPath','goodsDetailUrl','dispClsfNo','dlgtDispClsfEnNm','compDispClsfEnNm','compDispClsfNo','uspDescList','goodsOptStr','saleStatCd','sysRegDtm','goodsTpCd','intgrSpecYn','flagStr','goodsFlagName','itdcMsg1','bspkGoodsYn','salePrice'];
try{
for(const c of W.cats){
  try{
    const j=await fetch(LIST(c.no)).then(r=>r.json());
    c.allFilters=j.filters||[]; c.listCount=j.count;
    for(const p of (j.products||[])){
      const o={catPath:c.p, catNo:c.no, catTitle:c.title};
      for(const k of KEEP) o[k]=p[k];
      o.images=[]; for(let i=1;i<=8;i++){ if(p['imgPath'+i]) o.images.push({src:p['imgPath'+i], alt:p['imgContent'+i]||null}); }
      W.products[p.goodsId]=o; W.cardOrder.push(p.goodsId);
      for(const line of (p.goodsOptStr||'').split('\n')){ const f=line.split('|'); if(f.length>9 && f[9]) { W.variants[f[9]]={goodsId:f[9], mdlCode:f[8], parentGoodsId:p.goodsId, optName:f[4], optValue:f[5], optValue2:f[6], soldOut:f[7]}; } }
    }
    W.n.lists++;
    W.filters[c.no]={};
    for(const f of (j.filters||[])){
      try{ const k=await fetch(LIST(c.no,f)).then(r=>r.json()); W.filters[c.no][f]=(k.products||[]).map(x=>x.goodsId); W.n.filters++; }catch(e){W.errors.push({stage:'filter',c:c.no,f,e:String(e)});}
      await sleep(150);
    }
  }catch(e){W.errors.push({stage:'list',c:c.no,e:String(e)});}
  await sleep(200);
}
W.phase='specs';
const ids=[...new Set([...Object.keys(W.products), ...Object.keys(W.variants)])];
W.specTargets=ids.length;
for(const gid of ids){
  try{
    const tp=(W.products[gid]&&W.products[gid].goodsTpCd)||(W.products[(W.variants[gid]||{}).parentGoodsId]||{}).goodsTpCd||'10';
    const html=await fetch('/sec/business/xhr/goods/getGoodsSpecList',{method:'POST',body:new URLSearchParams({goodsId:gid,goodsTpCd:tp}),headers:{'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8','X-Requested-With':'XMLHttpRequest'}}).then(r=>r.text());
    const d=new DOMParser().parseFromString(html,'text/html'); const rows=[];
    for(const dl of d.querySelectorAll('dl')){ let g=null; for(const ch of dl.children){ if(ch.tagName==='DT') g=ch.textContent.trim(); else if(ch.tagName==='DD'){ for(const li of ch.querySelectorAll('li')){ const t=li.querySelector('.spec-title'); const v=li.querySelector('.spec-desc'); if(t) rows.push([g, t.textContent.replace(/\s+/g,' ').trim(), v? v.textContent.replace(/ /g,' ').replace(/\s+/g,' ').trim(): null]); } } } }
    W.specs[gid]=rows; W.n.specs++;
  }catch(e){W.errors.push({stage:'spec',gid,e:String(e)});}
  await sleep(250);
}
W.phase='features';
for(const gid of W.cardOrder){
  const p=W.products[gid]; if(!p.goodsDetailUrl) continue;
  try{
    const html=await fetch('/sec/business/'+p.goodsDetailUrl).then(r=>r.text());
    const d=new DOMParser().parseFromString(html,'text/html');
    const val=id=>{const e=d.getElementById(id); return e? (e.value||e.textContent||'').trim():null;};
    const meta=(n)=>{const e=d.querySelector(`meta[name="${n}"],meta[property="${n}"]`); return e?e.content:null;};
    let blocks=[...d.querySelectorAll('.itm-component .wrap-component')]; if(!blocks.length) blocks=[...d.querySelectorAll('.itm-component > *')];
    const feats=blocks.map(b=>{
      const h=b.querySelector('h2,h3,h4,.title,strong'); 
      const imgs=[...b.querySelectorAll('img,source')].map(i=>({src:i.getAttribute('src')||i.getAttribute('data-src')||i.getAttribute('srcset')||i.getAttribute('data-srcset'), alt:i.getAttribute('alt')})).filter(x=>x.src && !x.src.startsWith('data:'));
      return {h: h? h.textContent.replace(/\s+/g,' ').trim():null, text: b.textContent.replace(/\s+/g,' ').trim().slice(0,1500), imgs};
    }).filter(f=>f.text||f.imgs.length);
    W.features[gid]={title:(d.querySelector('title')||{}).textContent, desc:meta('description'), ogImage:meta('og:image'), ctg1:val('1depthCtgNm'), ctg2:val('2depthCtgNm'), feats};
    W.n.features++;
  }catch(e){W.errors.push({stage:'feature',gid,e:String(e)});}
  await sleep(400);
}
W.phase='done'; W.status='done'; W.finishedAt=new Date().toISOString();
}catch(e){W.status='error'; W.fatal=String(e);}
})();
'started'