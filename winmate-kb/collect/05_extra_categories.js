window.__wkbx = {status:'running', added:[], specs:0, errors:[]};
(async()=>{
const W=window.__wkb, X=window.__wkbx, sleep=ms=>new Promise(r=>setTimeout(r,ms));
const extra=[["chromebooks/all-chromebooks","10002700","Chromebook"],["display-solution/all-display-solution","100002762","사이니지 솔루션"],["harman/all-harman","10001500","하만 프로 오디오"],["mobile-solution/all-mobile-solution","100002767","모바일 솔루션"],["printing-solution/all-printing-solution","100002689","프린팅 솔루션"],["sac-solution/all-sac-solution","100002745","시스템에어컨 솔루션"],["tv-vd-solution/all-tv-vd-solution","100002764","TV/음향 솔루션"],["xr/all-xr","100002875","갤럭시 XR"]];
const LIST=(no,f='',rows=400)=>`/sec/business/cxhr/pf/goodsList?searchFilter=${encodeURIComponent(f)}&dispClsfNo=${no}&sortType=10&page=1&rows=${rows}&ehcacheYn=Y&soldOutExceptYn=N&pfFasterUseYn=N&secApp=false&secIos=false&aiscCtgYn=N&tcPlantCode=`;
const KEEP=['goodsId','goodsNm','mdlCode','mdlNm','grpPath','goodsDetailUrl','dispClsfNo','dlgtDispClsfEnNm','compDispClsfEnNm','compDispClsfNo','uspDescList','goodsOptStr','saleStatCd','sysRegDtm','goodsTpCd','intgrSpecYn','flagStr','goodsFlagName','itdcMsg1','bspkGoodsYn','salePrice'];
const newIds=[];
for(const [p,no,title] of extra){
  try{
    const c={p,no,title,extra:true}; const j=await fetch(LIST(no)).then(r=>r.json());
    c.allFilters=j.filters||[]; c.filters=c.allFilters; c.listCount=j.count; c.count=j.count;
    W.cats.push(c);
    for(const pr of (j.products||[])){
      if(W.products[pr.goodsId]) { X.errors.push({dupe:pr.goodsId,p}); continue; }
      const o={catPath:p, catNo:no, catTitle:title}; for(const k of KEEP) o[k]=pr[k];
      o.images=[]; for(let i=1;i<=8;i++){ if(pr['imgPath'+i]) o.images.push({src:pr['imgPath'+i], alt:pr['imgContent'+i]||null}); }
      W.products[pr.goodsId]=o; W.cardOrder.push(pr.goodsId); X.added.push(pr.goodsId); newIds.push(pr.goodsId);
      for(const line of (pr.goodsOptStr||'').split('\n')){ const f=line.split('|'); if(f.length>9 && f[9]) { W.variants[f[9]]={goodsId:f[9], mdlCode:f[8], parentGoodsId:pr.goodsId, optName:f[4], optValue:f[5], optValue2:f[6], soldOut:f[7]}; newIds.push(f[9]); } }
    }
    W.filters[no]={};
    for(const f of (j.filters||[])){ try{ const k=await fetch(LIST(no,f)).then(r=>r.json()); W.filters[no][f]=(k.products||[]).map(x=>x.goodsId);}catch(e){X.errors.push({stage:'filter',no,f,e:String(e)});} await sleep(150); }
  }catch(e){X.errors.push({stage:'list',p,e:String(e)});}
  await sleep(200);
}
X.phase='specs';
for(const gid of [...new Set(newIds)]){
  if(W.specs[gid]) continue;
  try{
    const tp=(W.products[gid]&&W.products[gid].goodsTpCd)||(W.products[(W.variants[gid]||{}).parentGoodsId]||{}).goodsTpCd||'10';
    const html=await fetch('/sec/business/xhr/goods/getGoodsSpecList',{method:'POST',body:new URLSearchParams({goodsId:gid,goodsTpCd:tp}),headers:{'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8','X-Requested-With':'XMLHttpRequest'}}).then(r=>r.text());
    const d=new DOMParser().parseFromString(html,'text/html'); const rows=[];
    for(const dl of d.querySelectorAll('dl')){ let g=null; for(const ch of dl.children){ if(ch.tagName==='DT') g=ch.textContent.trim(); else if(ch.tagName==='DD'){ for(const li of ch.querySelectorAll('li')){ const t=li.querySelector('.spec-title'); const v=li.querySelector('.spec-desc'); if(t) rows.push([g, t.textContent.replace(/\s+/g,' ').trim(), v? v.textContent.replace(/ /g,' ').replace(/\s+/g,' ').trim(): null]); } } } }
    W.specs[gid]=rows; X.specs++;
  }catch(e){X.errors.push({stage:'spec',gid,e:String(e)});}
  await sleep(300);
}
X.status='done';
})();
'started'