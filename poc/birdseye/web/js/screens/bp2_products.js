// BP2 — 2D 조감도 2/4 · 제품 · 수량 (공간 치수로 권장 수량 계산 · 근거 = 룰 ID + 식, 사용자가 확정)
import { api, library, products as fetchProducts, rememberProducts } from "../api.js";
import { h, icon, replace, fmt, wmsg, popover, toast, debounce, josa } from "../dom.js";
import { go, link2d } from "../shell.js";
import { Doc2D } from "../state.js";
import { frame2d, catalogSearch, sizeText } from "../ui2d.js";

export async function mount(id) {
  const doc = await Doc2D.load(id);
  const lib = await library();
  const { fr, off } = frame2d(doc, "products");
  let recs = {};
  let prods = await fetchProducts(doc.p.lines.map(l => l.product));
  let suggestion = null, skipped = [];

  const head = h("div", {});
  const tableCard = h("div", { class: "card" });
  const sugBox = h("div", {});
  fr.content.append(h("div", { class: "col", style: { gap: "14px", maxWidth: "1180px" } }, head, tableCard, sugBox,
    h("div", { class: "note" }, "집기(소파 · 벤치 등)는 3단계에서 동선 검토용 블록으로만 들어가요 — 인테리어는 3D 조감도에서")));

  async function refreshRecs() {
    if (!doc.p.lines.length) { recs = {}; return; }
    recs = (await api.post("/api/2d/recommend", { project: doc.p })).recs;
    doc.commit(p => { for (const l of p.lines) { const r = recs[l.id]; if (r) { l.qty_rec = r.qty_rec; if (l.qty === null || l.qty === undefined) l.qty = r.qty_rec || 1; } } }, { validate: false });
  }
  async function refreshSuggest() {
    const r = await api.post("/api/2d/suggest", { project: doc.p, skip: skipped }, { quiet: true }).catch(() => ({ items: [] }));
    suggestion = r.items[0] || null;
    drawSuggest();
  }

  function ruleBox(r) {
    const rules = lib.rules || {};
    const items = (r.rule_ids || []).map(rid => rules[rid] || (Array.isArray(rules) ? rules.find(x => x.id === rid) : null)).filter(Boolean);
    return h("div", {},
      h("h4", {}, `${r.strategy_name || "배치 방식"} · 권장 ${r.qty_rec ?? "–"}대`),
      h("div", { class: "formula" }, r.formula || "식 없음"),
      items.map(rule => h("div", { style: { marginTop: "10px" } },
        h("div", { class: "row" }, h("span", { class: "rid" }, rule.id), h("span", { class: "tag" }, rule.status === "draft" ? "PoC 임시값" : rule.status || "")),
        h("div", { class: "small", style: { marginTop: "4px" } }, rule.explanation_ko || ""),
        h("div", { class: "formula", style: { marginTop: "6px" } }, rule.expression || ""),
        rule.params ? h("div", { class: "xs muted", style: { marginTop: "4px" } }, Object.entries(rule.params).map(([k, v]) => `${k} = ${typeof v === "object" ? JSON.stringify(v) : v}`).join(" · ")) : null)),
      (r.notes || []).length ? h("div", { class: "xs muted", style: { marginTop: "8px" } }, r.notes.join(" · ")) : null);
  }

  function drawHead() {
    const sp = doc.p.space;
    const ops = sp.openings || [];
    const c = k => ops.filter(o => o.kind === k).length;
    const ex = doc.p.lines.map(l => [prods[l.product], recs[l.id]]).filter(([p, r]) => p && r && r.explain).slice(0, 2)
      .map(([p, r]) => `${josa(p.short, "은/는")} ${r.explain}`);
    replace(head,
      h("div", { class: "small muted", style: { marginBottom: "10px" } }, `${fmt(sp.width / 1000, 1)} × ${fmt(sp.depth / 1000, 1)} m · 층고 ${fmt(sp.height / 1000, 1)} m · 유리창 ${c("window")} · 출입구 ${c("entrance")} · 기둥 ${(sp.pillars || []).length} · 콘센트 ${(sp.outlets || []).length}`),
      wmsg(doc.p.lines.length ? `공간 치수로 권장 수량을 계산했어요. 근거를 보고 수량을 확정해 주세요.${ex.length ? " 예를 들어 " + ex.join(", ") + "." : ""}`
        : "제안할 제품을 아래에서 검색해 넣어 주세요. 넣는 즉시 공간 치수로 권장 수량과 위치를 계산해요."));
  }

  function drawTable() {
    const lines = doc.p.lines;
    const kinds = lines.filter(l => (l.qty || 0) > 0).length, total = lines.reduce((a, l) => a + (l.qty || 0), 0);
    const setLine = (i, fn, rec = false) => { doc.commit(p => fn(p.lines[i]), { validate: false }); if (rec) refreshRecs().then(draw); else draw(); };
    const rows = lines.map((l, i) => {
      const p = prods[l.product], r = recs[l.id] || {};
      const mounts = (p && p.mounts) || [l.mount];
      const diff = r.qty_rec !== undefined && r.qty_rec !== null && l.qty !== r.qty_rec;
      return h("tr", {},
        h("td", {}, h("div", { class: "b" }, p ? p.short : l.product), h("div", { class: "xs muted ellipsis", style: { maxWidth: "260px" } }, p ? `${p.name} · ${sizeText(p)}` : "제품 정보 없음")),
        h("td", {}, h("select", { class: "sel sm", "aria-label": "설치 방식", onchange: e => setLine(i, ln => { ln.mount = e.target.value; ln.qty = null; }, true) },
          mounts.map(m => h("option", { value: m, selected: (l.mount || (p && p.default_mount)) === m }, (lib.mounts || {})[m] || m)))),
        h("td", { class: "small" }, r.anchor_desc || h("span", { class: "faint" }, "–")),
        h("td", {}, h("div", { class: "row", style: { gap: "4px" } },
          h("button", { class: "iconbtn", "aria-label": "줄이기", disabled: (l.qty || 0) <= 0, onclick: () => setLine(i, ln => { ln.qty = Math.max(0, (ln.qty || 0) - 1); }) }, icon("minus", 13)),
          h("span", { class: "num b", style: { width: "28px", textAlign: "center", fontSize: "15px" } }, l.qty ?? "–"),
          h("button", { class: "iconbtn", "aria-label": "늘리기", onclick: () => setLine(i, ln => { ln.qty = (ln.qty || 0) + 1; }) }, icon("plus", 13)),
          r.qty_rec !== undefined ? h("span", { class: "tag" + (diff ? " dark" : " pri"), title: "공간 치수로 계산한 권장 수량" }, `권장 ${r.qty_rec ?? "–"}`) : null)),
        h("td", { class: "small" }, h("div", { class: "row", style: { gap: "6px" } },
          h("span", { class: "ellipsis", style: { maxWidth: "240px" } }, r.explain || ""),
          r.formula ? h("button", { class: "iconbtn ghost", "aria-label": "근거 보기", "data-pop-anchor": "", onclick: e => popover(e.currentTarget, ruleBox(r)) }, icon("info", 15)) : null)),
        h("td", { class: "r" }, h("button", { class: "iconbtn ghost", "aria-label": "빼기", onclick: () => { doc.commit(pp => { pp.lines.splice(i, 1); pp.placements = (pp.placements || []).filter(x => x.line !== l.id); }, { validate: false }); refreshSuggest(); draw(); } }, icon("x", 14))));
    });
    replace(tableCard,
      h("div", { class: "card-h", style: { padding: "14px 16px 8px" } }, h("h3", {}, "제품 · 수량"), h("span", { class: "sub" }, "공간 치수 기준 권장값 · 크기 단위 mm"), h("span", { class: "spacer" }),
        h("button", { class: "btn sm ghost", disabled: !lines.length, onclick: () => { doc.commit(p => { for (const ln of p.lines) if (recs[ln.id]) ln.qty = recs[ln.id].qty_rec || 0; }, { validate: false }); draw(); toast("권장값으로 되돌렸어요"); } }, icon("undo", 13), "권장값으로 되돌리기")),
      lines.length ? h("table", { class: "tbl" },
        h("thead", {}, h("tr", {}, h("th", {}, "제품"), h("th", {}, "설치 방식"), h("th", {}, "위치"), h("th", {}, "수량"), h("th", {}, "근거"), h("th", {}, ""))),
        h("tbody", {}, rows,
          h("tr", {}, h("td", { class: "b" }, "합계"), h("td", {}), h("td", {}),
            h("td", {}, h("span", { class: "num b" }, kinds), " 종 ", h("span", { class: "num b", style: { marginLeft: "6px" } }, total), " 대"),
            h("td", { class: "small muted", colspan: 2 }, "이 수량이 3단계 배치에 그대로 놓여요"))))
        : h("div", { class: "empty" }, "아직 제품이 없어요 — 아래 검색창에서 모델명 · 제품군으로 추가해 주세요"));
  }

  function drawSuggest() {
    if (!suggestion) { replace(sugBox); return; }
    const s = suggestion;
    replace(sugBox, h("div", { class: "card pad row", style: { gap: "12px" } },
      h("span", { class: "tag pri" }, "추천"),
      h("div", { class: "grow" }, h("b", {}, `${s.short} ${s.qty_rec}대`), h("span", { class: "muted" }, ` — ${s.reason}`),
        h("div", { class: "xs muted" }, `${s.explain || ""} · 규칙 기반 추천 (${(s.rule_ids || []).join(", ")})`)),
      h("button", { class: "btn sm soft", onclick: () => addProduct(s.product, s.mount) }, icon("plus", 13), "추가"),
      h("button", { class: "btn sm ghost", onclick: () => { skipped.push(s.product); refreshSuggest(); } }, "넘기기")));
  }

  async function addProduct(code, mount) {
    if (doc.p.lines.some(l => l.product === code && (!mount || l.mount === mount))) { toast("이미 표에 있어요"); return; }
    const p = (await fetchProducts([code]))[code];
    if (!p) { toast("제품 정보를 찾지 못했어요", "err"); return; }
    prods[code] = p;
    const n = 1 + Math.max(0, ...doc.p.lines.map(l => parseInt(String(l.id).slice(1), 10) || 0));
    doc.commit(pp => { pp.lines.push({ id: `L${n}`, product: code, mount: mount || p.default_mount, qty: null }); }, { validate: false });
    await refreshRecs();
    refreshSuggest();
    draw();
    toast(`${josa(p.short, "을/를")} 넣었어요`);
  }

  // 하단: 제품 검색
  const results = h("div", { class: "menu", style: { position: "absolute", bottom: "72px", left: "10px", maxHeight: "320px", overflow: "auto", display: "none", width: "560px" } });
  const search = h("input", { placeholder: "모델명 · 제품군으로 추가 (예: 전자칠판, QM55, 비디오월)", "aria-label": "제품 추가 검색" });
  const runSearch = debounce(async () => {
    const q = search.value.trim();
    if (!q) { results.style.display = "none"; return; }
    const items = await catalogSearch(q, 14);
    rememberProducts(items);
    replace(results, items.length ? items.map(p => h("button", { onclick: () => { results.style.display = "none"; search.value = ""; addProduct(p.code); } },
      h("b", {}, p.short), h("span", { class: "small muted ellipsis" }, `${p.name} · ${sizeText(p)}`), h("span", { class: "xs faint", style: { marginLeft: "auto" } }, (lib.categories || {})[p.category] || ""))) :
      h("div", { class: "small muted", style: { padding: "10px" } }, "맞는 제품이 없어요"));
    results.style.display = "block";
  }, 200);
  search.addEventListener("input", runSearch);
  search.addEventListener("keydown", e => { if (e.key === "Escape") { results.style.display = "none"; } });
  document.addEventListener("pointerdown", e => { if (!results.contains(e.target) && e.target !== search) results.style.display = "none"; });

  fr.setBottom(
    h("div", { style: { position: "relative", flex: "1 1 auto", minWidth: 0 } }, results,
      h("div", { class: "composer" }, icon("search", 15), search)),
    h("button", { class: "btn lg", onclick: () => go(link2d(id, "space")) }, "이전"),
    h("button", { class: "btn lg primary", onclick: next }, "배치 · 동선으로", icon("arrowR")));

  async function next() {
    const lines = doc.p.lines.filter(l => (l.qty || 0) > 0);
    if (!lines.length) { toast("제품을 1대 이상 넣어 주세요", "err"); return; }
    await doc.flush();
    const changed = !!doc.p.space_changed;
    const res = await api.post("/api/2d/layout", { project: doc.p, regenerate: changed ? null : [], fixtures: changed ? "suggest" : "auto", zones: changed ? "suggest" : "auto" });
    delete res.project.space_changed;
    res.project.step = ["space", "plan", "products"].includes(res.project.step) ? "layout" : res.project.step;
    doc.replace(res.project, { v: res.validation });
    await doc.flush();
    go(link2d(id, "layout"));
  }

  function draw() { drawHead(); drawTable(); }
  draw();
  await refreshRecs();
  draw();
  refreshSuggest();
  return { beforeLeave: () => doc.flush(), unmount: () => off(), dirty: () => doc.dirty() };
}
