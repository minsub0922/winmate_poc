// BP1 — 2D 조감도 1/4 · 공간 · 치수 (실측 치수 입력 + 실시간 미리보기)
import { library } from "../api.js";
import { h, icon, replace, fmt, wmsg, pyeong, toast } from "../dom.js";
import { go, link2d } from "../shell.js";
import { Doc2D } from "../state.js";
import { PlanView } from "../plan.js";
import { frame2d, numInput, unitField, WALL_NAMES, KIND_NAMES, DOOR_TYPES } from "../ui2d.js";

export async function mount(id) {
  const doc = await Doc2D.load(id);
  const lib = await library();
  const { fr, off } = frame2d(doc, "space", { fill: true });
  let tool = "select";
  let sel = null;

  const planBox = h("div", { class: "planbox", style: { flex: "1 1 auto", minHeight: "0" } });
  const pv = new PlanView(planBox, {
    mode: "space", snap: 100, layers: { dims: true, grid: true, labels: true },
    onSelect: (sid, kind) => { sel = sid ? { id: sid, kind } : null; drawPanel(); },
    onCommit: c => {
      const sp = doc.p.space;
      if (c.type === "move") {
        doc.commit(p => {
          const arr = c.kind === "pillar" ? p.space.pillars : p.space.outlets;
          const it = arr.find(x => x.id === c.id);
          if (c.kind === "outlet") {
            const s0 = pv.snapToSurface(it.x + c.dx, it.y + c.dy);
            Object.assign(it, s0);
          } else { it.x = clamp(it.x + c.dx, it.w / 2, sp.width - it.w / 2); it.y = clamp(it.y + c.dy, it.d / 2, sp.depth - it.d / 2); }
          p.space_changed = true;
        }, { validate: false });
      } else if (c.type === "outlet-add") {
        doc.commit(p => { p.space.outlets = p.space.outlets || []; const n = nextNo(p.space.outlets, "C"); p.space.outlets.push({ id: `C${n}`, label: `C${n}`, x: Math.round(c.x), y: Math.round(c.y), on: c.on }); }, { validate: false });
      } else if (c.type === "pillar-add") {
        doc.commit(p => { const n = nextNo(p.space.pillars, "P"); p.space.pillars.push({ id: `P${n}`, label: `기둥 ${n}`, x: c.x, y: c.y, w: 600, d: 600 }); p.space_changed = true; }, { validate: false });
        setTool("select");
      }
    },
  });
  const panel = h("div", { class: "rpanel", style: { width: "400px" } });
  const legend = h("div", { class: "legend" }, h("span", {}, h("i", { style: { background: "#d0d4db" } }), "벽"), h("span", {}, h("i", { style: { background: "#1428a0" } }), "유리창"),
    h("span", {}, h("i", { style: { background: "#596170" } }), "기둥"), h("span", {}, h("i", { style: { border: "1.5px solid #121417", borderRadius: "50%", width: "8px" } }), "콘센트"));
  planBox.append(legend);
  const toolBtns = h("div", { class: "row", style: { gap: "6px" } });
  const areaEl = h("span", { class: "small muted" });

  function setTool(t) { tool = t; pv.setOpt({ tool: t }); drawTools(); }
  function drawTools() {
    replace(toolBtns,
      h("button", { class: "btn sm" + (tool === "outlet" ? " soft" : ""), onclick: () => setTool(tool === "outlet" ? "select" : "outlet") }, icon("plug", 13), tool === "outlet" ? "콘센트 찍는 중 — 벽 · 기둥을 누르세요" : "콘센트 위치 찍기"),
      h("button", { class: "btn sm" + (tool === "pillar" ? " soft" : ""), onclick: () => setTool(tool === "pillar" ? "select" : "pillar") }, icon("plus", 13), tool === "pillar" ? "기둥 위치를 누르세요" : "기둥 찍기"),
      h("button", { class: "iconbtn", title: "화면에 맞춤", onclick: () => pv.fit() }, icon("fit", 14)));
  }

  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const nextNo = (arr, pre) => 1 + Math.max(0, ...(arr || []).map(x => parseInt(String(x.id).replace(pre, ""), 10) || 0));

  function problems() {
    const sp = doc.p.space, out = [];
    for (const o of sp.openings || []) {
      const L = o.wall === "front" || o.wall === "back" ? sp.width : sp.depth;
      if (o.start < 0 || o.start + o.length > L + 1) out.push(`${o.label || o.id}: 벽 길이(${fmt(L)})를 넘어요`);
    }
    for (const pi of sp.pillars || []) if (pi.x < 0 || pi.y < 0 || pi.x > sp.width || pi.y > sp.depth) out.push(`${pi.label}: 공간 밖이에요`);
    if (!(sp.openings || []).some(o => o.kind === "entrance")) out.push("출입구가 없어요 — 동선 시작점이 필요해요");
    return out;
  }

  function sec(title, sub, ...kids) {
    return h("div", { class: "card pad" }, h("div", { class: "card-h" }, h("h3", {}, title), sub ? h("span", { class: "sub" }, sub) : null), ...kids);
  }

  function drawPanel() {
    const p = doc.p, sp = p.space;
    const st = lib.space_types;
    const groups = [...new Set(st.map(s => s.group))];
    const setSp = (fn, changed = true) => doc.commit(pp => { fn(pp.space); if (changed) pp.space_changed = true; }, { validate: false });
    const opRows = (sp.openings || []).map((o, i) => h("div", { class: "col", style: { gap: "6px", padding: "10px 0", borderTop: i ? "1px solid var(--line)" : "none", background: sel && sel.id === o.id ? "var(--pri-soft)" : null, margin: "0 -8px", paddingLeft: "8px", paddingRight: "8px", borderRadius: "8px" } },
      h("div", { class: "row" },
        h("select", { class: "sel sm", style: { width: "92px" }, "aria-label": "종류", onchange: e => setSp(s => { s.openings[i].kind = e.target.value; }) },
          Object.entries(KIND_NAMES).map(([k, v]) => h("option", { value: k, selected: o.kind === k }, v))),
        h("select", { class: "sel sm", style: { width: "104px" }, "aria-label": "벽", onchange: e => setSp(s => { s.openings[i].wall = e.target.value; }) },
          Object.entries(WALL_NAMES).map(([k, v]) => h("option", { value: k, selected: o.wall === k }, v))),
        h("input", { class: "inp sm grow", value: o.label || "", placeholder: "이름", "aria-label": "이름", onchange: e => setSp(s => { s.openings[i].label = e.target.value; }, false) }),
        h("button", { class: "iconbtn ghost", "aria-label": "삭제", onclick: () => setSp(s => { s.openings.splice(i, 1); }) }, icon("x", 14))),
      h("div", { class: "row" },
        h("span", { class: "xs muted nowrap" }, "시작"), numInput(o.start, v => setSp(s => { s.openings[i].start = v; }), { sm: true, min: 0 }),
        h("span", { class: "xs muted nowrap" }, "폭"), numInput(o.length, v => setSp(s => { s.openings[i].length = v; }), { sm: true, min: 100 }),
        o.kind === "door" ? h("select", { class: "sel sm", style: { width: "120px" }, "aria-label": "문 종류", onchange: e => setSp(s => { s.openings[i].door_type = e.target.value; }) },
          Object.entries(DOOR_TYPES).map(([k, v]) => h("option", { value: k, selected: (o.door_type || "normal") === k }, v))) : null)));
    const pillarRows = (sp.pillars || []).map((pi, i) => h("div", { class: "col", style: { gap: "6px", padding: "8px 0", borderTop: i ? "1px solid var(--line)" : "none" } },
      h("div", { class: "row" }, h("b", { class: "small nowrap" }, pi.label || pi.id), h("span", { class: "xs muted" }, "중심 좌표 · 크기 (mm)"), h("span", { class: "spacer" }),
        h("button", { class: "iconbtn ghost", "aria-label": "삭제", onclick: () => setSp(s => { s.pillars.splice(i, 1); }) }, icon("x", 14))),
      h("div", { style: { display: "grid", gridTemplateColumns: "auto 1fr auto 1fr 64px auto 64px", gap: "6px", alignItems: "center" } },
        h("span", { class: "xs muted" }, "X"), numInput(pi.x, v => setSp(s => { s.pillars[i].x = v; }), { sm: true }),
        h("span", { class: "xs muted" }, "Y"), numInput(pi.y, v => setSp(s => { s.pillars[i].y = v; }), { sm: true }),
        numInput(pi.w, v => setSp(s => { s.pillars[i].w = v; s.pillars[i].d = s.pillars[i].d || v; }), { sm: true, min: 100, label: "가로" }),
        h("span", { class: "xs muted" }, "×"), numInput(pi.d, v => setSp(s => { s.pillars[i].d = v; }), { sm: true, min: 100, label: "세로" }))));
    const outlets = sp.outlets || [];
    const probs = problems();
    replace(panel,
      sec("공간", "단위 mm",
        h("div", { class: "col", style: { marginTop: "10px", gap: "10px" } },
          h("div", { class: "row" },
            h("div", { class: "field grow" }, h("label", {}, "공간 이름"), h("input", { class: "inp", value: sp.name || "", onchange: e => setSp(s => { s.name = e.target.value; }, false) })),
            h("div", { class: "field", style: { width: "150px" } }, h("label", {}, "공간 유형"),
              h("select", { class: "sel", onchange: e => setSp(s => { s.space_type = e.target.value; }, false) },
                groups.map(g => h("optgroup", { label: g }, st.filter(x => x.group === g).map(x => h("option", { value: x.code, selected: sp.space_type === x.code }, x.label))))))),
          h("div", { class: "row", style: { alignItems: "flex-end" } },
            unitField("가로 (X · 정면 폭)", numInput(sp.width, v => setSp(s => { s.width = v; }), { min: 1000, max: 200000 })),
            unitField("세로 (Y · 안쪽 깊이)", numInput(sp.depth, v => setSp(s => { s.depth = v; }), { min: 1000, max: 200000 })),
            unitField("층고", numInput(sp.height, v => setSp(s => { s.height = v; }), { min: 2000, max: 20000 }))),
          h("div", { class: "xs muted" }, "원점 (0, 0) = 정면(입구 · 도로측) 왼쪽 모서리 · X는 오른쪽, Y는 안쪽으로 재요."))),
      sec("개구부", `유리창 ${count("window")} · 출입구 ${count("entrance")} · 문 ${count("door")}`,
        h("div", { style: { marginTop: "6px" } }, opRows.length ? opRows : h("div", { class: "small muted", style: { padding: "8px 0" } }, "아직 없어요")),
        h("div", { class: "row", style: { marginTop: "6px" } },
          ["window", "entrance", "door"].map(k => h("button", { class: "btn xs", onclick: () => setSp(s => {
            const n = nextNo(s.openings, "O");
            const L = s.width;
            s.openings.push({ id: `O${n}`, kind: k, wall: k === "door" ? "back" : "front", start: Math.round(L / 2 / 100) * 100 - (k === "window" ? 1500 : 600), length: k === "window" ? 3000 : (k === "entrance" ? 1800 : 1000),
              label: { window: "유리창", entrance: "출입구", door: "문" }[k] + " " + n, sill: k === "window" ? 0 : 0, head: k === "window" ? Math.min(s.height - 400, 3000) : 2400, door_type: k === "door" ? "normal" : undefined });
          }) }, icon("plus", 12), KIND_NAMES[k])))),
      sec("기둥", `${(sp.pillars || []).length}개`,
        h("div", { style: { marginTop: "6px" } }, pillarRows.length ? pillarRows : h("div", { class: "small muted", style: { padding: "8px 0" } }, "없어요 — 평면에서 '기둥 찍기'로 추가")),
        h("div", { class: "row", style: { marginTop: "6px" } }, h("button", { class: "btn xs", onclick: () => setTool("pillar") }, icon("plus", 12), "기둥 찍기"))),
      sec("콘센트", `${outlets.length}개 · 전원 거리 계산에 써요`,
        h("div", { class: "row", style: { flexWrap: "wrap", gap: "6px", marginTop: "8px" } },
          outlets.map((o, i) => h("span", { class: "chip sm" + (sel && sel.id === o.id ? " on" : "") }, o.label || o.id, h("span", { class: "xs muted" }, `${fmt(o.x)}, ${fmt(o.y)}`),
            h("button", { class: "btn link", style: { padding: 0 }, "aria-label": "삭제", onclick: () => doc.commit(pp => { pp.space.outlets.splice(i, 1); }, { validate: false }) }, h("span", { class: "x" }, "×")))),
          h("button", { class: "btn xs" + (tool === "outlet" ? " soft" : ""), onclick: () => setTool(tool === "outlet" ? "select" : "outlet") }, icon("pin", 12), "위치 찍기"))),
      probs.length ? h("div", { class: "callout" }, probs.map(t => h("div", {}, "· " + t))) : null);
    function count(k) { return (sp.openings || []).filter(o => o.kind === k).length; }
    const m2 = sp.width * sp.depth / 1e6;
    areaEl.textContent = `${fmt(m2, 0)} ㎡ (약 ${pyeong(m2)}평) · 층고 ${fmt(sp.height)}`;
  }

  replace(fr.content,
    wmsg(h("span", {}, "2D 조감도는 실제 치수로 제품 위치 · 수량 · 동선을 정하는 도면이에요. 도면이 있으면 올려 주세요. 벽 · 창 · 문 · 기둥을 읽어 옵니다. 없으면 오른쪽에 실측 치수를 넣어 주세요. ",
      h("button", { class: "btn soft sm", style: { marginLeft: "4px", verticalAlign: "middle" }, onclick: () => go(link2d(id, "plan")) }, icon("upload", 13), "도면 올리기"))),
    h("div", { style: { display: "flex", gap: "12px", marginTop: "14px", flex: "1 1 auto", minHeight: 0 } },
      h("div", { class: "col", style: { flex: "1 1 auto", minWidth: 0, gap: "8px" } },
        h("div", { class: "row" }, h("b", {}, "실시간 미리보기"), h("span", { class: "small muted" }, "입력한 값만 그려요"), h("span", { class: "spacer" }), areaEl, toolBtns),
        planBox),
      panel));
  fr.setBottom(
    h("div", { class: "col grow", style: { gap: "0", paddingLeft: "6px" } }, h("b", {}, "공간 · 치수 · 1 / 4"), h("span", { class: "small muted" }, "치수는 mm 단위 · 줄자 실측값 기준 · 평면에서 기둥 · 콘센트를 끌어 옮길 수 있어요")),
    h("button", { class: "btn lg", onclick: () => go("#/") }, "작업 목록"),
    h("button", { class: "btn lg primary", onclick: async () => {
      const probs = problems().filter(t => !t.startsWith("출입구"));
      if (probs.length) { toast(probs[0], "err"); return; }
      doc.commit(p => { if (p.step === "space" || p.step === "plan") p.step = "products"; }, { validate: false });
      await doc.flush();
      go(link2d(id, "products"));
    } }, "제품 · 수량 입력", icon("arrowR")));

  const offCh = doc.on(w => { if (w === "change") { pv.set({ project: doc.p }); drawPanel(); } });
  pv.set({ project: doc.p });
  drawTools();
  drawPanel();
  const onKey = e => {
    if (e.target.closest("input,textarea,select")) return;
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "z") { e.preventDefault(); e.shiftKey ? doc.redo() : doc.undo(); }
    if (e.key === "Escape") setTool("select");
    if ((e.key === "Delete" || e.key === "Backspace") && sel) {
      if (sel.kind === "pillar") doc.commit(p => { p.space.pillars = p.space.pillars.filter(x => x.id !== sel.id); }, { validate: false });
      if (sel.kind === "outlet") doc.commit(p => { p.space.outlets = p.space.outlets.filter(x => x.id !== sel.id); }, { validate: false });
      if (sel.kind === "opening") doc.commit(p => { p.space.openings = p.space.openings.filter(x => x.id !== sel.id); }, { validate: false });
      sel = null;
    }
  };
  document.addEventListener("keydown", onKey);
  return { beforeLeave: () => doc.flush(), unmount: () => { off(); offCh(); pv.destroy(); document.removeEventListener("keydown", onKey); }, dirty: () => doc.dirty() };
}
