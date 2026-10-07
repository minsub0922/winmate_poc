window.__fmeta = {status:'running', meta:{}, tabs:{}, members:{}, errors:[]};
(async()=>{
const M=window.__fmeta, W=window.__wkb, sleep=ms=>new Promise(r=>setTimeout(r,ms));
const LIST=(no,rows=400)=>`/sec/business/cxhr/pf/goodsList?searchFilter=&dispClsfNo=${no}&sortType=10&page=1&rows=${rows}&ehcacheYn=Y&soldOutExceptYn=N&pfFasterUseYn=N&secApp=false&secIos=false&aiscCtgYn=N&tcPlantCode=`;
for (const c of W.cats) {
  try {
    const h = await fetch('/sec/business/'+c.p+'/').then(r=>r.text());
    const d = new DOMParser().parseFromString(h,'text/html');
    const m = {};
    for (const i of d.querySelectorAll('input[data-search-filter]')) m[i.getAttribute('data-search-filter')] = {group:i.getAttribute('data-filter-nm'), label:(i.getAttribute('data-filter-item-nm')||'').trim(), min:i.getAttribute('data-min-val')||null, max:i.getAttribute('data-max-val')||null};
    M.meta[c.no]=m;
    M.tabs[c.no]=[...d.querySelectorAll('a[onclick*="/?"]')].map(a=>{const mm=(a.getAttribute('onclick')||'').match(/\/sec\/business\/([^'"?]+)\/\?([^'"]+)/); return mm? [mm[1], mm[2], a.textContent.trim()]:null;}).filter(Boolean);
    const j = await fetch(LIST(c.no)).then(r=>r.json());
    M.members[c.no]=(j.products||[]).map(p=>p.goodsId);
  } catch(e) { M.errors.push({c:c.no, e:String(e)}); }
  await sleep(300);
}
M.status='done';
})();
'started'