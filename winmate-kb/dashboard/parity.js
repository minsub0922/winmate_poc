// 브라우저 엔진(engine.js) ↔ Python(query.py) 결과 비교. node dashboard/parity.js
const fs = require('fs');
const zlib = require('zlib');
const path = require('path');
const { KB, Lsa, parseVec } = require('./src/engine.js');

const D = path.join(__dirname, 'build', 'data');
const J = (n) => JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(D, n + '.json.gz'))).toString('utf8'));
const B = (n) => { const b = fs.readFileSync(path.join(D, n)); return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength); };

const t0 = Date.now();
const kb = new KB(J('core'), J('graph'));
kb.attachSearch(J('search'));
kb.attachImages(J('images'));
const VR = J('vec_refs');
kb.attachVectors(new Lsa(J('lsa_vocab'), B('lsa.bin')), null);
kb.attachMsgs(J('msgs'));
for (const [f, spaces] of Object.entries(VR.files)) kb.attachVectors(null, parseVec(B(f), VR, spaces));
console.log('load', Date.now() - t0, 'ms');
const G = JSON.parse(fs.readFileSync(path.join(__dirname, 'build', 'golden.json'), 'utf8'));

const overlap = (a, b, k) => { const A = new Set(a.slice(0, k)), Bs = b.slice(0, k); return Bs.length ? Bs.filter((x) => A.has(x)).length / Math.max(A.size, Bs.length) : (A.size ? 0 : 1); };
const rep = { S1: [], search: [], image_search: [], A2: [], E3: [] };
let t = Date.now();
for (const g of G.S1) {
  const r = kb.S1(g.q);
  const jsV = r.result.vertical.map((v) => [v.id, v.score]);
  const vOk = JSON.stringify(jsV) === JSON.stringify(g.vertical);
  const sp = (x) => x.map((p) => p.space).join(',');
  const spOk = sp(r.result.by_space) === sp(g.by_space);
  let famTop1 = 0, famTop3 = 0, famExact = 0, n = 0, capsOk = true, solOk = true;
  g.by_space.forEach((p, i) => {
    const q = r.result.by_space[i];
    if (!q) return;
    n++;
    const a = p.fams.map((x) => x[0]), b = q.families.map((x) => x.id);
    famTop1 += a[0] === b[0] ? 1 : 0;
    famTop3 += overlap(a, b, 3);
    famExact += JSON.stringify(p.fams) === JSON.stringify(q.families.map((f) => [f.id, f.score])) ? 1 : 0;
    if (JSON.stringify([p.hard, p.soft, p.category]) !== JSON.stringify([q.capabilities.hard, q.capabilities.soft, q.category])) capsOk = false;
    if (JSON.stringify(p.sols) !== JSON.stringify(q.solutions.map((s) => s.id))) solOk = false;
  });
  const cases = overlap(g.cases.map((x) => x[0]), r.result.similar_cases.map((x) => x.id), 5);
  rep.S1.push({ q: g.q, vOk, spOk, capsOk, solOk, famTop1: n ? famTop1 / n : 1, famTop3: n ? famTop3 / n : 1, famExact: n ? famExact / n : 1, cases, hint: r.decision_hint === g.hint,
    diff: vOk ? undefined : { py: g.vertical, js: jsV } });
}
const s1ms = (Date.now() - t) / G.S1.length;
t = Date.now();
for (const g of G.search) {
  const r = kb.search(g.q, 10);
  const kw = kb.kwSearch(r.result.tokens.filter((x) => [...x].length >= 3).join(' ') || g.q, 'chunk', 30).map(([d]) => kb.S.chunks[d][0]);
  const vec = kb.vecSearch(g.q, 'chunk', 30).map((x) => x[0]);
  rep.search.push({ q: g.q, tok: JSON.stringify(r.result.tokens) === JSON.stringify(g.tokens), kw10: overlap(g.kw, kw, 10), kw30: overlap(g.kw, kw, 30), vec10: overlap(g.vec, vec, 10),
    chunks5: overlap(g.chunks, r.result.chunks.map((h) => h.chunk_id), 5), chunks10: overlap(g.chunks, r.result.chunks.map((h) => h.chunk_id), 10),
    ents10: overlap(g.ents, r.result.entities.map((e) => e.ref), 10) });
}
const sms = (Date.now() - t) / G.search.length;
for (const g of G.image_search) {
  const r = kb.imageSearch(g.q, 20);
  rep.image_search.push({ q: g.q, top10: overlap(g.ids, r.result.images.map((i) => i.id), 10), top20: overlap(g.ids, r.result.images.map((i) => i.id), 20) });
}
for (const g of G.A2) {
  const r = kb.A2(g.q);
  rep.A2.push({ q: g.q, exact: JSON.stringify(r.candidates.map((c) => [c.id, c.score])) === JSON.stringify(g.cands), top1: (r.candidates[0] || {}).id === (g.cands[0] || [])[0] });
}
t = Date.now();
kb.e3Prepare();
const e3prep = Date.now() - t;
t = Date.now();
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
for (const g of G.E3) {
  const r = kb.E3(g.ctx);
  const res = r.result, c = res.context;
  const ctxOk = same(c.vertical, g.vertical) && same(c.spaces.map((s) => [s.id, s.from]), g.spaces) && same(c.products.map((p) => [p.kind, p.id, p.from]), g.products)
    && same(c.capabilities.map((x) => x.id), g.caps) && same(c.missing, g.missing) && same(c.weights, g.weights) && same(((c.customer || {}).deployments || []).map((d) => d.id), g.cust);
  const rk = res.ranked.map((x) => x.id), grk = g.ranked.map((x) => x[0]);
  const scoreDiff = Math.max(0, ...g.ranked.map(([id, s]) => { const x = res.ranked.find((y) => y.id === id); return x ? Math.abs(x.score - s) : 0; }));
  rep.E3.push({ q: JSON.stringify(g.ctx), ctxOk, headline: same(res.headline.map((h) => h.id), g.headline),
    km10: overlap(g.km.map((x) => x[0]), res.key_messages.map((k) => k.id), 10), kmExact: same(res.key_messages.map((k) => [k.id, k.score]), g.km),
    prods: overlap(g.prods.map((x) => x[0]), res.products.map((p) => p.id), 8), prodsExact: same(res.products.map((p) => [p.id, p.items.map((i) => i.id)]), g.prods),
    cases: overlap(g.cases.map((x) => x[0]), res.cases.map((d) => d.id), 6), ranked20: overlap(grk, rk, 20), ranked60: overlap(grk, rk, 60),
    rankedExact: same(res.ranked.map((x) => [x.id, x.score, x.dup]), g.ranked), rankedOrder: same(rk, grk), kmOrder: same(res.key_messages.map((k) => k.id), g.km.map((x) => x[0])), scoreDiff: Math.round(scoreDiff * 1000) / 1000,
    counts: res.n_scored === g.n_scored && res.n_candidates === g.n_candidates, hint: r.decision_hint === g.hint && same(r.decision_reasons, g.reasons), needs: same(r.needs_confirmation, g.needs) });
}
const e3ms = (Date.now() - t) / G.E3.length;
const avg = (a, f) => (a.reduce((s, x) => s + f(x), 0) / a.length);
const summary = {
  S1: { n: rep.S1.length, vertical_exact: avg(rep.S1, (x) => +x.vOk), spaces_exact: avg(rep.S1, (x) => +x.spOk), caps_exact: avg(rep.S1, (x) => +x.capsOk),
    solutions_exact: avg(rep.S1, (x) => +x.solOk), family_top1: avg(rep.S1, (x) => x.famTop1), family_top3_overlap: avg(rep.S1, (x) => x.famTop3),
    family_list_exact: avg(rep.S1, (x) => x.famExact), cases_top5_overlap: avg(rep.S1, (x) => x.cases), hint_exact: avg(rep.S1, (x) => +x.hint), ms_per_query: Math.round(s1ms) },
  search: { n: rep.search.length, tokens_exact: avg(rep.search, (x) => +x.tok), kw_top10: avg(rep.search, (x) => x.kw10), kw_top30: avg(rep.search, (x) => x.kw30),
    vec_top10: avg(rep.search, (x) => x.vec10), chunks_top5: avg(rep.search, (x) => x.chunks5), chunks_top10: avg(rep.search, (x) => x.chunks10), entities_top10: avg(rep.search, (x) => x.ents10), ms_per_query: Math.round(sms) },
  image_search: { n: rep.image_search.length, top10: avg(rep.image_search, (x) => x.top10), top20: avg(rep.image_search, (x) => x.top20) },
  A2: { n: rep.A2.length, exact: avg(rep.A2, (x) => +x.exact), top1: avg(rep.A2, (x) => +x.top1) },
  E3: { n: rep.E3.length, context_exact: avg(rep.E3, (x) => +x.ctxOk), headline_exact: avg(rep.E3, (x) => +x.headline), key_messages_top10: avg(rep.E3, (x) => x.km10),
    key_messages_exact: avg(rep.E3, (x) => +x.kmExact), products_top8: avg(rep.E3, (x) => x.prods), products_exact: avg(rep.E3, (x) => +x.prodsExact),
    cases_top6: avg(rep.E3, (x) => x.cases), ranked_top20: avg(rep.E3, (x) => x.ranked20), ranked_top60: avg(rep.E3, (x) => x.ranked60),
    key_messages_order_exact: avg(rep.E3, (x) => +x.kmOrder), ranked_order_exact: avg(rep.E3, (x) => +x.rankedOrder), ranked_exact: avg(rep.E3, (x) => +x.rankedExact), max_score_diff: Math.max(...rep.E3.map((x) => x.scoreDiff)), counts_exact: avg(rep.E3, (x) => +x.counts),
    hint_exact: avg(rep.E3, (x) => +x.hint), needs_exact: avg(rep.E3, (x) => +x.needs), ms_prepare: e3prep, ms_per_query: Math.round(e3ms) },
};
for (const k of Object.keys(summary)) for (const m of Object.keys(summary[k])) if (typeof summary[k][m] === 'number' && m !== 'n' && !m.startsWith('ms')) summary[k][m] = Math.round(summary[k][m] * 1000) / 1000;
console.log(JSON.stringify(summary, null, 1));
fs.writeFileSync(path.join(__dirname, 'build', 'parity.json'), JSON.stringify({ summary, detail: rep }, null, 1));
if (process.argv.includes('-v')) {
  for (const x of rep.S1) if (!x.vOk || !x.spOk || !x.capsOk || x.famTop1 < 1 || !x.solOk) console.log('S1', JSON.stringify(x));
  for (const x of rep.search) if (x.kw10 < 1 || x.chunks5 < 1) console.log('search', JSON.stringify(x));
  for (const x of rep.A2) if (!x.exact) console.log('A2', JSON.stringify(x));
  for (const x of rep.image_search) if (x.top10 < 1) console.log('img', JSON.stringify(x));
  for (const x of rep.E3) if (!x.ctxOk || !x.rankedOrder || !x.kmOrder || !x.prodsExact || x.cases < 1 || !x.hint || !x.needs || !x.counts) console.log('E3', JSON.stringify(x));
}
