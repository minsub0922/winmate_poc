/* Winmate KB 검증 대시보드 — 화면 로직(데이터 로딩·탭·드로어·검수 표시) */
(function () {
  'use strict';
  const W = window.WKB;
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
  const esc = (s) => (s == null ? '' : String(s)).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmt = (n) => (n == null || n === '' ? '' : Number(n).toLocaleString('ko-KR'));
  const pct = (x) => (x == null ? '–' : Math.round(x * 1000) / 10 + '%');
  const enc = new TextEncoder();
  const fnv36 = (s) => { let h = 0x811c9dc5; for (const b of enc.encode(s)) { h ^= b; h = Math.imul(h, 0x01000193) >>> 0; } return (h >>> 0).toString(36); };
  const reEsc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const store = {
    get(k, d) { try { const v = localStorage.getItem('wkb.' + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem('wkb.' + k, JSON.stringify(v)); } catch (e) { /* 저장 불가 환경 */ } },
  };
  const groupBy = (arr, f) => { const m = new Map(); for (const x of arr) { const k = f(x); let a = m.get(k); if (!a) { a = []; m.set(k, a); } a.push(x); } return m; };
  function toast(msg) { const t = $('#toast'); t.textContent = msg; t.classList.add('on'); clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove('on'), 2800); }
  const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };

  /* ── 표시용 이름 ── */
  const L = {
    pt: { industry: '업종 페이지', case_study: '도입사례', case_list: '사례 목록', landing: '랜딩', solution: '솔루션', service: '서비스', pdp: '상품 상세', pdp_feature: '상품 특장점', pdp_gallery: '상품 갤러리', spec: '스펙 API', us_vertical: 'US 업종', us_solution: 'US 솔루션', us_landing: 'US 랜딩', category_list: '상품 목록' },
    grade: { A: '설치·사용 장면', 'A?C': '장면 또는 제품 컷(미판정)', B: '공간 위주', C: '제품 단독 컷', D: '도식·UI', E: '아이콘·로고' },
    status: { ready: '준비됨', partial: '부분', blocked_by_source: '소스 부족', blocked: '막힘', draft: '초안', active: '사용', missing: '없음' },
    hint: { auto: '자동 확정', check: '확인 필요', ask: '질문 필요' },
    reason: { LOW_MARGIN: '1·2위 차이 작음', LOW_SCORE: '점수 낮음', LOW_TIER: '근거 등급 낮음(초안 규칙)', FALLBACK_USED: '폴백 사용', HARD_CONFLICT: '필수 역량 충돌', CATEGORY_RELAXED: '카테고리 조건 완화', AMBIGUOUS_INDUSTRY: '업종 애매', ASK: '질문 필요', NOT_FOUND: '없음' },
    kind: { family: '제품군', model: '모델', category: '카테고리', solution: '솔루션', service: '서비스', vertical: '업종', space_type: '공간', deployment: '도입사례', capability: '역량', industry_section: '업종 섹션', section: '업종 장면', item: '장면 항목', provides: '역량 근거', image: '이미지', message: '메시지', kpi: 'KPI', dep_item: '사례 제품 해소', dep_space: '사례 공간', s1: '요구사항 추천', search: '검색 결과', a2: '업종 판별', spec: '핵심 스펙', requires: '공간 요구 역량', segment: '세그먼트 대응', test: '시나리오 테스트', ctxmsg: '컨텍스트 → 메시지', document: '문서' },
    level: { tagline: '태그라인', key_message: '핵심 메시지', proof_point: '근거 문장', usp: 'USP' },
    verdict: { ok: '맞음', wrong: '틀림', unsure: '모름' },
    mt: { image: '이미지', animation: '움직이는 이미지', video: '동영상', vector: '벡터 이미지' },
    role: { list: '목록', comp: '비교 분류' },
    scheme: { kr_site: 'KR 업종', us_site: 'US 업종', winmate16: 'Winmate 세그먼트' },
  };
  const ptName = (p) => L.pt[p] || p || '';
  const kindName = (k) => L.kind[k] || k;
  const gcls = (g) => (g === 'A?C' ? 'AC' : g || '');
  const statusPill = (s) => `<span class="pill ${s === 'ready' ? 'p-ok' : s === 'partial' ? 'p-warn' : s && s.startsWith('blocked') ? 'p-bad' : 'p-mute'}">${esc(L.status[s] || s || '–')}</span>`;
  const hintPill = (h) => `<span class="pill ${h === 'auto' ? 'p-ok' : h === 'ask' ? 'p-bad' : 'p-warn'}">${esc(L.hint[h] || h)}</span>`;
  const reasonPill = (r) => `<span class="pill p-mute" title="${esc(r)}">${esc(L.reason[r] || r)}</span>`;
  const passPill = (ok) => `<span class="pill ${ok ? 'p-ok' : 'p-bad'}">${ok ? '통과' : '실패'}</span>`;
  const tierPill = (t) => (t ? `<span class="pill ${/^T[12]/.test(t) ? 'p-acc' : /^T3/.test(t) ? 'p-info' : 'p-warn'}" title="근거 등급">${esc(t)}</span>` : '');
  const ext = (url, text = '원문') => (url ? `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(text)} ↗</a>` : '');

  /* ── 데이터 로딩(지연 로딩·여러 조각 이어붙이기·gzip 풀기) ── */
  const Load = {
    manifest: null, active: new Map(), groups: new Map(),
    async man() {
      if (!this.manifest) { const r = await fetch('data/manifest.json'); if (!r.ok) throw new Error('manifest HTTP ' + r.status); this.manifest = await r.json(); }
      return this.manifest;
    },
    paint() {
      let tot = 0;
      for (const v of this.active.values()) tot += v;
      $('#loadbar').classList.toggle('on', this.active.size > 0);
      $('#loadmsg').textContent = this.active.size ? `데이터 받는 중 ${(tot / 1048576).toFixed(1)} MB` : '';
    },
    async part(url, key, encd) {
      const r = await fetch(url);
      if (!r.ok) throw new Error(url + ' HTTP ' + r.status);
      let u8;
      if (r.body && r.body.getReader) {
        const rd = r.body.getReader(), cs = [];
        let n = 0;
        for (;;) { const { done, value } = await rd.read(); if (done) break; cs.push(value); n += value.length; this.active.set(key, n); this.paint(); }
        u8 = new Uint8Array(n);
        let o = 0;
        for (const c of cs) { u8.set(c, o); o += c.length; }
      } else u8 = new Uint8Array(await r.arrayBuffer());
      if (encd === 'b64') {
        const s = new TextDecoder().decode(u8).replace(/\s+/g, ''), bin = atob(s);
        u8 = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
      }
      return u8;
    },
    async bytes(name) {
      const m = await this.man();
      const e = m.files[name];
      if (!e) throw new Error('데이터 파일 없음: ' + name);
      try {
        const parts = await Promise.all(e.parts.map((p, i) => this.part('data/' + p, name + '#' + i, e.enc)));
        if (parts.length === 1) return parts[0];
        const n = parts.reduce((a, p) => a + p.length, 0), out = new Uint8Array(n);
        let o = 0;
        for (const p of parts) { out.set(p, o); o += p.length; }
        return out;
      } finally { e.parts.forEach((p, i) => this.active.delete(name + '#' + i)); this.paint(); }
    },
    async gunzip(u8) {
      if (u8.length > 2 && u8[0] === 0x1f && u8[1] === 0x8b) {
        if (typeof DecompressionStream === 'undefined') throw new Error('이 브라우저는 gzip 풀기(DecompressionStream)를 지원하지 않습니다');
        const s = new Blob([u8]).stream().pipeThrough(new DecompressionStream('gzip'));
        return new Uint8Array(await new Response(s).arrayBuffer());
      }
      return u8;
    },
    async json(name) { return JSON.parse(new TextDecoder().decode(await this.gunzip(await this.bytes(name)))); },
    async bin(name) { const u8 = await this.gunzip(await this.bytes(name)); return u8.byteOffset === 0 && u8.byteLength === u8.buffer.byteLength ? u8.buffer : u8.slice().buffer; },
    has(name) { return !!(this.manifest && this.manifest.files[name]); },
    size(names) { return names.reduce((a, n) => a + ((this.manifest && this.manifest.files[n] && this.manifest.files[n].size) || 0), 0); },
    group(g, fn) {
      if (!this.groups.has(g)) this.groups.set(g, fn().catch((e) => { this.groups.delete(g); throw e; }));
      return this.groups.get(g);
    },
  };

  const D = { core: null, g: null, kb: null, parity: null, msgs: null, thumbs: null, pdp: null, images: null };
  const IX = {};   // 화면용 보조 색인

  const need = {
    msgs: () => Load.group('msgs', async () => { indexMsgs(await Load.json('msgs.json.gz')); }),
    images: () => Load.group('images', async () => {
      const [im] = await Promise.all([Load.json('images.json.gz'), Load.has('thumbs.json.gz') ? loadThumbs().catch(() => null) : null]);
      D.images = im;
      D.kb.attachImages(im);
      indexImages(im);
    }),
    pdp: () => Load.group('pdp', async () => {
      const p = await Load.json('pdp.json.gz');
      D.pdp = { feats: groupBy(p.feats, (f) => f[1]), specs: groupBy(p.specs, (s) => s[1]) };
    }),
    search: () => Load.group('search', async () => { D.kb.attachSearch(await Load.json('search.json.gz')); }),
    vec: () => Load.group('vec', async () => {
      const [voc, lsa, refs, core] = await Promise.all([Load.json('lsa_vocab.json.gz'), Load.bin('lsa.bin'), Load.json('vec_refs.json.gz'), Load.bin('vec_core.bin')]);
      D.vecRefs = refs;
      D.kb.attachVectors(new W.Lsa(voc, lsa), W.parseVec(core, refs, refs.files['vec_core.bin']));
    }),
    vecChunk: () => Load.group('vecChunk', async () => {
      await need.vec();
      const buf = await Load.bin('vec_chunk.bin');
      D.kb.attachVectors(null, W.parseVec(buf, D.vecRefs, D.vecRefs.files['vec_chunk.bin']));
    }),
  };

  /* 썸네일: 색인(thumbs.json.gz)은 이미지 데이터와 함께, 묶음(thumbs_NN.bin)은 화면에 보일 때 그 묶음만 받는다 */
  async function loadThumbs() {
    const t = await Load.json('thumbs.json.gz');
    D.thumbs = { idx: t.idx, n: t.packs, packs: new Map(), urls: new Map() };
  }
  const packName = (n) => `thumbs_${String(n).padStart(2, '0')}.bin`;
  function ensurePack(n) {
    const T = D.thumbs;
    if (!T.packs.has(n)) {
      const p = Load.bin(packName(n)).then((buf) => { p.u8 = new Uint8Array(buf); return p.u8; });
      p.catch(() => T.packs.delete(n));
      T.packs.set(n, p);
    }
    return T.packs.get(n);
  }
  const hasThumb = (aid) => !!(D.thumbs && D.thumbs.idx[aid]);
  function thumbURL(aid) {
    const T = D.thumbs, e = T && T.idx[aid];
    if (!e) return null;
    let u = T.urls.get(aid);
    if (u) return u;
    const p = T.packs.get(e[0]);
    if (!p || !p.u8) return null;
    u = URL.createObjectURL(new Blob([p.u8.subarray(e[1], e[1] + e[2])], { type: 'image/webp' }));
    T.urls.set(aid, u);
    return u;
  }
  function thumbDataURL(aid) {
    const T = D.thumbs, e = T && T.idx[aid], p = e && T.packs.get(e[0]);
    if (!p || !p.u8) return '';
    const b = p.u8.subarray(e[1], e[1] + e[2]);
    let s = '';
    for (let i = 0; i < b.length; i += 0x8000) s += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000));
    return 'data:image/webp;base64,' + btoa(s);
  }
  document.addEventListener('error', (ev) => {   // blob: 이 막힌 환경이면 data: 로 바꿔 다시 시도
    const t = ev.target;
    if (t && t.tagName === 'IMG' && t.dataset.aid && !t.dataset.fb) { t.dataset.fb = '1'; t.src = thumbDataURL(t.dataset.aid); }
  }, true);
  /* 화면에 그려진 빈 썸네일(<img data-aid> src 없음)을 묶음이 도착하는 대로 채운다 */
  function hydrateThumbs(root) {
    if (!D.thumbs) return;
    const byPack = new Map();
    for (const img of $$('img[data-aid]:not([src])', root)) {
      const e = D.thumbs.idx[img.dataset.aid];
      if (!e) continue;
      if (!byPack.has(e[0])) byPack.set(e[0], []);
      byPack.get(e[0]).push(img);
    }
    for (const [n, imgs] of byPack) ensurePack(n).then(() => { for (const img of imgs) { const u = thumbURL(img.dataset.aid); if (u) img.src = u; } }).catch(() => {});
  }
  function imgTag(aid, alt) {
    const u = thumbURL(aid);
    return `<img loading="lazy" alt="${esc(alt || '')}" data-aid="${esc(aid)}"${u ? ` src="${u}"` : ''}>`;
  }
  function thumbHTML(a, opts = {}) {
    const aid = a[0], g = a[4];
    const gb = opts.grade !== false && g ? `<span class="grade g-${gcls(g)}" title="${esc(L.grade[g] || g)}">${esc(g)}</span>` : '';
    if (hasThumb(aid)) return `<div class="thumb">${gb}${imgTag(aid, opts.alt)}</div>`;
    return `<div class="thumb nothumb">${gb}<div class="ph"><span>${esc(L.mt[a[3]] || '이미지')} · 미리보기 없음</span>${ext(a[1] || a[2], '원본 열기')}</div></div>`;
  }
  /* 작은 자리(장면 항목·검색 결과 등): 누르면 이미지 상세 */
  function miniImg(a, cls = '') {
    if (hasThumb(a[0])) return `<button class="mini ${cls}" data-open="image:${esc(a[0])}" title="${esc(L.grade[a[4]] || '')}">${thumbHTML(a)}</button>`;
    return `<a class="chip" href="${esc(a[1] || a[2] || '#')}" target="_blank" rel="noopener" title="${esc(L.grade[a[4]] || '')}"><span class="grade g-${gcls(a[4])}" style="height:16px;min-width:22px;font-size:10.5px">${esc(a[4] || '–')}</span>원본 ↗</a>`;
  }
  /* 자산 인덱스 목록 → 작은 썸네일 줄(최대 max, 나머지는 개수) */
  function stripHTML(assetIdxs, max = 8, cls = '') {
    if (!D.images || !assetIdxs || !assetIdxs.length) return '';
    const uniq = [...new Set(assetIdxs)];
    const GP = D.kb.kw.GRADE_PRIORITY;
    uniq.sort((x, y) => (+!hasThumb(D.images.assets[x][0])) - (+!hasThumb(D.images.assets[y][0])) || (GP[D.images.assets[x][4]] ?? 9) - (GP[D.images.assets[y][4]] ?? 9));
    return `<div class="tiny-thumbs ${cls}">${uniq.slice(0, max).map((i) => miniImg(D.images.assets[i])).join('')}${uniq.length > max ? `<span class="xs faint" style="align-self:center">+${uniq.length - max}</span>` : ''}</div>`;
  }

  /* ── 보조 색인 ── */
  function indexBase() {
    const g = D.g;
    IX.depItems = groupBy(g.dep_items, (r) => r[0]);
    IX.depSpace = groupBy(g.dep_space, (r) => r[0]);
    IX.depNeed = groupBy(g.dep_need, (r) => r[0]);
    IX.kpi = groupBy(g.kpis, (r) => r[1]);
    IX.ment = groupBy(g.ment, (r) => r[0] + '\u0001' + r[1]);
    IX.photo = new Set(g.dep_photo);
    IX.secByVert = groupBy(g.sections, (s) => s[1]);
    IX.itemById = new Map(g.items.map((it) => [it[0], it]));
    IX.capFams = groupBy(g.prov, (p) => p[2]);
    IX.vName = (v) => D.kb.name('vertical', v);
  }
  /* ── 계층 검색: 이름·모델·별칭 + 소속 분류와 그 상위 분류(별칭 포함) + 사이트 필터 라벨 ── */
  const nz = (t) => W.norm(t || '');
  const queryTokens = (q) => (q || '').trim().split(/\s+/).map(nz).filter(Boolean);
  function aliasesOf(kind, id) {
    if (!IX.aliasByTarget) { IX.aliasByTarget = new Map(); for (const a of D.g.alias) { const k = a[2] + '\u0001' + a[3]; if (!IX.aliasByTarget.has(k)) IX.aliasByTarget.set(k, new Set()); IX.aliasByTarget.get(k).add(a[0]); } }
    return [...(IX.aliasByTarget.get(kind + '\u0001' + id) || [])];
  }
  function famFields(f) {
    if (!IX.famFields) IX.famFields = new Map();
    let fields = IX.famFields.get(f.id);
    if (fields) return fields;
    fields = [];
    const add = (w, label, text) => { if (text) fields.push({ w, label, text, n: nz(text) }); };
    const kb = D.kb;
    add(3, '이름', f.name);
    add(3, '모델', [f.model, f.mkt, ...(kb.modelsByFam.get(f.id) || []).map((m) => m[1])].filter(Boolean).join(' '));
    for (const a of aliasesOf('family', f.id)) add(2.5, '별칭', a);
    const catRow = IX.catRow || (IX.catRow = new Map(D.core.CAT.map((c) => [c[0], c])));
    for (const cid of kb.fcats.get(f.id) || []) {
      const r = catRow.get(cid);
      if (!r) continue;
      const own = cid === f.cat || f.cats.some((x) => x[0] === cid) || cid === f.cat + '__' + f.sub;
      add(own ? 2 : 1.8, own ? '분류' : '상위 분류', r[2]);
      for (const a of aliasesOf('category', cid)) if (nz(a) !== nz(r[2])) add(own ? 2 : 1.8, own ? '분류 별칭' : '상위 분류 별칭', a);
    }
    add(2, '사이트 분류', (f.ctg || []).filter(Boolean).join(' > '));
    const seen = new Set();
    for (const t of kb.tagsByFam.get(f.id) || []) { const lab = t[6] || t[2]; if (lab && !seen.has(lab)) { seen.add(lab); add(1, '필터 ' + (t[5] || ''), lab); } }
    IX.famFields.set(f.id, fields);
    return fields;
  }
  /* 토큰마다 가장 높은 가중치의 필드를 찾는다. 모든 토큰이 맞아야 일치 → {score, hits:[[label,text]]} */
  function matchFields(fields, toks) {
    let score = 0;
    const hits = [];
    for (const t of toks) {
      let best = null;
      for (const fd of fields) if (fd.n.includes(t) && (!best || fd.w > best.w)) best = fd;
      if (!best) return null;
      score += best.w + (best.n === t ? 0.5 : 0);
      if (!hits.some((h) => h[1] === best.text)) hits.push([best.label, best.text]);
    }
    return { score, hits };
  }
  const hitsHTML = (hits) => (hits && hits.length && !hits.every((h) => h[0] === '이름') ? `<div class="xs" style="color:var(--accent-text)">일치: ${hits.map(([l, t]) => `${esc(l)} '${esc(t.length > 40 ? t.slice(0, 40) + '…' : t)}'`).join(' · ')}</div>` : '');
  /* 질의와 이름·별칭이 맞는 분류 → 바로가기 */
  function matchingCategories(toks) {
    if (!toks.length) return [];
    const out = [];
    for (const c of D.core.CAT) {
      const names = [c[2], ...aliasesOf('category', c[0])];
      const n = names.map(nz).join(' ');
      if (toks.every((t) => n.includes(t))) {
        let cnt = 0;
        for (const f of D.g.fam) if (D.kb.fcats.get(f.id).has(c[0])) cnt++;
        if (cnt) out.push([c, cnt]);
      }
    }
    return out.sort((a, b) => a[0][3] - b[0][3] || b[1] - a[1]).slice(0, 12);
  }
  function indexMsgs(v) {
    D.msgs = v;
    IX.msgById = new Map(v.map((m) => [m[0], m]));
    IX.msgByAbout = groupBy(v, (m) => m[4] + '\u0001' + m[5]);
    IX.msgKids = groupBy(v.filter((m) => m[3]), (m) => m[3]);
    D.kb.attachMsgs(v);
  }
  function indexImages(im) {
    IX.occByAsset = groupBy(im.occ, (o) => o[0]);
    IX.depictsByTarget = groupBy(im.depicts, (d) => d[1] + '\u0001' + d[2]);
    IX.depictsByAsset = groupBy(im.depicts, (d) => d[0]);
    IX.assetIdx = new Map(im.assets.map((a, i) => [a[0], i]));
    IX.occByDoc = groupBy(im.occ, (o) => o[1]);
    IX.famGallery = new Map();
    for (const d of im.depicts) {
      if (d[1] !== 'family' || IX.famGallery.has(d[2])) continue;
      const occ = IX.occByAsset.get(d[0]) || [];
      if (occ.some((o) => o[2] === 'pdp_gallery')) IX.famGallery.set(d[2], d[0]);
    }
    IX.depFirstPhoto = new Map();
    for (const d of im.depicts) {
      if (d[1] !== 'deployment') continue;
      const cur = IX.depFirstPhoto.get(d[2]);
      if (cur == null || (!hasThumb(im.assets[cur][0]) && hasThumb(im.assets[d[0]][0]))) IX.depFirstPhoto.set(d[2], d[0]);
    }
  }
  const targetAssets = (kind, id) => (IX.depictsByTarget && IX.depictsByTarget.get(kind + '\u0001' + id) || []).map((d) => d[0]);
  /* 엔티티 → 대표 이미지(자산 인덱스) */
  function entityImage(kind, id) {
    if (!D.images) return null;
    const pick = (arr) => { const a = (arr || []).filter((i) => i != null); return a.find((i) => hasThumb(D.images.assets[i][0])) ?? a[0] ?? null; };
    if (kind === 'image') return IX.assetIdx.get(id) ?? null;
    if (kind === 'family') return IX.famGallery.get(id) ?? pick(targetAssets('family', id));
    if (kind === 'deployment') return IX.depFirstPhoto.get(id) ?? null;
    if (kind === 'industry_section') {
      const its = D.kb.itemsBySec.get(id) || [];
      const fromItems = [];
      for (const it of its) for (const aid of it[14] || []) fromItems.push(IX.assetIdx.get(aid));
      const sec = D.kb.secById.get(id);
      return pick(fromItems.length ? fromItems : docImages(sec ? sec[2] : -1, null, sec ? sec[5] : null));
    }
    if (kind === 'vertical') { const ss = IX.secByVert.get(id) || []; for (const s2 of ss) { const x = entityImage('industry_section', s2[0]); if (x != null) return x; } return null; }
    if (kind === 'space_type') { if (!IX.spaceFirst) { IX.spaceFirst = new Map(); D.images.occ.forEach((o) => { if (o[6] && !IX.spaceFirst.has(o[6]) && hasThumb(D.images.assets[o[0]][0])) IX.spaceFirst.set(o[6], o[0]); }); } return IX.spaceFirst.get(id) ?? null; }
    return pick(targetAssets(kind, id));
  }
  function entityThumb(kind, id) {
    const i = entityImage(kind, id);
    return i != null && hasThumb(D.images.assets[i][0]) ? `<div class="tiny-thumbs sm" style="margin:0">${miniImg(D.images.assets[i])}</div>` : '';
  }
  /* 같은 문서·섹션에 나온 이미지(섹션이 없으면 문서 전체) */
  function docImages(di, section, title) {
    const occ = (IX.occByDoc && IX.occByDoc.get(di)) || [];
    let hit = [];
    if (section) hit = occ.filter((o) => o[5] >= 0 && D.core.SEC[o[5]] === section);
    if (!hit.length && title) hit = occ.filter((o) => o[5] >= 0 && D.core.SEC[o[5]].includes(title));
    return hit.map((o) => o[0]);
  }
  /* 자산 인덱스 집합 → 이미지 카드 격자(등급·사례 사진 우선) */
  function imgGrid(idxs, limit = 24) {
    const set = new Set(idxs);
    if (!set.size) return '';
    const rows = D.kb.imgRows((a) => set.has(IX.assetIdx.get(a[0])), limit);
    return `<div class="igrid">${rows.map((v) => imgCard(v)).join('')}</div>${set.size > limit ? `<div class="xs faint" style="margin-top:6px">${set.size}장 중 ${limit}장</div>` : ''}`;
  }
  const assetById = (aid) => { const i = IX.assetIdx && IX.assetIdx.get(aid); return i == null ? null : D.images.assets[i]; };

  /* ── 검수 표시(db + user) ── */
  const R = { db: null, user: null, uid: null, canWrite: false, state: 'wait', docs: new Map(), byTarget: new Map(), names: {} };
  const tkey = (k, i) => k + '\u0001' + i;
  const safeSeg = (s) => String(s || 'anon').replace(/[^A-Za-z0-9_\-.~:@+]/g, '_').slice(0, 120);
  async function initReviews() {
    try {
      if (!window.claude || typeof window.claude.use !== 'function') { R.state = 'off'; paintWho(); return; }
      const [db, user] = await Promise.all([window.claude.use('db'), window.claude.use('user')]);
      R.db = db; R.user = user;
      if (!db) { R.state = 'off'; paintWho(); return; }
      R.uid = user ? await user.id() : null;
      const cw = user ? await user.can('data.write') : null;
      R.canWrite = !!R.uid && cw !== false;
      R.state = R.canWrite ? 'on' : 'ro';
      if (user) { try { const me = await user.me(); R.myName = me && me.name; } catch (e) { /* 이름 없음 */ } }
      paintWho();
      db.collection('reviews').onSnapshot((snap) => {
        R.docs.clear(); R.byTarget.clear();
        for (const d of snap.docs) {
          const v = d.data();
          if (!v || !v.kind) continue;
          const row = Object.assign({ _id: d.id }, v);
          R.docs.set(d.id, row);
          const k = tkey(v.kind, v.id);
          if (!R.byTarget.has(k)) R.byTarget.set(k, []);
          R.byTarget.get(k).push(row);
        }
        paintReviews(document);
        $('#rvcount').textContent = R.docs.size ? String(R.docs.size) : '';
        resolveNames();
        if (current === 'reviews') renderReviewList();
      }, (err) => { R.state = 'err'; R.err = err && err.code; paintWho(); });
    } catch (e) { R.state = 'off'; paintWho(); }
  }
  async function resolveNames() {
    if (!R.user) return;
    const ids = [...new Set([...R.docs.values()].map((d) => d.by).filter(Boolean))].filter((i) => !(i in R.names));
    if (!ids.length) return;
    try { const ps = await R.user.profiles(ids); for (const i of ids) R.names[i] = (ps[i] && ps[i].name) || ''; } catch (e) { for (const i of ids) R.names[i] = ''; }
    if (current === 'reviews') renderReviewList();
  }
  const whoName = (id) => (id && id === R.uid ? '나' : R.names[id] || '다른 검수자');
  function paintWho() {
    const el = $('#who'), t = $('#whotext');
    el.classList.toggle('on', R.state === 'on');
    t.textContent = { wait: '검수 연결 중', on: '검수 저장 켜짐' + (R.myName ? ' · ' + R.myName : ''), ro: '검수 보기 전용', off: '검수 저장 꺼짐', err: '검수 저장 오류' }[R.state] || '';
    el.title = { on: '맞음·틀림·모름 표시가 이 페이지를 여는 사람 모두에게 공유됩니다', ro: '이 계정은 표시를 볼 수만 있습니다(공유 권한이 보기 전용)', off: '이 화면에서는 검수 저장을 쓸 수 없습니다(로그인 필요)', err: '저장소 오류: ' + (R.err || '') }[R.state] || '';
  }
  /* 검수 버튼: kind·id 로 대상을 식별, label 은 목록 표시용, ctx 는 대상을 다시 여는 정보 */
  function rv(kind, id, label, ctx, opts = {}) {
    const fix = opts.fix ? `<select data-fix title="고친 값">${['', ...opts.fix].map((g) => `<option value="${esc(g)}">${g ? esc(g) : '고친 값'}</option>`).join('')}</select>` : '';
    return `<span class="rv" data-k="${esc(kind)}" data-i="${esc(id)}" data-l="${esc(label || '')}" data-c="${esc(JSON.stringify(ctx || {}))}">`
      + `<button data-v="ok" class="v-ok" title="맞음">✓</button><button data-v="wrong" class="v-wrong" title="틀림">✗</button><button data-v="unsure" class="v-unsure" title="모름·확인 필요">?</button>`
      + `<button data-note class="v-note" title="메모">✎</button>${fix}<span class="tally"></span></span>`;
  }
  function paintReviews(root) {
    for (const el of $$('.rv', root)) {
      const rows = R.byTarget.get(tkey(el.dataset.k, el.dataset.i)) || [];
      const mine = rows.find((r) => r.by === R.uid);
      el.classList.toggle('ro', R.state !== 'on');
      for (const b of $$('button[data-v]', el)) b.classList.toggle('on', !!mine && mine.verdict === b.dataset.v);
      const nb = $('button[data-note]', el);
      if (nb) nb.classList.toggle('on', !!(mine && mine.note));
      const sel = $('select[data-fix]', el);
      if (sel && document.activeElement !== sel) sel.value = (mine && mine.fix) || '';
      const c = { ok: 0, wrong: 0, unsure: 0 };
      rows.forEach((r) => { if (c[r.verdict] != null) c[r.verdict]++; });
      const others = rows.length - (mine ? 1 : 0);
      const tally = $('.tally', el);
      tally.innerHTML = rows.length ? `${c.ok ? '✓<b>' + c.ok + '</b> ' : ''}${c.wrong ? '✗<b>' + c.wrong + '</b> ' : ''}${c.unsure ? '?<b>' + c.unsure + '</b>' : ''}` : '';
      tally.title = rows.map((r) => `${whoName(r.by)}: ${L.verdict[r.verdict] || r.verdict}${r.fix ? ' → ' + r.fix : ''}${r.note ? ' · ' + r.note : ''}`).join('\n');
      if (!others && !mine) tally.innerHTML = '';
    }
    hydrateThumbs(root);
  }
  async function saveReview(el, patch) {
    if (R.state !== 'on') { toast(R.state === 'ro' ? '이 계정은 검수 표시를 볼 수만 있습니다' : '검수 저장을 쓸 수 없는 화면입니다'); return; }
    const kind = el.dataset.k, id = el.dataset.i;
    const docId = 'r_' + fnv36(kind + ':' + id) + '_' + safeSeg(R.uid);
    const prev = R.docs.get(docId);
    const next = Object.assign({ kind, id, label: el.dataset.l || '', ctx: JSON.parse(el.dataset.c || '{}'), verdict: (prev && prev.verdict) || 'unsure', note: (prev && prev.note) || '', fix: (prev && prev.fix) || '' }, patch, { by: R.uid, at: Date.now() });
    try {
      if (patch.verdict === null) await R.db.collection('reviews').doc(docId).delete();
      else await R.db.collection('reviews').doc(docId).set(next);
    } catch (e) {
      const code = e && e.code;
      if (code === 'invalid_argument') { R.state = 'ro'; paintWho(); paintReviews(document); toast('이 계정은 검수 표시를 저장할 수 없습니다'); }
      else if (code === 'quota_exceeded') toast('저장 공간이 가득 찼습니다: ' + (e.message || ''));
      else toast('저장하지 못했습니다' + (code ? ' (' + code + ')' : ''));
    }
  }
  document.addEventListener('click', (ev) => {
    const b = ev.target.closest('.rv button');
    if (!b) return;
    ev.preventDefault(); ev.stopImmediatePropagation();
    const el = b.closest('.rv');
    if (b.dataset.note != null) {
      const host = el.parentElement;
      let box = host.querySelector(':scope > .rvnote');
      if (box) { box.remove(); return; }
      const mine = (R.byTarget.get(tkey(el.dataset.k, el.dataset.i)) || []).find((r) => r.by === R.uid);
      box = document.createElement('div');
      box.className = 'rvnote';
      box.innerHTML = `<input class="field" maxlength="500" placeholder="메모(무엇이 틀렸는지, 맞는 값 등) — Enter 로 저장"><button class="btn">저장</button>`;
      const inp = box.querySelector('input');
      inp.value = (mine && mine.note) || '';
      const go = () => { saveReview(el, { note: inp.value.trim() }); box.remove(); };
      box.querySelector('button').addEventListener('click', go);
      inp.addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); if (e.key === 'Escape') box.remove(); });
      el.insertAdjacentElement('afterend', box);
      inp.focus();
      return;
    }
    const mine = (R.byTarget.get(tkey(el.dataset.k, el.dataset.i)) || []).find((r) => r.by === R.uid);
    saveReview(el, { verdict: mine && mine.verdict === b.dataset.v ? null : b.dataset.v });
  });
  document.addEventListener('change', (ev) => {
    const s = ev.target.closest('.rv select[data-fix]');
    if (s) saveReview(s.closest('.rv'), s.value ? { fix: s.value, verdict: 'wrong' } : { fix: '' });
  });

  /* ── 드로어 ── */
  function openDrawer(head, body) {
    $('#dhead').innerHTML = head;
    $('#dbody').innerHTML = body;
    $('#dbody').scrollTop = 0;
    $('#drawer').classList.add('on');
    $('#drawer').setAttribute('aria-hidden', 'false');
    $('#ov').classList.add('on');
    paintReviews($('#drawer'));
  }
  function closeDrawer() { $('#drawer').classList.remove('on'); $('#drawer').setAttribute('aria-hidden', 'true'); $('#ov').classList.remove('on'); }
  $('#dclose').addEventListener('click', closeDrawer);
  $('#ov').addEventListener('click', closeDrawer);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeDrawer(); });

  /* 엔티티 링크: data-open="kind:id" 를 누르면 해당 화면·드로어로 */
  function entChip(kind, id, name, extra = '') {
    const clickable = ['family', 'deployment', 'vertical', 'category', 'image', 'solution', 'service', 'space_type', 'capability', 'model'].includes(kind);
    const label = name || D.kb.name(kind, id);
    return clickable
      ? `<button class="chip k-${esc(kind)}" data-open="${esc(kind)}:${esc(id)}" title="${esc(kindName(kind))} · ${esc(id)}">${esc(label)}${extra}</button>`
      : `<span class="chip k-${esc(kind)}" title="${esc(kindName(kind))} · ${esc(id)}">${esc(label)}${extra}</span>`;
  }
  document.addEventListener('click', (ev) => {
    const t = ev.target.closest('[data-open]');
    if (!t || ev.target.closest('.rv, .rvnote, a[href]')) return;
    ev.preventDefault();
    const v = t.dataset.open, j = v.indexOf(':');
    openEntity(v.slice(0, j), v.slice(j + 1));
  });
  function openEntity(kind, id) {
    if (kind === 'family') return openFamily(id);
    if (kind === 'model') { const m = D.g.models.find((x) => x[0] === id); if (m) return openFamily(m[2]); }
    if (kind === 'deployment') return openDeployment(id);
    if (kind === 'image') return openImage(id);
    if (kind === 'vertical') { closeDrawer(); S.vert.v = id; return go('verticals'); }
    if (kind === 'category') { closeDrawer(); S.prod.cat = id; S.prod.page = 0; return go('products'); }
    if (kind === 'capability') { closeDrawer(); S.prod.cap = id; S.prod.page = 0; return go('products'); }
    if (kind === 'solution' || kind === 'service') return openSolution(kind, id);
    if (kind === 'space_type') return openSpace(id);
    if (kind === 'message') return openMessage(id);
  }

  /* ── 탭 ── */
  const S = {
    q: { mode: store.get('qmode', 's1'), text: '' },
    vert: { v: store.get('vert', 'kr_hotel') },
    prod: { text: '', top: '', cat: '', cap: '', sort: 'rel', page: 0 },
    cases: { text: '', v: '', fmt: '', kpi: false, photo: false },
    img: { pt: '', grade: '', sp: '', v: '', rights: '', thumb: false, text: '', page: 0 },
    msg: { level: '', about: '', claim: false, text: '', v: '', page: 0 },
    cm: Object.assign({ v: '', spaces: [], products: [], cust: '', text: '', locale: 'ko-KR' }, store.get('cm', {})),
    rev: { verdict: '', kind: '', mine: false },
  };
  let current = null;
  const views = {};
  function go(tab) { if (location.hash !== '#' + tab) location.hash = tab; else route(); }
  function route() {
    const tab = (location.hash || '').replace(/^#/, '') || store.get('tab', 'overview');
    const t = views[tab] ? tab : 'overview';
    current = t;
    store.set('tab', t);
    for (const b of $$('.tab')) b.classList.toggle('on', b.dataset.tab === t);
    const el = $('#view');
    try { views[t](el); } catch (e) { el.innerHTML = `<div class="empty">화면을 그리지 못했습니다: ${esc(e.message)}</div>`; console.error(e); }
    paintReviews(el);
    window.scrollTo(0, 0);
  }
  $('#tabs').addEventListener('click', (e) => { const b = e.target.closest('.tab'); if (b) go(b.dataset.tab); });
  window.addEventListener('hashchange', route);

  function pager(total, page, size, key) {
    const n = Math.ceil(total / size);
    if (n <= 1) return '';
    return `<div class="pager"><button class="btn" data-page="${key}:${page - 1}" ${page <= 0 ? 'disabled' : ''}>이전</button><span class="small muted">${page + 1} / ${n} 쪽 · ${fmt(total)}건</span><button class="btn" data-page="${key}:${page + 1}" ${page >= n - 1 ? 'disabled' : ''}>다음</button></div>`;
  }
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-page]');
    if (!b) return;
    const [k, p] = b.dataset.page.split(':');
    S[k].page = +p;
    ({ prod: renderProdList, img: renderImgList, msg: renderMsgList })[k]();
    window.scrollTo(0, 0);
  });

  /* ═════════ 개요 ═════════ */
  views.overview = (el) => {
    const c = D.core, cnt = c.counts, tests = c.tests, pr = c.probes;
    const tp = tests.filter((t) => t.pass).length, pp = pr.filter((p) => p.pass).length;
    const par = D.parity && D.parity.summary;
    const kp = [['product_family', '제품군(상품 카드)'], ['product_model', '모델 코드'], ['spec_value', '스펙 값'], ['feature_block', '특장점 블록'], ['industry_section', '업종 페이지 섹션'],
      ['industry_section_item', '장면 항목'], ['deployment', '도입사례'], ['kpi_claim', 'KPI 문장'], ['value_prop', '메시지 문장'], ['image_asset', '이미지'], ['provides', '역량 근거'],
      ['alias', '별칭'], ['mention', '언급'], ['kg_edge', '그래프 엣지'], ['text_chunk', '원문 청크'], ['source_document', '수집 문서']];
    el.innerHTML = `
      <p class="lead">samsung.com/business(KR·일부 US)에서 모은 Winmate KB v1을 원문 근거와 함께 보면서 틀린 곳을 표시하는 화면입니다. 항목 옆 <b>✓ 맞음 · ✗ 틀림 · ? 모름 · ✎ 메모</b>로 남긴 표시는 이 페이지를 여는 사람 모두에게 공유되고 <a href="#reviews">검수</a> 탭에 모입니다. <a href="#query">질의</a>는 Python 질의 엔진(build/query.py)과 같은 규칙을 브라우저에서 계산합니다(LLM 없음).</p>
      <div class="status-strip">
        <div class="card"><span class="big">${tp}/${tests.length}</span><span class="small muted">시나리오 테스트 통과</span></div>
        <div class="card"><span class="big">${pp}/${pr.length}</span><span class="small muted">품질 프로브 통과</span></div>
        <div class="card"><span class="big">${esc(fmtTime(c.meta.products_fetched_at))}</span><span class="small muted">상품 수집 시각</span></div>
        ${par ? `<div class="card"><span class="big">${pct(par.S1.family_top1)}</span><span class="small muted">요구사항 질의 1순위 제품이 Python 결과와 같은 비율(${par.S1.n}문장)</span></div>` : ''}
      </div>
      <div class="section"><h2>적재 건수</h2><div class="kpis">${kp.map(([k, l]) => `<div class="card kpi"><div class="v">${fmt(cnt[k])}</div><div class="l">${esc(l)}</div></div>`).join('')}</div></div>
      <div class="section"><h2>시나리오별 상태 <span class="hint">qa.py 가 DR 커버리지·프로브로 판정</span></h2>
        <div class="card tw"><table><thead><tr><th>시나리오</th><th>이름</th><th>상태</th><th>근거</th></tr></thead><tbody>
        ${c.scen.map((s) => `<tr><td class="mono">${esc(s[0])}</td><td>${esc(s[1])}</td><td>${statusPill(s[2])}</td><td class="small muted">${esc(s[3])}</td></tr>`).join('')}
        </tbody></table></div></div>
      <div class="section"><h2>시나리오 테스트 ${tp}/${tests.length} <span class="hint">tests/test_scenarios.py · 펼치면 실제 질의 출력</span></h2>
        <div class="card">${tests.map((t, i) => `<details class="pad" style="border-bottom:1px solid var(--border)"><summary><span class="row" style="display:inline-flex"><span class="mono">${esc(t.scenario)}</span> ${passPill(t.pass)} <b>${esc(t.name)}</b> <span class="small muted">${esc(t.detail)}</span> ${t.decision ? hintPill(t.decision) : ''}</span></summary>
          <div class="lines">${esc((t.lines || []).join('\n'))}</div><div style="margin:6px 0 0 14px">${rv('test', t.scenario + '|' + t.name, `${t.scenario} ${t.name}`, {})}</div></details>`).join('')}</div></div>
      <div class="section"><h2>품질 프로브 ${pp}/${pr.length}</h2>
        <div class="card tw"><table><thead><tr><th>시나리오</th><th>프로브</th><th>결과</th><th>상세</th></tr></thead><tbody>
        ${pr.map((p) => `<tr><td class="mono">${esc(p.scenario)}</td><td>${esc(p.probe)}</td><td>${passPill(p.pass)}</td><td class="small muted">${esc(p.detail)}</td></tr>`).join('')}
        </tbody></table></div></div>
      <div class="section"><h2>데이터 요소(DR) 커버리지</h2>
        <div class="card tw"><table><thead><tr><th>DR</th><th>요소</th><th>지표</th><th>값</th><th>상태</th><th>메모</th></tr></thead><tbody>
        ${c.dr.map((r) => `<tr><td class="mono">${esc(r[0])}</td><td>${esc(r[1])}</td><td class="small">${esc(r[2])}</td><td class="small">${esc(r[3])}</td><td>${statusPill(r[4])}</td><td class="small muted">${esc(r[5])}</td></tr>`).join('')}
        </tbody></table></div></div>
      ${par ? parityHTML(par) : ''}
      <div class="section"><h2>Winmate 세그먼트 ↔ 사이트 업종 대응 <span class="hint">초안 · 빈칸은 사람이 채울 곳</span></h2>
        <div class="card tw"><table><thead><tr><th>세그먼트</th><th>이름</th><th>KR 업종</th><th>US 업종</th><th>카탈로그 장</th><th>상태</th><th>검수</th></tr></thead><tbody>
        ${c.SEG.map((s) => `<tr><td class="mono">${esc(s[0])}</td><td>${esc(s[1])}</td><td>${listChips('vertical', s[2])}</td><td>${listChips('vertical', s[3])}</td><td class="small">${esc(s[4] || '')}</td><td>${statusPill(s[5])}</td><td>${rv('segment', s[0], s[1], {})}</td></tr>`).join('')}
        </tbody></table></div></div>`;
  };
  function listChips(kind, v) {
    let arr = [];
    try { arr = typeof v === 'string' ? JSON.parse(v) : v || []; } catch (e) { arr = String(v || '').split(/[,\s]+/).filter(Boolean); }
    if (!Array.isArray(arr)) arr = [arr];
    return arr.length ? arr.map((x) => entChip(kind, x)).join(' ') : '<span class="pill p-warn">빈칸</span>';
  }
  function fmtTime(iso) {
    if (!iso) return '–';
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    return d.toLocaleString('ko-KR', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  }
  function parityHTML(p) {
    const row = (name, v, note = '') => `<tr><td>${esc(name)}</td><td class="num">${pct(v)}</td><td class="small muted">${esc(note)}</td></tr>`;
    return `<div class="section"><h2>브라우저 엔진 ↔ Python 결과 일치 <span class="hint">같은 문장을 두 엔진에 넣어 비교(dashboard/parity.js)</span></h2>
      <div class="card tw"><table><thead><tr><th>항목</th><th class="num">일치</th><th>설명</th></tr></thead><tbody>
      ${row('요구사항: 업종 판별 top-2(점수까지)', p.S1.vertical_exact, p.S1.n + '문장')}
      ${row('요구사항: 공간 묶음', p.S1.spaces_exact)}
      ${row('요구사항: 필수·권장 역량·카테고리', p.S1.caps_exact)}
      ${row('요구사항: 추천 솔루션', p.S1.solutions_exact)}
      ${row('요구사항: 1순위 제품군', p.S1.family_top1, '동점(같은 이름·점수)은 Python 도 순서가 실행마다 다름')}
      ${row('요구사항: 상위 3 제품군 겹침', p.S1.family_top3_overlap)}
      ${row('요구사항: 유사 사례 상위 5 겹침', p.S1.cases_top5_overlap)}
      ${row('원문 검색: 키워드(BM25) 상위 10', p.search.kw_top10, 'SQLite FTS5 trigram BM25 를 같은 공식으로 계산')}
      ${row('원문 검색: 최종 상위 10 겹침', p.search.chunks_top10, p.search.n + '문장')}
      ${row('이미지 검색: 상위 10 겹침', p.image_search.top10, p.image_search.n + '문장')}
      ${row('업종 판별(A2): 후보·점수 완전 일치', p.A2.exact, p.A2.n + '문장')}
      ${p.E3 ? `${row('컨텍스트 → 메시지: 컨텍스트 해석(업종·공간·제품·고객·가중치)', p.E3.context_exact, p.E3.n + '컨텍스트')}
      ${row('컨텍스트 → 메시지: 핵심 메시지 순서', p.E3.key_messages_order_exact)}
      ${row('컨텍스트 → 메시지: 제품 메시지 묶음', p.E3.products_exact)}
      ${row('컨텍스트 → 메시지: 근거 사례 상위 6 겹침', p.E3.cases_top6)}
      ${row('컨텍스트 → 메시지: 전체 순위 상위 60 겹침', p.E3.ranked_top60, `순서까지 같음 ${pct(p.E3.ranked_order_exact)} · 점수 차 최대 ${p.E3.max_score_diff}(float16 벡터)`)}` : ''}
      </tbody></table></div></div>`;
  }

  /* ═════════ 질의 ═════════ */
  const EX = {
    s1: ['호텔 객실 TV를 통합 관리하고 로비에 대형 비디오월을 설치하고 싶어', '매장 입구 쇼윈도에 햇빛에서도 잘 보이는 사이니지', '학교 교실에 판서가 되는 전자칠판', '물류센터 현장 작업자가 쓸 내구성 좋은 태블릿',
      '사무실 회의실에 직바람 없는 무풍 냉방', '병원 로비 대기실 안내 사이니지와 진료실 모니터', '주차장 입구 옥외에 설치할 실외 사이니지', '관제 상황실 24시간 비디오월'],
    search: ['병상 태블릿 환자 소통', '호텔 객실 TV 원격 관리', '무풍 시스템에어컨 사무실', '전자칠판 판서 공유', '옥외 사이니지 고휘도', '매직인포 콘텐츠 스케줄'],
    image: ['카페 천장에 설치된 시스템에어컨', '호텔 객실 TV', '매장 쇼윈도 사이니지', '교실 전자칠판', '회의실 화상회의', '로비 비디오월'],
    a2: ['공장 생산 라인 작업자용 산업용 태블릿', '병원 진료 대기실', '은행 창구', '카페 주문', '아파트 거실 에어컨'],
    a1: ['LH85WMBWLGCXKR 전자칠판을 강의실에', '호텔 로비에 매직인포로 관리하는 비디오월', '옥외 24시간 운영 사이니지'],
  };
  const MODES = [['s1', '요구사항 → 추천'], ['search', '원문 검색'], ['image', '이미지 검색'], ['a2', '업종 판별'], ['a1', '표현 인식']];
  const MODE_NOTE = {
    s1: '문장 → 업종 판별(A2) → 절마다 공간·카테고리·역량 인식(A1) → 공간별 후보 제품군(C2: 역량 0.4 · 사이트 추천 0.3 · 카테고리 0.1 · 선례 0.1 · 문장 유사도 0.1) → 유사 사례(D1)',
    search: '원문 청크 하이브리드 검색: 키워드(trigram BM25) + 2글자 토큰 부분일치 + LSA 벡터 → RRF → 토큰 포괄도 재정렬',
    image: '이미지 alt·캡션·섹션·맥락 문서 검색(키워드 + 벡터), 같은 점수면 A 등급 우선',
    a2: '업종명 언급 > 공간 신호(업종 페이지 장면) > 제품 신호(업종 페이지 추천) > 벡터 유사도. 1·2위 차이가 0.1 미만이면 질문',
    a1: '모델 코드·별칭(제품군·카테고리·솔루션·업종) + 공간 키워드 + 역량 키워드',
  };
  views.query = (el) => {
    el.innerHTML = `
      <div class="section"><div class="row" style="margin-bottom:10px"><div class="seg" id="qmode">${MODES.map(([k, l]) => `<button data-m="${k}" class="${S.q.mode === k ? 'on' : ''}">${esc(l)}</button>`).join('')}</div></div>
        <div class="qbox"><textarea class="field" id="qtext" rows="2" placeholder="예: ${esc(EX[S.q.mode][0])}">${esc(S.q.text)}</textarea><button class="btn primary" id="qrun">실행</button></div>
        <div class="small muted" id="qnote" style="margin-top:6px">${esc(MODE_NOTE[S.q.mode])}</div>
        <div class="examples" id="qex">${EX[S.q.mode].map((x) => `<button class="chip" data-ex="${esc(x)}">${esc(x)}</button>`).join('')}</div></div>
      <div id="qout"></div>`;
    $('#qmode', el).addEventListener('click', (e) => { const b = e.target.closest('button'); if (!b) return; S.q.mode = b.dataset.m; store.set('qmode', S.q.mode); views.query(el); paintReviews(el); if (S.q.text) runQuery(); });
    $('#qex', el).addEventListener('click', (e) => { const b = e.target.closest('[data-ex]'); if (!b) return; $('#qtext').value = b.dataset.ex; runQuery(); });
    $('#qrun', el).addEventListener('click', runQuery);
    $('#qtext', el).addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); runQuery(); } });
    if (S.q.last && S.q.last.mode === S.q.mode) { $('#qout').innerHTML = S.q.last.html; paintReviews($('#qout')); }
  };
  async function runQuery() {
    const text = ($('#qtext').value || '').trim();
    if (!text) return;
    S.q.text = text;
    const mode = S.q.mode, out = $('#qout');
    const groups = { s1: ['vec', 'images'], search: ['search', 'vecChunk', 'images'], image: ['search', 'images', 'vec'], a2: ['vec'], a1: [] }[mode];
    const sizeMB = (Load.size({ vec: ['lsa_vocab.json.gz', 'lsa.bin', 'vec_refs.json.gz', 'vec_core.bin'], vecChunk: ['vec_chunk.bin'], search: ['search.json.gz'], images: ['images.json.gz', 'thumbs.bin'] }[groups[0]] || []) / 1048576);
    const pending = groups.filter((g) => !Load.groups.has(g));
    out.innerHTML = `<div class="empty"><span class="spin"></span> ${pending.length ? `질의 엔진 데이터를 처음 한 번 받는 중입니다${sizeMB ? ` (약 ${Math.round(sizeMB)} MB 이상)` : ''}…` : '계산 중…'}</div>`;
    try {
      await Promise.all(groups.map((g) => need[g]()));
      await new Promise((r) => setTimeout(r, 20));
      const kb = D.kb;
      let html = '';
      if (mode === 's1') html = renderS1(kb.S1(text), text);
      else if (mode === 'search') html = renderSearch(kb.search(text, 20), text);
      else if (mode === 'image') html = renderImageSearch(kb.imageSearch(text, 40), text);
      else if (mode === 'a2') html = renderA2(kb.A2(text));
      else html = renderA1(kb.A1(text), kb.B2(text));
      if (S.q.mode !== mode || current !== 'query') return;
      out.innerHTML = html;
      S.q.last = { mode, html };
      paintReviews(out);
    } catch (e) {
      console.error(e);
      out.innerHTML = `<div class="empty">계산하지 못했습니다: ${esc(e.message)}</div>`;
    }
  }
  const decisionRow = (r) => `<div class="row" style="margin-bottom:14px">${hintPill(r.decision_hint)} ${r.decision_reasons.map(reasonPill).join(' ')} ${r.tier_min ? tierPill(r.tier_min) : ''} <span class="small faint">${r.timings_ms.total} ms · 브라우저 계산</span></div>`;
  const needsHTML = (r) => (r.needs_confirmation && r.needs_confirmation.length ? `<div class="note">확인할 것: ${r.needs_confirmation.map(esc).join(' · ')}</div>` : '');
  function scoreBar(v) { return `<span class="score"><span class="bar"><i class="b-one" style="width:${Math.max(0, Math.min(1, v)) * 100}%"></i></span>${(+v).toFixed(3)}</span>`; }
  function stackBar(b) {
    const parts = [['b-cap', 0.4 * b.cap, '역량'], ['b-site', 0.3 * b.site, '사이트 추천'], ['b-cat', 0.1 * b.category, '카테고리'], ['b-prec', 0.1 * b.precedent, '선례'], ['b-text', 0.1 * b.text, '문장 유사도']];
    return `<span class="bar" title="${parts.map(([, v, l]) => `${l} ${v.toFixed(3)}`).join(' · ')}">${parts.map(([c, v]) => `<i class="${c}" style="width:${v * 100}%"></i>`).join('')}</span>`;
  }
  const LEGEND = `<span class="legend"><span><i class="b-cap"></i>역량 0.4</span><span><i class="b-site"></i>사이트 추천 0.3</span><span><i class="b-cat"></i>카테고리 0.1</span><span><i class="b-prec"></i>선례 0.1</span><span><i class="b-text"></i>문장 유사도 0.1</span></span>`;
  function linkChips(links) {
    if (!links.length) return '<span class="small muted">인식한 표현 없음</span>';
    return links.map((l) => `<span title="${esc(l.method)} · 신뢰도 ${l.conf}">${entChip(l.type, l.id, `${l.surface} → ${l.name || l.id}`)}</span>`).join(' ');
  }
  function renderS1(r, q) {
    const res = r.result;
    let h = decisionRow(r);
    h += `<div class="section"><h2>업종 판별 <span class="hint">상위 후보와 신호</span></h2><div class="card tw"><table><tbody>
      ${(res.vertical_all || res.vertical).map((v, i) => `<tr><td class="num" style="width:28px">${i + 1}</td><td>${entChip('vertical', v.id, v.name)}</td><td style="width:150px">${scoreBar(v.score)}</td><td class="small muted">${esc((v.signals || []).join(' · '))}</td></tr>`).join('') || '<tr><td class="muted">업종 신호 없음</td></tr>'}
      </tbody></table></div></div>`;
    h += `<div class="section"><h2>문장에서 인식한 표현</h2><div class="row">${linkChips(res.links || [])}</div></div>`;
    h += `<div class="section"><h2>공간별 추천 <span class="hint">${LEGEND}</span></h2><div class="stack">`;
    for (const p of res.by_space) {
      const sname = p.space ? `${esc(p.space_name)} <span class="mono faint">${esc(p.space)}</span>` : '공간 미지정';
      h += `<div class="card spacecard"><header><div class="row"><h3>${sname}</h3>${p.decision_reasons.map(reasonPill).join(' ')}<span class="small muted">후보 풀 ${fmt(p.n_pool)}</span></div>
        <div class="small" style="margin-top:4px">${p.clauses.map((c) => `<span class="quote">${esc(c)}</span>`).join(' ')}</div>
        <div class="row small" style="margin-top:6px">${p.category ? `<span class="muted">카테고리</span> ${entChip('category', p.category, p.category_name)}` : ''}
          ${p.capabilities.hard.length ? `<span class="muted">필수 역량</span> ${p.capabilities.hard.map((c) => entChip('capability', c)).join(' ')}` : ''}
          ${p.capabilities.soft.length ? `<span class="muted">권장 역량</span> ${p.capabilities.soft.map((c) => entChip('capability', c)).join(' ')}` : ''}</div></header>
        <div class="tw"><table><thead><tr><th class="num">#</th><th>제품군</th><th>점수</th><th>근거</th><th>검수</th></tr></thead><tbody>
        ${p.families.map((f, i) => `<tr><td class="num">${i + 1}</td><td style="min-width:200px">${famThumb(f.id)}${entChip('family', f.id, f.name)}<div class="mono faint">${esc(f.model || '')}</div><div class="xs muted">${esc(f.category)}</div></td>
          <td style="white-space:nowrap">${stackBar(f.breakdown)} <b>${f.score.toFixed(3)}</b></td>
          <td><ul class="reasons">${f.reasons.map((x) => `<li>${esc(x)}</li>`).join('')}</ul></td>
          <td>${rv('s1', `${q}|${p.space || ''}|${f.id}`, `${f.name} ← “${q}” (${p.space_name || '공간 미지정'})`, { q, mode: 's1', fid: f.id })}</td></tr>`).join('') || '<tr><td colspan="5" class="muted">후보 없음</td></tr>'}
        </tbody></table></div>
        ${placementImages(p)}
        ${p.solutions.length ? `<div class="pad small"><span class="muted">사이트가 함께 추천한 솔루션·서비스</span> ${p.solutions.map((s) => `<span title="${esc(s.evidence || '')}">${entChip(s.kind, s.id, s.name, ` <span class="faint">(${s.via === 'space' ? '공간' : '업종'})</span>`)}</span>`).join(' ')}</div>` : ''}
      </div>`;
    }
    h += '</div></div>';
    h += `<div class="section"><h2>유사 도입사례 <span class="hint">업종 0.3 · 공간 0.25 · 제품 0.3 · 문장 0.15</span></h2><div class="card tw"><table><thead><tr><th>사례</th><th>점수</th><th>업종·공간·제품·문장</th><th>KPI</th></tr></thead><tbody>
      ${res.similar_cases.map((d) => `<tr><td>${caseThumb(d.id)}${entChip('deployment', d.id, d.title)} <span class="xs faint">${esc(d.date || '')}</span></td><td>${scoreBar(d.score)}</td><td class="small mono">${['vertical', 'space', 'product', 'text'].map((k) => d.similarity_breakdown[k]).join(' · ')}</td><td class="num">${d.kpis_count || ''}${d.has_photos ? ' 📷' : ''}</td></tr>`).join('') || '<tr><td class="muted">없음</td></tr>'}
      </tbody></table></div></div>`;
    if (res.gaps && res.gaps.length) h += `<div class="section"><h2>되물을 질문 <span class="hint">공간이 요구하는 역량 중 문장에 없는 것(requires 초안)</span></h2><div class="card pad"><ul style="margin:0;padding-left:18px">${res.gaps.map((g) => `<li>${esc(g.question_ko)} <span class="pill p-mute">${esc(g.strength || '')}</span></li>`).join('')}</ul></div></div>`;
    h += needsHTML(r);
    return h;
  }
  function famThumb(fid) {
    const g = IX.famGallery && IX.famGallery.get(fid);
    return g != null && hasThumb(D.images.assets[g][0]) ? `<div class="tiny-thumbs sm" style="margin:0 0 4px">${miniImg(D.images.assets[g])}</div>` : '';
  }
  function caseThumb(did) {
    const g = IX.depFirstPhoto && IX.depFirstPhoto.get(did);
    return g != null && hasThumb(D.images.assets[g][0]) ? `<div class="tiny-thumbs sm" style="margin:0 0 4px">${miniImg(D.images.assets[g])}</div>` : '';
  }
  /* 공간 × 카테고리 배치 이미지(G1: 공간+카테고리 → 공간 → 카테고리 문맥 → 제품 컷 순으로 폴백) */
  function placementImages(p) {
    if (!p.space || !D.images) return '';
    const g = D.kb.G1(p.space, p.category, null, 14);
    const imgs = g.result.images;
    if (!imgs.length) return '';
    const lv = { 'space+category': '공간 + 카테고리', space_only: '공간', category_context: '카테고리 문맥', category_product_cut: '제품 컷' }[g.result.level] || g.result.level;
    return `<div class="pad"><div class="xs muted">배치 이미지(G1) · ${esc(lv)}${g.fallback_level ? ' · 폴백' : ''}</div>${stripHTML(imgs.map((v) => IX.assetIdx.get(v.id)), 14)}</div>`;
  }
  function highlight(text, toks) {
    const t = (toks || []).filter(Boolean);
    if (!t.length) return esc(text);
    const re = new RegExp('(' + t.map(reEsc).sort((a, b) => b.length - a.length).join('|') + ')', 'g');
    return String(text).split(re).map((part, i) => (i % 2 ? `<mark>${esc(part)}</mark>` : esc(part))).join('');
  }
  function chunkImages(cid) {
    if (!D.images || !D.kb.chunkById) return '';
    const row = D.kb.S.chunks[D.kb.chunkById.get(cid)];
    if (!row) return '';
    let idxs = docImages(row[1], row[3], null);
    if (!idxs.length) idxs = ((IX.occByDoc.get(row[1])) || []).map((o) => o[0]);
    return idxs.length ? stripHTML(idxs, 8, 'sm') : '';
  }
  function renderSearch(r, q) {
    const res = r.result;
    let h = `<div class="row" style="margin-bottom:12px"><span class="small muted">토큰</span> ${res.tokens.map((t) => `<span class="chip">${esc(t)}</span>`).join(' ')} <span class="small faint">${r.timings_ms.total} ms</span></div>`;
    h += `<div class="section"><h2>관련 엔티티</h2><div class="row">${res.entities.map((e) => entChip(e.kind, e.id, e.name)).join(' ') || '<span class="muted small">없음</span>'}</div></div>`;
    h += `<div class="section"><h2>원문 청크 <span class="hint">점수 = 0.5 × 융합 순위 + 0.5 × 토큰 포괄도</span></h2><div class="card">
      ${res.chunks.map((c) => `<div class="hit"><div class="row"><span class="pill p-acc">${esc(ptName(c.page_type))}</span><span class="t">${esc(c.title || '')}</span><span class="small muted">${esc(c.section || '')}</span><span class="grow"></span><span class="small faint">점수 ${c.score} · 포괄도 ${c.coverage}</span>${ext(c.url)}</div>
        <div class="x">${highlight(c.text, res.tokens)}</div>${chunkImages(c.chunk_id)}
        <div class="row" style="margin-top:6px">${(c.entities || []).map((e) => { const j = e.indexOf(':'); return entChip(e.slice(0, j), e.slice(j + 1)); }).join(' ')}<span class="grow"></span>${rv('search', `${q}|${c.chunk_id}`, `“${q}” → ${c.title || ''} ${c.section || ''}`, { q, mode: 'search' })}</div></div>`).join('') || '<div class="empty">결과 없음</div>'}
      </div></div>`;
    return h;
  }
  function imgCard(v, opts = {}) {
    const a = assetById(v.id) || [v.id, v.url, v.url_mobile, v.media_type, v.grade_hint, v.grade_hint_reason, v.rights, v.n];
    return `<div class="card icard"><button style="border:0;padding:0;background:none;cursor:zoom-in" data-open="image:${esc(v.id)}">${thumbHTML(a, { alt: v.alt, grade: false })}</button>
      <div class="meta"><div class="row"><span class="grade g-${gcls(a[4])}">${esc(a[4] || '–')}</span><span class="xs muted grow">${esc(L.grade[a[4]] || '')}${a[5] ? ' · ' + esc(a[5]) : ''}</span></div>
      ${v.alt ? `<div class="clamp3">${esc(v.alt)}</div>` : '<div class="faint small">alt 없음</div>'}
      ${v.caption ? `<div class="small muted clamp2">캡션: ${esc(v.caption)}</div>` : ''}
      <div class="row xs">${v.page_type ? `<span class="pill p-mute">${esc(ptName(v.page_type))}</span>` : ''}${v.space_name ? entChip('space_type', v.sp, v.space_name) : ''}${a[6] === 'customer_case' ? '<span class="pill p-info">사례 사진</span>' : ''}</div>
      <div class="xs muted clamp2">${v.page_url ? `<a href="${esc(v.page_url)}" target="_blank" rel="noopener">${esc(v.title || v.page_url)}</a>` : ''}${v.section_path ? ' · ' + esc(v.section_path) : ''}</div>
      ${opts.score != null ? `<div class="xs faint">점수 ${opts.score}</div>` : ''}
      <div>${rv('image', v.id, (v.alt || v.title || v.id).slice(0, 80), { aid: v.id }, { fix: ['A', 'A?C', 'B', 'C', 'D', 'E'] })}</div></div></div>`;
  }
  function renderImageSearch(r) {
    const res = r.result;
    return `<div class="row" style="margin-bottom:12px"><span class="small muted">토큰</span> ${res.tokens.map((t) => `<span class="chip">${esc(t)}</span>`).join(' ')} <span class="small faint">${r.timings_ms.total} ms</span>${D.thumbs ? '' : ' <span class="pill p-warn">미리보기 이미지 없음 — 원본 링크로 확인</span>'}</div>
      <div class="igrid">${res.images.map((v) => imgCard(v, { score: v.score })).join('') || '<div class="empty">결과 없음</div>'}</div>`;
  }
  function renderA2(r) {
    const c = r.result.all || [];
    return decisionRow(r) + `<div class="card tw"><table><thead><tr><th class="num">#</th><th>업종</th><th>정규화 점수</th><th>신호</th><th>검수</th></tr></thead><tbody>
      ${c.map((v, i) => `<tr><td class="num">${i + 1}</td><td>${entChip('vertical', v.id, v.name)}</td><td>${scoreBar(v.score)}</td><td class="small muted">${esc(v.signals.join(' · '))}</td><td>${i === 0 ? rv('a2', `${S.q.text}|${v.id}`, `“${S.q.text}” → ${v.name}`, { q: S.q.text, mode: 'a2' }) : ''}</td></tr>`).join('') || '<tr><td class="muted">신호 없음 → 질문 필요</td></tr>'}
      </tbody></table></div>`;
  }
  function renderA1(r, b2) {
    const links = r.result.links;
    return `<div class="card tw"><table><thead><tr><th>표현</th><th>유형</th><th>대상</th><th>방법</th><th>신뢰도</th><th>다른 후보</th></tr></thead><tbody>
      ${links.map((l) => `<tr><td><b>${esc(l.surface)}</b></td><td class="small">${esc(kindName(l.type))}</td><td>${l.id ? entChip(l.type, l.id, l.name) : '<span class="pill p-warn">해소 안 됨</span>'}</td><td class="small mono">${esc(l.method)}</td><td class="num">${l.conf}</td><td>${(l.alternatives || []).map((a) => entChip(a.type, a.id, a.name)).join(' ')}</td></tr>`).join('') || '<tr><td class="muted" colspan="6">인식한 표현 없음</td></tr>'}
      </tbody></table></div>
      <div class="section" style="margin-top:16px"><h2>되물을 질문(B2)</h2><div class="card pad"><ul style="margin:0;padding-left:18px">${b2.result.gaps.map((g) => `<li>${esc(g.question_ko)}</li>`).join('')}</ul></div></div>`;
  }

  /* ═════════ 업종 장면 ═════════ */
  views.verticals = (el) => {
    const V = D.core.V;
    const kr = V.filter((v) => v[5] === 'kr_site'), us = V.filter((v) => v[5] === 'us_site');
    if (!D.kb.vertById.has(S.vert.v) && kr.length) S.vert.v = kr[0][0];
    const nScenes = (id) => (IX.secByVert.get(id) || []).filter((s) => !['hero', 'recommend', 'cases'].includes(s[4])).length;
    const btn = (v, child) => `<button class="${child ? 'child' : ''} ${S.vert.v === v[0] ? 'on' : ''}" data-v="${esc(v[0])}"><span class="grow">${esc(v[2] || v[3])}</span><span class="xs faint">${nScenes(v[0]) || ''}</span></button>`;
    let side = '<div class="grp">KR 업종</div>';
    for (const p of kr.filter((v) => !v[4])) {
      side += btn(p, false);
      for (const c of kr.filter((v) => v[4] === p[0])) side += btn(c, true);
    }
    side += '<div class="grp">US 업종</div>' + us.map((v) => btn(v, false)).join('');
    el.innerHTML = `<div class="cols"><nav class="card side" id="vside">${side}</nav><div id="vmain"></div></div>`;
    $('#vside', el).addEventListener('click', (e) => { const b = e.target.closest('[data-v]'); if (!b) return; S.vert.v = b.dataset.v; store.set('vert', S.vert.v); $$('#vside button').forEach((x) => x.classList.toggle('on', x === b)); renderVertical(); });
    renderVertical();
    need.msgs().then(() => { if (current === 'verticals') renderVertical(); }).catch(() => {});
    if (!D.images) need.images().then(() => { if (current === 'verticals') renderVertical(); }).catch(() => {});
  };
  function msgTree(about, aboutId) {
    if (!D.msgs) return '<div class="small faint"><span class="spin"></span> 메시지 불러오는 중</div>';
    const rows = IX.msgByAbout.get(about + '\u0001' + aboutId) || [];
    if (!rows.length) return '';
    const tag = rows.filter((m) => m[1] === 'tagline'), km = rows.filter((m) => m[1] === 'key_message'), usp = rows.filter((m) => m[1] === 'usp');
    const orphan = rows.filter((m) => m[1] === 'proof_point' && !m[3]);
    const line = (m, cls = '') => `<div class="${cls}">${esc(m[2])} ${m[9] ? '<span class="pill p-warn" title="숫자·최상급 등 대외 사용 전 확인">claim</span>' : ''} ${rv('message', m[0], m[2].slice(0, 80), { mid: m[0] })}</div>`;
    return `<details class="msgs"><summary class="small muted">메시지 ${rows.length}개 (원문 그대로)</summary>
      ${tag.map((m) => line(m, 'km')).join('')}
      ${km.map((m) => line(m, 'km') + (IX.msgKids.get(m[0]) || []).map((k) => line(k, 'pp')).join('')).join('')}
      ${orphan.map((m) => line(m, 'pp')).join('')}${usp.map((m) => line(m, 'km')).join('')}</details>`;
  }
  function itemImages(ids) {
    if (!ids || !ids.length) return '';
    if (!D.images) return `<span class="xs faint">이미지 ${ids.length}</span>`;
    return `<div class="tiny-thumbs">${ids.slice(0, 4).map((aid) => { const a = assetById(aid); return a ? miniImg(a) : ''; }).join('')}</div>`;
  }
  function sceneImages(s, vid) {
    if (!D.images) return '';
    const sec = D.kb.secById.get(s.section_id);
    const shown = new Set();
    for (const it of s.items) for (const aid of it.images || []) { const i = IX.assetIdx.get(aid); if (i != null) shown.add(i); }
    const own = docImages(sec ? sec[2] : -1, null, s.title).filter((i) => !shown.has(i));
    own.forEach((i) => shown.add(i));
    let h = own.length ? `<div style="margin-top:8px"><div class="xs muted">이 장면의 다른 이미지</div>${stripHTML(own, 12)}</div>` : '';
    if (s.space_types.length) {
      const sp = new Set(s.space_types);
      const near = D.kb.imgRows((a, o) => sp.has(o[6]) && o[7] === vid && o[1] !== (sec ? sec[2] : -1), 40).map((v) => IX.assetIdx.get(v.id));
      const wide = near.length < 12 ? D.kb.imgRows((a, o) => sp.has(o[6]) && o[1] !== (sec ? sec[2] : -1), 40).map((v) => IX.assetIdx.get(v.id)) : [];
      const ctx = [...new Set([...near, ...wide])].filter((i) => !shown.has(i));
      if (ctx.length) h += `<div style="margin-top:8px"><div class="xs muted">같은 공간(${s.space_names.map(esc).join('·')})의 다른 페이지 이미지 — 도입사례·상품 상세 등</div>${stripHTML(ctx, 14)}</div>`;
    }
    return h;
  }
  function renderVertical() {
    const el = $('#vmain');
    if (!el) return;
    const vid = S.vert.v;
    const r = D.kb.B1(vid).result;
    const vrow = D.kb.vertById.get(vid) || [];
    const vname = D.kb.name('vertical', vid);
    const srcLink = (s) => { const x = D.kb.srcInfo(s); return x ? `<span class="xs faint">${esc(x.section || '')}</span> ${ext(x.url)}` : ''; };
    const itemRow = (it, sec) => `<tr><td style="min-width:160px"><b>${esc(it.name || '')}</b>${it.tagline ? `<div class="xs muted">${esc(it.tagline)}</div>` : ''}${it.space_label ? `<div class="xs faint">공간 라벨: ${esc(it.space_label)}${it.space_type ? ' → ' + esc(D.kb.name('space_type', it.space_type)) : ''}</div>` : ''}</td>
      <td class="small">${esc(it.kind || '')}</td>
      <td>${it.target[1] ? entChip(it.target[0], it.target[1], it.target_name) : '<span class="pill p-warn">해소 안 됨</span>'}<div class="xs faint">${esc(it.resolve || '')}${it.conf != null ? ' · ' + it.conf : ''}</div></td>
      <td>${ext(it.link, '링크')}${itemImages(it.images)}</td>
      <td>${rv('item', it.id, `${vname} · ${sec.title || ''} · ${it.name || ''}`, { v: vid, sid: sec.section_id })}</td></tr>`;
    const itemsTable = (sec) => (sec.items.length ? `<div class="tw items"><table><thead><tr><th>항목</th><th>유형</th><th>해소 대상</th><th>링크·이미지</th><th>검수</th></tr></thead><tbody>${sec.items.map((it) => itemRow(it, sec)).join('')}</tbody></table></div>` : '');
    let h = `<div class="row" style="margin-bottom:12px"><h2 style="font-size:18px">${esc(vname)}</h2><span class="mono faint">${esc(vid)}</span>${vrow[6] ? ext(vrow[6], '업종 페이지') : ''}<span class="grow"></span>${rv('vertical', vid, vname, { v: vid })}</div>`;
    if (r.hero.length) h += `<div class="card pad section">${r.hero.map((s) => `<div class="small muted">히어로</div><h3 style="font-size:16px;margin:2px 0 4px">${esc(s.title || '')}</h3>${s.description ? `<div>${esc(s.description)}</div>` : ''}${s.tagline ? `<div class="quote">${esc(s.tagline)}</div>` : ''}<div class="row" style="margin-top:6px">${srcLink(s.src)}<span class="grow"></span>${rv('section', s.section_id, `${vname} · 히어로`, { v: vid })}</div>${msgTree('industry_section', s.section_id)}`).join('<hr style="border:0;border-top:1px solid var(--border)">')}</div>`;
    h += `<div class="section"><h2>공간 시퀀스 <span class="hint">업종 페이지 장면 순서</span></h2><div class="row">${r.space_sequence.map((s, i) => `<span class="row" style="gap:4px"><span class="seqno">${i + 1}</span>${entChip('space_type', s.space_type, s.name)}</span>`).join(' ') || '<span class="muted small">공간이 붙은 장면 없음</span>'}</div></div>`;
    h += `<div class="section"><h2>장면 ${r.scenes.length}</h2><div class="card">${r.scenes.map((s, i) => `<div class="scene" id="sec-${esc(s.section_id)}">
        <div class="row"><span class="seqno">${i + 1}</span><h3>${esc(s.title || '(제목 없음)')}</h3>${s.vertical !== vid ? entChip('vertical', s.vertical) : ''}<span class="grow"></span>${rv('section', s.section_id, `${D.kb.name('vertical', s.vertical)} · ${s.title || ''}`, { v: vid, sid: s.section_id })}</div>
        <div class="row small" style="margin-top:4px">${s.space_label ? `<span class="muted">사이트 라벨</span> <b>${esc(s.space_label)}</b> →` : '<span class="muted">공간</span>'} ${s.space_types.map((x) => entChip('space_type', x)).join(' ') || '<span class="pill p-warn">공간 미해소</span>'} ${s.space_method ? `<span class="xs faint">${esc(s.space_method)}</span>` : ''}</div>
        ${s.description ? `<div style="margin-top:6px">${esc(s.description)}</div>` : ''}${s.tagline ? `<div class="quote" style="margin-top:4px">${esc(s.tagline)}</div>` : ''}
        ${(s.chips && s.chips.length) || (s.labels && s.labels.length) ? `<div class="row xs" style="margin-top:6px">${[...(s.labels || []), ...(s.chips || [])].map((x) => `<span class="chip">${esc(typeof x === 'string' ? x : JSON.stringify(x))}</span>`).join('')}</div>` : ''}
        ${itemsTable(s)}${sceneImages(s, vid)}
        <div class="row" style="margin-top:6px">${srcLink(s.src)}</div>${msgTree('industry_section', s.section_id)}</div>`).join('') || '<div class="empty">이 업종은 장면 데이터가 없습니다(US 업종은 섹션 단위로만 수집)</div>'}</div></div>`;
    for (const [lab, arr] of [['사이트 추천 솔루션', r.recommended], ['대표 도입사례 링크', r.cases]]) {
      if (!arr.length) continue;
      h += `<div class="section"><h2>${lab}</h2><div class="card">${arr.map((s) => `<div class="scene"><div class="row"><h3>${esc(s.title || '')}</h3><span class="grow"></span>${rv('section', s.section_id, `${vname} · ${s.title || lab}`, { v: vid })}</div>${itemsTable(s)}<div class="row">${srcLink(s.src)}</div></div>`).join('')}</div></div>`;
    }
    h += needsHTML(D.kb.B1(vid));
    el.innerHTML = h;
    paintReviews(el);
  }

  /* ═════════ 제품 ═════════ */
  views.products = (el) => {
    const CAT = D.core.CAT;
    const tops = CAT.filter((c) => c[3] === 1);
    const kids = (p) => CAT.filter((c) => c[1] === p);
    const pathOf = (cid) => { const out = []; let x = cid; const seen = new Set(); while (x && !seen.has(x)) { seen.add(x); out.unshift(x); x = D.kb.catParent.get(x); } return out; };
    if (S.prod.cat && !S.prod.top) S.prod.top = pathOf(S.prod.cat)[0] || '';
    const listCats = S.prod.top ? kids(S.prod.top) : [];
    const subCats = [];
    for (const c of listCats) for (const s of kids(c[0])) subCats.push([s, c]);
    el.innerHTML = `<div class="filters">
        <input class="field" id="pq" placeholder="이름·모델·분류 검색 (예: 에어컨, 무풍 4way)" value="${esc(S.prod.text)}" style="width:260px">
        <select class="field" id="ptop"><option value="">전체 상위 분류</option>${tops.map((c) => `<option value="${esc(c[0])}" ${S.prod.top === c[0] ? 'selected' : ''}>${esc(c[2])}</option>`).join('')}</select>
        <select class="field" id="pcat" ${S.prod.top ? '' : 'disabled'}><option value="">${S.prod.top ? '전체 목록·하위 분류' : '상위 분류를 먼저 선택'}</option>
          ${listCats.map((c) => `<option value="${esc(c[0])}" ${S.prod.cat === c[0] ? 'selected' : ''}>${esc(c[2])}</option>${kids(c[0]).map((s) => `<option value="${esc(s[0])}" ${S.prod.cat === s[0] ? 'selected' : ''}>　└ ${esc(s[2])}</option>`).join('')}`).join('')}</select>
        <select class="field" id="pcap"><option value="">역량(provides) 전체</option>${D.core.K.map((k) => `<option value="${esc(k[0])}" ${S.prod.cap === k[0] ? 'selected' : ''}>${esc(k[2])} (${(IX.capFams.get(k[0]) || []).length})</option>`).join('')}</select>
        <select class="field" id="psort"><option value="rel" ${S.prod.sort === 'rel' ? 'selected' : ''}>관련도순(검색 시)</option><option value="cat" ${S.prod.sort === 'cat' ? 'selected' : ''}>분류순</option><option value="name" ${S.prod.sort === 'name' ? 'selected' : ''}>이름순</option><option value="caps" ${S.prod.sort === 'caps' ? 'selected' : ''}>역량 많은 순</option></select>
        ${S.prod.cat && !listCats.some((c) => c[0] === S.prod.cat) && !subCats.some(([s]) => s[0] === S.prod.cat) ? `<span class="chip k-category">${esc(D.kb.name('category', S.prod.cat))} <button class="x" style="width:18px;height:18px;font-size:11px" id="pclr">✕</button></span>` : ''}
      </div><div id="plist"></div>`;
    $('#pq', el).addEventListener('input', debounce((e) => { S.prod.text = e.target.value; S.prod.page = 0; S.prod.open = new Set(); renderProdList(); }, 150));
    $('#ptop', el).addEventListener('change', (e) => { S.prod.top = e.target.value; S.prod.cat = ''; S.prod.page = 0; views.products(el); });
    $('#pcat', el).addEventListener('change', (e) => { S.prod.cat = e.target.value; S.prod.page = 0; renderProdList(); });
    $('#pcap', el).addEventListener('change', (e) => { S.prod.cap = e.target.value; S.prod.page = 0; renderProdList(); });
    $('#psort', el).addEventListener('change', (e) => { S.prod.sort = e.target.value; renderProdList(); });
    const clr = $('#pclr', el);
    if (clr) clr.addEventListener('click', () => { S.prod.cat = ''; S.prod.top = ''; views.products(el); });
    renderProdList();
    if (!D.images) need.images().then(() => { if (current === 'products') renderProdList(); }).catch(() => {});
  };
  function renderProdList() {
    const el = $('#plist');
    if (!el) return;
    const kb = D.kb, P = S.prod;
    const toks = queryTokens(P.text);
    const M = new Map();
    let fams = D.g.fam.filter((f) => {
      if (P.top && !kb.fcats.get(f.id).has(P.top)) return false;
      if (P.cat && !kb.fcats.get(f.id).has(P.cat)) return false;
      if (P.cap && !(kb.prov.get(f.id) || new Map()).has(P.cap)) return false;
      if (toks.length) { const m = matchFields(famFields(f), toks); if (!m) return false; M.set(f.id, m); }
      return true;
    });
    const catName = (f) => kb.name('category', f.cat);
    const rel = (a, b) => (toks.length && P.sort === 'rel' ? M.get(b.id).score - M.get(a.id).score : 0);
    if (P.sort === 'name') fams.sort((a, b) => a.name.localeCompare(b.name, 'ko'));
    else if (P.sort === 'caps') fams.sort((a, b) => (kb.prov.get(b.id) || new Map()).size - (kb.prov.get(a.id) || new Map()).size);
    else fams.sort((a, b) => rel(a, b) || catName(a).localeCompare(catName(b), 'ko') || a.name.localeCompare(b.name, 'ko'));
    const cats = toks.length ? matchingCategories(toks) : [];
    // 검색 중이면 목록 분류별로 묶어 보여 준다(상위 분류로만 걸린 제품도 묶음 머리에서 바로 보이게)
    let groups = null;
    if (toks.length) {
      const g = new Map();
      for (const f of fams) { if (!g.has(f.cat)) g.set(f.cat, []); g.get(f.cat).push(f); }
      groups = [...g.entries()].map(([cid, fs]) => ({ cid, fs, best: Math.max(...fs.map((f) => M.get(f.id).score)) }));
      groups.sort((a, b) => b.best - a.best || kb.name('category', a.cid).localeCompare(kb.name('category', b.cid), 'ko'));
      fams = groups.flatMap((x) => x.fs);
    }
    const size = toks.length ? Infinity : 60, page = toks.length ? 0 : Math.min(P.page, Math.max(0, Math.ceil(fams.length / size) - 1));
    const show = toks.length ? fams : fams.slice(page * size, page * size + size);
    const pathName = (cid) => { const out = []; let x = cid; const seen = new Set(); while (x && !seen.has(x)) { seen.add(x); out.unshift(kb.name('category', x).split(' > ').pop()); x = kb.catParent.get(x); } return out.join(' > '); };
    const card = (f) => {
      const caps = [...(kb.prov.get(f.id) || new Map()).keys()];
      const g = IX.famGallery && IX.famGallery.get(f.id);
      const a = g != null && D.images ? D.images.assets[g] : null;
      return `<div class="card fcard" data-open="family:${esc(f.id)}" role="button" tabindex="0">${a && hasThumb(a[0]) ? thumbHTML(a, { grade: false }) : ''}<div class="nm">${esc(f.name)}</div><div class="mono faint">${esc(f.model || '')}</div>
        <div class="small muted">${esc(catName(f))}</div>${toks.length ? hitsHTML(M.get(f.id).hits) : ''}${caps.length ? `<div class="row">${caps.map((c) => `<span class="chip k-capability">${esc(kb.name('capability', c))}</span>`).join('')}</div>` : ''}
        <div class="xs faint">모델 ${(kb.modelsByFam.get(f.id) || []).length} · 스펙 ${fmt(f.nspec)} · 특장점 ${fmt(f.nfeat)}</div></div>`;
    };
    let body;
    if (groups) {
      const CAP = 8;
      P.open = P.open || new Set();
      body = groups.map((gr) => {
        const open = P.open.has(gr.cid) || gr.fs.length <= CAP + 2;
        const fs = open ? gr.fs : gr.fs.slice(0, CAP);
        return `<div class="section"><h2 style="font-size:14px"><button class="chip k-category" data-pcat="${esc(gr.cid)}" title="이 분류만 보기">${esc(pathName(gr.cid))}</button><span class="hint">${gr.fs.length}개</span></h2><div class="grid">${fs.map(card).join('')}</div>${open ? '' : `<button class="btn" data-pmore="${esc(gr.cid)}" style="margin-top:8px">나머지 ${gr.fs.length - CAP}개 더 보기</button>`}</div>`;
      }).join('');
    } else body = `<div class="grid">${show.map(card).join('')}</div>`;
    el.innerHTML = `${cats.length ? `<div class="row" style="margin-bottom:10px"><span class="small muted">'${esc(P.text.trim())}'와 맞는 분류</span>${cats.map(([c, n]) => `<button class="chip k-category" data-pcat="${esc(c[0])}" title="${esc(c[0])}">${esc(kb.name('category', c[0]))} <span class="faint">${n}</span></button>`).join('')}</div>` : ''}
      <div class="small muted" style="margin-bottom:8px">${fmt(fams.length)}개 제품군${toks.length ? ` · ${groups.length}개 분류 · 이름·모델·별칭과 소속 분류(상위 분류 포함)·사이트 필터 라벨에서 찾음` : ''}</div>${body}${toks.length ? '' : pager(fams.length, page, size, 'prod')}`;
    hydrateThumbs(el);
  }

  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-pmore]');
    if (!b) return;
    S.prod.open = S.prod.open || new Set();
    S.prod.open.add(b.dataset.pmore);
    const y = window.scrollY;
    renderProdList();
    window.scrollTo(0, y);
  });
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-pcat]');
    if (!b) return;
    const cid = b.dataset.pcat;
    let x = cid, top = cid;
    while (D.kb.catParent.get(x)) { x = D.kb.catParent.get(x); top = x; }
    S.prod.top = top; S.prod.cat = cid === top ? '' : cid; S.prod.text = ''; S.prod.page = 0;
    views.products($('#view'));
  });
  function openFamily(fid) {
    const kb = D.kb, f = kb.famById.get(fid);
    if (!f) return toast('제품군을 찾지 못했습니다: ' + fid);
    const src = kb.srcInfo(f.src);
    const models = kb.modelsByFam.get(fid) || [];
    const tags = groupBy(kb.tagsByFam.get(fid) || [], (t) => t[5] || t[1] || '기타');
    const prov = kb.provRowsByFam.get(fid) || [];
    const ks = kb.keyspecByFam.get(fid) || [];
    const c3 = kb.C3(fid);
    const ment = (IX.ment.get('family\u0001' + fid) || []).slice().sort((a, b) => b[3] - a[3]).slice(0, 12);
    const head = `<div class="small muted">${esc(kindName('family'))} · <span class="mono">${esc(fid)}</span></div><h2>${esc(f.name)}</h2><div class="row" style="margin-top:4px"><span class="mono">${esc(f.model || '')}</span>${entChip('category', f.cat)}${ext(f.url || (src && src.url), '상품 페이지')}<span class="grow"></span>${rv('family', fid, f.name, { fid })}</div>`;
    let b = '';
    b += `<div class="section"><h2>기본 정보</h2><div class="card pad kv">
      <div>상품 ID</div><div class="mono">${esc(f.goods || '')}</div>
      <div>대표 모델</div><div class="mono">${esc(f.model || '')}${f.mkt && f.mkt !== f.model ? ' · 마케팅 ' + esc(f.mkt) : ''}</div>
      <div>사이트 분류</div><div>${esc((f.ctg || []).filter(Boolean).join(' > '))}${f.grp ? ` <span class="mono faint">${esc(f.grp)}</span>` : ''}</div>
      <div>노출 목록</div><div class="row">${f.cats.map(([c, role]) => entChip('category', c, null, ` <span class="faint">${esc(L.role[role] || role)}</span>`)).join(' ')}</div>
      <div>판매 상태</div><div>${esc(f.sale || '–')}${f.reg ? ' · 등록 ' + esc(f.reg) : ''}</div>
      <div>출처</div><div>${src ? `${tierPill(f.tier)} ${ext(src.url, src.title || src.url)}` : '–'}</div>
      ${f.pdpd ? `<div>PDP 설명</div><div class="small">${esc(f.pdpd)}</div>` : ''}</div></div>`;
    b += `<div class="section"><h2>역량 근거(provides) <span class="hint">presence 규칙 초안 — 틀리면 ✗</span></h2><div class="card tw"><table><thead><tr><th>역량</th><th>근거</th><th>규칙</th><th>검수</th></tr></thead><tbody>
      ${prov.map((p) => `<tr><td>${entChip('capability', p[2])}</td><td class="small">${esc(p[4] || '')}</td><td class="xs mono faint">${esc(p[3] || '')}<br>${esc(p[6] || '')} ${esc(p[5] || '')}</td><td>${rv('provides', `${fid}|${p[2]}`, `${f.name} · ${kb.name('capability', p[2])}`, { fid })}</td></tr>`).join('') || '<tr><td class="muted" colspan="4">자동 규칙으로 잡힌 역량 없음</td></tr>'}
      </tbody></table></div></div>`;
    if (ks.length) b += `<div class="section"><h2>핵심 스펙 <span class="hint">대표 모델 · 정규 키</span></h2><div class="card tw"><table><thead><tr><th>항목(원문)</th><th>값(원문)</th><th>정규 키 · 수치</th><th>검수</th></tr></thead><tbody>
      ${ks.map((k) => `<tr><td>${esc(k[2])}</td><td>${esc(k[3])}</td><td class="small mono">${esc(k[1])}${k[4] != null ? ` = ${esc(k[4])} ${esc(k[5] || '')}` : ''}</td><td>${rv('spec', `${fid}|${k[1]}|${k[2]}`, `${f.name} · ${k[2]} ${k[3]}`, { fid })}</td></tr>`).join('')}
      </tbody></table></div></div>`;
    b += `<div class="section"><h2>사이트 필터 태그</h2><div class="card pad">${[...tags.entries()].map(([g, ts]) => `<div class="row" style="margin-bottom:6px"><span class="small muted" style="min-width:90px">${esc(g)}</span>${ts.map((t) => `<span class="chip" title="${esc(t[3] || '')} · ${esc(t[8] || '')}">${esc(t[6] || t[2] || t[3])}</span>`).join(' ')}</div>`).join('') || '<span class="muted small">없음</span>'}</div></div>`;
    b += `<div class="section"><h2>모델 ${models.length}</h2><div class="card tw"><table><thead><tr><th>모델 코드</th><th>옵션</th><th>대표</th><th>품절</th></tr></thead><tbody>
      ${models.map((m) => `<tr><td class="mono">${esc(m[1])}</td><td class="small">${esc([m[3], m[4]].filter(Boolean).join(': '))}</td><td>${m[5] ? '●' : ''}</td><td>${m[6] ? '품절' : ''}</td></tr>`).join('')}</tbody></table></div></div>`;
    if (f.usp.length || f.heads.length) b += `<div class="section"><h2>USP · 특장점 헤드라인</h2><div class="card pad">${f.usp.length ? `<div class="small muted">USP</div><ul style="margin:4px 0 10px;padding-left:18px">${f.usp.map((u) => `<li>${esc(u)}</li>`).join('')}</ul>` : ''}${f.heads.length ? `<div class="small muted">특장점 헤드라인</div><ul style="margin:4px 0 0;padding-left:18px">${f.heads.map((u) => `<li>${esc(u)}</li>`).join('')}</ul>` : ''}</div></div>`;
    b += `<div class="section"><h2>사이트가 추천한 업종·공간 <span class="hint">업종 페이지 장면 근거(C3)</span></h2><div class="card tw"><table><thead><tr><th>업종</th><th>공간</th><th>경로</th><th class="num">장면 수</th></tr></thead><tbody>
      ${c3.fits.map((x) => `<tr><td>${x.vertical ? entChip('vertical', x.vertical, x.vertical_name) : '–'}</td><td>${entChip('space_type', x.space, x.space_name)}</td><td class="small">${esc(x.via)}</td><td class="num">${x.n_sections}</td></tr>`).join('') || '<tr><td class="muted" colspan="4">업종 페이지 추천 없음</td></tr>'}
      </tbody></table></div>${c3.deployments.length ? `<div style="margin-top:8px" class="row"><span class="small muted">쓰인 도입사례 ${c3.precedent_count}</span> ${c3.deployments.slice(0, 20).map((d) => entChip('deployment', d.id, d.title)).join(' ')}</div>` : ''}</div>`;
    if (ment.length) b += `<div class="section"><h2>언급된 페이지 <span class="hint">이름·별칭·모델코드 언급 수</span></h2><div class="card tw"><table><tbody>${ment.map((m) => { const d = kb.docInfo(m[2]) || {}; return `<tr><td><span class="pill p-mute">${esc(ptName(d.page_type))}</span></td><td>${ext(d.url, d.title || d.url)}</td><td class="num">${m[3]}</td></tr>`; }).join('')}</tbody></table></div></div>`;
    b += `<div id="famimgs"><div class="small muted"><span class="spin"></span> 이미지 불러오는 중</div></div><div class="section" id="fampdp"><button class="btn" id="loadpdp">전체 스펙·특장점 블록 보기</button></div>`;
    openDrawer(head, b);
    $('#loadpdp').addEventListener('click', async () => {
      $('#fampdp').innerHTML = '<div class="small muted"><span class="spin"></span> 상품 상세 데이터 받는 중…</div>';
      try { await need.pdp(); $('#fampdp').innerHTML = pdpHTML(fid); paintReviews($('#fampdp')); } catch (e) { $('#fampdp').innerHTML = `<div class="empty">불러오지 못했습니다: ${esc(e.message)}</div>`; }
    });
    need.images().then(() => {
      const box = $('#famimgs');
      if (!box || !$('#drawer').classList.contains('on')) return;
      const all = targetAssets('family', fid);
      const pt = (ai) => (IX.occByAsset.get(ai) || []).map((o) => o[2]);
      const gal = all.filter((ai) => pt(ai).includes('pdp_gallery'));
      const feat = all.filter((ai) => !gal.includes(ai) && pt(ai).includes('pdp_feature'));
      const other = all.filter((ai) => !gal.includes(ai) && !feat.includes(ai));
      const caseImgs = [];
      for (const d of c3.deployments) for (const ai of targetAssets('deployment', d.id)) caseImgs.push(ai);
      const sec = (t, idxs, n) => (idxs.length ? `<div class="section"><h2>${t} <span class="hint">${idxs.length}장</span></h2>${imgGrid(idxs, n)}</div>` : '');
      box.innerHTML = sec('상품 갤러리', gal, 40) + sec('특장점 이미지', feat, 60) + sec('다른 페이지의 이미지(업종·솔루션)', other, 30) + sec('이 제품군을 쓴 도입사례 사진', caseImgs, 30);
      paintReviews(box);
    }).catch(() => {});
  }
  function pdpHTML(fid) {
    const kb = D.kb, specs = D.pdp.specs.get(fid) || [], feats = D.pdp.feats.get(fid) || [];
    const byModel = groupBy(specs, (s) => s[0]);
    let h = `<h2>전체 스펙 <span class="hint">모델 ${byModel.size} · 값 ${fmt(specs.length)}</span></h2>`;
    for (const [mid, rows] of byModel) {
      h += `<details class="card pad" style="margin-bottom:8px"><summary><b class="mono">${esc(kb.name('model', mid))}</b> <span class="small muted">${rows.length}행</span></summary><div class="tw"><table><tbody>
        ${[...groupBy(rows, (r) => r[2] || '').entries()].map(([g, rs]) => `<tr><th colspan="3">${esc(g || '기타')}</th></tr>${rs.map((r) => `<tr><td>${esc(r[3])}</td><td>${esc(r[4])}</td><td class="xs mono faint">${r[5] ? esc(r[5]) + (r[6] != null ? ' = ' + esc(r[6]) + (r[7] != null ? '~' + esc(r[7]) : '') + ' ' + esc(r[8] || '') : '') : ''}</td></tr>`).join('')}`).join('')}
        </tbody></table></div></details>`;
    }
    h += `<h2 style="margin-top:16px">특장점 블록 ${feats.length} <span class="hint">PDP 컴포넌트 · 헤드라인/본문/면책 분리</span></h2><div class="card">`;
    h += feats.map((x) => `<div class="hit"><div class="row"><span class="pill p-mute">${esc(x[4] || '')}</span><b>${esc(x[5] || '')}</b><span class="grow"></span>${x[9] ? `<span class="xs faint">이미지 ${x[9]}</span>` : ''}</div>${x[6] ? `<div class="small muted">${esc(x[6])}</div>` : ''}${x[7] ? `<div class="x small">${esc(x[7])}</div>` : ''}${x[8] ? `<div class="xs faint" style="margin-top:4px">${esc(x[8])}</div>` : ''}</div>`).join('') || '<div class="empty">특장점 블록 없음</div>';
    return h + '</div>';
  }

  /* ═════════ 도입사례 ═════════ */
  views.cases = (el) => {
    const krTop = D.core.V.filter((v) => v[5] === 'kr_site' && !v[4]);
    const fmts = [...new Set(D.g.deps.map((d) => d.format).filter(Boolean))].sort();
    el.innerHTML = `<div class="filters">
      <input class="field" id="cq" placeholder="제목·고객·제품·분류·공간 검색" value="${esc(S.cases.text)}" style="width:240px">
      <select class="field" id="cv"><option value="">전체 업종</option>${krTop.map((v) => `<option value="${esc(v[0])}" ${S.cases.v === v[0] ? 'selected' : ''}>${esc(v[2])}</option>`).join('')}</select>
      <select class="field" id="cf"><option value="">전체 형식</option>${fmts.map((f) => `<option ${S.cases.fmt === f ? 'selected' : ''}>${esc(f)}</option>`).join('')}</select>
      <label class="small row" style="gap:4px"><input type="checkbox" id="ck" ${S.cases.kpi ? 'checked' : ''}>KPI 있는 것만</label>
      <label class="small row" style="gap:4px"><input type="checkbox" id="cp" ${S.cases.photo ? 'checked' : ''}>사진 있는 것만</label></div><div id="clist"></div>`;
    const upd = () => { S.cases.text = $('#cq').value; S.cases.v = $('#cv').value; S.cases.fmt = $('#cf').value; S.cases.kpi = $('#ck').checked; S.cases.photo = $('#cp').checked; renderCaseList(); };
    $('#cq', el).addEventListener('input', debounce(upd, 150));
    for (const id of ['#cv', '#cf', '#ck', '#cp']) $(id, el).addEventListener('change', upd);
    renderCaseList();
    if (!D.images) need.images().then(() => { if (current === 'cases') renderCaseList(); }).catch(() => {});
  };
  function depText(d) {
    if (!IX.depText) IX.depText = new Map();
    let t = IX.depText.get(d.id);
    if (t) return t;
    const parts = [d.title, d.cust, d.scale, d.sind, ...(d.ind || []), ...(d.pg || []), ...(d.sg || []), ...(d.v || []).map((v) => D.kb.name('vertical', v))];
    for (const x of IX.depItems.get(d.id) || []) {
      parts.push(x[1]);
      if (!x[4]) continue;
      parts.push(D.kb.name(x[3], x[4]));
      const fam = x[3] === 'family' ? D.kb.famById.get(x[4]) : null;
      const cats = fam ? D.kb.fcats.get(fam.id) : x[3] === 'category' ? new Set([x[4]]) : null;
      if (cats) for (const cid of cats) { let y = cid; const seen = new Set(); while (y && !seen.has(y)) { seen.add(y); parts.push(D.kb.name('category', y), ...aliasesOf('category', y)); y = D.kb.catParent.get(y); } }
    }
    for (const s2 of IX.depSpace.get(d.id) || []) parts.push(s2[1], s2[2] ? D.kb.name('space_type', s2[2]) : '');
    t = nz(parts.filter(Boolean).join(' '));
    IX.depText.set(d.id, t);
    return t;
  }
  function renderCaseList() {
    const el = $('#clist');
    if (!el) return;
    const C = S.cases, toks = queryTokens(C.text), kb = D.kb;
    const deps = D.g.deps.filter((d) => {
      if (C.v && !(d.v || []).some((x) => x === C.v || (kb.vertById.get(x) || [])[4] === C.v)) return false;
      if (C.fmt && d.format !== C.fmt) return false;
      if (C.kpi && !(IX.kpi.get(d.id) || []).length) return false;
      if (C.photo && !IX.photo.has(d.id)) return false;
      if (toks.length) { const n = depText(d); if (!toks.every((t) => n.includes(t))) return false; }
      return true;
    }).sort((a, b) => String(b.date || '').localeCompare(String(a.date || '')));
    el.innerHTML = `<div class="small muted" style="margin-bottom:8px">${fmt(deps.length)}건</div><div class="card tw"><table><thead><tr><th style="width:84px"></th><th>사례</th><th>날짜</th><th>형식</th><th>업종</th><th class="num">제품 항목(해소)</th><th class="num">공간</th><th class="num">KPI</th></tr></thead><tbody>
      ${deps.map((d) => { const its = IX.depItems.get(d.id) || []; const ph = IX.depFirstPhoto && IX.depFirstPhoto.get(d.id); return `<tr class="click" data-open="deployment:${esc(d.id)}"><td class="tiny-thumbs sm" style="margin:0">${ph != null ? thumbHTML(D.images.assets[ph], { grade: false }) : ''}</td><td><b>${esc(d.title)}</b>${IX.photo.has(d.id) ? ' <span class="xs faint">📷</span>' : ''}</td><td class="small">${esc(d.date || '')}</td><td class="small">${esc(d.format || '')}</td><td>${(d.v || []).map((v) => `<span class="chip k-vertical">${esc(kb.name('vertical', v))}</span>`).join(' ')}</td><td class="num">${its.length} (${its.filter((x) => x[4]).length})</td><td class="num">${(IX.depSpace.get(d.id) || []).length}</td><td class="num">${(IX.kpi.get(d.id) || []).length || ''}</td></tr>`; }).join('')}
      </tbody></table></div>`;
    hydrateThumbs(el);
  }
  function openDeployment(did) {
    const kb = D.kb, d = kb.depById.get(did);
    if (!d) return toast('사례를 찾지 못했습니다: ' + did);
    const items = IX.depItems.get(did) || [], spaces = IX.depSpace.get(did) || [], needs = groupBy(IX.depNeed.get(did) || [], (n) => n[2] || '기타'), kpis = IX.kpi.get(did) || [];
    const doc = d.doc >= 0 ? kb.docInfo(d.doc) : null;
    const head = `<div class="small muted">도입사례 · <span class="mono">${esc(did)}</span></div><h2>${esc(d.title)}</h2><div class="row" style="margin-top:4px">${esc(d.date || '')} ${d.format ? `<span class="pill p-mute">${esc(d.format)}</span>` : ''}${ext(d.url || (doc && doc.url), '사례 페이지')}<span class="grow"></span>${rv('deployment', did, d.title, { did })}</div>`;
    let b = `<div class="section"><h2>기본 정보</h2><div class="card pad kv">
      <div>업종</div><div class="row">${(d.v || []).map((v) => entChip('vertical', v)).join(' ') || '–'}</div>
      <div>사이트 업종 표기</div><div>${esc(d.sind || '–')}</div><div>고객 유형·규모</div><div>${esc([d.cust, d.scale, d.sscale].filter(Boolean).join(' · ') || '–')}</div>
      <div>업종(원문)</div><div class="small">${esc((d.ind || []).join(', '))}</div><div>제품·솔루션 분류</div><div class="small">${esc([...(d.pg || []), ...(d.sg || [])].join(', '))}</div>
      <div>근거</div><div>${tierPill(d.tier)} <span class="xs mono faint">${esc(d.method || '')}</span></div></div>${d.quote ? `<div class="card pad" style="margin-top:8px"><span class="quote">${esc(d.quote)}</span></div>` : ''}</div>`;
    b += `<div class="section"><h2>공간 ${spaces.length} <span class="hint">원문 표현 → 공간 유형</span></h2><div class="card tw"><table><tbody>${spaces.map((s) => `<tr><td>${esc(s[1])}</td><td>${s[2] ? entChip('space_type', s[2]) : '<span class="pill p-warn">미해소</span>'}</td><td class="xs mono faint">${esc(s[3] || '')}</td><td>${rv('dep_space', `${did}|${s[1]}`, `${d.title} · ${s[1]}`, { did })}</td></tr>`).join('') || '<tr><td class="muted">없음</td></tr>'}</tbody></table></div></div>`;
    b += `<div class="section"><h2>쓰인 제품·솔루션 ${items.length} <span class="hint">원문 항목 → KB 대상</span></h2><div class="card tw"><table><thead><tr><th>원문</th><th>해소 대상</th><th>방법</th><th>검수</th></tr></thead><tbody>
      ${items.map((x) => `<tr><td>${esc(x[1])}${x[8] ? ' ' + ext(x[8], '링크') : ''}</td><td>${x[4] ? entChip(x[3], x[4]) : '<span class="pill p-warn">미해소</span>'}${x[2] ? ` <span class="xs faint">${esc(x[2])}</span>` : ''}</td><td class="xs mono faint">${esc(x[5] || '')}${x[6] != null ? ' · ' + x[6] : ''}${x[7] ? ' · ' + esc(x[7]) : ''}</td><td>${rv('dep_item', `${did}|${x[1]}`, `${d.title} · ${x[1]}`, { did })}</td></tr>`).join('') || '<tr><td class="muted">없음</td></tr>'}
      </tbody></table></div></div>`;
    if (kpis.length) b += `<div class="section"><h2>KPI 문장 ${kpis.length} <span class="hint">이전 세션 추출(T5) — 원문 대조 필요</span></h2><div class="card">${kpis.map((k) => `<div class="hit"><div class="row"><span class="grow">${esc(k[2])}</span>${k[4] ? '<span class="pill p-warn">claim</span>' : ''}${k[3] ? '<span class="pill p-acc">수치</span>' : ''}</div><div style="margin-top:4px">${rv('kpi', k[0], `${d.title} · ${k[2].slice(0, 60)}`, { did })}</div></div>`).join('')}</div></div>`;
    if (needs.size) b += `<div class="section"><h2>요구·과제</h2><div class="card pad">${[...needs.entries()].map(([k, ns]) => `<div class="row" style="margin-bottom:6px"><span class="small muted" style="min-width:90px">${esc(k)}</span>${ns.map((n) => `<span class="chip">${esc(n[1])}</span>`).join(' ')}</div>`).join('')}</div></div>`;
    b += '<div class="section" id="depimgs"></div>';
    openDrawer(head, b);
    need.images().then(() => {
      const box = $('#depimgs');
      if (!box) return;
      const set = new Set((IX.depictsByTarget.get('deployment\u0001' + did) || []).map((x) => x[0]));
      const rows = D.kb.imgRows((a, o) => o[2] === 'case_study' && set.has(IX.assetIdx.get(a[0])), 80);
      const others = targetAssets('deployment', did).filter((ai) => !rows.some((r) => r.id === D.images.assets[ai][0]));
      box.innerHTML = (rows.length ? `<h2>사례 사진 ${rows.length}</h2><div class="igrid">${rows.map((v) => imgCard(v)).join('')}</div>` : '')
        + (others.length ? `<div class="section" style="margin-top:16px"><h2>다른 페이지에서 이 사례를 보여 준 이미지</h2>${imgGrid(others, 24)}</div>` : '');
      paintReviews(box);
    }).catch(() => {});
  }

  /* ═════════ 이미지 ═════════ */
  views.images = (el) => {
    el.innerHTML = '<div class="empty"><span class="spin"></span> 이미지 데이터를 불러오는 중…</div>';
    need.images().then(() => { if (current === 'images') drawImages(el); }).catch((e) => { el.innerHTML = `<div class="empty">불러오지 못했습니다: ${esc(e.message)}</div>`; });
  };
  function drawImages(el) {
    const I = D.images, kb = D.kb;
    const pts = [...new Set(I.occ.map((o) => o[2]))].sort();
    const sps = [...new Set(I.occ.map((o) => o[6]).filter(Boolean))].sort((a, b) => kb.name('space_type', a).localeCompare(kb.name('space_type', b), 'ko'));
    const vs = [...new Set(I.occ.map((o) => o[7]).filter(Boolean))];
    el.innerHTML = `<div class="filters">
      <input class="field" id="iq" placeholder="alt·캡션·제품·분류·공간 검색" value="${esc(S.img.text)}" style="width:240px">
      <select class="field" id="ipt"><option value="">전체 페이지 유형</option>${pts.map((p) => `<option value="${esc(p)}" ${S.img.pt === p ? 'selected' : ''}>${esc(ptName(p))}</option>`).join('')}</select>
      <select class="field" id="ig"><option value="">전체 등급</option>${Object.keys(L.grade).map((g) => `<option value="${esc(g)}" ${S.img.grade === g ? 'selected' : ''}>${esc(g)} · ${esc(L.grade[g])}</option>`).join('')}</select>
      <select class="field" id="isp"><option value="">전체 공간</option>${sps.map((s) => `<option value="${esc(s)}" ${S.img.sp === s ? 'selected' : ''}>${esc(kb.name('space_type', s))}</option>`).join('')}</select>
      <select class="field" id="iv"><option value="">전체 업종</option>${vs.map((v) => `<option value="${esc(v)}" ${S.img.v === v ? 'selected' : ''}>${esc(kb.name('vertical', v))}</option>`).join('')}</select>
      <select class="field" id="ir"><option value="">전체 권리</option><option value="customer_case" ${S.img.rights === 'customer_case' ? 'selected' : ''}>사례 사진</option><option value="official" ${S.img.rights === 'official' ? 'selected' : ''}>공식 이미지</option></select>
      ${D.thumbs ? `<label class="small row" style="gap:4px"><input type="checkbox" id="it" ${S.img.thumb ? 'checked' : ''}>미리보기 있는 것만</label>` : '<span class="pill p-warn" title="썸네일 데이터가 이번 배포에 없음">미리보기 없음 — 카드의 원본 링크로 확인</span>'}
    </div><div id="ilist"></div>`;
    const upd = () => { S.img.text = $('#iq').value; S.img.pt = $('#ipt').value; S.img.grade = $('#ig').value; S.img.sp = $('#isp').value; S.img.v = $('#iv').value; S.img.rights = $('#ir').value; S.img.thumb = !!($('#it') && $('#it').checked); S.img.page = 0; renderImgList(); };
    $('#iq', el).addEventListener('input', debounce(upd, 200));
    for (const id of ['#ipt', '#ig', '#isp', '#iv', '#ir', '#it']) { const x = $(id, el); if (x) x.addEventListener('change', upd); }
    renderImgList();
  }
  function imgText(ai) {
    if (!IX.imgText) IX.imgText = new Map();
    let t = IX.imgText.get(ai);
    if (t) return t;
    const parts = [];
    for (const o of IX.occByAsset.get(ai) || []) {
      parts.push(o[3], o[4], o[5] >= 0 ? D.core.SEC[o[5]] : '', o[6] ? D.kb.name('space_type', o[6]) : '', o[7] ? D.kb.name('vertical', o[7]) : '');
      for (const [k, i] of o[8] || []) parts.push(D.kb.name(k, i));
    }
    for (const d of IX.depictsByAsset.get(ai) || []) {
      parts.push(D.kb.name(d[1], d[2]));
      const cats = d[1] === 'family' ? D.kb.fcats.get(d[2]) : d[1] === 'category' ? new Set([d[2]]) : null;
      if (cats) for (const cid of cats) parts.push(D.kb.name('category', cid), ...aliasesOf('category', cid));
    }
    t = nz(parts.filter(Boolean).join(' '));
    IX.imgText.set(ai, t);
    return t;
  }
  function renderImgList() {
    const el = $('#ilist');
    if (!el) return;
    const I = D.images, F = S.img, toks = queryTokens(F.text);
    const out = [];
    I.assets.forEach((a, ai) => {
      if (F.grade && a[4] !== F.grade) return;
      if (F.rights && a[6] !== F.rights) return;
      if (F.thumb && !(D.thumbs && D.thumbs.idx[a[0]])) return;
      const occ = IX.occByAsset.get(ai) || [];
      let o = occ[0];
      if (F.pt || F.sp || F.v) {
        o = occ.find((x) => (!F.pt || x[2] === F.pt) && (!F.sp || x[6] === F.sp) && (!F.v || x[7] === F.v));
        if (!o) return;
      }
      if (toks.length) { const n = imgText(ai); if (!toks.every((t) => n.includes(t))) return; }
      if (!o) return;
      out.push([a, o]);
    });
    const GP = D.kb.kw.GRADE_PRIORITY;
    out.sort((x, y) => (D.thumbs ? (+!D.thumbs.idx[x[0][0]]) - (+!D.thumbs.idx[y[0][0]]) : 0) || (GP[x[0][4]] ?? 9) - (GP[y[0][4]] ?? 9));
    const size = 48, page = Math.min(F.page, Math.max(0, Math.ceil(out.length / size) - 1));
    el.innerHTML = `<div class="small muted" style="margin-bottom:8px">${fmt(out.length)}개 이미지 · 등급은 규칙 힌트(VLM 판정 전). 틀린 등급은 ✗ 와 함께 고친 값을 고르세요</div>
      <div class="igrid">${out.slice(page * size, page * size + size).map(([a, o]) => imgCard(D.kb.imgView(a, o))).join('')}</div>${pager(out.length, page, size, 'img')}`;
    paintReviews(el);
  }
  function openImage(aid) {
    const go2 = () => {
      const kb = D.kb, ai = IX.assetIdx.get(aid);
      if (ai == null) return toast('이미지를 찾지 못했습니다');
      const a = D.images.assets[ai], occ = IX.occByAsset.get(ai) || [], dep = IX.depictsByAsset.get(ai) || [];
      const head = `<div class="small muted">이미지 · <span class="mono">${esc(aid)}</span></div><h2>${esc((occ[0] && occ[0][3]) || '이미지')}</h2><div class="row" style="margin-top:4px"><span class="grade g-${gcls(a[4])}">${esc(a[4] || '–')}</span><span class="small muted">${esc(L.grade[a[4]] || '')}${a[5] ? ' · ' + esc(a[5]) : ''}</span>${ext(a[1], 'PC 원본')}${ext(a[2], '모바일 원본')}</div>`;
      let b = `<div class="section" style="max-width:420px">${thumbHTML(a)}</div><div class="section">${rv('image', aid, ((occ[0] && occ[0][3]) || aid).slice(0, 80), { aid }, { fix: ['A', 'A?C', 'B', 'C', 'D', 'E'] })}</div>`;
      b += `<div class="section"><h2>등장 ${occ.length}</h2><div class="card">${occ.map((o) => { const d = kb.docInfo(o[1]) || {}; return `<div class="hit"><div class="row"><span class="pill p-mute">${esc(ptName(o[2]))}</span>${ext(d.url, d.title || d.url)}</div>
        ${o[3] ? `<div class="small" style="margin-top:4px">alt: ${esc(o[3])}</div>` : ''}${o[4] ? `<div class="small muted">캡션: ${esc(o[4])}</div>` : ''}${o[5] >= 0 ? `<div class="xs faint">섹션: ${esc(D.core.SEC[o[5]])}</div>` : ''}
        <div class="row" style="margin-top:4px">${o[6] ? entChip('space_type', o[6]) : ''}${o[7] ? entChip('vertical', o[7]) : ''}${(o[8] || []).map(([k, i]) => entChip(k, i)).join(' ')}</div></div>`; }).join('')}</div></div>`;
      const rel = [];
      for (const o of occ) for (const x of IX.occByDoc.get(o[1]) || []) if (x[0] !== ai) rel.push(x[0]);
      if (rel.length) b += `<div class="section"><h2>같은 페이지의 다른 이미지 <span class="hint">${new Set(rel).size}장</span></h2>${stripHTML(rel, 24)}</div>`;
      if (dep.length) b += `<div class="section"><h2>묘사 대상</h2><div class="card tw"><table><tbody>${dep.map((x) => `<tr><td>${entChip(x[1], x[2])}</td><td class="small">${esc(x[3] || '')}</td><td class="num">${x[4] != null ? x[4] : ''}</td></tr>`).join('')}</tbody></table></div></div>`;
      openDrawer(head, b);
    };
    if (D.images) go2(); else need.images().then(go2).catch((e) => toast(e.message));
  }

  /* ═════════ 메시지 ═════════ */
  views.messages = (el) => {
    el.innerHTML = '<div class="empty"><span class="spin"></span> 메시지를 불러오는 중…</div>';
    need.msgs().then(() => { if (current === 'messages') drawMessages(el); }).catch((e) => { el.innerHTML = `<div class="empty">불러오지 못했습니다: ${esc(e.message)}</div>`; });
  };
  function drawMessages(el) {
    const kinds = [...new Set(D.msgs.map((m) => m[4]))].sort();
    el.innerHTML = `<p class="lead">사이트 원문 그대로의 메시지 계층(태그라인 → 핵심 메시지 → 근거 문장, USP). 문장을 바꾸지 않았는지, 대상(about)이 맞는지, claim(수치·최상급) 표시가 맞는지 확인합니다.</p>
      <div class="filters"><input class="field" id="mq" placeholder="문장 검색" value="${esc(S.msg.text)}" style="width:220px">
      <select class="field" id="ml"><option value="">전체 단계</option>${Object.entries(L.level).map(([k, v]) => `<option value="${k}" ${S.msg.level === k ? 'selected' : ''}>${esc(v)}</option>`).join('')}</select>
      <select class="field" id="ma"><option value="">전체 대상 유형</option>${kinds.map((k) => `<option value="${esc(k)}" ${S.msg.about === k ? 'selected' : ''}>${esc(kindName(k))}</option>`).join('')}</select>
      <label class="small row" style="gap:4px"><input type="checkbox" id="mc" ${S.msg.claim ? 'checked' : ''}>claim 표시만</label></div><div id="mlist"></div>`;
    const upd = () => { S.msg.text = $('#mq').value; S.msg.level = $('#ml').value; S.msg.about = $('#ma').value; S.msg.claim = $('#mc').checked; S.msg.page = 0; renderMsgList(); };
    $('#mq', el).addEventListener('input', debounce(upd, 200));
    for (const id of ['#ml', '#ma', '#mc']) $(id, el).addEventListener('change', upd);
    renderMsgList();
    if (!D.images) need.images().then(() => { if (current === 'messages') renderMsgList(); }).catch(() => {});
  }
  function aboutChip(kind, id) {
    if (kind === 'industry_section') { const s = D.kb.secById.get(id); return s ? `<button class="chip k-vertical" data-sec="${esc(id)}">${esc(D.kb.name('vertical', s[1]))} · ${esc(s[5] || '')}</button>` : esc(id); }
    return entChip(kind, id);
  }
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-sec]');
    if (!b) return;
    const s = D.kb.secById.get(b.dataset.sec);
    if (!s) return;
    closeDrawer();
    S.vert.v = s[1];
    go('verticals');
    setTimeout(() => { const x = document.getElementById('sec-' + s[0]); if (x) x.scrollIntoView({ block: 'center' }); }, 60);
  });
  function renderMsgList() {
    const el = $('#mlist');
    if (!el) return;
    const F = S.msg, q = F.text.trim();
    const rows = D.msgs.filter((m) => (!F.level || m[1] === F.level) && (!F.about || m[4] === F.about) && (!F.claim || m[9]) && (!q || m[2].includes(q)));
    const size = 50, page = Math.min(F.page, Math.max(0, Math.ceil(rows.length / size) - 1));
    el.innerHTML = `<div class="small muted" style="margin-bottom:8px">${fmt(rows.length)}개 문장</div><div class="card tw"><table><thead><tr><th style="width:76px"></th><th>단계</th><th>문장</th><th>대상</th><th>출처</th><th>검수</th></tr></thead><tbody>
      ${rows.slice(page * size, page * size + size).map((m) => { const s = D.kb.srcInfo(m[10]); return `<tr><td>${entityThumb(m[4], m[5])}</td><td><span class="pill p-mute">${esc(L.level[m[1]] || m[1])}</span>${m[9] ? ' <span class="pill p-warn">claim</span>' : ''}</td><td style="min-width:260px">${highlight(m[2], q ? [q] : [])}${m[3] && IX.msgById.get(m[3]) ? `<div class="xs faint">상위: ${esc(IX.msgById.get(m[3])[2].slice(0, 60))}</div>` : ''}</td><td>${aboutChip(m[4], m[5])}</td><td class="small">${s ? ext(s.url, ptName(s.page_type) || '원문') : ''} ${tierPill(m[11])}</td><td>${rv('message', m[0], m[2].slice(0, 80), { mid: m[0] })}</td></tr>`; }).join('')}
      </tbody></table></div>${pager(rows.length, page, size, 'msg')}`;
    paintReviews(el);
  }
  function openMessage(mid) {
    need.msgs().then(() => {
      const m = IX.msgById.get(mid);
      if (!m) return toast('메시지를 찾지 못했습니다');
      const s = D.kb.srcInfo(m[10]);
      openDrawer(`<div class="small muted">메시지 · ${esc(L.level[m[1]] || m[1])}</div><h2>${esc(m[2])}</h2>`,
        `<div class="card pad kv"><div>대상</div><div>${aboutChip(m[4], m[5])}</div><div>claim</div><div>${m[9] ? '예' : '아니오'}</div><div>출처</div><div>${s ? ext(s.url, s.title || s.url) + ' · ' + esc(s.section || '') : '–'}</div><div>방법</div><div class="mono small">${esc(m[12] || '')} ${esc(m[11] || '')}</div></div>
        <div class="section" style="margin-top:12px">${rv('message', m[0], m[2].slice(0, 80), { mid })}</div>`);
    });
  }
  function openSolution(kind, id) {
    const row = (kind === 'solution' ? D.core.SOL : D.core.SVC).find((x) => x[0] === id);
    const kb = D.kb;
    const recs = (kb.edgesByRel.get('RECOMMENDED_BY_SITE') || []).filter((e) => e[3] === kind && e[4] === id);
    const feats = (kb.edgesByRel.get('FEATURED_BY_SITE') || []).filter((e) => e[3] === kind && e[4] === id);
    const deps = (kb.edgesByRel.get('USES') || []).filter((e) => e[0] === 'deployment' && e[3] === kind && e[4] === id);
    openDrawer(`<div class="small muted">${esc(kindName(kind))} · <span class="mono">${esc(id)}</span></div><h2>${esc(kb.name(kind, id))}</h2><div class="row">${row && row[5] ? ext(row[5], '페이지') : ''}<span class="grow"></span>${rv(kind, id, kb.name(kind, id), {})}</div>`,
      `<div class="section"><h2>추천된 공간 ${recs.length}</h2><div class="row">${recs.map((e) => entChip('space_type', e[1])).join(' ') || '<span class="muted small">없음</span>'}</div></div>
       <div class="section"><h2>업종 페이지 노출 ${feats.length}</h2><div class="row">${[...new Set(feats.map((e) => e[1]))].map((v) => entChip('vertical', v)).join(' ') || '<span class="muted small">없음</span>'}</div></div>
       <div class="section"><h2>쓰인 도입사례 ${deps.length}</h2><div class="row">${deps.map((e) => entChip('deployment', e[1])).join(' ') || '<span class="muted small">없음</span>'}</div></div>
       <div class="section" id="solimgs"></div><div class="section" id="solmsgs"></div>`);
    need.images().then(() => { const b = $('#solimgs'); if (b) { const idxs = targetAssets(kind, id); b.innerHTML = idxs.length ? `<h2>이 ${esc(kindName(kind))}을 보여 주는 이미지 <span class="hint">${idxs.length}장</span></h2>${imgGrid(idxs, 36)}` : ''; paintReviews(b); } }).catch(() => {});
    need.msgs().then(() => { const b = $('#solmsgs'); if (b) { b.innerHTML = `<h2>메시지</h2>${msgTree(kind, id) || '<span class="muted small">없음</span>'}`; paintReviews(b); } });
  }
  function openSpace(sp) {
    const kb = D.kb;
    const req = kb.req.get(sp) || [];
    const recs = (kb.edgesByRel.get('RECOMMENDED_BY_SITE') || []).filter((e) => e[1] === sp);
    const verts = (kb.edgesByRel.get('HAS_SPACE') || []).filter((e) => e[4] === sp).map((e) => e[1]);
    const labels = D.core.SL.filter((l) => l[2] === sp);
    const deps = D.g.dep_space.filter((d) => d[2] === sp);
    openDrawer(`<div class="small muted">공간 유형 · <span class="mono">${esc(sp)}</span></div><h2>${esc(kb.name('space_type', sp))}</h2>`,
      `<div class="section"><h2>요구 역량(requires 초안)</h2><div class="card tw"><table><tbody>${req.map((r) => `<tr><td>${entChip('capability', r[1])}</td><td>${esc(r[2])}</td><td class="small muted">${esc(r[3] || '')} ${esc(r[4] || '')}</td><td>${rv('requires', `${sp}|${r[1]}`, `${kb.name('space_type', sp)} → ${kb.name('capability', r[1])}`, {})}</td></tr>`).join('') || '<tr><td class="muted">없음</td></tr>'}</tbody></table></div></div>
       <div class="section"><h2>사이트 라벨 ${labels.length}</h2><div class="row">${labels.map((l) => `<span class="chip" title="${esc(l[3] || '')} · ${l[5] || 0}회">${esc(l[0])}</span>`).join(' ') || '<span class="muted small">없음</span>'}</div></div>
       <div class="section"><h2>이 공간이 있는 업종</h2><div class="row">${[...new Set(verts)].map((v) => entChip('vertical', v)).join(' ') || '<span class="muted small">없음</span>'}</div></div>
       <div class="section"><h2>사이트 추천 대상 ${recs.length}</h2><div class="row">${recs.map((e) => `<span title="${esc(e[8] || '')}">${entChip(e[3], e[4])}</span>`).join(' ') || '<span class="muted small">없음</span>'}</div></div>
       <div class="section"><h2>도입사례 ${deps.length}</h2><div class="row">${[...new Set(deps.map((d) => d[0]))].map((d) => entChip('deployment', d)).join(' ') || '<span class="muted small">없음</span>'}</div></div>
       <div class="section" id="spimgs"></div>`);
    need.images().then(() => { const b = $('#spimgs'); if (!b) return; const rows = D.kb.imgRows((a, o) => o[6] === sp, 36); b.innerHTML = rows.length ? `<h2>이 공간 이미지 <span class="hint">맥락 공간이 ${esc(kb.name('space_type', sp))}인 이미지</span></h2><div class="igrid">${rows.map((v) => imgCard(v)).join('')}</div>` : ''; paintReviews(b); }).catch(() => {});
  }

  /* ═════════ 컨텍스트 → 메시지(E3) ═════════ */
  const CM_PRESETS = [
    ['호텔 객실', { v: 'kr_hotel', spaces: ['guest_room'], products: [], cust: '비즈니스호텔 체인', text: '객실 TV를 통합 관리하고 투숙객 만족도를 높이고 싶어' }],
    ['병원 병실 태블릿', { v: 'kr_hospital', spaces: ['patient_room'], products: [['category', 'cat_tablets']], cust: '', text: '병상에서 환자가 쓰는 태블릿' }],
    ['학교 교실', { v: 'kr_school', spaces: ['classroom'], products: [], cust: '초등학교', text: '전자칠판으로 판서를 공유하고 싶어' }],
    ['카페 프랜차이즈', { v: '', spaces: [], products: [], cust: '프랜차이즈 카페 본사', text: '여러 매장의 메뉴보드 콘텐츠를 원격으로 중앙 관리' }],
    ['요구사항 문장만', { v: '', spaces: [], products: [], cust: '', text: '호텔 객실 TV를 통합 관리하고 로비에 대형 비디오월을 설치하고 싶어' }],
    ['제품만(b.IoT)', { v: '', spaces: [], products: [['solution', 'sol_biot']], cust: '', text: '' }],
  ];
  const CM_F = { product: '제품', vertical: '업종', space: '공간', customer: '타겟고객', text: '요구사항 유사도' };
  const CM_C = { product: 'b-fprod', vertical: 'b-fvert', space: 'b-fspace', customer: 'b-fcust', text: 'b-ftext' };
  const CM_GAIN = {
    vertical: '업종을 정하면 업종 페이지 헤드라인·장면 문구와 그 업종 사례가 붙습니다',
    space: '공간을 정하면 그 공간 장면 문구와 공간 추천 제품이 올라옵니다',
    product: '제품을 정하면 그 제품군의 USP·특장점 문구와 그 제품을 쓴 사례가 붙습니다',
    customer: '타겟고객을 적으면 고객 유형이 비슷한 도입사례 인용이 붙습니다',
    text: '요구사항 문장을 적으면 비슷한 문구를 찾고, 비워 둔 업종·공간·제품을 추론합니다',
  };
  const cmClean = (c) => ({ v: c.v || '', spaces: [...(c.spaces || [])], products: (c.products || []).map((p) => [p[0], p[1]]), cust: c.cust || '', text: c.text || '', locale: c.locale == null ? 'ko-KR' : c.locale });
  const cmInput = () => cmClean(S.cm);
  const cmKey = (c) => fnv36(JSON.stringify([c.v, [...c.spaces].sort(), c.products.map((p) => p.join(':')).sort(), c.cust.trim(), c.text.trim(), c.locale]));
  function cmSummary(c) {
    const kb = D.kb, parts = [];
    if (c.v) parts.push(kb.name('vertical', c.v));
    if (c.spaces.length) parts.push(c.spaces.map((s) => kb.name('space_type', s)).join('·'));
    if (c.products.length) parts.push(c.products.map((p) => kb.name(p[0], p[1])).join('·'));
    if (c.cust.trim()) parts.push(c.cust.trim());
    if (c.text.trim()) parts.push('“' + (c.text.trim().length > 30 ? c.text.trim().slice(0, 30) + '…' : c.text.trim()) + '”');
    return parts.join(' / ') || '(빈 컨텍스트)';
  }
  views.ctxmsg = (el) => {
    const c = S.cm, V = D.core.V;
    const kr = V.filter((v) => v[5] === 'kr_site'), us = V.filter((v) => v[5] === 'us_site');
    let vopt = '<option value="">선택 안 함(문장에서 추론)</option><optgroup label="KR 업종">';
    for (const p of kr.filter((v) => !v[4])) {
      vopt += `<option value="${esc(p[0])}" ${c.v === p[0] ? 'selected' : ''}>${esc(p[2] || p[3])}</option>`;
      for (const ch of kr.filter((v) => v[4] === p[0])) vopt += `<option value="${esc(ch[0])}" ${c.v === ch[0] ? 'selected' : ''}>  └ ${esc(ch[2] || ch[3])}</option>`;
    }
    vopt += `</optgroup><optgroup label="US 업종(영어 메시지)">${us.map((v) => `<option value="${esc(v[0])}" ${c.v === v[0] ? 'selected' : ''}>${esc(v[2] || v[3])}</option>`).join('')}</optgroup>`;
    const sps = [...D.core.S].sort((a, b) => (a[2] || a[0]).localeCompare(b[2] || b[0], 'ko'));
    const custs = [...new Set(D.g.deps.map((d) => d.cust).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'ko'));
    el.innerHTML = `<p class="lead">요구사항 컨텍스트(업종·공간·제품·타겟고객·요구사항 — 모두 선택)를 넣으면 KB의 원문 메시지를 <b>헤드라인 → 핵심 메시지(+근거 문장) → 제품 메시지 → 근거 사례</b>로 뽑습니다. 문장은 사이트 원문 그대로이고, 비워 둔 업종·공간·제품은 타겟고객·요구사항 문장에서 추론합니다(가중치 0.5배). 각 문장의 ✓ ✗ ? 는 “이 컨텍스트에 맞는 메시지인가”를 표시합니다.</p>
      <div class="card pad section">
        <div class="cmform">
          <div class="cmf"><label for="cmv">업종 <span class="opt">선택</span></label><select class="field" id="cmv">${vopt}</select></div>
          <div class="cmf"><label for="cmsp">공간 <span class="opt">선택 · 여러 개</span></label><select class="field" id="cmsp"><option value="">공간 추가…</option>${sps.map((s) => `<option value="${esc(s[0])}">${esc(s[2] || s[0])}</option>`).join('')}</select><div class="picked" id="cmsppick"></div></div>
          <div class="cmf"><label for="cmpq">제품 <span class="opt">선택 · 여러 개 · 제품군·분류·솔루션</span></label><div class="combo"><input class="field" id="cmpq" placeholder="예: 호텔 TV, 비디오월, b.IoT" autocomplete="off" role="combobox" aria-expanded="false" aria-controls="cmsugg"><div class="sugg" id="cmsugg" role="listbox"></div></div><div class="picked" id="cmppick"></div></div>
          <div class="cmf"><label for="cmcust">타겟고객 <span class="opt">선택</span></label><input class="field" id="cmcust" list="cmcustl" placeholder="예: 비즈니스호텔 체인, 대학교, 프랜차이즈 카페 본사" value="${esc(c.cust)}"><datalist id="cmcustl">${custs.map((x) => `<option value="${esc(x)}">`).join('')}</datalist></div>
          <div class="cmf full"><label for="cmtext">요구사항 <span class="opt">선택</span></label><textarea class="field" id="cmtext" rows="2" placeholder="예: 객실 TV를 통합 관리하고 로비에 대형 비디오월을 설치하고 싶어">${esc(c.text)}</textarea></div>
        </div>
        <div class="row" style="margin-top:12px"><button class="btn primary" id="cmrun">메시지 뽑기</button><button class="btn" id="cmclear">지우기</button>
          <select class="field" id="cmloc" title="메시지 언어"><option value="ko-KR" ${c.locale === 'ko-KR' ? 'selected' : ''}>한국어 메시지</option><option value="en-US" ${c.locale === 'en-US' ? 'selected' : ''}>영어(US) 메시지</option><option value="" ${c.locale === '' ? 'selected' : ''}>모든 언어</option></select>
          <span class="grow"></span><span class="small faint" id="cmstat"></span></div>
        <div class="examples" id="cmex"><span class="small muted" style="align-self:center">예시</span>${CM_PRESETS.map(([l], i) => `<button class="chip" data-cmpre="${i}">${esc(l)}</button>`).join('')}</div>
      </div>
      <div id="cmout"></div>`;
    paintPicked();
    $('#cmv', el).addEventListener('change', (e) => { S.cm.v = e.target.value; cmSave(); });
    $('#cmsp', el).addEventListener('change', (e) => { const v = e.target.value; if (v && !S.cm.spaces.includes(v)) S.cm.spaces.push(v); e.target.value = ''; paintPicked(); cmSave(); });
    $('#cmcust', el).addEventListener('input', (e) => { S.cm.cust = e.target.value; cmSave(); });
    $('#cmtext', el).addEventListener('input', (e) => { S.cm.text = e.target.value; cmSave(); });
    $('#cmtext', el).addEventListener('keydown', (e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); runCtxMsg(); } });
    $('#cmloc', el).addEventListener('change', (e) => { S.cm.locale = e.target.value; cmSave(); });
    $('#cmrun', el).addEventListener('click', runCtxMsg);
    $('#cmclear', el).addEventListener('click', () => { Object.assign(S.cm, cmClean({ locale: S.cm.locale })); S.cm.lastHTML = null; cmSave(); views.ctxmsg(el); });
    $('#cmex', el).addEventListener('click', (e) => { const b = e.target.closest('[data-cmpre]'); if (!b) return; Object.assign(S.cm, cmClean({ ...CM_PRESETS[+b.dataset.cmpre][1], locale: S.cm.locale })); cmSave(); views.ctxmsg(el); runCtxMsg(); });
    const pq = $('#cmpq', el), sg = $('#cmsugg', el);
    const showSugg = () => {
      const items = productSuggest(pq.value);
      sg.innerHTML = items.length ? items.map(([k, i, n, sub], j) => `<button type="button" role="option" data-add="${esc(k)}:${esc(i)}" class="${j === 0 ? 'act' : ''}"><span class="k">${esc(kindName(k))}</span><span class="grow">${esc(n)}</span><span class="xs faint">${esc(sub || '')}</span></button>`).join('')
        : (pq.value.trim() ? '<div class="small muted" style="padding:8px 10px">맞는 제품·분류·솔루션 없음</div>' : '');
      const on = !!pq.value.trim();
      sg.classList.toggle('on', on);
      pq.setAttribute('aria-expanded', on ? 'true' : 'false');
    };
    pq.addEventListener('input', debounce(showSugg, 120));
    pq.addEventListener('focus', () => { if (pq.value.trim()) showSugg(); });
    pq.addEventListener('keydown', (e) => {
      const bs = $$('button', sg);
      let k = bs.findIndex((b) => b.classList.contains('act'));
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); if (!bs.length) return; k = (k + (e.key === 'ArrowDown' ? 1 : bs.length - 1)) % bs.length; bs.forEach((b, j) => b.classList.toggle('act', j === k)); bs[k].scrollIntoView({ block: 'nearest' }); }
      else if (e.key === 'Enter') { e.preventDefault(); if (bs[k >= 0 ? k : 0]) bs[k >= 0 ? k : 0].click(); }
      else if (e.key === 'Escape') { sg.classList.remove('on'); pq.setAttribute('aria-expanded', 'false'); }
    });
    sg.addEventListener('mousedown', (e) => e.preventDefault());
    sg.addEventListener('click', (e) => {
      const b = e.target.closest('[data-add]');
      if (!b) return;
      const v = b.dataset.add, j = v.indexOf(':'), p = [v.slice(0, j), v.slice(j + 1)];
      if (!S.cm.products.some((x) => x[0] === p[0] && x[1] === p[1])) S.cm.products.push(p);
      pq.value = ''; sg.classList.remove('on'); pq.setAttribute('aria-expanded', 'false');
      paintPicked(); cmSave();
    });
    pq.addEventListener('blur', () => setTimeout(() => { sg.classList.remove('on'); pq.setAttribute('aria-expanded', 'false'); }, 120));
    if (S.cm.lastHTML) { $('#cmout').innerHTML = S.cm.lastHTML; paintReviews($('#cmout')); }
    need.msgs().catch(() => {});
    if (!D.images) need.images().catch(() => {});
  };
  function cmSave() { const c = cmInput(); store.set('cm', c); }
  function paintPicked() {
    const kb = D.kb;
    const a = $('#cmsppick'), b = $('#cmppick');
    if (a) a.innerHTML = S.cm.spaces.map((s, i) => `<span class="chip k-space_type">${esc(kb.name('space_type', s))}<button type="button" data-rm="s:${i}" aria-label="${esc(kb.name('space_type', s))} 빼기">×</button></span>`).join('');
    if (b) b.innerHTML = S.cm.products.map((p, i) => `<span class="chip k-${esc(p[0])}" title="${esc(kindName(p[0]))}">${esc(kb.name(p[0], p[1]))}<button type="button" data-rm="p:${i}" aria-label="${esc(kb.name(p[0], p[1]))} 빼기">×</button></span>`).join('');
  }
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-rm]');
    if (!b || current !== 'ctxmsg') return;
    const [k, i] = b.dataset.rm.split(':');
    (k === 's' ? S.cm.spaces : S.cm.products).splice(+i, 1);
    paintPicked(); cmSave();
  });
  /* 결과에서 추론값 고정·다른 업종 후보 고르기 */
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-cmset]');
    if (!b || current !== 'ctxmsg') return;
    const r = S.cm.res && S.cm.res.result.context;
    const v = b.dataset.cmset;
    if (v.startsWith('v:')) S.cm.v = v.slice(2);
    else if (v === 'spaces' && r) S.cm.spaces = r.spaces.map((s) => s.id);
    else if (v === 'products' && r) S.cm.products = r.products.map((p) => [p.kind, p.id]);
    cmSave();
    views.ctxmsg($('#view'));
    runCtxMsg();
  });
  /* 제품 입력 제안: 분류(이름·별칭) → 솔루션·서비스 → 제품군(계층 검색과 같은 필드) */
  function productSuggest(q) {
    const toks = queryTokens(q);
    if (!toks.length) return [];
    const out = [];
    for (const [c, cnt] of matchingCategories(toks).slice(0, 6)) out.push(['category', c[0], D.kb.name('category', c[0]), `제품군 ${cnt}`]);
    for (const [arr, kind] of [[D.core.SOL, 'solution'], [D.core.SVC, 'service']]) for (const s of arr) {
      const n = [s[2], s[1], ...aliasesOf(kind, s[0])].filter(Boolean).map(nz).join(' ');
      if (toks.every((t) => n.includes(t))) out.push([kind, s[0], s[2], '']);
    }
    const fams = [];
    for (const f of D.g.fam) { const m = matchFields(famFields(f), toks); if (m) fams.push([m.score, f]); }
    fams.sort((a, b) => b[0] - a[0]);
    for (const [, f] of fams.slice(0, 10)) out.push(['family', f.id, f.name, f.model || '']);
    return out.slice(0, 18);
  }
  let cmRunId = 0;
  async function runCtxMsg() {
    const out = $('#cmout'), stat = $('#cmstat');
    if (!out) return;
    const c = cmInput();
    if (!c.v && !c.spaces.length && !c.products.length && !c.cust.trim() && !c.text.trim()) { out.innerHTML = '<div class="empty">업종·공간·제품·타겟고객·요구사항 중 하나 이상을 넣어 주세요.</div>'; return; }
    const my = ++cmRunId;
    const pending = ['msgs', 'vec'].filter((g) => !Load.groups.has(g));
    out.innerHTML = `<div class="empty"><span class="spin"></span> ${pending.length ? `메시지와 문장 벡터 데이터를 처음 한 번 받는 중입니다(약 ${Math.round(Load.size(['msgs.json.gz', 'lsa_vocab.json.gz', 'lsa.bin', 'vec_refs.json.gz', 'vec_core.bin']) / 1048576)} MB)…` : '계산 중…'}</div>`;
    try {
      await Promise.all([need.msgs(), need.vec()]);
      if (!D.images) need.images().then(() => { if (current === 'ctxmsg' && S.cm.res && my === cmRunId) { const o = $('#cmout'); if (o) { o.innerHTML = S.cm.lastHTML = renderE3(S.cm.res, S.cm.resInput); paintReviews(o); } } }).catch(() => {});
      const kb = D.kb;
      while (!kb.e3Prepare(1200)) {
        if (my !== cmRunId) return;
        const p = kb._e3 && kb.M ? kb._e3.zi / kb.M.length : 0;
        if (stat) stat.textContent = `메시지 ${fmt(kb.M.length)}개 문장 벡터 계산 중 ${Math.round(p * 100)}% (처음 한 번)`;
        await new Promise((r) => setTimeout(r, 0));
      }
      if (stat) stat.textContent = '';
      if (my !== cmRunId) return;
      await new Promise((r) => setTimeout(r, 10));
      const r = kb.E3({ vertical: c.v || null, spaces: c.spaces, products: c.products, customer: c.cust, text: c.text, locale: c.locale || null });
      if (my !== cmRunId || current !== 'ctxmsg') return;
      S.cm.res = r; S.cm.resInput = c;
      const o = $('#cmout');
      o.innerHTML = S.cm.lastHTML = renderE3(r, c);
      paintReviews(o);
    } catch (e) {
      console.error(e);
      out.innerHTML = `<div class="empty">계산하지 못했습니다: ${esc(e.message)}</div>`;
    }
  }
  function cmBar(sig, W) {
    let tw = 0;
    for (const k of Object.keys(CM_F)) tw += W[k] || 0;
    const parts = Object.keys(CM_F).filter((k) => W[k]).map((k) => [k, ((W[k] || 0) * ((sig || {})[k] || 0)) / (tw || 1)]);
    return `<span class="bar" title="${esc(parts.map(([k, v]) => `${CM_F[k]} ${v.toFixed(3)}`).join(' · '))}">${parts.map(([k, v]) => `<i class="${CM_C[k]}" style="width:${v * 100}%"></i>`).join('')}</span>`;
  }
  const cmFrom = (x) => (x.from === 'input' ? '<span class="pill p-acc">입력</span>' : `<span class="pill p-info" title="${esc(x.surface ? `'${x.surface}'에서 추론` : '문장에서 추론')}">추론${x.surface ? ' · ' + esc(x.surface) : ''}</span>`);
  function cmContextHTML(r) {
    const c = r.result.context, W = c.weights;
    const gap = (k) => `<span class="small faint">비어 있음 — ${esc(CM_GAIN[k])}</span>`;
    const wtag = (k) => (W[k] ? `<span class="xs faint">가중치 ${W[k]}</span>` : '');
    const rows = [];
    rows.push(['업종', c.vertical ? `${entChip('vertical', c.vertical.id, c.vertical.name)} ${cmFrom(c.vertical)} ${wtag('vertical')}
      ${c.vertical.from === 'inferred' ? `<button class="chip" data-cmset="v:${esc(c.vertical.id)}" title="이 업종을 입력값으로 고정">입력으로 고정</button>` : ''}
      ${(c.vertical_alternatives || []).length ? `<div class="xs muted" style="margin-top:4px">다른 후보: ${c.vertical_alternatives.map((a) => `<button class="chip k-vertical" data-cmset="v:${esc(a.id)}" title="이 업종으로 다시 뽑기">${esc(a.name)} ${a.score}</button>`).join(' ')}</div>` : ''}` : gap('vertical')]);
    rows.push(['공간', c.spaces.length ? `${c.spaces.map((s) => `${entChip('space_type', s.id, s.name)} ${cmFrom(s)}`).join(' ')} ${wtag('space')} ${c.spaces[0].from === 'inferred' ? '<button class="chip" data-cmset="spaces">입력으로 고정</button>' : ''}` : gap('space')]);
    rows.push(['제품', c.products.length ? `${c.products.map((p) => `${entChip(p.kind, p.id, p.name)} ${cmFrom(p)}`).join(' ')} ${wtag('product')} ${c.products[0].from === 'inferred' ? '<button class="chip" data-cmset="products">입력으로 고정</button>' : ''}` : gap('product')]);
    if (c.capabilities.length) rows.push(['요구 역량', `${c.capabilities.map((x) => entChip('capability', x.id, x.name)).join(' ')} <span class="xs faint">요구사항 문장에서 읽음(초안 규칙) · 그 역량을 가진 제품군을 제품 0.5로 올림</span>`]);
    rows.push(['타겟고객', c.customer ? `<b>${esc(c.customer.text)}</b> ${wtag('customer')}<div class="xs muted" style="margin-top:4px">${c.customer.deployments.length ? `고객 유형이 맞는 사례 ${c.customer.deployments.length}${c.customer.deployments.length >= 12 ? '+' : ''}: ${c.customer.deployments.slice(0, 6).map((d) => entChip('deployment', d.id, d.customer_type || d.title)).join(' ')}` : '고객 유형이 맞는 사례 없음 → 문장 유사도에만 쓰임'}</div>` : gap('customer')]);
    rows.push(['요구사항', c.text ? `<span class="quote">${esc(c.text)}</span> ${wtag('text')}` : gap('text')]);
    return `<div class="section"><h2>해석한 컨텍스트 <span class="hint">점수 = Σ(가중치 × 일치도) ÷ Σ(쓴 항목 가중치) · 입력 1배, 추론 0.5배</span></h2><div class="card tw"><table class="ctxtab"><tbody>${rows.map(([a, b]) => `<tr><td>${a}</td><td>${b}</td></tr>`).join('')}</tbody></table></div>
      <div class="legend" style="margin-top:8px">${Object.keys(CM_F).filter((k) => W[k]).map((k) => `<span><i class="${CM_C[k]}"></i>${CM_F[k]} ${W[k]}</span>`).join('')}</div></div>`;
  }
  function cmItem(it, W, ref, opts = {}) {
    let own = 0, tw = 0;
    for (const k of Object.keys(CM_F)) { own += (W[k] || 0) * ((it.signals || {})[k] || 0); tw += W[k] || 0; }
    own = tw ? own / tw : 0;
    const lifted = it.score - own > 0.0015;
    const thumb = opts.noThumb ? '' : entityThumb(it.about[0], it.about[1]);
    const ctxObj = { cm: ref.input, mid: it.id };
    return `<div class="mrow ${opts.cls || ''}"><div class="mth">${thumb}</div><div style="min-width:0">
      <div class="row" style="gap:6px"><span class="pill p-mute">${esc(L.level[it.level] || it.level)}</span>${it.claim_flag ? '<span class="pill p-warn" title="숫자·최상급 등 대외 사용 전 확인">claim</span>' : ''}${/^T[3-6]/.test(it.tier || '') ? tierPill(it.tier) : ''}${opts.noAbout ? '' : aboutChip(it.about[0], it.about[1])}${it.dup ? `<span class="xs faint" title="같은 문장이 다른 대상에도 붙어 있음">같은 문장 ${it.dup}곳 더</span>` : ''}</div>
      <div class="mtext">${esc(it.text)}</div>
      ${(() => { const rs = (it.reasons || []).filter((x) => !(opts.hide && opts.hide.has(x) && !x.startsWith('요구사항 유사'))); return rs.length ? `<div class="why">${rs.map((x) => `<span>${esc(x)}</span>`).join('')}</div>` : ''; })()}
      <div class="row" style="margin-top:6px">${cmBar(it.signals, W)} <b class="small">${(+it.score).toFixed(3)}</b>${lifted ? '<span class="xs faint" title="이 문장 자체 점수보다 아래 근거 문장 점수(×0.9)가 높아 올림">↑ 근거 문장</span>' : ''}${it.source_url ? ' ' + ext(it.source_url) : ''}<span class="grow"></span>${rv('ctxmsg', ref.key + '|' + it.id, `${it.text.slice(0, 60)} ← ${ref.sum}`, ctxObj)}</div>
      ${opts.extra || ''}</div></div>`;
  }
  function renderE3(r, input) {
    const res = r.result, W = res.context.weights;
    const ref = { key: cmKey(input), input, sum: cmSummary(input) };
    let h = `<div class="row" style="margin-bottom:14px">${hintPill(r.decision_hint)} ${r.decision_reasons.map(reasonPill).join(' ')} ${r.tier_min ? tierPill(r.tier_min) : ''}<span class="small faint">후보 ${fmt(res.n_candidates)} / 일치 ${fmt(res.n_scored)}문장 · ${r.timings_ms.total} ms · 브라우저 계산</span><span class="grow"></span>${res.ranked.length ? '<button class="btn" id="cmcsv">묶음 CSV 내려받기</button>' : ''}</div>`;
    h += cmContextHTML(r);
    if (!res.ranked.length && !res.key_messages.length && !res.cases.length) return h + '<div class="empty">이 컨텍스트에 맞는 메시지가 없습니다(최소 점수 0.1).</div>' + needsHTML(r);
    if (res.headline.length) h += `<div class="section"><h2>헤드라인 <span class="hint">업종 페이지 히어로 문구(tagline)</span></h2><div class="card">${res.headline.map((it) => cmItem(it, W, ref, { cls: 'headline' })).join('')}</div></div>`;
    h += `<div class="section"><h2>핵심 메시지 ${res.key_messages.length} <span class="hint">업종 장면·분류·솔루션 문구 + 그 아래 근거 문장</span></h2><div class="card">${res.key_messages.map((it) => cmItem(it, W, ref, {
      extra: it.proof_points.length ? `<div class="pps">${it.proof_points.map((p) => `<div class="pp"><div>${esc(p.text)} ${p.claim_flag ? '<span class="pill p-warn">claim</span>' : ''}</div><div class="row xs muted" style="margin-top:2px">${p.score ? `${cmBar(p.signals, W)} ${(+p.score).toFixed(3)}` : '<span class="faint">근거 문장 · 컨텍스트 일치 없음</span>'}<span class="grow"></span>${rv('ctxmsg', ref.key + '|' + p.id, `${p.text.slice(0, 60)} ← ${ref.sum}`, { cm: ref.input, mid: p.id })}</div></div>`).join('')}</div>` : '' })).join('') || '<div class="empty">없음</div>'}</div></div>`;
    h += `<div class="section"><h2>제품 메시지 ${res.products.length} <span class="hint">제품군별 USP·특장점 문구(상위 4)</span></h2><div class="pgrid">${res.products.map((p) => `<div class="card pcard"><header class="row">${famThumb(p.id)}<div class="grow" style="min-width:0">${entChip('family', p.id, p.name)}<div class="why">${(p.items[0].reasons || []).filter((x) => !x.startsWith('요구사항 유사')).map((x) => `<span>${esc(x)}</span>`).join('')}</div></div><b class="small">${(+p.score).toFixed(3)}</b></header>
      ${p.items.map((it) => cmItem(it, W, ref, { noThumb: true, noAbout: true, hide: new Set(p.items[0].reasons || []) })).join('')}</div>`).join('') || '<div class="empty">없음</div>'}</div></div>`;
    h += `<div class="section"><h2>근거 사례 ${res.cases.length} <span class="hint">사례 인용(T5)·KPI(T3) — 업종·공간·제품·고객 유형·문장 유사도</span></h2><div class="card">${res.cases.map((d) => `<div class="mrow"><div class="mth">${caseThumb(d.id)}</div><div style="min-width:0">
        <div class="row" style="gap:6px">${entChip('deployment', d.id, d.title)}<span class="xs faint">${esc(d.date || '')}</span>${d.customer_type ? `<span class="pill p-mute">${esc(d.customer_type)}</span>` : ''}</div>
        <div class="why">${d.reasons.map((x) => `<span>${esc(x)}</span>`).join('')}</div>
        ${d.quotes.map((q) => `<div class="row" style="margin-top:6px"><span class="quote grow" style="font-size:13.5px;color:var(--text)">${esc(q.text)}</span>${rv('ctxmsg', ref.key + '|' + q.id, `${q.text.slice(0, 60)} ← ${ref.sum}`, { cm: ref.input, mid: q.id })}</div>`).join('')}
        ${d.kpis.length ? `<ul class="reasons">${d.kpis.map((k) => `<li>${esc(k.text)} ${k.claim_flag ? '<span class="pill p-warn">claim</span>' : ''}</li>`).join('')}</ul>` : ''}
        <div class="row" style="margin-top:6px">${cmBar(d.signals, W)} <b class="small">${(+d.score).toFixed(3)}</b> ${ext(d.url)}<span class="grow"></span>${rv('ctxmsg', ref.key + '|' + d.id, `사례: ${d.title.slice(0, 50)} ← ${ref.sum}`, { cm: ref.input, did: d.id })}</div></div></div>`).join('') || '<div class="empty">없음</div>'}</div></div>`;
    h += `<details class="section"><summary class="small muted" style="font-weight:600">전체 순위 ${res.ranked.length} (같은 문장은 하나로)</summary><div class="card tw" style="margin-top:8px"><table><thead><tr><th class="num">#</th><th style="width:76px"></th><th>단계</th><th>문장</th><th>대상</th><th>점수</th><th>검수</th></tr></thead><tbody>
      ${res.ranked.map((it, i) => `<tr><td class="num">${i + 1}</td><td>${entityThumb(it.about[0], it.about[1])}</td><td><span class="pill p-mute">${esc(L.level[it.level] || it.level)}</span>${it.claim_flag ? ' <span class="pill p-warn">claim</span>' : ''}</td><td style="min-width:220px">${esc(it.text)}<div class="xs faint">${esc((it.reasons || []).join(' · '))}</div></td><td>${aboutChip(it.about[0], it.about[1])}</td><td style="white-space:nowrap">${cmBar(it.signals, W)} ${(+it.score).toFixed(3)}</td><td>${rv('ctxmsg', ref.key + '|' + it.id, `${it.text.slice(0, 60)} ← ${ref.sum}`, { cm: ref.input, mid: it.id })}</td></tr>`).join('')}
      </tbody></table></div></details>`;
    h += needsHTML(r);
    return h;
  }
  document.addEventListener('click', async (e) => {
    if (!e.target.closest('#cmcsv') || !S.cm.res) return;
    const res = S.cm.res.result, input = S.cm.resInput;
    const q = (s) => '"' + String(s == null ? '' : s).replace(/"/g, '""') + '"';
    const rows = [['구분', '단계', '문장', '대상 유형', '대상', '점수', '근거', 'claim', '출처', '메시지 id']];
    const add = (sec, it) => rows.push([sec, L.level[it.level] || it.level, it.text, kindName(it.about[0]), it.about_name, it.score, (it.reasons || []).join(' · '), it.claim_flag ? 'Y' : '', it.source_url || '', it.id]);
    res.headline.forEach((it) => add('헤드라인', it));
    res.key_messages.forEach((it) => { add('핵심 메시지', it); it.proof_points.forEach((p) => add('근거 문장', p)); });
    res.products.forEach((p) => p.items.forEach((it) => add('제품 메시지', it)));
    res.cases.forEach((d) => { d.quotes.forEach((it) => add('사례 인용', it)); d.kpis.forEach((k) => rows.push(['사례 KPI', 'KPI', k.text, '도입사례', d.title, d.score, (d.reasons || []).join(' · '), k.claim_flag ? 'Y' : '', d.url || '', d.id])); });
    const csv = '﻿' + [[`컨텍스트: ${cmSummary(input)}`]].concat(rows).map((r) => r.map(q).join(',')).join('\r\n');
    try {
      const dl = window.claude && window.claude.use ? await window.claude.use('downloads') : null;
      if (!dl) return toast('이 화면에서는 파일 내려받기를 쓸 수 없습니다');
      await dl.save({ filename: 'winmate-messages.csv', data: csv });
    } catch (err) {
      if (err && err.code === 'declined') return;
      toast('내려받지 못했습니다' + (err && err.code ? ' (' + err.code + ')' : ''));
    }
  });

  /* ═════════ 검수 ═════════ */
  views.reviews = (el) => {
    const note = { off: '이 화면에서는 검수 저장을 쓸 수 없습니다. claude.ai 에 로그인한 상태로 이 페이지를 열면 표시를 남길 수 있습니다.', ro: '이 계정은 표시를 볼 수만 있습니다. 표시를 남기려면 공유 권한이 Contributor 이상이어야 합니다.', err: '검수 저장소에 연결하지 못했습니다.', wait: '검수 저장소에 연결하는 중입니다.' }[R.state];
    el.innerHTML = `${note ? `<div class="note" style="margin-bottom:14px">${esc(note)}</div>` : ''}
      <div class="filters"><select class="field" id="rvv"><option value="">전체 판정</option>${Object.entries(L.verdict).map(([k, v]) => `<option value="${k}" ${S.rev.verdict === k ? 'selected' : ''}>${esc(v)}</option>`).join('')}</select>
      <select class="field" id="rvk"><option value="">전체 대상</option>${Object.entries(L.kind).map(([k, v]) => `<option value="${k}" ${S.rev.kind === k ? 'selected' : ''}>${esc(v)}</option>`).join('')}</select>
      <label class="small row" style="gap:4px"><input type="checkbox" id="rvm" ${S.rev.mine ? 'checked' : ''}>내 표시만</label><span class="grow"></span><button class="btn" id="rvcsv">CSV 내려받기</button></div><div id="rvlist"></div>`;
    const upd = () => { S.rev.verdict = $('#rvv').value; S.rev.kind = $('#rvk').value; S.rev.mine = $('#rvm').checked; renderReviewList(); };
    for (const id of ['#rvv', '#rvk', '#rvm']) $(id, el).addEventListener('change', upd);
    $('#rvcsv', el).addEventListener('click', exportCSV);
    renderReviewList();
    if (!D.images) need.images().then(() => { if (current === 'reviews') renderReviewList(); }).catch(() => {});
    if (!D.msgs && [...R.docs.values()].some((d) => d.ctx && d.ctx.mid)) need.msgs().then(() => { if (current === 'reviews') renderReviewList(); }).catch(() => {});
  };
  function reviewRows() {
    const F = S.rev;
    return [...R.docs.values()].filter((r) => (!F.verdict || r.verdict === F.verdict) && (!F.kind || r.kind === F.kind) && (!F.mine || r.by === R.uid)).sort((a, b) => (b.at || 0) - (a.at || 0));
  }
  function reviewThumb(r) {
    const c = r.ctx || {};
    if (c.aid) return entityThumb('image', c.aid);
    if (c.fid) return entityThumb('family', c.fid);
    if (c.did) return entityThumb('deployment', c.did);
    if (c.sid) return entityThumb('industry_section', c.sid);
    if (c.mid && IX.msgById) { const m = IX.msgById.get(c.mid); if (m) return entityThumb(m[4], m[5]); }
    if (['family', 'deployment', 'solution', 'service', 'vertical'].includes(r.kind)) return entityThumb(r.kind, r.id);
    return '';
  }
  function renderReviewList() {
    const el = $('#rvlist');
    if (!el) return;
    const rows = reviewRows();
    const all = [...R.docs.values()];
    const c = { ok: 0, wrong: 0, unsure: 0 };
    all.forEach((r) => { if (c[r.verdict] != null) c[r.verdict]++; });
    const byKind = groupBy(all, (r) => r.kind);
    el.innerHTML = `<div class="status-strip"><div class="card"><span class="big">${fmt(all.length)}</span><span class="small muted">전체 표시</span></div><div class="card"><span class="big" style="color:var(--ok)">${c.ok}</span><span class="small muted">맞음</span></div><div class="card"><span class="big" style="color:var(--bad)">${c.wrong}</span><span class="small muted">틀림</span></div><div class="card"><span class="big" style="color:var(--warn)">${c.unsure}</span><span class="small muted">모름</span></div>
      <div class="card small">${[...byKind.entries()].map(([k, v]) => `${esc(kindName(k))} ${v.length}`).join(' · ') || '<span class="muted">아직 표시 없음</span>'}</div></div>
      <div class="card tw"><table><thead><tr><th style="width:76px"></th><th>대상</th><th>판정</th><th>고친 값</th><th>메모</th><th>검수자</th><th>시각</th><th></th></tr></thead><tbody>
      ${rows.map((r) => `<tr><td>${reviewThumb(r)}</td><td><span class="pill p-mute">${esc(kindName(r.kind))}</span> ${esc(r.label || r.id)}</td><td><span class="pill ${r.verdict === 'ok' ? 'p-ok' : r.verdict === 'wrong' ? 'p-bad' : 'p-warn'}">${esc(L.verdict[r.verdict] || r.verdict)}</span></td><td>${esc(r.fix || '')}</td><td class="small">${esc(r.note || '')}</td><td class="small">${esc(whoName(r.by))}</td><td class="small muted">${r.at ? esc(new Date(r.at).toLocaleString('ko-KR')) : ''}</td><td><button class="btn" data-goto="${esc(r._id)}">열기</button></td></tr>`).join('') || '<tr><td colspan="8" class="empty">표시가 없습니다. 다른 탭에서 ✓ ✗ ? 를 눌러 남겨 보세요.</td></tr>'}
      </tbody></table></div>`;
    hydrateThumbs(el);
  }
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-goto]');
    if (!b) return;
    const r = R.docs.get(b.dataset.goto);
    if (!r) return;
    const ctx = r.ctx || {}, id = r.id;
    if (ctx.cm) { Object.assign(S.cm, cmClean(ctx.cm)); S.cm.lastHTML = null; go('ctxmsg'); setTimeout(runCtxMsg, 30); return; }
    if (ctx.fid) return openFamily(ctx.fid);
    if (ctx.did) return openDeployment(ctx.did);
    if (ctx.aid) return openImage(ctx.aid);
    if (ctx.mid) return openMessage(ctx.mid);
    if (ctx.q) { S.q.mode = ctx.mode || 's1'; S.q.text = ctx.q; S.q.last = null; go('query'); setTimeout(runQuery, 30); return; }
    if (ctx.v) { S.vert.v = ctx.v; go('verticals'); if (ctx.sid) setTimeout(() => { const x = document.getElementById('sec-' + ctx.sid); if (x) x.scrollIntoView({ block: 'center' }); }, 80); return; }
    if (r.kind === 'family') return openFamily(id);
    if (r.kind === 'deployment') return openDeployment(id);
    if (['solution', 'service'].includes(r.kind)) return openSolution(r.kind, id);
    if (r.kind === 'requires') return openSpace(id.split('|')[0]);
    if (r.kind === 'test') return go('overview');
    toast('이 표시는 열 화면이 없습니다');
  });
  async function exportCSV() {
    const rows = reviewRows();
    if (!rows.length) return toast('내보낼 표시가 없습니다');
    const q = (s) => '"' + String(s == null ? '' : s).replace(/"/g, '""') + '"';
    const csv = '﻿' + [['대상 유형', '대상 id', '대상', '판정', '고친 값', '메모', '검수자', '시각'].map(q).join(',')]
      .concat(rows.map((r) => [kindName(r.kind), r.id, r.label, L.verdict[r.verdict] || r.verdict, r.fix, r.note, whoName(r.by), r.at ? new Date(r.at).toISOString() : ''].map(q).join(','))).join('\r\n');
    try {
      const dl = window.claude && window.claude.use ? await window.claude.use('downloads') : null;
      if (!dl) return toast('이 화면에서는 파일 내려받기를 쓸 수 없습니다');
      await dl.save({ filename: 'winmate-kb-review.csv', data: csv });
    } catch (e) {
      if (e && e.code === 'declined') return;
      toast('내려받지 못했습니다' + (e && e.code ? ' (' + e.code + ')' : ''));
    }
  }

  /* ── 시작 ── */
  async function boot() {
    try {
      const m = await Load.man();
      const [core, graph] = await Promise.all([Load.json('core.json.gz'), Load.json('graph.json.gz')]);
      D.core = core; D.g = graph;
      D.kb = new W.KB(core, graph);
      if (m.files['parity.json.gz']) Load.json('parity.json.gz').then((p) => { D.parity = p; if (current === 'overview') route(); }).catch(() => {});
      indexBase();
      const t = core.tests.filter((x) => x.pass).length;
      $('#buildsub').textContent = `상품 수집 ${fmtTime(core.meta.products_fetched_at)} · 테스트 ${t}/${core.tests.length} · ${core.meta.schema_version || 'kb_v1'}`;
      route();
    } catch (e) {
      console.error(e);
      $('#view').innerHTML = `<div class="empty">KB 데이터를 불러오지 못했습니다: ${esc(e.message)}</div>`;
    }
    initReviews();
  }
  for (const b of $$('.tab')) b.addEventListener('keydown', (e) => { if (e.key === 'Enter') go(b.dataset.tab); });
  document.addEventListener('keydown', (e) => { const t = e.target.closest && e.target.closest('.fcard[data-open]'); if (t && e.key === 'Enter') t.click(); });
  boot();
})();
