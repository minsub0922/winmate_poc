const paths = ["dvms/all-dvms","cooling-single/all-cooling-single","cooling-for-residential/all-cooling-for-residential","heat-pump-boilers/all-heat-pump-boilers","ventilations/all-ventilations","central-air-conditionings/all-central-air-conditionings","Cold_Chain_System/all-Cold_Chain_System","refrigerator/all-refrigerator","kimchi-refrigerators/all-kimchi-refrigerators","dish-washer/all-dish-washer","electric-range/all-electric-range","micro-wave-ovens/all-micro-wave-ovens","qooker/all-qooker","water-purifier/all-water-purifier","hood/all-hood","accessories/all-accessories","washing-machines/all-washing-machines","dryers/all-dryers","airdresser/all-airdresser","shoedresser/all-shoedresser","air-conditioners/all-air-conditioners","air-cleaners/all-air-cleaners","vacuum-cleaners/all-vacuum-cleaners","led-lights/all-led-lights","smart-signage/all-smart-signage","led-signage/all-led-signage","hotel-tvs/all-hotel-tvs","tvs/all-tvs","smartphones/all-smartphones","tablets/all-tablets","watches/all-watches","buds/all-buds","rings/all-rings","mobile-accessories/all-mobile-accessories","digital-multifunction-printers/all-digital-multifunction-printers","general-multifunction-printers/all-general-multifunction-printers","multifunction-printers-supplies/all-multifunction-printers-supplies","notebook/all-notebook","desktop/all-desktop","monitors/all-monitors","printing-solutions/all-printing-solutions","ac-clean/all-ac-clean","air-conditioners-care-service/all-air-conditioners-care-service"];
window.__cats = [];
for (const p of paths) {
  try {
    const h = await fetch('/sec/business/'+p+'/').then(r=>r.ok? r.text(): '');
    const m = h.match(/dispClsfNo["'\s:=]+["']?(\d{6,})/);
    const t = (h.match(/<title>([^<]*)<\/title>/)||[])[1]||'';
    let count=null, filters=null;
    if (m) { const j = await fetch(`/sec/business/cxhr/pf/goodsList?searchFilter=&dispClsfNo=${m[1]}&sortType=10&page=1&rows=1&ehcacheYn=Y&soldOutExceptYn=N&pfFasterUseYn=N&secApp=false&secIos=false&aiscCtgYn=N&tcPlantCode=`).then(r=>r.json()).catch(e=>null); count = j&&j.count; filters = j&&j.filters; }
    window.__cats.push({p, no: m&&m[1], title: t.split('|')[0].trim(), count, filters});
  } catch(e) { window.__cats.push({p, err:String(e)}); }
}
window.__cats.map(c=>`${c.p}\t${c.no}\t${c.count}\t${c.title}`).join('\n') + '\nTOTAL ' + window.__cats.reduce((a,c)=>a+(c.count||0),0)