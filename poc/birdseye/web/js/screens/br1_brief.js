// BR1 — 3D 조감도 1/3 · 요구사항 (말로 적고, 공간 유형 · 분위기 · 제품만 고르면 AI 가 구성 · 배치 · 렌더링)
import { api, products as fetchProducts, rememberProducts } from "../api.js";
import { h, icon, replace, fmt, wmsg, toast, popover, debounce, closePop } from "../dom.js";
import { go, link2d, link3d, getEnv } from "../shell.js";
import { load3d, patch3d, frame3d, labels, QUALITY_TIME } from "../ui3d.js";
import { catalogSearch, sizeText } from "../ui2d.js";

export async function mount(id) {
  let p = await load3d(id);
  const L = await labels();
  const env = await getEnv(true);
  const fr = frame3d(p, "brief");
  const all = (await api.get("/api/projects")).items;
  const twoDs = all.filter(x => x.kind === "2d");
  const inp = JSON.parse(JSON.stringify(p.input));
  let linked = p.linked_2d || null;
  let prods = await fetchProducts(inp.products || []);
  let saving = null;
  const save = debounce(() => { saving = patch3d(id, { input: inp, linked_2d: linked }).then(r => { p = r; }).finally(() => { saving = null; }); }, 500);

  const body = h("div", { class: "col", style: { gap: "14px", maxWidth: "1100px" } });
  fr.content.append(body);

  function linkedInfo() { return twoDs.find(x => x.id === linked) || null; }
  function draw() {
    const st = L.lib.space_types;
    const moods = Object.keys(L.lib.materials.moods);
    const l2 = linkedInfo();
    const blender = env && env.blender;
    const chip = (on, label, fn, extra) => h("button", { class: "chip" + (on ? " on" : ""), onclick: fn }, label, extra || null);
    replace(body,
      wmsg("어떤 공간에서 어떤 느낌으로 쓰일지 말로 적어주세요. W가 요구사항을 분석해 인테리어와 가구를 고르고 배치한 뒤 3D로 렌더링합니다. 치수와 수량은 대략이면 충분해요."),
      h("div", { class: "card pad" },
        h("div", { class: "card-h" }, h("h3", {}, "이렇게 만들어요"), h("span", { class: "sub" }, "W가 Blender로 자동 구성 · 만드는 동안 다른 작업을 해도 돼요")),
        h("div", { style: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "10px", marginTop: "10px" } },
          [["01", "요구사항 분석", "공간 · 분위기 · 제품을 읽어요", null], ["02", "인테리어 · 가구 선정 · 배치", "마감 · 가구를 고르고 배치해요", "Blender"], ["03", "렌더링 · 품질 확인", "제품 비율 · 겹침까지 점검해요", "Cycles"]].map(([n, t, s, tag]) =>
            h("div", { class: "callout", style: { background: "var(--surface-2)", border: "1px solid var(--line)" } },
              h("div", { class: "row" }, h("span", { class: "num b", style: { color: "var(--pri)" } }, n), h("b", {}, t), tag ? h("span", { class: "tag" }, tag) : null),
              h("div", { class: "xs muted", style: { marginTop: "4px" } }, s)))),
        h("div", { class: "small muted", style: { marginTop: "10px" } }, "3D 조감도는 분위기를 보여주는 개략 이미지예요. 정확한 치수 · 수량 · 동선이 필요하면 ",
          h("button", { class: "btn link small", onclick: async () => { const n = await api.post("/api/projects", { kind: "2d" }); go(link2d(n.id, "space")); } }, "2D 조감도로 시작"))),
      blender && !blender.kind ? h("div", { class: "callout" }, h("b", {}, "Blender 를 찾지 못했어요. "), blender.note || "", " — 설치 후 사이드바 '실행 환경'에서 다시 확인해 주세요.") : null,
      h("div", { class: "card pad col", style: { gap: "14px" } },
        h("div", { class: "card-h" }, h("h3", {}, "요구사항"), h("span", { class: "sub" }, "1 / 3"), h("span", { class: "spacer" }),
          h("span", { class: "small muted" }, "대략 규모 · ", l2 ? `2D 치수 사용 · ${l2.title}` : scaleText())),
        h("textarea", { class: "ta", rows: 3, placeholder: "예: 강남 플래그십 1층 로비를 고객이 브랜드를 체험하는 갤러리 같은 공간으로 보여주고 싶어요. 길에서도 창 너머 화면이 보이고, 안쪽엔 큰 미디어월이 있었으면 해요.",
          oninput: e => { inp.text = e.target.value; save(); } }, inp.text || ""),
        row("공간 유형", h("div", { class: "row", style: { flexWrap: "wrap", gap: "6px" } },
          st.map(s => chip(inp.space_type === s.code, s.label, () => { inp.space_type = s.code; save(); draw(); })))),
        row("분위기 (선택)", h("div", { class: "row", style: { flexWrap: "wrap", gap: "6px" } },
          moods.map(m => chip((inp.moods || []).includes(m), L.mood(m), () => { inp.moods = (inp.moods || []).includes(m) ? inp.moods.filter(x => x !== m) : [...(inp.moods || []), m]; save(); draw(); })))),
        row("제품", h("div", { class: "row", style: { flexWrap: "wrap", gap: "6px" } },
          (inp.products || []).map(c => h("span", { class: "chip on" }, prods[c] ? prods[c].short : c,
            l2 ? null : h("button", { class: "btn link", style: { padding: 0, height: "auto" }, "aria-label": "빼기", onclick: () => { inp.products = inp.products.filter(x => x !== c); save(); draw(); } }, h("span", { class: "x" }, "×")))),
          l2 ? h("span", { class: "small muted" }, "2D 배치의 제품 · 대수를 그대로 써요") : h("button", { class: "chip", "data-pop-anchor": "", onclick: e => addProduct(e.currentTarget) }, icon("plus", 12), "제품"),
          l2 ? null : h("span", { class: "xs muted" }, "대수는 AI가 공간에 맞춰 정해요"))),
        row("참고 자료", h("div", { class: "row", style: { flexWrap: "wrap", gap: "6px" } },
          h("select", { class: "sel sm", style: { maxWidth: "320px" }, "aria-label": "2D 조감도 연결", onchange: e => setLink(e.target.value || null) },
            h("option", { value: "" }, "2D 조감도 연결 안 함"),
            twoDs.map(x => h("option", { value: x.id, selected: x.id === linked }, `2D 연결 · ${x.title}${x.summary && x.summary.total ? ` (${x.summary.kinds}종 ${x.summary.total}대)` : ""}`))),
          h("button", { class: "chip", onclick: async () => { await flush(); go(link3d(id, "photos")); } }, icon("camera", 13), "현장 사진", (inp.photo_read ? h("span", { class: "tag ok" }, "읽음") : null)),
          h("button", { class: "chip", disabled: true, title: "이 PoC 범위 밖 — 이미지 생성 기능과 연결 예정" }, icon("image", 13), "참조 이미지"),
          h("button", { class: "chip", disabled: true, title: "이 PoC 범위 밖 — 고객 요구사항 기능과 연결 예정" }, icon("doc", 13), "고객 요구사항 불러오기"))),
        l2 ? null : row("대략 규모", h("div", { class: "row", style: { gap: "8px" } },
          h("span", { class: "small muted" }, "약"),
          h("input", { class: "inp sm num", style: { width: "80px" }, inputmode: "numeric", value: (inp.scale || {}).area_pyeong || "", placeholder: "평", onchange: e => { inp.scale = { ...(inp.scale || {}), area_pyeong: parseInt(e.target.value, 10) || null }; save(); draw(); } }),
          h("span", { class: "small muted" }, "평 · 층고"),
          h("div", { class: "seg" }, [["low", "낮음"], ["normal", "보통"], ["high", "높음"]].map(([k, l]) => h("button", { class: ((inp.scale || {}).height || "normal") === k ? "on" : "", onclick: () => { inp.scale = { ...(inp.scale || {}), height: k }; save(); draw(); } }, l))),
          h("span", { class: "xs muted" }, "비워 두면 공간 유형 기본값"))),
        row("품질", h("div", { class: "row", style: { gap: "8px" } },
          h("div", { class: "seg" }, Object.entries(L.lib.quality).map(([k, q]) => h("button", { class: (inp.quality || "standard") === k ? "on" : "", onclick: () => { inp.quality = k; save(); draw(); } }, q.label))),
          h("span", { class: "xs muted" }, QUALITY_TIME[inp.quality || "standard"] + (blender && blender.kind ? ` · ${blender.note}` : "")))),
        h("div", { class: "xs muted" }, "참고 자료는 모두 선택이에요. 2D 조감도를 연결하면 제품 위치는 2D 배치를 따르고, 인테리어 · 가구는 AI가 정해요.")));
  }
  const row = (label, el) => h("div", { style: { display: "grid", gridTemplateColumns: "96px 1fr", gap: "10px", alignItems: "center" } }, h("span", { class: "flabel" }, label), el);
  function scaleText() {
    const sc = inp.scale || {};
    const hh = { low: "낮음", normal: "보통", high: "높음 (4.5 m 이상)" }[sc.height || "normal"];
    return sc.area_pyeong ? `약 ${sc.area_pyeong}평 · 층고 ${hh}` : `${L.space(inp.space_type)} 기본값 · 층고 ${hh}`;
  }
  async function setLink(pid2) {
    linked = pid2;
    if (pid2) {
      const p2 = await api.get(`/api/projects/${pid2}`);
      const codes = [...new Set((p2.lines || []).filter(l => (l.qty || 0) > 0).map(l => l.product))];
      prods = { ...prods, ...await fetchProducts(codes) };
      inp.products = codes;
      inp.space_type = p2.space.space_type || inp.space_type;
      inp.scale = { area_pyeong: Math.round(p2.space.width * p2.space.depth / 1e6 / 3.3058), height: p2.space.height >= 4000 ? "high" : "normal" };
    }
    save(); draw();
  }
  function addProduct(anchor) {
    const list = h("div", { style: { maxHeight: "300px", overflow: "auto", width: "460px" } });
    const q = h("input", { class: "inp sm", placeholder: "모델명 · 제품군 (예: 사이니지, Flip, 비디오월)", "aria-label": "제품 검색" });
    const run = debounce(async () => {
      const items = await catalogSearch(q.value.trim(), 20);
      rememberProducts(items);
      replace(list, items.map(pp => h("button", { class: "btn ghost", style: { width: "100%", justifyContent: "flex-start", height: "auto", padding: "6px 8px" }, onclick: () => {
        if (!(inp.products || []).includes(pp.code)) inp.products = [...(inp.products || []), pp.code];
        prods[pp.code] = pp; save(); closePop(); draw();
      } }, h("b", {}, pp.short), h("span", { class: "xs muted ellipsis" }, `${pp.name} · ${sizeText(pp)}`))));
    }, 150);
    q.addEventListener("input", run);
    popover(anchor, h("div", { class: "col", style: { gap: "8px" } }, q, list));
    run();
    setTimeout(() => q.focus(), 30);
  }
  async function flush() { if (save.pending()) save.flush(); if (saving) await saving; }
  async function start() {
    if (!(inp.text || "").trim() && !(inp.products || []).length) { toast("요구사항이나 제품을 하나 이상 넣어 주세요", "err"); return; }
    await flush();
    const r = await api.post(`/api/projects/${id}/render`, { quality: inp.quality || "standard", mode: "full" });
    if (r && r.id) go(link3d(id, "build"));
  }
  fr.setBottom(
    h("div", { class: "col grow", style: { gap: 0, paddingLeft: "6px" } }, h("b", {}, "여기까지만 적으면 돼요"), h("span", { class: "small muted" }, "구성 · 배치 · 렌더링은 W가 진행합니다 · 먼저 조감 45° · 입구 시점 두 컷을 만들어요")),
    h("button", { class: "btn lg", onclick: async () => { await flush(); go("#/"); } }, "작업 목록"),
    h("button", { class: "btn lg primary", disabled: !(env && env.blender && env.blender.kind), onclick: start }, icon("cube", 15), "3D 조감도 만들기"));
  draw();
  return { beforeLeave: flush, dirty: () => save.pending() };
}
