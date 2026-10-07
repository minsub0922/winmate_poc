// BP3Z — 존 구획 · 동선 순서 (존 이름 · 포인트 문구 → 제안서 '존별 포인트' ZP-A, 3D 렌더 위 번호)
import { api } from "../api.js";
import { h, icon, replace, fmt, wmsg, toast, confirmBox } from "../dom.js";
import { go, link2d, link3d } from "../shell.js";
import { Doc2D } from "../state.js";
import { PlanView } from "../plan.js";
import { frame2d } from "../ui2d.js";

export async function mount(id) {
  const doc = await Doc2D.load(id);
  const { fr, off } = frame2d(doc, "zones", { fill: true });
  let tool = "select", zsel = (doc.p.zones || [])[0] ? doc.p.zones[0].id : null, busy = false;
  const all = (await api.get("/api/projects")).items;
  const linked3d = all.filter(p => p.kind === "3d" && p.linked_2d === id);

  const planBox = h("div", { class: "planbox", style: { flex: "1 1 auto", minHeight: 0 } });
  const pv = new PlanView(planBox, {
    mode: "zones", snap: 100, layers: { dims: true, flow: true, zones: true, labels: true, fixtures: true, grid: true, view: false, power: false, warnings: false },
    onSelect: (sid, kind) => { if (kind === "zone") { zsel = sid; drawList(); } },
    onCommit: c => {
      if (c.type === "zone") doc.commit(p => { const z = p.zones.find(z => z.id === c.id); Object.assign(z, clampRect(c)); });
      if (c.type === "zone-new") {
        doc.commit(p => {
          p.zones = p.zones || [];
          const n = 1 + Math.max(0, ...p.zones.map(z => parseInt(String(z.id).slice(1), 10) || 0));
          zsel = `Z${n}`;
          p.zones.push({ id: zsel, no: p.zones.length + 1, key: "custom", name: `존 ${p.zones.length + 1}`, ...clampRect(c), point: "" });
        });
        setTool("select");
      }
    },
  });
  planBox.append(h("div", { class: "legend" },
    h("span", {}, h("i", { style: { background: "rgba(20,40,160,.1)", border: "1px dashed #1428a0" } }), "존"),
    h("span", {}, h("i", { style: { background: "#1428a0" } }), "삼성 제품"), h("span", {}, h("i", { style: { border: "1px dashed #8a91a0", background: "#fff" } }), "집기 블록"),
    h("span", {}, h("i", { style: { height: "2px", background: "#1428a0" } }), "동선")));
  const clampRect = r => {
    const sp = doc.p.space;
    const c = (v, hi) => Math.max(0, Math.min(hi, Math.round(v)));
    return { x0: c(Math.min(r.x0, r.x1), sp.width), y0: c(Math.min(r.y0, r.y1), sp.depth), x1: c(Math.max(r.x0, r.x1), sp.width), y1: c(Math.max(r.y0, r.y1), sp.depth) };
  };
  const toolbar = h("div", { class: "toolbar", style: { margin: "0 0 10px" } });
  function setTool(t) { tool = t; pv.setOpt({ tool: t }); drawToolbar(); }
  function drawToolbar() {
    replace(toolbar,
      h("div", { class: "seg" },
        h("button", { class: tool === "select" ? "on" : "", onclick: () => setTool("select") }, icon("pointer", 12), "선택 · 경계 조정"),
        h("button", { class: tool === "zone" ? "on" : "", onclick: () => setTool("zone") }, icon("zone", 12), "영역 그리기")),
      h("button", { class: "btn sm", disabled: busy, onclick: reorder }, icon("list", 13), "동선 순서로 번호"),
      h("button", { class: "btn sm ghost", disabled: busy, onclick: resuggest }, icon("wand", 13), "존 다시 제안"),
      h("span", { class: "spacer" }),
      h("span", { class: "small muted" }, "모서리를 끌어 경계 조정 · 안을 끌어 이동 · 스냅 100 mm"));
  }
  async function reorder() {
    busy = true; drawToolbar();
    try { const r = await api.post("/api/2d/zones", { project: doc.p, mode: "order" }); doc.commit(p => { p.zones = r.zones; }); toast("입구에서 가까운 순서로 번호를 다시 매겼어요"); }
    finally { busy = false; drawToolbar(); }
  }
  async function resuggest() {
    if (!await confirmBox("존 다시 제안", "제품 그룹 · 집기 묶음으로 존을 새로 나눠요. 지금 이름 · 문구는 사라져요(되돌리기 가능).", "다시 제안")) return;
    const r = await api.post("/api/2d/zones", { project: doc.p });
    doc.commit(p => { p.zones = r.zones; });
    zsel = (r.zones[0] || {}).id || null;
  }

  const list = h("div", { class: "col", style: { gap: "6px" } });
  const right = h("div", { class: "rpanel", style: { width: "440px" } });
  function zoneContents(z) {
    const g = (doc.v && doc.v.geom) || { placements: {}, fixtures: {} };
    const prods = {}, fx = [];
    for (const pl of doc.p.placements) { const gg = g.placements[pl.id]; if (gg && gg.zone === z.no) prods[gg.short] = (prods[gg.short] || 0) + 1; }
    for (const f of doc.p.fixtures) { const gg = g.fixtures[f.id]; if (gg && gg.zone === z.no) fx.push(f.label || gg.type_label); }
    return { prods, fx };
  }
  function drawList() {
    const zs = [...(doc.p.zones || [])].sort((a, b) => a.no - b.no);
    const sp = doc.p.space;
    const total = sp.width * sp.depth / 1e6;
    const zArea = zs.reduce((a, z) => a + Math.abs(z.x1 - z.x0) * Math.abs(z.y1 - z.y0) / 1e6, 0);
    const g = (doc.v && doc.v.geom) || { placements: {} };
    const outside = doc.p.placements.filter(pl => g.placements[pl.id] && !g.placements[pl.id].zone && g.placements[pl.id].category !== "hvac_cassette");
    const kinds = new Set(doc.p.placements.map(p => p.product)).size;
    const move = (z, d) => doc.commit(p => {
      const arr = [...p.zones].sort((a, b) => a.no - b.no);
      const i = arr.findIndex(x => x.id === z.id), j = i + d;
      if (j < 0 || j >= arr.length) return;
      [arr[i], arr[j]] = [arr[j], arr[i]];
      arr.forEach((x, k) => { x.no = k + 1; });
      p.zones = arr;
    });
    replace(list, zs.map(z => {
      const { prods, fx } = zoneContents(z);
      const area = Math.abs(z.x1 - z.x0) * Math.abs(z.y1 - z.y0) / 1e6;
      const on = z.id === zsel;
      return h("div", { class: "warn-item" + (on ? " picked" : ""), onclick: e => { if (!e.target.closest("button,input,textarea")) { zsel = z.id; pv.set({ zoneSel: z.id }); drawList(); } } },
        h("div", { class: "row" },
          h("span", { class: "wno", style: { background: "var(--pri)", width: "24px", height: "24px", fontSize: "12px" } }, z.no),
          h("input", { class: "inp sm grow b", value: z.name || "", "aria-label": `존 ${z.no} 이름`, onchange: e => doc.commit(p => { p.zones.find(x => x.id === z.id).name = e.target.value; }) }),
          h("span", { class: "small muted nowrap" }, `약 ${fmt(area, 0)} ㎡`),
          h("button", { class: "iconbtn ghost", title: "앞으로", onclick: () => move(z, -1) }, "↑"),
          h("button", { class: "iconbtn ghost", title: "뒤로", onclick: () => move(z, 1) }, "↓"),
          h("button", { class: "iconbtn ghost", "aria-label": "존 삭제", onclick: () => doc.commit(p => { p.zones = p.zones.filter(x => x.id !== z.id).sort((a, b) => a.no - b.no); p.zones.forEach((x, k) => { x.no = k + 1; }); }) }, icon("x", 13))),
        h("div", { class: "small", style: { paddingLeft: "32px" } },
          Object.keys(prods).length ? h("b", { style: { color: "var(--pri)" } }, Object.entries(prods).map(([k, n]) => `${k} ×${n}`).join(" · ")) : h("span", { class: "muted" }, "제품 없음 · 집기만"),
          fx.length ? h("span", { class: "muted" }, " · " + [...new Set(fx)].slice(0, 3).join(" · ")) : null),
        on ? h("textarea", { class: "ta", rows: 2, style: { marginLeft: "32px", width: "calc(100% - 32px)", fontSize: "13px", padding: "7px 10px" }, placeholder: "포인트 문구 — 고객 관점 한 문장 (아래 '포인트 문구 수정 요청'으로 채울 수 있어요)",
          onchange: e => doc.commit(p => { p.zones.find(x => x.id === z.id).point = e.target.value; }) }, z.point || "")
          : (z.point ? h("div", { class: "xs muted ellipsis", style: { paddingLeft: "32px" } }, "“" + z.point + "”") : null));
    }),
    h("div", { class: "xs muted", style: { padding: "4px 2px" } },
      `구획 합계 약 ${fmt(zArea, 0)} ㎡ · 나머지 ${fmt(Math.max(0, total - zArea), 0)} ㎡는 통로 · ` +
      (outside.length ? `존 밖 제품 ${outside.length}대` : `제품 ${kinds}종 ${doc.p.placements.length}대 모두 존에 들어감`)));
    drawRight();
  }
  const thumb = h("img", { alt: "존 구획도 미리보기", style: { width: "100%", display: "block", borderRadius: "8px", border: "1px solid var(--line)", background: "#fff" } });
  let thumbT = null;
  function refreshThumb() { clearTimeout(thumbT); thumbT = setTimeout(async () => { await doc.flush(); thumb.src = `/api/projects/${id}/drawing.svg?kind=zones&paper=A4&t=${Date.now()}`; }, 700); }
  function drawRight() {
    replace(right,
      h("div", { class: "card pad" },
        h("div", { class: "card-h" }, h("h3", {}, "존 구획"), h("span", { class: "sub" }, `${(doc.p.zones || []).length}곳 · 동선 순서`), h("span", { class: "spacer" }),
          h("button", { class: "btn xs soft", onclick: () => setTool("zone") }, icon("plus", 12), "존 추가")),
        h("div", { style: { marginTop: "10px" } }, list)),
      h("div", { class: "card pad col", style: { gap: "8px" } },
        h("div", { class: "card-h" }, h("h3", {}, "제안서 미리보기"), h("span", { class: "tag" }, "ZP-A"), h("span", { class: "sub" }, "조감도 · 존별 포인트")),
        thumb,
        h("div", { class: "xs muted" }, `2D 평면 + 번호 ${(doc.p.zones || []).length}곳 · 존 이름 · 제품${doc.p.proposal ? " · " + doc.p.proposal : ""}`)),
      h("div", { class: "card pad row" },
        h("div", { class: "grow" }, h("b", { class: "small" }, "3D 조감도 위에도 번호 표시"),
          h("div", { class: "xs muted" }, linked3d.length ? `연결된 3D ${linked3d.length}개 · 렌더 카메라로 번호 위치를 옮겨요` : "연결된 3D 없음 — 2D 완성 화면에서 만들 수 있어요")),
        linked3d.length ? h("button", { class: "btn sm", onclick: () => go(link3d(linked3d[0].id, "result")) }, "3D 보기") : null));
  }

  const nl = h("input", { placeholder: "포인트 문구 수정 요청 (예: 존 2 이름을 '웰컴 라운지'로, 존마다 고객 관점 한 문장으로)", "aria-label": "포인트 문구 수정 요청" });
  const composer = h("div", { class: "composer" }, nl, h("button", { class: "send", "aria-label": "보내기", onclick: () => sendNl() }, icon("send", 15)));
  nl.addEventListener("input", () => composer.classList.toggle("ready", !!nl.value.trim()));
  nl.addEventListener("keydown", e => { if (e.key === "Enter" && !e.isComposing) sendNl(); });
  async function sendNl() {
    if (busy || !(doc.p.zones || []).length) return;
    busy = true;
    try {
      const r = await api.post("/api/2d/zone_points", { project: doc.p, text: nl.value.trim() });
      doc.replace(r.project);
      nl.value = ""; composer.classList.remove("ready");
      toast(r.reply + (r.source === "rules" && !r.reply.includes("규칙") ? " · 규칙 기반" : ""));
    } finally { busy = false; }
  }

  replace(fr.content,
    wmsg(`고객 동선 순서대로 존 ${(doc.p.zones || []).length}곳을 나눴어요. 존 이름과 제품이 제안서 '존별 포인트'와 공간 시나리오 장면으로 이어져요.`, { one: true }),
    h("div", { style: { display: "flex", gap: "12px", marginTop: "12px", flex: "1 1 auto", minHeight: 0 } },
      h("div", { class: "col", style: { flex: "1 1 auto", minWidth: 0, gap: 0 } }, toolbar, planBox), right));
  fr.setBottom(composer,
    h("button", { class: "btn lg", onclick: () => go(link2d(id, "layout")) }, "배치 편집으로"),
    h("button", { class: "btn lg primary", onclick: async () => { await doc.flush(); toast("존 구획을 저장했어요"); go(link2d(id, doc.p.status === "done" ? "done" : "layout")); } }, "존 구획 저장"));

  const offCh = doc.on(w => {
    if (w === "change") { pv.set({ project: doc.p, zoneSel: zsel }); drawList(); refreshThumb(); }
    if (w === "validation") { pv.set({ v: doc.v }); drawList(); }
  });
  pv.set({ project: doc.p, zoneSel: zsel });
  drawToolbar();
  drawList();
  refreshThumb();
  await doc.validateNow();
  const onKey = e => {
    if (e.target.closest("input,textarea,select")) return;
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "z") { e.preventDefault(); e.shiftKey ? doc.redo() : doc.undo(); }
    if (e.key === "Escape") setTool("select");
  };
  document.addEventListener("keydown", onKey);
  return { beforeLeave: () => doc.flush(), unmount: () => { off(); offCh(); pv.destroy(); clearTimeout(thumbT); document.removeEventListener("keydown", onKey); }, dirty: () => doc.dirty() };
}
