/* Winmate KB 브라우저 질의 엔진 — build/query.py 의 결정적 질의 패턴을 JavaScript 로 옮긴 것.
 * 같은 데이터(dashboard/export_data.py 산출물)를 읽어 같은 규칙·점수식으로 계산한다.
 * 차이: SQLite FTS5(trigram BM25)·LIKE 는 같은 공식을 직접 계산하고, LSA 벡터는 DB 와 같은 float16 값을 쓴다(계산은 float64).
 * 브라우저와 Node 양쪽에서 동작(Node 는 검증 하네스용).
 */
(function (root) {
  'use strict';

  const TIER_RANK = { T1: 1, T2: 2, T3: 3, T4: 4, T5: 5, T6: 6 };
  const TH = { auto_score_min: 0.7, auto_margin_min: 0.15, industry_ask_margin: 0.10, precedent_min: 1 };
  const NON_RELAXABLE = new Set(['cap_weatherproof', 'cap_sunlight_readable', 'cap_wide_temp_operation']);
  const PARTICLE = /(으로|에서|에게|까지|부터|이랑|하고|과|와|을|를|이|가|은|는|의|에|로|도|만)$/;
  const STOP = new Set(['기능', '제품', '솔루션', '삼성', '사용', '필요', '제공', '관련', '위한', '있는', '하는']);
  const TOKSPLIT = /[\s,./·()\[\]"'?!:;]+/;
  const CLAUSE_SPLIT = /\s*(?:[,，;·/]|\s그리고\s|\s및\s|(?<=[가-힣A-Za-z0-9])(?:와|과|랑|하고)\s)\s*/;

  const tierOf = (t) => TIER_RANK[(t || 'T6').slice(0, 2)] || 6;
  const reEscape = (s) => s.replace(/[.*+?^${}()|[\]\\\/-]/g, '\\$&');
  const asciiLower = (s) => (s || '').replace(/[A-Z]+/g, (m) => m.toLowerCase());
  const cpLen = (s) => { let n = 0; for (const _ of s) n++; return n; };

  function norm(s) {
    if (!s) return '';
    s = s.replace(/ /g, ' ').replace(/™/g, '').replace(/®/g, '');
    return s.replace(/[\s·∙\-_/()\[\]]+/g, '').toLowerCase();
  }

  /* Python round(x, n): 정확한 이진값 기준 반올림, 정확히 반이면 짝수 쪽 */
  function pyRound(x, n) {
    if (!isFinite(x)) return x;
    const p = Math.pow(10, n);
    const m = x * p;
    const f = Math.floor(m);
    if (m - f === 0.5 && Number.isInteger(x * 2 * p)) return (f % 2 === 0 ? f : f + 1) / p;
    return Number(x.toFixed(n));
  }

  /* itertools.combinations(arr, r) 순서 */
  function* combinations(arr, r) {
    const n = arr.length;
    if (r > n) return;
    const idx = Array.from({ length: r }, (_, i) => i);
    yield idx.map((i) => arr[i]);
    while (true) {
      let i = r - 1;
      while (i >= 0 && idx[i] === i + n - r) i--;
      if (i < 0) return;
      idx[i]++;
      for (let j = i + 1; j < r; j++) idx[j] = idx[j - 1] + 1;
      yield idx.map((k) => arr[k]);
    }
  }

  /* SQLite LIKE '%tok%' (ASCII 만 대소문자 무시, %·_ 와일드카드) */
  function likeMatcher(tok) {
    const t = asciiLower(tok);
    if (!/[%_]/.test(t)) return (hayLower) => hayLower.indexOf(t) >= 0;
    const re = new RegExp(t.split('').map((ch) => (ch === '%' ? '[\\s\\S]*' : ch === '_' ? '[\\s\\S]' : reEscape(ch))).join(''));
    return (hayLower) => re.test(hayLower);
  }

  /* FTS5 trigram + bm25 재현: 구(phrase)=부분 문자열(대소문자 무시), 겹치는 등장 수 = 히트 수 */
  class FtsIndex {
    constructor(docs, cols, weights) {
      // docs: 배열, cols: doc → [색인 열 문자열...]
      this.n = docs.length;
      this.weights = weights || null;
      this.folded = new Array(this.n);
      this.len = new Float64Array(this.n);
      let total = 0;
      for (let i = 0; i < this.n; i++) {
        const cs = cols(docs[i]).map((s) => (s || '').toLowerCase());
        this.folded[i] = cs;
        let L = 0;
        for (const s of cs) { const l = cpLen(s); if (l >= 3) L += l - 2; }
        this.len[i] = L;
        total += L;
      }
      this.avgdl = total / Math.max(1, this.n);
    }
    static countHits(hay, needle) {
      let c = 0, i = hay.indexOf(needle);
      while (i >= 0) { c++; i = hay.indexOf(needle, i + 1); }
      return c;
    }
    search(phrases, k) {
      const k1 = 1.2, b = 0.75;
      const P = phrases.map((p) => p.toLowerCase());
      const freq = new Map();   // doc → Float64Array(nPhrase)
      const nHit = new Array(P.length).fill(0);
      for (let pi = 0; pi < P.length; pi++) {
        const ph = P[pi];
        if (!ph) continue;
        for (let d = 0; d < this.n; d++) {
          const cs = this.folded[d];
          let f = 0, any = false;
          for (let ci = 0; ci < cs.length; ci++) {
            if (cs[ci].indexOf(ph) < 0) continue;
            const h = FtsIndex.countHits(cs[ci], ph);
            if (h) { any = true; f += h * (this.weights ? (this.weights[ci] ?? 1) : 1); }
          }
          if (any) {
            nHit[pi]++;
            let a = freq.get(d);
            if (!a) { a = new Float64Array(P.length); freq.set(d, a); }
            a[pi] += f;
          }
        }
      }
      const idf = nHit.map((h) => { let v = Math.log((this.n - h + 0.5) / (h + 0.5)); return v <= 0 ? 1e-6 : v; });
      const out = [];
      for (const [d, a] of freq) {
        const D = this.len[d];
        let s = 0;
        for (let i = 0; i < P.length; i++) s += idf[i] * ((a[i] * (k1 + 1)) / (a[i] + k1 * (1 - b + (b * D) / this.avgdl)));
        out.push([d, s]);
      }
      out.sort((x, y) => y[1] - x[1] || x[0] - y[0]);
      return out.slice(0, k);
    }
  }

  /* LSA: sklearn TfidfVectorizer(char_wb 2–4, sublinear_tf, l2) → TruncatedSVD 성분(float16, 예전 형식 int8 도 읽음) */
  let F16 = null;
  function f16table() {
    if (F16) return F16;
    F16 = new Float32Array(65536);
    for (let h = 0; h < 65536; h++) {
      const s = h & 0x8000 ? -1 : 1, e = (h >> 10) & 0x1f, f = h & 0x3ff;
      F16[h] = e === 0 ? s * Math.pow(2, -14) * (f / 1024) : e === 31 ? (f ? NaN : s * Infinity) : s * Math.pow(2, e - 15) * (1 + f / 1024);
    }
    return F16;
  }
  function f16to32(u16) { const T = f16table(), out = new Float32Array(u16.length); for (let i = 0; i < u16.length; i++) out[i] = T[u16[i]]; return out; }
  const magic = (buf) => String.fromCharCode(...new Uint8Array(buf, 0, 4));

  class Lsa {
    constructor(vocabObj, buf) {
      const dv = new DataView(buf);
      this.nf = dv.getUint32(4, true);
      this.dim = dv.getUint32(8, true);
      this.idf = new Float32Array(buf, 12, this.nf);
      if (magic(buf) === 'WLSH') {          // float16 성분
        this.fscale = new Float32Array(this.nf).fill(1);
        this.comp = f16to32(new Uint16Array(buf, 12 + 4 * this.nf, this.nf * this.dim));
      } else {                               // int8 성분 + 특징별 배율
        this.fscale = new Float32Array(buf, 12 + 4 * this.nf, this.nf);
        this.comp = new Int8Array(buf, 12 + 8 * this.nf, this.nf * this.dim);
      }
      this.vocab = new Map();
      vocabObj.vocab.forEach((g, i) => this.vocab.set(g, i));
      this.lo = vocabObj.params.ngram[0];
      this.hi = vocabObj.params.ngram[1];
    }
    ngrams(text) {
      const t = text.toLowerCase().replace(/\s\s+/g, ' ');
      const out = [];
      for (const w0 of t.split(/\s+/)) {
        if (!w0) continue;
        const w = Array.from(' ' + w0 + ' ');
        const L = w.length;
        for (let n = this.lo; n <= this.hi; n++) {
          let off = 0;
          out.push(w.slice(off, off + n).join(''));
          while (off + n < L) { off++; out.push(w.slice(off, off + n).join('')); }
          if (off === 0) break;
        }
      }
      return out;
    }
    embed(text) {
      const cnt = new Map();
      for (const g of this.ngrams(text || '')) {
        const j = this.vocab.get(g);
        if (j !== undefined) cnt.set(j, (cnt.get(j) || 0) + 1);
      }
      const z = new Float64Array(this.dim);
      if (!cnt.size) return z;
      let nrm = 0;
      const xs = [];
      for (const [j, c] of cnt) { const v = (1 + Math.log(c)) * this.idf[j]; xs.push([j, v]); nrm += v * v; }
      nrm = Math.sqrt(nrm) || 1;
      for (const [j, v0] of xs) {
        const v = (v0 / nrm) * this.fscale[j];
        const base = j * this.dim;
        for (let d = 0; d < this.dim; d++) z[d] += v * this.comp[base + d];
      }
      let zn = 0;
      for (let d = 0; d < this.dim; d++) zn += z[d] * z[d];
      zn = Math.sqrt(zn) + 1e-9;
      for (let d = 0; d < this.dim; d++) z[d] /= zn;
      return z;
    }
  }

  class VecSpace {
    constructor(refs, scale, q, dim) { this.refs = refs; this.scale = scale; this.q = q; this.dim = dim; this.n = refs.length; }
    scores(z) {
      const s = new Float64Array(this.n), D = this.dim, q = this.q;
      for (let i = 0; i < this.n; i++) {
        let acc = 0;
        const base = i * D;
        for (let d = 0; d < D; d++) acc += q[base + d] * z[d];
        s[i] = acc * this.scale[i];
      }
      return s;
    }
  }

  /* 벡터 파일 하나 → {space: VecSpace}. spaceList = 그 파일에 든 공간 순서(vec_refs.files) */
  function parseVec(buf, refsObj, spaceList) {
    const dv = new DataView(buf);
    const dim = dv.getUint32(4, true);
    const half = magic(buf) === 'WVEH';
    let off = 8;
    const spaces = {};
    for (const space of spaceList || refsObj.order) {
      const n = dv.getUint32(off, true); off += 4;
      let scale, q;
      if (half) { scale = new Float32Array(n).fill(1); q = f16to32(new Uint16Array(buf, off, n * dim)); off += 2 * n * dim; }
      else { scale = new Float32Array(buf, off, n); off += 4 * n; q = new Int8Array(buf, off, n * dim); off += n * dim; }
      spaces[space] = new VecSpace(refsObj.refs[space], scale, q, dim);
    }
    return spaces;
  }

  const groupBy = (arr, keyf) => {
    const m = new Map();
    for (const x of arr) { const k = keyf(x); let a = m.get(k); if (!a) { a = []; m.set(k, a); } a.push(x); }
    return m;
  };
  const setInter = (a, b) => { for (const x of a) if (b.has(x)) return true; return false; };

  class KB {
    constructor(core, graph) {
      this.core = core;
      this.g = graph;
      this.kw = graph.kw;
      this._index();
    }

    /* ── 인덱스 ── */
    _index() {
      const N = (this.N = new Map());
      const g = this.g, core = this.core;
      const put = (k, i, n) => N.set(k + '\u0001' + i, n);
      for (const f of g.fam) put('family', f.id, f.name);
      for (const m of g.models) put('model', m[0], m[1]);
      for (const c of core.CAT) put('category', c[0], c[2]);
      for (const s of core.SOL) put('solution', s[0], s[2]);
      for (const s of core.SVC) put('service', s[0], s[2]);
      for (const v of core.V) put('vertical', v[0], v[2] != null ? v[2] : v[3]);
      for (const s of core.S) put('space_type', s[0], s[2]);
      for (const d of g.deps) put('deployment', d.id, d.title);
      for (const k of core.K) put('capability', k[0], k[2]);
      this.catParent = new Map(core.CAT.map((c) => [c[0], c[1]]));
      this.catLevel = new Map(core.CAT.map((c) => [c[0], c[3]]));
      this.catChildren = groupBy(core.CAT.filter((c) => c[1] != null), (c) => c[1]);
      for (const c of core.CAT) if (c[3] === 3) { const pn = N.get('category\u0001' + c[1]); if (pn) put('category', c[0], pn + ' > ' + c[2]); }
      this.famById = new Map(g.fam.map((f) => [f.id, f]));
      this.fcats = new Map();
      for (const f of g.fam) {
        const cats = new Set(f.cats.map((x) => x[0]));
        if (f.cat) { cats.add(f.cat); if (f.sub) cats.add(f.cat + '__' + f.sub); }
        let frontier = [...cats];
        while (frontier.length) {
          const ps = [];
          for (const x of frontier) { const p = this.catParent.get(x); if (p != null && !cats.has(p)) { cats.add(p); ps.push(p); } }
          frontier = ps;
        }
        this.fcats.set(f.id, cats);
      }
      this.vertById = new Map(core.V.map((v) => [v[0], v]));
      this.vertChildren = groupBy(core.V.filter((v) => v[4] != null), (v) => v[4]);
      this.prov = new Map();
      for (const p of g.prov) { let m = this.prov.get(p[0]); if (!m) { m = new Map(); this.prov.set(p[0], m); } m.set(p[2], p[4]); }
      this.edgesByRel = groupBy(g.edges, (e) => e[2]);
      this.req = groupBy(core.REQ, (r) => r[0]);
      this.depById = new Map(g.deps.map((d) => [d.id, d]));
      this.modelsByFam = groupBy(g.models, (m) => m[2]);
      this.tagsByFam = groupBy(g.tags, (t) => t[0]);
      this.provRowsByFam = groupBy(g.prov, (p) => p[0]);
      this.keyspecByFam = groupBy(g.keyspec, (k) => k[0]);
      this.sections = g.sections;
      this.secById = new Map(g.sections.map((s) => [s[0], s]));
      this.itemsBySec = groupBy(g.items, (it) => it[1]);
      // 선례(USES) 카운터
      this.prec = new Map();
      for (const e of this.edgesByRel.get('USES') || []) if (e[0] === 'deployment') { const k = e[3] + '\u0001' + e[4]; this.prec.set(k, (this.prec.get(k) || 0) + 1); }
      // 공간·역량 키워드
      this.KW_KO = this.kw.KW_KO;
      this.KW_EN = this.kw.KW_EN;
      this.REQ_RE = Object.entries(this.kw.REQ_CAP).map(([cap, pats]) => [cap, pats.map((p) => new RegExp(p, 'i'))]);
    }

    name(kind, id) { const n = this.N.get(kind + '\u0001' + id); return n || id; }

    docInfo(di) { const d = this.core.docs[di]; return d ? { url: d[0], title: d[1], page_type: d[2], locale: d[3] } : null; }
    srcInfo(src) { if (!src) return null; const d = this.docInfo(src[0]); return d ? { ...d, section: src[1] >= 0 ? this.core.SEC[src[1]] : null } : null; }

    envelope(pattern, result, o = {}) {
      const tiers = (o.tiers || []).filter(Boolean);
      let tierMin = null;
      for (const t of tiers) if (tierMin === null || tierOf(t) > tierOf(tierMin)) tierMin = t;
      const reasons = [...(o.reasons || [])];
      const cands = o.candidates || [];
      let hint = 'auto';
      if (cands.length) {
        const s1 = cands[0].score, s2 = cands.length > 1 ? cands[1].score : 0;
        if (s1 < TH.auto_score_min || s1 - s2 < TH.auto_margin_min) {
          hint = 'check';
          reasons.push(s1 - s2 < TH.auto_margin_min ? 'LOW_MARGIN' : 'LOW_SCORE');
        }
      }
      if (tierMin && tierOf(tierMin) >= 3) { if (hint === 'auto') hint = 'check'; reasons.push('LOW_TIER'); }
      if (o.fallback) reasons.push('FALLBACK_USED');
      if (reasons.includes('ASK') || reasons.includes('AMBIGUOUS_INDUSTRY')) hint = 'ask';
      return {
        pattern, result, evidence_paths: o.evidence || [], tier_min: tierMin, candidates: cands.slice(0, 10), decision_hint: hint,
        decision_reasons: [...new Set(reasons)].sort(), needs_confirmation: o.needs || [], fallback_level: o.fallback || null,
        modes_used: o.modes || [], timings_ms: { total: o.t0 ? Math.round(now() - o.t0) : 0 },
      };
    }

    /* ── 사전 규칙(curation.py) ── */
    kitchen(vertical) {
      if (this.kw.RESIDENTIAL.includes(vertical)) return 'residential_kitchen';
      if (this.kw.COMMERCIAL_KITCHEN.includes(vertical)) return 'commercial_kitchen';
      return null;
    }
    spacesInText(text, lang = 'ko', vertical = null) {
      const out = [], used = [];
      const table = lang === 'en' ? this.KW_EN : this.KW_KO;
      const src = lang === 'en' ? (text || '').toLowerCase() : text || '';
      for (const [kw, code] of table) {
        let start = 0;
        while (true) {
          const i = src.indexOf(kw, start);
          if (i < 0) break;
          if (!used.some(([a, b]) => a <= i && i < b)) {
            used.push([i, i + kw.length]);
            if (code && !out.some((x) => x[0] === code)) out.push([code, kw]);
          }
          start = i + kw.length;
        }
      }
      for (const kw of ['주방', '키친']) {
        const kc = this.kitchen(vertical);
        if ((text || '').includes(kw) && kc && !out.some((x) => x[0] === kc)) out.push([kc, kw]);
      }
      if ((text || '').includes('창구')) {
        const sp = ['kr_finance', 'us_finance'].includes(vertical) ? 'bank_branch' : 'civil_service_counter';
        if (!out.some((x) => x[0] === sp)) out.push([sp, '창구']);
      }
      return out;
    }
    capsFromText(text) {
      const out = [];
      for (const [cap, pats] of this.REQ_RE) {
        for (const p of pats) { const m = p.exec(text || ''); if (m) { out.push([cap, m[0]]); break; } }
      }
      return out;
    }

    /* ── 검색 인덱스(지연 생성) ── */
    attachSearch(search) {
      this.S = search;
      this.chunkById = new Map(search.chunks.map((c, i) => [c[0], i]));
      this.chunkLower = search.chunks.map((c) => asciiLower(c[4]));
      this.edocLower = search.edocs.map((e) => asciiLower((e[2] || '') + ' ' + (e[3] || '')));
      this.idocLower = search.idocs.map((d) => asciiLower(d[1]));
      this.idocById = new Map(search.idocs.map((d) => [d[0], d[1]]));
      this.fts = {
        chunk: new FtsIndex(search.chunks, (c) => [c[4], c[3]]),
        entity: new FtsIndex(search.edocs, (e) => [e[2], e[3]], [5.0, 1.0]),
        image: new FtsIndex(search.idocs, (d) => [d[1]]),
      };
    }
    attachVectors(lsa, vec) { if (lsa) this.lsa = lsa; this.vec = Object.assign(this.vec || {}, vec || {}); }
    attachImages(images) {
      this.I = images;
      this.assetIdx = new Map(images.assets.map((a, i) => [a[0], i]));
      this.occByAsset = groupBy(images.occ.map((o, i) => [o, i]), (x) => x[0][0]);
      this.depictsByTarget = groupBy(images.depicts, (d) => d[2]);
    }

    embed(text) { return this.lsa ? this.lsa.embed(text) : null; }
    vecSearch(text, space, k = 20) {
      if (!this.vec || !this.lsa || !this.vec[space]) return [];
      const V = this.vec[space];
      const z = this.embed(text);
      const s = V.scores(z);
      const idx = Array.from(s.keys()).sort((a, b) => s[b] - s[a]).slice(0, k);
      return idx.map((i) => [V.refs[i], s[i]]);
    }

    static ftsQuery(text) {
      let toks = (text || '').split(TOKSPLIT).filter((t) => cpLen(t) >= 3);
      if (!toks.length) toks = (text || '').split(/\s+/).filter((t) => t && cpLen(t) >= 3);
      return toks.slice(0, 12).map((t) => t.replace(/"/g, ''));
    }
    queryTokens(text) {
      const toks = [];
      for (let t of (text || '').split(TOKSPLIT)) {
        t = t.trim();
        if (cpLen(t) >= 3) { const t2 = t.replace(PARTICLE, ''); t = cpLen(t2) >= 2 ? t2 : t; }
        if (cpLen(t) >= 2 && !STOP.has(t) && !toks.includes(t)) toks.push(t);
      }
      return toks;
    }
    kwSearch(text, which, k = 20) {
      const ph = KB.ftsQuery(text);
      if (!ph.length) return [];
      return this.fts[which].search(ph, k);
    }
    likeSearch(toks, lowerArr, k = 200) {
      if (!toks.length) return [];
      for (let need = toks.length; need > Math.max(0, toks.length - 2); need--) {
        let hits = [];
        for (const combo of combinations(toks, need)) {
          const ms = combo.map(likeMatcher);
          let n = 0;
          for (let i = 0; i < lowerArr.length && n < k; i++) {
            const h = lowerArr[i];
            if (ms.every((m) => m(h))) { hits.push(i); n++; }
          }
          if (hits.length >= k) break;
        }
        if (hits.length) return [...new Set(hits)].slice(0, k);
      }
      return [];
    }

    search(text, k = 10, modes = ['kw', 'vec']) {
      const t0 = now();
      const toks = this.queryTokens(text);
      const fused = new Map();
      const addF = (key, v) => fused.set(key, (fused.get(key) || 0) + v);
      const kwText = toks.filter((t) => cpLen(t) >= 3).join(' ') || text;
      const C = this.S.chunks;
      if (modes.includes('kw')) {
        this.kwSearch(kwText, 'chunk', 100).forEach(([d], r) => addF(C[d][0], 1 / (60 + r)));
        this.likeSearch(toks, this.chunkLower).forEach((d, r) => addF(C[d][0], 1 / (60 + r)));
      }
      if (modes.includes('vec')) this.vecSearch(text, 'chunk', 100).forEach(([cid], r) => addF(cid, 1 / (60 + r)));
      const cand = [...fused.entries()].sort((a, b) => b[1] - a[1]).slice(0, 300);
      const mx = Math.max(...cand.map((x) => x[1]), 1e-300) || 1;
      const scored = [];
      for (const [cid, v] of cand) {
        const i = this.chunkById.get(cid);
        if (i === undefined) continue;
        const row = C[i];
        const body = (row[3] || '') + ' ' + row[4];
        const cov = toks.length ? toks.filter((t) => body.includes(t)).length / toks.length : 0;
        scored.push([0.5 * v / mx + 0.5 * cov, cid, row, cov]);
      }
      scored.sort((a, b) => b[0] - a[0]);
      const hits = scored.slice(0, k).map(([sc, cid, row, cov]) => {
        const d = this.docInfo(row[1]) || {};
        return { chunk_id: cid, score: pyRound(sc, 4), coverage: pyRound(cov, 2), title: d.title, section: row[3], page_type: row[2],
          url: d.url, text: row[4].slice(0, 400), entities: (row[5] || []).slice(0, 8) };
      });
      const ents = new Map();
      const addE = (key, v) => ents.set(key, (ents.get(key) || 0) + v);
      const E = this.S.edocs;
      if (modes.includes('kw')) {
        const ph = KB.ftsQuery(kwText);
        if (ph.length) this.fts.entity.search(ph, 30).forEach(([d], r) => addE(E[d][0] + ':' + E[d][1], 1 / (60 + r)));
        this.likeSearch(toks, this.edocLower, 60).forEach((d, r) => addE(E[d][0] + ':' + E[d][1], 1 / (60 + r)));
      }
      if (modes.includes('vec')) this.vecSearch(text, 'entity', 30).forEach(([ref], r) => addE(ref.slice(ref.indexOf(':') + 1), 1 / (60 + r)));
      const entHits = [...ents.entries()].sort((a, b) => b[1] - a[1]).slice(0, k).map(([e, s]) => {
        const j = e.indexOf(':');
        return { ref: e, kind: e.slice(0, j), id: e.slice(j + 1), name: this.name(e.slice(0, j), e.slice(j + 1)), score: pyRound(s, 4) };
      });
      return this.envelope('search', { tokens: toks, chunks: hits, entities: entHits }, { modes: [...modes], t0,
        evidence: hits.map((h) => [{ kind: 'doc_block', ref: h.chunk_id, source_url: h.url }]) });
    }

    /* ── A. 해석 ── */
    aliasIndex() {
      if (!this._alias) {
        const by = new Map();
        for (const r of this.g.alias) { let s = by.get(r[1]); if (!s) { s = []; by.set(r[1], s); } if (!s.some((x) => x[0] === r[2] && x[1] === r[3])) s.push([r[2], r[3]]); }
        const surf = [...new Set(this.g.alias.filter((r) => cpLen(r[1]) >= 2).map((r) => r[0]))];
        surf.sort((a, b) => cpLen(b) - cpLen(a));
        const codes = [...new Set(this.g.alias.filter((r) => r[2] === 'model').map((r) => r[0]))];
        codes.sort((a, b) => cpLen(b) - cpLen(a));
        this._alias = {
          by,
          are: new RegExp(surf.map(reEscape).join('|'), 'gi'),
          cre: codes.length ? new RegExp('(?<![A-Z0-9])(' + codes.map(reEscape).join('|') + ')(?![A-Z0-9])', 'g') : null,
        };
      }
      return this._alias;
    }
    static tupleSort(a, b) { return a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : 0; }

    A1(text, lang = 'ko') {
      const t0 = now();
      const { by, are, cre } = this.aliasIndex();
      const links = [], used = [];
      if (cre) {
        for (const m of text.matchAll(cre)) {
          const hs = (by.get(norm(m[0])) || []).slice().sort(KB.tupleSort);
          links.push({ span: [m.index, m.index + m[0].length], surface: m[0], type: 'model', id: hs.length ? hs[0][1] : null, conf: 1.0, method: 'code_exact' });
          used.push([m.index, m.index + m[0].length]);
        }
      }
      const KP = this.kw.KIND_PRIORITY;
      for (const m of text.matchAll(are)) {
        if (used.some(([a, b]) => a <= m.index && m.index < b)) continue;
        const hits = (by.get(norm(m[0])) || []).slice().sort((x, y) => ((KP[x[0]] ?? 9) - (KP[y[0]] ?? 9)) || (x[1] < y[1] ? -1 : x[1] > y[1] ? 1 : 0));
        if (!hits.length) continue;
        const [k, t] = hits[0];
        links.push({ span: [m.index, m.index + m[0].length], surface: m[0], type: k, id: t, name: this.name(k, t), conf: hits.length === 1 ? 0.9 : 0.6,
          method: 'alias', alternatives: hits.slice(1, 6).map(([a, b]) => ({ type: a, id: b, name: this.name(a, b) })) });
        used.push([m.index, m.index + m[0].length]);
      }
      for (const [sp, kw] of this.spacesInText(text, lang)) links.push({ surface: kw, type: 'space_type', id: sp, name: this.name('space_type', sp), conf: 0.8, method: 'space_keyword' });
      for (const [cap, kw] of this.capsFromText(text)) links.push({ surface: kw, type: 'capability', id: 'cap_' + cap, name: this.name('capability', 'cap_' + cap), conf: 0.7, method: 'need_keyword' });
      return this.envelope('A1', { links }, { modes: ['sql', 'rule'], t0 });
    }

    A2(text) {
      const t0 = now();
      const score = new Map(), signals = new Map();
      const add = (v, x) => score.set(v, (score.get(v) || 0) + x);
      const sig = (v, s) => { let a = signals.get(v); if (!a) { a = []; signals.set(v, a); } a.push(s); };
      const kr = new Map(this.core.V.filter((v) => v[5] === 'kr_site').map((v) => [v[0], v]));
      for (const [vid, r] of kr) if (r[2] && cpLen(r[2]) >= 2 && text.includes(r[2])) { add(vid, 1.0); sig(vid, `업종명 '${r[2]}'`); }
      const links = this.A1(text).result.links;
      const spaces = links.filter((l) => l.type === 'space_type').map((l) => l.id);
      const ents = links.filter((l) => ['family', 'category', 'solution', 'service'].includes(l.type)).map((l) => [l.type, l.id]);
      const krLike = (s) => /^kr./i.test(s);
      const HS = this.edgesByRel.get('HAS_SPACE') || [];
      for (const sp of spaces) {
        const cnt = new Map();
        for (const e of HS) if (e[4] === sp && krLike(e[1])) cnt.set(e[1], (cnt.get(e[1]) || 0) + 1);
        const vs = [...cnt.entries()].sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
        const tot = vs.reduce((a, x) => a + x[1], 0) || 1;
        for (const [v, n] of vs) { add(v, (0.6 * n) / tot); sig(v, `공간 '${this.name('space_type', sp)}'`); }
      }
      const FB = this.edgesByRel.get('FEATURED_BY_SITE') || [];
      for (const [k, i] of ents) {
        const vs = [];
        for (const e of FB) if (e[3] === k && e[4] === i && krLike(e[1]) && !vs.includes(e[1])) vs.push(e[1]);
        for (const v of vs) { add(v, 0.3 / Math.max(1, vs.length)); sig(v, `제품·솔루션 '${this.name(k, i)}'`); }
      }
      for (const [ref, s] of this.vecSearch(text, 'entity', 60)) {
        const rest = ref.slice(ref.indexOf(':') + 1);
        const j = rest.indexOf(':');
        const kind = rest.slice(0, j), i = rest.slice(j + 1);
        if (kind === 'vertical' && kr.has(i) && s > 0.1) { add(i, 0.4 * s); sig(i, `유사도 ${s.toFixed(2)}`); }
      }
      for (const vid of [...score.keys()]) {
        const p = kr.get(vid) ? kr.get(vid)[4] : null;
        if (p) score.set(p, Math.max(score.get(p) || 0, score.get(vid)));
      }
      const ranked = [...score.entries()].sort((a, b) => b[1] - a[1]);
      const top = ranked.length ? ranked[0][1] : 0;
      const cands = ranked.slice(0, 6).map(([v, s]) => ({ id: v, name: this.name('vertical', v), score: top ? pyRound(s / top, 3) : 0, signals: (signals.get(v) || []).slice(0, 6) }));
      const reasons = [];
      const isParent = (id) => [...kr.values()].some((x) => x[4] === id);
      const leaves = cands.filter((c) => !isParent(c.id));
      if (leaves.length >= 2 && leaves[0].score - leaves[1].score < TH.industry_ask_margin) reasons.push('AMBIGUOUS_INDUSTRY');
      if (!cands.length) reasons.push('ASK');
      return this.envelope('A2', { top2: cands.slice(0, 2), ask: reasons.length > 0, all: cands },
        { candidates: cands.map((c) => ({ id: c.id, score: c.score, reasons: c.signals })), reasons, modes: ['sql', 'kg', 'vec'], t0 });
    }

    /* ── B. 프리셋 ── */
    B1(verticalId) {
      const t0 = now();
      const vids = [verticalId, ...((this.vertChildren.get(verticalId) || []).map((v) => v[0]))];
      const secs = this.sections.filter((s) => vids.includes(s[1]));
      secs.sort((a, b) => (a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : a[3] - b[3]));
      const seq = [], hero = [], rec = [], cases = [];
      for (const s of secs) {
        const items = (this.itemsBySec.get(s[0]) || []).slice().sort((a, b) => a[2] - b[2]).map((it) => ({
          id: it[0], name: it[4], kind: it[3], tagline: it[5], target: [it[10], it[11]], target_name: it[11] ? this.name(it[10], it[11]) : null,
          space_label: it[8], space_type: it[9], link: it[6], images: it[14], resolve: it[12], conf: it[13], src: it[15] }));
        const d = this.docInfo(s[2]) || {};
        const ent = { section_id: s[0], vertical: s[1], seq: s[3], kind: s[4], title: s[5], description: s[6], tagline: s[7], space_label: s[8],
          space_types: s[10], space_names: s[10].map((x) => this.name('space_type', x)), space_method: s[11], labels: s[12], chips: s[13],
          items, source: d.url, src: s[14] };
        ({ hero, recommend: rec, cases }[s[4]] || seq).push(ent);
      }
      const order = [];
      for (const e of seq) for (const sp of e.space_types) if (!order.includes(sp)) order.push(sp);
      const needs = [];
      if (!seq.length) needs.push('이 업종의 업종 페이지 장면이 없음(US 업종이거나 수집 누락)');
      needs.push('페르소나·시간대·비교축은 사이트에 구조화된 소스가 없음(카탈로그·제안서 필요)');
      return this.envelope('B1', { vertical: verticalId, space_sequence: order.map((x) => ({ space_type: x, name: this.name('space_type', x) })), hero, scenes: seq, recommended: rec, cases },
        { needs, modes: ['sql', 'kg'], t0, tiers: ['T2_official'] });
    }

    B2(text) {
      const t0 = now();
      const sp = this.spacesInText(text).map((x) => x[0]);
      const have = new Set(this.capsFromText(text).map((x) => x[0]));
      const gaps = [];
      for (const s of sp) for (const r of this.req.get(s) || []) {
        const cap = r[1].replace('cap_', '');
        if (!have.has(cap)) gaps.push({ space: s, capability: cap, strength: r[2], question_ko: `${this.name('space_type', s)}에 '${this.name('capability', r[1])}'이(가) 필요한가요?` });
      }
      if (!sp.length) gaps.push({ space: null, capability: null, strength: 'hard', question_ko: '설치할 공간(예: 로비, 객실, 매장 입구)을 알려 주세요.' });
      return this.envelope('B2', { gaps }, { modes: ['rule', 'kg'], t0, tiers: ['T5_seed_draft'], needs: ['requires 엣지는 시드 초안(전문가 승인 전)'] });
    }

    /* ── C. 추론 ── */
    catSubtree(cid) {
      const out = new Set([cid]);
      let frontier = [cid];
      while (frontier.length) {
        const nxt = [];
        for (const c of this.core.CAT) if (frontier.includes(c[1]) && !out.has(c[0])) nxt.push(c[0]);
        for (const x of nxt) out.add(x);
        frontier = nxt;
      }
      return out;
    }
    siteRecommended(space, vertical) {
      const rows = [];
      if (space) for (const e of this.edgesByRel.get('RECOMMENDED_BY_SITE') || []) if (e[1] === space) rows.push({ k: e[3], i: e[4], ev: e[8], via: 'space' });
      if (vertical) {
        const vids = [vertical, ...((this.vertChildren.get(vertical) || []).map((v) => v[0]))];
        const sorted = [...new Set(vids)].sort();
        const FB = this.edgesByRel.get('FEATURED_BY_SITE') || [];
        for (const v of sorted) for (const e of FB) if (e[1] === v) rows.push({ k: e[3], i: e[4], ev: e[8], via: 'vertical' });
      }
      return rows;
    }
    familySims(text) {
      if (!this.vec || !this.vec.entity || !this.lsa || !text) return new Map();
      const V = this.vec.entity;
      const s = V.scores(this.embed(text));
      const out = new Map();
      V.refs.forEach((r, i) => { if (r.startsWith('entity:family:')) out.set(r.slice(14), s[i]); });
      return out;
    }

    C2(capabilities = [], category = null, space = null, vertical = null, limit = 15, soft = [], text = null) {
      const t0 = now();
      const caps = capabilities.map((c) => (c.startsWith('cap_') ? c : 'cap_' + c));
      const softs = soft.filter((c) => !capabilities.includes(c)).map((c) => (c.startsWith('cap_') ? c : 'cap_' + c));
      const fams = this.famById;
      const fcats = this.fcats;
      const prov = (fid) => this.prov.get(fid) || new Map();
      const rec = this.siteRecommended(space, vertical);
      const recCats = new Map(), recFams = new Map(), recSols = new Map();
      for (const r of rec) {
        if (r.k === 'category') { if (!recCats.has(r.i)) recCats.set(r.i, []); recCats.get(r.i).push(r); }
        else if (r.k === 'family') { if (!recFams.has(r.i)) recFams.set(r.i, []); recFams.get(r.i).push(r); }
        else if (r.k === 'solution' || r.k === 'service') { const key = r.k + '\u0001' + r.i; if (!recSols.has(key)) recSols.set(key, r); }
      }
      const catsub = category ? this.catSubtree(category) : new Set();
      let pool = new Set();
      if (category) for (const f of fams.keys()) if (setInter(fcats.get(f), catsub)) pool.add(f);
      if (space || vertical) {
        const sitePool = new Set();
        for (const f of fams.keys()) if (recFams.has(f) || [...fcats.get(f)].some((c) => recCats.has(c))) sitePool.add(f);
        const inter = new Set([...pool].filter((x) => sitePool.has(x)));
        if (category && inter.size) pool = inter;
        else if (!category) pool = new Set([...pool, ...sitePool]);
      }
      if (caps.length && !category) for (const f of fams.keys()) if (caps.every((c) => prov(f).has(c))) pool.add(f);
      if (!(category || space || vertical || caps.length)) pool = new Set(fams.keys());
      const precOf = (k, i) => this.prec.get(k + '\u0001' + i) || 0;
      const sims = text ? this.familySims(text) : new Map();
      const lw = (r) => (this.catLevel.get(r.i) === 3 ? 2 : 1);
      let maxW = 0;
      for (const f of pool) { let w = 0; for (const c of fcats.get(f)) if (recCats.has(c)) for (const r of recCats.get(c)) w += lw(r); maxW = Math.max(maxW, w); }
      maxW = maxW || 1;
      let out = [];
      for (const fid of pool) {
        const f = fams.get(fid);
        const P = prov(fid);
        const sat = {};
        for (const c of caps) if (P.has(c)) sat[c] = P.get(c);
        const miss = caps.filter((c) => !(c in sat));
        const ssat = softs.filter((c) => P.has(c));
        let capScore = caps.length ? Object.keys(sat).length / caps.length : 0.5;
        capScore = Math.min(1.0, capScore + 0.1 * ssat.length);
        const site = [...(recFams.get(fid) || [])];
        for (const c of fcats.get(fid)) if (recCats.has(c)) site.push(...recCats.get(c));
        const w = site.filter((r) => r.k === 'category').reduce((a, r) => a + lw(r), 0);
        const siteScore = recFams.has(fid) ? 1.0 : site.length ? 0.4 + (0.6 * w) / maxW : 0.0;
        const catScore = category && setInter(fcats.get(fid), catsub) ? 1.0 : 0.0;
        let p = precOf('family', fid);
        let pc = 0;
        for (const c of fcats.get(fid)) pc += precOf('category', c);
        p += 0.2 * pc;
        const sim = Math.max(0.0, sims.get(fid) || 0.0);
        const score = 0.4 * capScore + 0.3 * siteScore + 0.1 * catScore + 0.1 * Math.min(1.0, p / 5) + 0.1 * Math.min(1.0, sim / 0.5);
        const reasons = Object.entries(sat).map(([c, ev]) => `충족 ${this.name('capability', c)}: ${ev}`);
        for (const c of ssat) reasons.push(`충족(soft) ${this.name('capability', c)}`);
        for (const r of site.slice(0, 2)) reasons.push(`사이트 추천: ${this.name(r.k, r.i)} (${r.via})`);
        if (p) reasons.push(`선례 점수 ${p.toFixed(1)}`);
        if (sim > 0.2) reasons.push(`요구 문장 유사도 ${sim.toFixed(2)}`);
        out.push({ id: fid, name: f.name, model: f.model, category: this.name('category', f.cat), score: pyRound(score, 3), satisfies: sat, missing_hard: miss,
          satisfies_soft: ssat, site_recommendation: site.length > 0, precedent: pyRound(p, 1), sim: pyRound(sim, 3), reasons,
          breakdown: { cap: pyRound(capScore, 3), site: pyRound(siteScore, 3), category: catScore, precedent: pyRound(Math.min(1, p / 5), 3), text: pyRound(Math.min(1, sim / 0.5), 3) } });
      }
      const reasonsEnv = [], needs = [];
      const strict = out.filter((o) => !o.missing_hard.length);
      out = out.filter((o) => !o.missing_hard.some((c) => NON_RELAXABLE.has(c)));
      if (caps.length && !strict.length && out.length) { reasonsEnv.push('HARD_CONFLICT'); needs.push('hard 역량을 모두 충족하는 후보가 없어 일부 충족 후보를 표시'); }
      else if (caps.length) out = strict;
      out.sort((a, b) => b.score - a.score || ((a.name || '') < (b.name || '') ? -1 : (a.name || '') > (b.name || '') ? 1 : 0) || (a.id < b.id ? -1 : 1));
      if (caps.length || softs.length) needs.push('역량 판정은 presence 규칙 초안(rule_presence_v1) — 임계값 규칙은 전문가 승인 전 비활성');
      const sols = [...recSols.values()].map((r) => ({ kind: r.k, id: r.i, name: this.name(r.k, r.i), via: r.via, evidence: r.ev }));
      sols.sort((a, b) => (a.via === 'space' ? 0 : 1) - (b.via === 'space' ? 0 : 1));
      return this.envelope('C2', { families: out.slice(0, limit), solutions: sols, n_pool: pool.size },
        { candidates: out.slice(0, 10).map((o) => ({ id: o.id, score: o.score, reasons: o.reasons.slice(0, 3) })), reasons: reasonsEnv,
          modes: ['sql', 'kg', 'rule'], t0, needs, tiers: ['T2_official', ...(caps.length ? ['T5_rule_draft'] : [])],
          evidence: out.slice(0, limit).map((o) => Object.entries(o.satisfies).map(([c, ev]) => ({ kind: 'rule', ref: c, summary_ko: ev }))) });
    }

    C3(familyId) {
      const cats = this.fcats.get(familyId) || new Set();
      const targets = [['family', familyId], ...[...cats].map((c) => ['category', c])];
      const fits = [];
      const RB = this.edgesByRel.get('RECOMMENDED_BY_SITE') || [];
      for (const [k, i] of targets) for (const e of RB) if (e[3] === k && e[4] === i) {
        const ev = e[8] || '|';
        const j = ev.indexOf('|');
        const v = j >= 0 ? ev.slice(0, j) : ev, sid = j >= 0 ? ev.slice(j + 1) : '';
        fits.push({ space: e[1], space_name: this.name('space_type', e[1]), vertical: v || null, vertical_name: v ? this.name('vertical', v) : null, via: `${k}:${this.name(k, i)}`, section: sid });
      }
      const deps = [];
      for (const rel of ['USES', 'MENTIONS']) for (const e of this.edgesByRel.get(rel) || []) {
        if (e[0] !== 'deployment') continue;
        if ((e[3] === 'family' && e[4] === familyId) || (e[3] === 'category' && cats.has(e[4]))) if (!deps.includes(e[1])) deps.push(e[1]);
      }
      const agg = new Map();
      for (const f of fits) { const key = f.vertical + '|' + f.space; if (!agg.has(key)) agg.set(key, { ...f, n_sections: 0 }); agg.get(key).n_sections++; }
      const uniq = [...agg.values()].sort((a, b) => b.n_sections - a.n_sections);
      return { fits: uniq, deployments: deps.map((d) => ({ id: d, title: this.name('deployment', d) })), precedent_count: deps.length };
    }

    /* ── D. 선례 ── */
    D1(vertical = null, spaces = [], targets = [], text = null, limit = 10) {
      const t0 = now();
      const deps = this.g.deps;
      const ds = new Map();
      for (const r of this.g.dep_space) if (r[2]) { if (!ds.has(r[0])) ds.set(r[0], new Set()); ds.get(r[0]).add(r[2]); }
      const du = new Map();
      for (const rel of ['USES', 'MENTIONS']) for (const e of this.edgesByRel.get(rel) || []) if (e[0] === 'deployment') { if (!du.has(e[1])) du.set(e[1], new Set()); du.get(e[1]).add(e[3] + '\u0001' + e[4]); }
      const tgt = new Set(targets.map(([k, i]) => k + '\u0001' + i));
      const tgtCats = new Set();
      for (const [k, i] of targets) if (k === 'family') for (const c of this.fcats.get(i) || []) tgtCats.add('category\u0001' + c);
      let vtop = null;
      if (vertical) { const r = this.vertById.get(vertical); vtop = r && r[4] ? r[4] : vertical; }
      const sim = new Map();
      if (text) for (const [ref, s] of this.vecSearch(text, 'entity', 400)) if (ref.startsWith('entity:deployment:')) sim.set(ref.slice(18), s);
      const kpi = new Map();
      for (const k of this.g.kpis) kpi.set(k[1], (kpi.get(k[1]) || 0) + 1);
      const photos = new Set(this.g.dep_photo);
      const out = [];
      for (const d of deps) {
        const dv = new Set(d.v || []);
        const dsp = ds.get(d.id) || new Set();
        const dus = du.get(d.id) || new Set();
        const b = {
          vertical: vtop && (dv.has(vtop) || dv.has(vertical)) ? 1.0 : 0.0,
          space: spaces.length ? [...new Set(spaces)].filter((s) => dsp.has(s)).length / spaces.length : 0.0,
          product: tgt.size ? (setInter(dus, tgt) ? 1.0 : setInter(dus, tgtCats) ? 0.6 : 0.0) : 0.0,
          text: Math.max(0.0, sim.get(d.id) || 0.0),
        };
        const w = { vertical: vertical ? 0.3 : 0, space: spaces.length ? 0.25 : 0, product: tgt.size ? 0.3 : 0, text: text ? 0.15 : 0 };
        const tw = Object.values(w).reduce((a, x) => a + x, 0) || 1;
        const s = (b.vertical * w.vertical + b.space * w.space + b.product * w.product + b.text * w.text) / tw;
        if (s <= 0) continue;
        out.push({ id: d.id, title: d.title, url: d.url, format: d.format, date: d.date, score: pyRound(s, 3),
          similarity_breakdown: Object.fromEntries(Object.entries(b).map(([k, v]) => [k, pyRound(v, 2)])), kpis_count: kpi.get(d.id) || 0, has_photos: photos.has(d.id) });
      }
      out.sort((a, b) => b.score - a.score);
      return this.envelope('D1', { deployments: out.slice(0, limit) }, { candidates: out.slice(0, 10).map((o) => ({ id: o.id, score: o.score, reasons: [] })), modes: ['kg', 'vec'], t0, tiers: ['T3_case'] });
    }

    /* ── E3. 요구사항 컨텍스트 → 메시지 묶음(query.py E3) ── */
    attachMsgs(rows) {
      // rows: [id, level, text, parent_id, about_kind, about_id, vertical_id, space_type_id, locale, claim_flag, src, tier, method] (value_prop rowid 순서)
      this.M = rows;
      this.mKids = new Map();
      rows.forEach((r, i) => { if (r[3]) { let a = this.mKids.get(r[3]); if (!a) { a = []; this.mKids.set(r[3], a); } a.push(i); } });
      this._e3 = null;
    }
    _e3Base() {
      if (this._e3) return this._e3;
      const g = this.g;
      const edges = new Map();
      for (const rel of ['USES', 'MENTIONS', 'FEATURED_BY_SITE', 'RECOMMENDED_BY_SITE', 'FEATURED_CASE', 'SOLD_AS']) edges.set(rel, this.edgesByRel.get(rel) || []);
      const depUse = new Map();
      for (const rel of ['USES', 'MENTIONS']) for (const e of edges.get(rel)) if (e[0] === 'deployment') { if (!depUse.has(e[1])) depUse.set(e[1], new Set()); depUse.get(e[1]).add(e[3] + '\u0001' + e[4]); }
      const depSpace = new Map();
      for (const r of g.dep_space) if (r[2]) { if (!depSpace.has(r[0])) depSpace.set(r[0], new Set()); depSpace.get(r[0]).add(r[2]); }
      const secItems = new Map();
      for (const it of g.items) if (it[11] != null) { if (!secItems.has(it[1])) secItems.set(it[1], new Set()); secItems.get(it[1]).add(it[10] + '\u0001' + it[11]); }
      const famCaps = new Map();
      for (const p of g.prov) { if (!famCaps.has(p[0])) famCaps.set(p[0], new Set()); famCaps.get(p[0]).add(p[2]); }
      const kpis = new Map();
      for (const k of g.kpis) { if (!kpis.has(k[1])) kpis.set(k[1], []); kpis.get(k[1]).push({ text: k[2], claim_flag: k[4] }); }
      const modelFam = new Map(g.models.map((m) => [m[0], m[2]]));
      this._e3 = { edges, depUse, depSpace, secItems, famCaps, kpis, modelFam, Z: null, zi: 0, Zd: null };
      return this._e3;
    }
    /* 메시지·사례 문장 LSA 벡터를 나눠서 계산(화면이 멈추지 않게). 다 되면 true */
    e3Prepare(budget = Infinity) {
      const E = this._e3Base();
      if (!this.lsa || !this.M) return true;
      const dim = this.lsa.dim, n = this.M.length;
      if (!E.Z) { E.Z = new Float32Array(n * dim); E.zi = 0; }
      const end = Math.min(n, E.zi + budget);
      for (let i = E.zi; i < end; i++) E.Z.set(this.lsa.embed(this.M[i][2]), i * dim);
      E.zi = end;
      if (E.zi < n) return false;
      if (!E.Zd) {
        const deps = this.g.deps;
        E.Zd = new Float32Array(deps.length * dim);
        deps.forEach((d, j) => E.Zd.set(this.lsa.embed([d.title, d.cust, d.quote].filter(Boolean).join(' ')), j * dim));
      }
      return true;
    }
    E3({ vertical = null, spaces = [], products = [], customer = null, text = null, locale = 'ko-KR', limit = 12 } = {}) {
      const t0 = now();
      const W3 = { product: 0.35, vertical: 0.25, space: 0.2, customer: 0.15, text: 0.35 }, INFER = 0.5, MIN = 0.1;
      const LR = { tagline: 0, key_message: 1, usp: 2, proof_point: 3 };
      const rank = (lv) => LR[lv] ?? 9;
      const KM_KINDS = new Set(['industry_section', 'category', 'solution', 'service', 'vertical', 'document']);
      this.e3Prepare();
      const E = this._e3Base();
      const M = this.M || [];
      const key = (k, i) => k + '\u0001' + i;
      spaces = (spaces || []).filter(Boolean);
      products = (products || []).filter((p) => p && p[1]).map((p) => [p[0], p[1]]);
      customer = ((customer || '').trim()) || null;
      text = ((text || '').trim()) || null;
      const ctxText = [customer, text].filter(Boolean).join(' ');
      const reasons = [], needs = [];
      const ctx = { vertical: null, spaces: [], products: [], customer: null, text, capabilities: [], missing: [] };
      const vn = (i) => this.name('vertical', i), cn = (i) => this.name('category', i);
      // 업종
      let vFrom = null;
      if (vertical) vFrom = 'input';
      else if (ctxText) {
        const a2 = this.A2(ctxText);
        const top = a2.result.top2.length ? a2.result.top2[0] : null;
        if (top && top.signals.some((s) => !s.startsWith('유사도'))) {
          vertical = top.id; vFrom = 'inferred';
          if (a2.decision_reasons.includes('AMBIGUOUS_INDUSTRY')) reasons.push('AMBIGUOUS_INDUSTRY');
          ctx.vertical_alternatives = a2.candidates.slice(1, 4).map((c) => ({ id: c.id, name: vn(c.id), score: c.score }));
        }
      }
      if (vertical) ctx.vertical = { id: vertical, name: vn(vertical), from: vFrom };
      const vset = new Set(vertical ? [vertical, ...(this.vertChildren.get(vertical) || []).map((v) => v[0])] : []);
      const vparRow = vertical ? this.vertById.get(vertical) : null;
      const vpar = vparRow && vparRow[4] != null ? vparRow[4] : null;
      // 공간
      let spFrom = null;
      if (spaces.length) { spFrom = 'input'; ctx.spaces = spaces.map((s) => ({ id: s, name: this.name('space_type', s), from: 'input' })); }
      else if (ctxText) {
        const found = this.spacesInText(ctxText, 'ko', vertical);
        if (found.length) { spaces = found.map((x) => x[0]); spFrom = 'inferred'; ctx.spaces = found.map(([s, kw]) => ({ id: s, name: this.name('space_type', s), from: 'inferred', surface: kw })); }
      }
      const spset = new Set(spaces);
      // 제품
      let pFrom = null;
      if (products.length) { pFrom = 'input'; ctx.products = products.map(([k, i]) => ({ kind: k, id: i, name: this.name(k, i), from: 'input' })); }
      else if (ctxText) {
        const seen = [];
        for (const l of this.A1(ctxText).result.links) {
          let k = l.type, i = l.id;
          if (k === 'model' && i) { const f = E.modelFam.get(i); [k, i] = f ? ['family', f] : [null, null]; }
          if (['family', 'category', 'solution', 'service'].includes(k) && i && !seen.some((x) => x[0] === k && x[1] === i)) {
            seen.push([k, i]);
            ctx.products.push({ kind: k, id: i, name: this.name(k, i), from: 'inferred', surface: l.surface });
          }
        }
        products = seen; pFrom = seen.length ? 'inferred' : null;
      }
      const caps = text ? this.capsFromText(text).map((x) => 'cap_' + x[0]) : [];
      ctx.capabilities = caps.map((c) => ({ id: c, name: this.name('capability', c) }));
      const capSet = new Set(caps);
      const pset = new Set(products.map(([k, i]) => key(k, i)));
      const pcat = new Set(products.filter((p) => p[0] === 'category').map((p) => p[1]));
      const pfam = new Set(products.filter((p) => p[0] === 'family').map((p) => p[1]));
      const psol = new Set(products.filter((p) => p[0] === 'solution' || p[0] === 'service').map((p) => p[1]));
      const pfamCats = new Set();
      for (const f of pfam) for (const c of this.fcats.get(f) || []) pfamCats.add(c);
      const catDesc = new Set();
      if (pcat.size) {
        const kidsOf = new Map();
        for (const [c, p] of this.catParent) if (p) { if (!kidsOf.has(p)) kidsOf.set(p, []); kidsOf.get(p).push(c); }
        for (const c of pcat) catDesc.add(c);
        let frontier = [...pcat];
        while (frontier.length) {
          const nx = [];
          for (const x of frontier) for (const k of kidsOf.get(x) || []) if (!catDesc.has(k)) { catDesc.add(k); nx.push(k); }
          frontier = nx;
        }
      }
      const catAnc = new Set();
      for (const c of pcat) { let p = this.catParent.get(c); while (p && !catAnc.has(p)) { catAnc.add(p); p = this.catParent.get(p); } }
      const soldFams = new Set(), solSelling = new Set();
      for (const e of E.edges.get('SOLD_AS')) { if (psol.has(e[1]) && e[3] === 'family') soldFams.add(e[4]); if (pfam.has(e[4])) solSelling.add(e[1]); }
      const feat = new Set(), featN = new Map(), featCase = new Set();
      for (const e of E.edges.get('FEATURED_BY_SITE')) if (vset.has(e[1])) { feat.add(key(e[3], e[4])); if (e[3] === 'category') featN.set(e[4], (featN.get(e[4]) || 0) + 1); }
      for (const e of E.edges.get('FEATURED_CASE')) if (vset.has(e[1])) featCase.add(e[4]);
      const rec = new Set(), recN = new Map();
      for (const e of E.edges.get('RECOMMENDED_BY_SITE')) if (spset.has(e[1])) { rec.add(key(e[3], e[4])); if (e[3] === 'category') recN.set(e[4], (recN.get(e[4]) || 0) + 1); }
      // 타겟고객 → 사례
      const custDep = new Map();
      if (customer) {
        const toks = this.queryTokens(customer).map(norm).filter(Boolean);
        const tot = toks.reduce((a, t) => a + cpLen(t), 0);
        for (const d of this.g.deps) {
          // 글자 수로 가중한 토큰 포괄도(짧은 일반어 '체인'·'본사' 하나만 맞는 사례는 빠지게)
          const hay = norm([d.cust, d.title, d.sind].filter(Boolean).join(' '));
          let hit = 0;
          for (const t of toks) if (hay.includes(t)) hit += cpLen(t);
          const cov = tot ? hit / tot : 0;
          if (cov >= 0.5) custDep.set(d.id, cov);
        }
        ctx.customer = { text: customer, deployments: this.g.deps.filter((d) => custDep.has(d.id)).map((d) => ({ id: d.id, title: d.title, customer_type: d.cust, cov: pyRound(custDep.get(d.id), 2) })).slice(0, 12) };
      }
      // 가중치(입력 1배, 추론 0.5배)
      const w = {
        product: pset.size || caps.length ? W3.product * (pFrom === 'input' ? 1 : INFER) : 0,
        vertical: vset.size ? W3.vertical * (vFrom === 'input' ? 1 : INFER) : 0,
        space: spset.size ? W3.space * (spFrom === 'input' ? 1 : INFER) : 0,
        customer: customer ? W3.customer : 0,
        text: ctxText ? W3.text : 0,
      };
      const FIELDS = ['product', 'vertical', 'space', 'customer', 'text'];
      let tw = 0;
      for (const k of FIELDS) tw += w[k];
      ctx.weights = Object.fromEntries(FIELDS.map((k) => [k, pyRound(w[k], 3)]));
      ctx.missing = [['vertical', vset.size], ['space', spset.size], ['product', pset.size], ['customer', customer], ['text', text]].filter((x) => !x[1]).map((x) => x[0]);
      if (!tw) return this.envelope('E3', { context: ctx, headline: [], key_messages: [], products: [], cases: [], ranked: [], n_scored: 0, n_candidates: 0 }, { reasons: ['ASK'], t0 });

      // 엔티티 단위 일치도 — 항목마다 가장 높은 근거 하나
      const cache = new Map();
      const sortN = (arr, n) => arr.sort((a, b) => (n.get(b) - n.get(a)) || (a < b ? -1 : a > b ? 1 : 0));
      const ent = (kind, i) => {
        const ck = key(kind, i);
        if (cache.has(ck)) return cache.get(ck);
        const s = { product: 0, vertical: 0, space: 0, customer: 0 }, why = {};
        const up = (k, v, r) => { if (v > s[k]) { s[k] = v; why[k] = r; } };
        if (kind === 'family') {
          const fc = this.fcats.get(i) || new Set();
          if (pset.has(ck)) up('product', 1.0, '선택 제품');
          const hit = [...fc].filter((c) => pcat.has(c)).sort();
          if (hit.length) up('product', 0.8, `선택 분류 '${cn(hit[0])}'의 제품`);
          if (soldFams.has(i)) up('product', 0.8, '선택 솔루션의 판매 제품');
          const hc = [...(E.famCaps.get(i) || [])].filter((c) => capSet.has(c)).sort();
          if (hc.length) up('product', 0.5, `요구 역량 '${this.name('capability', hc[0])}' 제공`);
          const hf = sortN([...fc].filter((c) => featN.has(c)), featN);
          if (hf.length) up('vertical', Math.min(0.5, 0.2 + 0.1 * featN.get(hf[0])), `업종 페이지 추천 분류 '${cn(hf[0])}'(${featN.get(hf[0])}곳)의 제품`);
          const hr = sortN([...fc].filter((c) => recN.has(c)), recN);
          if (hr.length) up('space', Math.min(0.5, 0.2 + 0.1 * recN.get(hr[0])), `공간 추천 분류 '${cn(hr[0])}'(${recN.get(hr[0])}곳)의 제품`);
        } else if (kind === 'category') {
          if (pset.has(ck)) up('product', 1.0, '선택 분류');
          if (catDesc.has(i)) up('product', 0.8, '선택 분류의 하위 분류');
          if (pfamCats.has(i)) up('product', 0.6, '선택 제품의 분류');
          if (catAnc.has(i)) up('product', 0.5, '선택 분류의 상위 분류');
          if (featN.has(i)) up('vertical', 0.4, '업종 페이지 추천 분류');
          if (recN.has(i)) up('space', 0.4, '공간 추천 분류');
        } else if (kind === 'solution' || kind === 'service') {
          if (pset.has(ck)) up('product', 1.0, '선택 솔루션');
          if (solSelling.has(i)) up('product', 0.6, '선택 제품을 파는 솔루션');
          if (feat.has(ck)) up('vertical', 0.4, '업종 페이지 추천 솔루션');
          if (rec.has(ck)) up('space', 0.4, '공간 추천 솔루션');
        } else if (kind === 'deployment') {
          const du = E.depUse.get(i) || new Set();
          const catKeys = new Set([...pcat, ...pfamCats].map((c) => key('category', c)));
          if (setInter(du, pset)) up('product', 1.0, '선택 제품을 쓴 사례');
          else if (setInter(du, catKeys)) up('product', 0.6, '선택 제품 분류를 쓴 사례');
          const d = this.depById.get(i);
          const dv = new Set(d ? d.v || [] : []);
          const inV = setInter(dv, vset);
          if (inV || featCase.has(i)) up('vertical', 1.0, inV ? '업종 사례' : '업종 페이지 대표 사례');
          else if (vpar && dv.has(vpar)) up('vertical', 0.5, `상위 업종 '${vn(vpar)}' 사례`);
          if (setInter(E.depSpace.get(i) || new Set(), spset) || rec.has(key('deployment', i))) up('space', 1.0, '같은 공간 사례');
          if (custDep.has(i)) up('customer', custDep.get(i), `고객 유형 '${(d && d.cust) || ''}'`);
        } else if (kind === 'industry_section') {
          const sr = this.secById.get(i);
          if (sr) {
            if (vset.has(sr[1])) up('vertical', 1.0, `업종 '${vn(sr[1])}' 페이지 장면`);
            else if (vpar && sr[1] === vpar) up('vertical', 0.5, `상위 업종 '${vn(vpar)}' 페이지 장면`);
            if ((sr[10] || []).some((x) => spset.has(x))) up('space', 1.0, '같은 공간 장면');
            const its = E.secItems.get(i) || new Set();
            if (setInter(its, pset)) up('product', 0.8, '장면 항목에 선택 제품');
            else if ([...its].some((ki) => { const j = ki.indexOf('\u0001'), k = ki.slice(0, j), c = ki.slice(j + 1); return (k === 'category' && (catDesc.has(c) || pfamCats.has(c))) || (k === 'family' && setInter(this.fcats.get(c) || new Set(), pcat)); })) up('product', 0.6, '장면 항목에 선택 분류');
          }
        } else if (kind === 'vertical') {
          if (vset.has(i)) up('vertical', 1.0, `업종 '${vn(i)}' 헤드라인`);
          else if (vpar && i === vpar) up('vertical', 0.5, `상위 업종 '${vn(i)}' 헤드라인`);
        }
        const res = [s, why];
        cache.set(ck, res);
        return res;
      };

      // 문장 유사도 = 0.6 × LSA 코사인 + 0.4 × 토큰 포괄도
      const theme = ctxText || null;
      const toks = theme ? this.queryTokens(theme) : [];
      const dim = this.lsa ? this.lsa.dim : 0;
      const zq = theme && this.lsa && E.Z ? this.lsa.embed(theme) : null;
      const dot = (Z, i) => { let a = 0; const b = i * dim; for (let d = 0; d < dim; d++) a += Z[b + d] * zq[d]; return a; };
      const tsim = (cos, body) => {
        if (!theme) return 0;
        const kw = toks.length ? toks.filter((t) => body.includes(t)).length / toks.length : 0;
        return Math.max(0, Math.min(1, 0.6 * cos + 0.4 * kw));
      };
      const combine = (s0, why0, st, extra) => {
        const s = { ...s0 }, why = { ...why0 };
        if (extra) for (const k of Object.keys(extra)) { const [v, r] = extra[k]; if (v > s[k]) { s[k] = v; why[k] = r; } }
        s.text = st;
        if (st > 0) why.text = `요구사항 유사 ${pyRound(st, 2).toFixed(2)}`;
        let sc = 0;
        for (const k of FIELDS) sc += w[k] * s[k];
        sc /= tw;
        return [sc, s, FIELDS.filter((k) => w[k] && (s[k] || 0) > 0 && k in why).map((k) => why[k])];
      };

      const scored = new Array(M.length).fill(null);
      for (let idx = 0; idx < M.length; idx++) {
        const r = M[idx];
        if (locale && r[8] !== locale) continue;
        const [s, why] = ent(r[4], r[5]);
        const extra = {};
        if (r[6] && vset.has(r[6])) extra.vertical = [1.0, `업종 '${vn(r[6])}' 페이지 문구`];
        else if (vpar && r[6] === vpar) extra.vertical = [0.5, `상위 업종 '${vn(vpar)}' 페이지 문구`];
        if (r[7] && spset.has(r[7])) extra.space = [1.0, `공간 '${this.name('space_type', r[7])}' 장면 문구`];
        const [sc, sg, whyL] = combine(s, why, tsim(zq ? dot(E.Z, idx) : 0, r[2]), extra);
        if (sc > 0) scored[idx] = [pyRound(sc, 4), sg, whyL];
      }
      const aboutName = (k, i) => {
        if (k === 'industry_section') { const sr = this.secById.get(i); return sr ? `${vn(sr[1])} · ${sr[5] || ''}` : i; }
        return this.name(k, i);
      };
      const item = (idx, sc = null) => {
        const r = M[idx];
        const [s4, sg, whyL] = scored[idx] || [0, {}, []];
        const src = this.srcInfo(r[10]);
        return { id: r[0], level: r[1], text: r[2], about: [r[4], r[5]], about_name: aboutName(r[4], r[5]), score: pyRound(sc != null ? sc : s4, 3),
          signals: Object.fromEntries(Object.entries(sg).filter(([, v]) => v).map(([k, v]) => [k, pyRound(v, 2)])), reasons: whyL, claim_flag: r[9],
          source_url: src ? src.url : null, tier: r[11], method: r[12], parent_id: r[3] };
      };
      const order = [];
      for (let i = 0; i < M.length; i++) if (scored[i] && scored[i][0] >= MIN) order.push(i);
      order.sort((a, b) => (scored[b][0] - scored[a][0]) || (rank(M[a][1]) - rank(M[b][1])));
      // 같은 문장은 첫 번째만 남기고 개수를 센다
      const seen = new Map(), dedup = [];
      for (const i of order) {
        const k = norm(M[i][2]);
        if (seen.has(k)) { seen.get(k).dup += 1; continue; }
        const it = item(i);
        it.dup = 0;
        seen.set(k, it);
        dedup.push([i, it]);
      }
      const headline = dedup.filter(([i]) => M[i][1] === 'tagline').map((x) => x[1]).slice(0, 3);
      // 핵심 메시지(+근거 문장): 근거 문장 점수의 0.9배까지 끌어올린다
      const km = [];
      for (let idx = 0; idx < M.length; idx++) {
        const r = M[idx];
        if (!KM_KINDS.has(r[4]) || !(r[1] === 'key_message' || r[1] === 'proof_point') || (r[1] === 'proof_point' && r[3])) continue;
        if (locale && r[8] !== locale) continue;
        const own = scored[idx] ? scored[idx][0] : 0;
        let kid = 0;
        for (const j of this.mKids.get(r[0]) || []) if (scored[j] && scored[j][0] > kid) kid = scored[j][0];
        const eff = pyRound(Math.max(own, 0.9 * kid), 4);
        if (eff >= MIN) km.push([eff, idx]);
      }
      km.sort((a, b) => (b[0] - a[0]) || (rank(M[a[1]][1]) - rank(M[b[1]][1])));
      const keyMessages = [], kmSeen = new Set();
      for (const [eff, idx] of km) {
        const k = norm(M[idx][2]);
        if (kmSeen.has(k)) continue;
        kmSeen.add(k);
        const it = item(idx, eff);
        const kids = (this.mKids.get(M[idx][0]) || []).filter((j) => !locale || M[j][8] === locale)
          .sort((a, b) => (scored[b] ? scored[b][0] : 0) - (scored[a] ? scored[a][0] : 0));
        it.proof_points = kids.slice(0, 4).map((j) => item(j));
        keyMessages.push(it);
        if (keyMessages.length >= limit) break;
      }
      // 제품 메시지: 제품군별 묶음
      const groups = new Map();
      for (const [i, it] of dedup) {
        if (M[i][4] !== 'family') continue;
        if (!groups.has(M[i][5])) groups.set(M[i][5], []);
        const g = groups.get(M[i][5]);
        if (g.length < 4) g.push(it);
      }
      const prods = [...groups.entries()].slice(0, 8).map(([f, its]) => ({ kind: 'family', id: f, name: this.name('family', f), score: its[0].score, items: its }));
      // 근거 사례: 사례 단위 점수(문장 유사도는 제목·고객 유형·인용으로)
      const depMsgs = new Map();
      M.forEach((r, idx) => { if (r[4] === 'deployment' && (!locale || r[8] === locale)) { if (!depMsgs.has(r[5])) depMsgs.set(r[5], []); depMsgs.get(r[5]).push(idx); } });
      let cases = [];
      this.g.deps.forEach((d, j) => {
        if (!depMsgs.has(d.id) && !E.kpis.has(d.id)) return;
        const [s, why] = ent('deployment', d.id);
        const body = [d.title, d.cust, d.quote].filter(Boolean).join(' ');
        const st = theme ? tsim(zq && E.Zd ? dot(E.Zd, j) : 0, body) : 0;
        const [sc, sg, whyL] = combine(s, why, st);
        if (pyRound(sc, 4) < MIN) return;
        cases.push({ id: d.id, title: d.title, url: d.url, date: d.date, customer_type: d.cust, score: pyRound(sc, 3), _s: pyRound(sc, 4),
          signals: Object.fromEntries(Object.entries(sg).filter(([, v]) => v).map(([k, v]) => [k, pyRound(v, 2)])), reasons: whyL,
          quotes: (depMsgs.get(d.id) || []).map((i) => item(i)), kpis: (E.kpis.get(d.id) || []).slice(0, 4) });
      });
      cases.sort((a, b) => b._s - a._s);
      cases = cases.slice(0, 6);
      for (const c of cases) delete c._s;
      const ranked = dedup.slice(0, 60).map((x) => x[1]);
      if (ranked.some((it) => it.claim_flag) || cases.some((c) => c.kpis.some((k) => k.claim_flag))) needs.push('claim(수치·최상급) 문구는 대외 사용 전 원문 확인');
      if (cases.some((c) => c.quotes.length)) needs.push('사례 인용(T5)은 사례 원문에서 확인');
      const inferred = [['업종', vFrom], ['공간', spFrom], ['제품', pFrom]].filter((x) => x[1] === 'inferred').map((x) => x[0]);
      if (inferred.length) needs.push(`문장에서 추론한 ${inferred.join('·')}이 맞는지 확인`);
      return this.envelope('E3', { context: ctx, headline, key_messages: keyMessages, products: prods, cases, ranked, n_scored: scored.filter(Boolean).length, n_candidates: order.length },
        { reasons, needs, modes: ['sql', 'kg', 'rule', 'vec', 'kw'], t0, tiers: [...new Set(ranked.map((it) => it.tier).filter(Boolean))].sort() });
    }

    /* ── G. 이미지 ── */
    imgRows(pred, limit = 30) {
      // image_asset ⋈ image_occurrence ⋈ source_document, occurrence 순서(rowid)에서 자산별 첫 행
      const A = this.I.assets, GP = this.kw.GRADE_PRIORITY;
      const best = new Map();
      this.I.occ.forEach((o, oi) => {
        const a = A[o[0]];
        if (best.has(a[0])) return;
        if (!pred(a, o)) return;
        best.set(a[0], { a, o, oi });
      });
      const out = [...best.values()].sort((x, y) => ((GP[x.a[4]] ?? 9) - (GP[y.a[4]] ?? 9)) || ((x.a[6] === 'customer_case' ? 0 : 1) - (y.a[6] === 'customer_case' ? 0 : 1)));
      return out.slice(0, limit).map((r) => this.imgView(r.a, r.o));
    }
    imgView(a, o) {
      const d = this.docInfo(o[1]) || {};
      return { id: a[0], url: a[1], url_mobile: a[2], media_type: a[3], grade_hint: a[4], grade_hint_reason: a[5], rights: a[6], n: a[7],
        alt: o[3], caption: o[4], section_path: o[5] >= 0 ? this.core.SEC[o[5]] : null, sp: o[6], v: o[7], page_type: o[2], page_url: d.url, title: d.title,
        caption_rule: a[6] === 'customer_case' ? '도입사례 사진' : '예시 사진(삼성 공식 이미지)', space_name: o[6] ? this.name('space_type', o[6]) : null,
        entities: (o[8] || []).map(([k, i]) => [k, i, this.name(k, i)]) };
    }
    G1(space, category = null, vertical = null, limit = 20) {
      const t0 = now();
      const cats = category ? this.catSubtree(category) : new Set();
      const fams = new Set();
      if (category) for (const [fid, fc] of this.fcats) if (setInter(fc, cats)) fams.add(fid);
      const tgt = new Set([...cats, ...fams]);
      const entMatch = (r) => r.entities.some((e) => tgt.has(e[1]));
      const levels = [];
      const rows = this.imgRows((a, o) => o[6] === space && (!vertical || o[7] === vertical), 400);
      if (category) levels.push(['space+category', rows.filter(entMatch)]);
      levels.push(['space_only', rows]);
      if (category) {
        const ids = new Set([...tgt].slice(0, 900));
        const depAssets = new Set();
        for (const id of ids) for (const d of this.depictsByTarget.get(id) || []) depAssets.add(d[0]);
        const dep = this.imgRows((a, o) => depAssets.has(this.assetIdx.get(a[0])), 400);
        levels.push(['category_context', dep.filter((r) => ['A', 'A?C'].includes(r.grade_hint) && r.page_type !== 'pdp_gallery')]);
        levels.push(['category_product_cut', dep.filter((r) => r.grade_hint === 'C')]);
      }
      for (const [lv, rs] of levels) if (rs.length) {
        const fb = lv === levels[0][0] ? null : lv;
        return this.envelope('G1', { images: rs.slice(0, limit), level: lv }, { fallback: fb, modes: ['sql', 'kg'], t0, tiers: ['T2_official'], needs: ['VLM 판정 전: 등급은 페이지 유형·파일명 기반 힌트'] });
      }
      return this.envelope('G1', { images: [], level: null }, { fallback: 'none', t0 });
    }
    imageSearch(text, limit = 20, grade = null) {
      const t0 = now();
      const toks = this.queryTokens(text);
      const fused = new Map();
      const addF = (key, v) => fused.set(key, (fused.get(key) || 0) + v);
      const D = this.S.idocs;
      this.kwSearch(toks.filter((t) => cpLen(t) >= 3).join(' ') || text, 'image', 100).forEach(([d], r) => addF(D[d][0], 1 / (60 + r)));
      this.likeSearch(toks, this.idocLower, 200).forEach((d, r) => addF(D[d][0], 1 / (60 + r)));
      this.vecSearch(text, 'image', 100).forEach(([ref], r) => addF(ref.slice(ref.indexOf(':') + 1), 1 / (60 + r)));
      const ids = [...fused.entries()].sort((a, b) => b[1] - a[1]).slice(0, 400).map((x) => x[0]);
      if (!ids.length) return this.envelope('image_search', { tokens: toks, images: [] }, { t0 });
      const idSet = new Set(ids);
      const rows = new Map(this.imgRows((a) => idSet.has(a[0]), 1000).map((r) => [r.id, r]));
      const mx = Math.max(...ids.map((a) => fused.get(a)));
      const GP = this.kw.GRADE_PRIORITY;
      const scored = [];
      for (const a of ids) {
        const r = rows.get(a);
        if (!r || (grade && !grade.includes(r.grade_hint))) continue;
        const doc = this.idocById.get(a) || '';
        const cov = toks.length ? toks.filter((t) => doc.includes(t)).length / toks.length : 0;
        scored.push([0.4 * fused.get(a) / mx + 0.6 * cov - 0.02 * (GP[r.grade_hint] ?? 9), a]);
      }
      scored.sort((x, y) => y[0] - x[0]);
      return this.envelope('image_search', { tokens: toks, images: scored.slice(0, limit).map(([s, a]) => ({ ...rows.get(a), score: pyRound(s, 4) })) }, { modes: ['kw', 'vec'], t0 });
    }

    /* ── 시나리오 체인 ── */
    S1(text, limit = 8) {
      const t0 = now();
      const a2 = this.A2(text);
      const vertical = a2.result.top2.length ? a2.result.top2[0].id : null;
      const clauses = text.split(CLAUSE_SPLIT).filter((c) => c && c.trim());
      let groups = [];
      let carry = null;
      for (const cl of clauses) {
        const links = this.A1(cl).result.links;
        let sps = links.filter((l) => l.type === 'space_type').map((l) => l.id);
        const cats = links.filter((l) => l.type === 'category').map((l) => l.id);
        const caps = links.filter((l) => l.type === 'capability').map((l) => l.id);
        if (!sps.length && carry && (cats.length || caps.length)) sps = [carry];
        if (sps.length) carry = sps[sps.length - 1];
        if (sps.length || cats.length || caps.length) groups.push({ clause: cl, spaces: sps, categories: cats, capabilities: caps });
      }
      if (!groups.length) groups = [{ clause: text, spaces: [], categories: [], capabilities: [] }];
      const merged = new Map();
      for (const g of groups) for (const sp of g.spaces.length ? g.spaces : [null]) {
        if (!merged.has(sp)) merged.set(sp, { space: sp, clauses: [], categories: [], capabilities: [] });
        const m = merged.get(sp);
        m.clauses.push(g.clause);
        for (const c of g.categories) if (!m.categories.includes(c)) m.categories.push(c);
        for (const c of g.capabilities) if (!m.capabilities.includes(c)) m.capabilities.push(c);
      }
      const glob = merged.get(null);
      merged.delete(null);
      if (glob && merged.size) {
        for (const m of merged.values()) {
          for (const c of glob.categories) if (!m.categories.includes(c)) m.categories.push(c);
          for (const c of glob.capabilities) if (!m.capabilities.includes(c)) m.capabilities.push(c);
        }
      } else if (glob) merged.set(null, glob);
      const perSpace = [], allCaps = [], allTargets = [];
      for (const [sp, m] of merged) {
        const req = sp ? this.req.get(sp) || [] : [];
        const hard = [...m.capabilities, ...req.filter((r) => r[2] === 'hard' && !m.capabilities.includes(r[1])).map((r) => r[1])];
        const softL = req.filter((r) => r[2] === 'soft' && !hard.includes(r[1])).map((r) => r[1]);
        let cat = m.categories.length ? m.categories[0] : null;
        const ctext = m.clauses.join(' ');
        let c2 = this.C2(hard, cat, sp, vertical, limit, softL, ctext);
        if (cat && hard.length && (c2.decision_reasons.includes('HARD_CONFLICT') || !c2.result.families.length)) {
          const c2b = this.C2(hard, null, sp, vertical, limit, softL, ctext);
          if (c2b.result.families.length && !c2b.decision_reasons.includes('HARD_CONFLICT')) {
            c2 = c2b;
            c2.decision_reasons = [...new Set([...c2.decision_reasons, 'CATEGORY_RELAXED'])].sort();
            cat = null;
          }
        }
        perSpace.push({ space: sp, space_name: sp ? this.name('space_type', sp) : null, clauses: m.clauses, category: cat, category_name: cat ? this.name('category', cat) : null,
          capabilities: { hard, soft: softL }, families: c2.result.families, solutions: c2.result.solutions.slice(0, 6), decision_reasons: c2.decision_reasons, n_pool: c2.result.n_pool });
        for (const c of [...hard, ...softL]) if (!allCaps.includes(c)) allCaps.push(c);
        for (const c of m.categories) allTargets.push(['category', c]);
        for (const f of c2.result.families.slice(0, 3)) allTargets.push(['family', f.id]);
      }
      const spaces = perSpace.filter((p) => p.space).map((p) => p.space);
      const d1 = this.D1(vertical, spaces, allTargets, text, 5);
      const reasons = [...a2.decision_reasons, ...perSpace.flatMap((p) => p.decision_reasons.filter((r) => r === 'HARD_CONFLICT'))];
      return this.envelope('S1', { vertical: a2.result.top2, vertical_all: a2.result.all, by_space: perSpace, capabilities: allCaps.map((c) => ({ id: c, name: this.name('capability', c) })),
        similar_cases: d1.result.deployments, links: this.A1(text).result.links, gaps: this.B2(text).result.gaps },
        { reasons, modes: ['sql', 'kg', 'rule', 'vec'], t0, tiers: ['T2_official', 'T5_rule_draft', ...(spaces.length ? ['T5_seed_draft'] : [])],
          needs: ['역량·requires 는 초안(전문가 승인 전)', '판매 상태(단종·미판매)는 사이트 목록 노출 여부만 반영'] });
    }
  }

  const now = () => (typeof performance !== 'undefined' ? performance.now() : Date.now());

  const api = { KB, Lsa, parseVec, FtsIndex, norm, pyRound, combinations };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.WKB = api;
})(typeof self !== 'undefined' ? self : this);
