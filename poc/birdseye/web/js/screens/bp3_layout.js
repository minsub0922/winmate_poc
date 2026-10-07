// BP3 — 2D 조감도 3/4 · 배치 · 동선 (끌어서 배치 · 회전 · 스냅, 옮길 때마다 F4 검증: 시야각 · 통로 폭 · 전원 거리 …)
import { api, library } from "../api.js";
import { h, icon, replace, fmt, wmsg, toast, menu, confirmBox } from "../dom.js";
import { go, link2d } from "../shell.js";
import { Doc2D } from "../state.js";
import { PlanView, openingWallOfAnchor } from "../plan.js";
import { frame2d, numInput } from "../ui2d.js";

const KIND = { viewing_angle: "시야각", traffic: "동선", power: "전원", overlap: "겹침", height: "높이", support: "설치", size: "크기" };
const persisted = { layers: { dims: true, view: true, flow: true, power: false, zones: true }, snap: 100 };

export async function mount(id) {
  const doc = await Doc2D.load(id);
  const lib = await library();
  const { fr, off } = frame2d(doc, "layout", { fill: true });
  let tool = "select", sel = null, focus = null, busy = false, live = null;

  const planBox = h("div", { class: "planbox" });
  const pv = new PlanView(planBox, {
    mode: "layout", snap: persisted.snap, layers: { ...persisted.layers, grid: true, labels: true, warnings: true, fixtures: true },
    onSelect: (sid, kind) => { sel = sid ? { id: sid, kind } : null; live = null; focus = null; pv.set({ sel: sid, focus: null }); drawPanel(); },
    onDrag: d => { live = d; drawInspectorLive(); },
    onWarning: wid => { focusWarning(wid); },
    onMeasure: m => { const d = Math.hypot(m.b[0] - m.a[0], m.b[1] - m.a[1]); toast(`거리 ${fmt(d)} mm`); },
    onCommit: c => handleCommit(c),
  });
  planBox.append(h("div", { class: "legend" },
    h("span", {}, h("i", { style: { background: "#1428a0" } }), "삼성 제품"), h("span", {}, h("i", { style: { border: "1px dashed #8a91a0", background: "#fff" } }), "집기 블록"),
    h("span", {}, h("i", { style: { background: "#596170" } }), "기둥"), h("span", {}, h("i", { style: { height: "2px", background: "#1428a0" } }), "동선"),
    h("span", {}, h("i", { style: { background: "rgba(20,40,160,.12)", border: "1px dashed rgba(20,40,160,.5)" } }), "시야각"),
    h("span", {}, h("i", { style: { background: "#121417", borderRadius: "50%", width: "9px", height: "9px" } }), "경고")));
  const panel = h("div", { class: "rpanel" });
  const inspector = h("div", { class: "card pad insp" });
  const review = h("div", { class: "card pad" });
  panel.append(inspector, review);
  const toolbar = h("div", { class: "toolbar" });

  function handleCommit(c) {
    if (c.type === "move") {
      doc.commit(p => { const it = find(p, c.kind, c.id); if (it) { it.x = Math.round(it.x + c.dx); it.y = Math.round(it.y + c.dy); } });
    } else if (c.type === "rotate") {
      doc.commit(p => { const it = find(p, c.kind, c.id); if (it) it.rot = ((Math.round(it.rot || 0) + c.delta) % 360 + 360) % 360; });
    } else if (c.type === "zone-new") {
      doc.commit(p => {
        p.zones = p.zones || [];
        const n = 1 + Math.max(0, ...p.zones.map(z => parseInt(String(z.id).slice(1), 10) || 0));
        p.zones.push({ id: `Z${n}`, no: p.zones.length + 1, key: "custom", name: `존 ${p.zones.length + 1}`, x0: c.x0, y0: c.y0, x1: c.x1, y1: c.y1, point: "" });
      });
      toast("존을 추가했어요 — 이름은 '존 구획'에서 바꿀 수 있어요");
      setTool("select");
    }
  }
  const find = (p, kind, fid) => (kind === "placement" ? p.placements : p.fixtures).find(x => x.id === fid);
  const geomOf = fid => doc.v && doc.v.geom && (doc.v.geom.placements[fid] || doc.v.geom.fixtures[fid]);

  function setTool(t) { tool = t; pv.setOpt({ tool: t }); drawToolbar(); }
  function drawToolbar() {
    const L = persisted.layers;
    const tb = (t, ic, label, key) => h("button", { class: tool === t ? "on" : "", "aria-pressed": tool === t, title: key ? `${label} (${key})` : label, onclick: () => setTool(t) }, icon(ic, 12), label);
    const lt = (k, label) => h("button", { class: "toggle" + (L[k] ? " on" : ""), "aria-pressed": !!L[k], onclick: () => { L[k] = !L[k]; pv.setOpt({ layers: { [k]: L[k] } }); drawToolbar(); } }, L[k] ? icon("check", 10, 3.4) : null, label);
    replace(toolbar,
      h("div", { class: "seg", role: "group", "aria-label": "편집 도구" }, tb("select", "pointer", "선택 · 이동", "V"), tb("rotate", "rotate", "회전", "R"), tb("measure", "ruler", "치수 재기", "M"), tb("zone", "zone", "존 그리기")),
      h("span", { class: "vsep" }),
      lt("dims", "치수"), lt("view", "시야각"), lt("flow", "동선"), lt("power", "전원"), lt("zones", "존"),
      h("span", { class: "vsep" }),
      h("select", { class: "sel sm", style: { width: "128px" }, "aria-label": "스냅", title: "끌 때 움직이는 단위", onchange: e => { persisted.snap = +e.target.value; pv.setOpt({ snap: persisted.snap }); } },
        [10, 50, 100, 500].map(v => h("option", { value: v, selected: persisted.snap === v }, `스냅 ${v} mm`))),
      h("span", { class: "spacer" }),
      h("button", { class: "iconbtn", title: "되돌리기 (⌘Z)", disabled: !doc.undoStack.length, onclick: () => doc.undo() }, icon("undo", 14)),
      h("button", { class: "iconbtn", title: "다시 하기 (⇧⌘Z)", disabled: !doc.redoStack.length, onclick: () => doc.redo() }, icon("redo", 14)),
      h("button", { class: "iconbtn", title: "화면에 맞춤", onclick: () => pv.fit() }, icon("fit", 14)),
      h("button", { class: "btn sm", "data-pop-anchor": "", onclick: e => fixtureMenu(e.currentTarget) }, icon("sofa", 14), "집기"));
  }

  function fixtureMenu(anchor) {
    const types = lib.furniture.filter(t => !["generic"].includes(t.type));
    menu(anchor, [{ label: "집기 다시 추천 — 제품 · 동선 기준으로 자동 배치", icon: "wand", run: refurnish }, "-",
      ...types.map(t => ({ label: t.label + " 추가", hint: `${fmt(t.w)} × ${fmt(t.d)}`, run: () => addFixture(t) }))]);
  }
  function addFixture(t) {
    const sp = doc.p.space;
    const vb = pv.vb || [0, 0, sp.width, sp.depth];
    let x = Math.round((vb[0] + vb[2] / 2) / 100) * 100, y = Math.round((vb[1] + vb[3] / 2) / 100) * 100;
    x = Math.max(t.w / 2, Math.min(sp.width - t.w / 2, x)); y = Math.max(t.d / 2, Math.min(sp.depth - t.d / 2, y));
    let nid;
    doc.commit(p => {
      const n = 1 + Math.max(0, ...p.fixtures.map(f => parseInt(String(f.id).replace(/\D/g, ""), 10) || 0));
      nid = `F${n}`;
      p.fixtures.push({ id: nid, type: t.type, label: t.label, x, y, w: t.w, d: t.d, h: t.h, rot: 0, seats: t.seats, user: true });
    });
    sel = { id: nid, kind: "fixture" };
    pv.set({ sel: nid });
    drawPanel();
  }
  async function refurnish() {
    if (doc.p.fixtures.length && !await confirmBox("집기 다시 추천", "지금 집기 블록을 모두 지우고 제품 배치 · 동선 기준으로 다시 놓아요. 되돌리기(⌘Z)로 돌아올 수 있어요.", "다시 추천")) return;
    const r = await api.post("/api/2d/fixtures", { project: doc.p });
    doc.commit(p => { p.fixtures = r.fixtures; });
    const sk = (r.log && r.log.skipped) || [];
    toast(`집기 ${r.fixtures.length}개를 놓았어요` + (sk.length ? ` · 자리가 없어 ${sk.length}개 생략` : ""));
  }

  // ── 오른쪽: 선택한 항목 ──
  function drawInspectorLive() {
    if (!live || !sel || live.id !== sel.id) return;
    const xs = inspector.querySelectorAll("[data-live]");
    for (const el of xs) el.value = fmt(live[el.dataset.live]);
  }
  function drawPanel() {
    drawInspector();
    drawReview();
  }
  function drawInspector() {
    const p = doc.p;
    if (!sel) {
      const kinds = new Set(p.placements.map(x => x.product)).size;
      replace(inspector,
        h("div", { class: "card-h" }, h("h3", {}, "배치"), h("span", { class: "sub" }, `제품 ${kinds}종 ${p.placements.length}대 · 집기 ${p.fixtures.length}개 · 존 ${(p.zones || []).length}`)),
        h("div", { class: "small muted", style: { marginTop: "8px" } }, "평면에서 항목을 누르면 좌표 · 회전 · 높이를 바꿀 수 있어요. 끌어서 옮기면 시야각 · 통로 폭 · 전원 거리를 다시 재요."),
        h("div", { class: "kv xs", style: { marginTop: "10px", color: "var(--muted)" } },
          h("div", { class: "k" }, "끌기"), h("div", {}, "스냅 단위로 이동 · 벽 · 창 제품은 벽을 따라서만 (Alt 로 자유 이동)"),
          h("div", { class: "k" }, "← → ↑ ↓"), h("div", {}, "스냅만큼 이동 · Shift 는 10배"),
          h("div", { class: "k" }, "R"), h("div", {}, "90° 회전 (Shift 는 반대)"),
          h("div", { class: "k" }, "⌘D · Delete"), h("div", {}, "복제 · 빼기"),
          h("div", { class: "k" }, "⌘Z"), h("div", {}, "되돌리기"),
          h("div", { class: "k" }, "휠 · 더블클릭"), h("div", {}, "확대 · 맞춤")));
      return;
    }
    const isP = sel.kind === "placement";
    const it = find(p, sel.kind, sel.id);
    if (!it) { sel = null; drawInspector(); return; }
    const g0 = geomOf(sel.id) || {};
    const met = (doc.v && doc.v.metrics && doc.v.metrics.placements && doc.v.metrics.placements[sel.id]) || {};
    const zone = (p.zones || []).find(z => z.no === g0.zone);
    const upd = (key, val) => doc.commit(pp => { const x = find(pp, sel.kind, sel.id); if (x) x[key] = val; });
    const wall = isP ? openingWallOfAnchor(p.space, it.anchor) : null;
    const field = (label, key, opts = {}) => h("div", { class: "field" }, h("label", {}, label), h("div", { class: "unit" },
      (() => { const el = numInput(it[key] ?? 0, v => upd(key, opts.mod ? ((v % 360) + 360) % 360 : v), { sm: true, min: opts.min, max: opts.max }); if (opts.live) el.dataset.live = key; return el; })(), h("span", {}, opts.unit || "mm")));
    const pw = met.power;
    const title = isP ? `${g0.short || it.product}` : (it.label || g0.type_label || it.type);
    replace(inspector,
      h("div", { class: "card-h" }, h("span", { class: "small muted" }, "선택한 항목 · ", isP ? "삼성 제품" : "집기 블록"), h("span", { class: "spacer" }),
        zone ? h("span", { class: "tag pri" }, `존 ${zone.no} · ${zone.name}`) : null),
      h("div", { style: { marginTop: "4px" } },
        isP ? h("div", { class: "b", style: { fontSize: "15px" } }, title, h("span", { class: "small muted", style: { fontWeight: 500, marginLeft: "6px" } }, g0.name || ""))
          : h("input", { class: "inp sm b", value: title, "aria-label": "이름", onchange: e => upd("label", e.target.value) })),
      h("div", { class: "fields" },
        field("X", "x", { live: true }), field(wall ? "Y · 벽면" : "Y", "y", { live: true }),
        field("회전", "rot", { unit: "°", mod: true }),
        isP ? (g0.category === "hvac_cassette" ? h("div", { class: "field" }, h("label", {}, "설치"), h("div", { class: "ro" }, "천장 매립")) : field("하단 높이", "bottom", { min: 0 }))
          : field("폭", "w", { min: 200 }),
        isP ? h("div", { class: "field" }, h("label", {}, "폭 · 스펙"), h("div", { class: "ro" }, fmt(g0.fw))) : field("깊이", "d", { min: 200 }),
        isP ? h("div", { class: "field" }, h("label", {}, "높이 · 스펙"), h("div", { class: "ro" }, fmt(g0.sh))) : (it.seats ? field("좌석", "seats", { unit: "석", min: 1 }) : h("div", {})),
        isP ? h("div", { class: "field" }, h("label", {}, "전원"), h("div", { class: "ro" }, pw ? `${pw.outlet}까지 ${fmt(pw.mm / 1000, 1)} m` : "콘센트 없음"),
          h("div", { class: "xs muted" }, pw ? (pw.mm <= 2000 ? "가까운 콘센트 사용" : (g0.mount === "ceiling_hang" || g0.category === "hvac_cassette" ? "천장 배선 필요" : g0.mount === "wall" ? "벽 배선 필요" : "바닥 배선 필요")) : "콘센트 위치를 넣어 주세요")) : null,
        isP && met.view_mm ? h("div", { class: "field" }, h("label", {}, "시청 거리"), h("div", { class: "ro" }, `${fmt(met.view_mm)} mm`),
          met.diag_range ? h("div", { class: "xs muted" }, `권장 ${met.diag_range[0]}–${met.diag_range[1]}" · 지금 ${met.diag_in}"`) : null) : null),
      isP ? h("div", { class: "xs muted", style: { marginTop: "8px" } }, `${g0.mount_name || ""} · 높이 ${fmt(g0.z0)}–${fmt(g0.z1)} mm` + (it.anchor ? ` · 기준 ${it.anchor}` : "")) : null,
      h("div", { class: "row", style: { marginTop: "12px" } },
        h("button", { class: "btn xs", onclick: duplicate }, icon("copy", 12), isP ? "같은 제품 1대 더" : "복제"),
        h("button", { class: "btn xs ghost danger", onclick: removeSel }, icon("trash", 12), isP ? "이 제품 빼기" : "삭제")));
  }
  function duplicate() {
    if (!sel) return;
    const isP = sel.kind === "placement";
    let nid;
    doc.commit(p => {
      const it = find(p, sel.kind, sel.id);
      const c = JSON.parse(JSON.stringify(it));
      const g0 = geomOf(sel.id) || {};
      const lat = [Math.cos((it.rot || 0) * Math.PI / 180), Math.sin((it.rot || 0) * Math.PI / 180)];
      const step = (isP ? (g0.fw || 1000) : it.w) + 300;
      c.x = Math.round(it.x + lat[0] * step); c.y = Math.round(it.y + lat[1] * step);
      if (isP) {
        const line = p.lines.find(l => l.id === it.line);
        const n = 1 + Math.max(0, ...p.placements.filter(x => x.line === it.line).map(x => parseInt(x.id.split("-").pop(), 10) || 0));
        c.id = `${it.line}-${n}`;
        if (line) line.qty = (line.qty || 0) + 1;
        p.placements.push(c);
      } else {
        const n = 1 + Math.max(0, ...p.fixtures.map(f => parseInt(String(f.id).replace(/\D/g, ""), 10) || 0));
        c.id = `F${n}`; c.user = true;
        p.fixtures.push(c);
      }
      nid = c.id;
    });
    sel = { id: nid, kind: sel.kind };
    pv.set({ sel: nid });
    drawPanel();
  }
  function removeSel() {
    if (!sel) return;
    const isP = sel.kind === "placement";
    doc.commit(p => {
      if (isP) {
        const it = p.placements.find(x => x.id === sel.id);
        const line = it && p.lines.find(l => l.id === it.line);
        if (line) line.qty = Math.max(0, (line.qty || 1) - 1);
        p.placements = p.placements.filter(x => x.id !== sel.id);
      } else p.fixtures = p.fixtures.filter(x => x.id !== sel.id);
    });
    if (isP) toast("수량표에서도 1대 줄였어요");
    sel = null;
    pv.set({ sel: null });
    drawPanel();
  }

  // ── 오른쪽: 검토 ──
  function focusWarning(wid) {
    const w = doc.v && doc.v.warnings.find(x => x.id === wid);
    if (!w) return;
    focus = wid;
    const t = (w.targets || [])[0];
    if (t) { const kind = doc.p.placements.some(x => x.id === t) ? "placement" : "fixture"; sel = { id: t, kind }; }
    pv.set({ focus: wid, sel: t || null });
    drawPanel();
    const el = review.querySelector(`[data-w="${CSS.escape(wid)}"]`);
    if (el) el.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }
  async function applyFix(w, alt = 0) {
    if (busy) return;
    busy = true;
    try {
      const r = await api.post("/api/2d/fix", { project: doc.p, warning_id: w.id, alt });
      doc.replace(r.project, { v: r.validation });
      toast(`${r.fix} — 반영했어요`);
      focus = null;
    } finally { busy = false; drawPanel(); }
  }
  async function autofixAll() {
    if (busy) return;
    busy = true; drawReview();
    try {
      const r = await api.post("/api/2d/autofix", { project: doc.p });
      doc.replace(r.project, { v: r.validation });
      const n = (r.log || []).length;
      toast(n ? `${n}가지를 고쳤어요 — 되돌리기(⌘Z)로 돌아갈 수 있어요` : "자동으로 고칠 수 있는 경고가 없어요");
    } finally { busy = false; drawPanel(); }
  }
  function drawReview() {
    const v = doc.v;
    if (!v) { replace(review, h("div", { class: "row small muted" }, h("span", { class: "spin" }), "배치를 검토하는 중…")); return; }
    const notes = doc.p.notes || [];
    const ws = v.warnings;
    const active = ws.filter(w => (w.level === "warn" || w.level === "error") && !w.ignored);
    const item = w => {
      const noted = notes.find(n => n.ref === w.id);
      const fixes = [w.fix, ...(w.alt_fixes || [])].filter(Boolean);
      const cls = w.level === "info" ? "info" : w.level === "memo" ? "memo" : w.level === "error" ? "err" : "";
      return h("div", { class: "warn-item" + (focus === w.id ? " picked" : "") + (w.ignored ? " ign" : ""), "data-w": w.id, onclick: e => { if (!e.target.closest("button")) focusWarning(w.id); } },
        h("div", { class: "row", style: { gap: "8px", minWidth: 0 } },
          h("span", { class: "wno " + cls }, w.level === "memo" ? "메모" : w.no),
          h("b", { class: "small nowrap" }, KIND[w.kind] || w.kind),
          h("span", { class: "small muted ellipsis" }, w.title)),
        h("div", { class: "wd" }, w.detail),
        h("div", { class: "wd rid" }, w.rule_id),
        h("div", { class: "wa" },
          w.level === "memo" && noted ? [h("span", { class: "tag ok" }, "메모로 남김"), h("button", { class: "btn xs ghost", onclick: () => doc.commit(p => { p.notes = p.notes.filter(n => n.ref !== w.id); }) }, "메모 지우기")]
            : fixes.map((f, i) => h("button", { class: "btn xs" + (i === 0 ? " outline" : ""), disabled: busy, onclick: () => applyFix(w, i) }, f.label)),
          w.level !== "memo" ? (w.ignored
            ? h("button", { class: "btn xs ghost", onclick: () => doc.commit(p => { p.ignored = (p.ignored || []).filter(x => x !== w.id); }) }, "다시 보기")
            : h("button", { class: "btn xs ghost", onclick: () => doc.commit(p => { p.ignored = [...new Set([...(p.ignored || []), w.id])]; }) }, "무시")) : null));
    };
    replace(review,
      h("div", { class: "card-h" }, h("span", { class: "wno info", style: { width: "18px", height: "18px" } }, "!"), h("h3", {}, "검토"),
        h("span", { class: "sub" }, active.length ? `경고 ${active.length}` : `검토 완료${v.summary.memos ? " · 메모 " + v.summary.memos : ""}`),
        h("span", { class: "spacer" }),
        active.some(w => w.fix) ? h("button", { class: "btn link small", disabled: busy, onclick: autofixAll }, icon("wand", 12), "경고 모두 자동 조정") : null),
      v.flow && v.metrics.flow ? h("div", { class: "xs muted", style: { margin: "4px 0 8px" } },
        `동선 ${fmt(v.metrics.flow.length_mm / 1000, 1)} m · 가장 좁은 곳 ${fmt(v.metrics.flow.min_width_mm)} mm` + (v.metrics.flow.ok ? "" : " · 막힌 곳 있음")) : null,
      ws.length ? h("div", { class: "col", style: { gap: "4px" } }, ws.map(item)) : h("div", { class: "small muted", style: { padding: "8px 0" } }, "문제가 없어요 — 시야각 · 통로 폭 · 문 앞 · 겹침 · 높이 · 전원 모두 통과"));
  }

  // ── 말로 수정 ──
  const nl = h("input", { placeholder: "말로 수정 (예: 라운지 소파 600 오른쪽으로, 관람 벤치 3열 삭제, QM43C 하단 1200)", "aria-label": "말로 수정" });
  const composer = h("div", { class: "composer" }, nl, h("button", { class: "send", "aria-label": "보내기", onclick: () => sendNl() }, icon("send", 15)));
  nl.addEventListener("input", () => composer.classList.toggle("ready", !!nl.value.trim()));
  nl.addEventListener("keydown", e => { if (e.key === "Enter" && !e.isComposing) sendNl(); });
  async function sendNl() {
    const text = nl.value.trim();
    if (!text || busy) return;
    busy = true;
    try {
      const r = await api.post("/api/2d/nl", { project: doc.p, text });
      if (r.ops && r.ops.length) { doc.replace(r.project, { v: r.validation }); nl.value = ""; composer.classList.remove("ready"); }
      toast(`${r.reply}${r.source === "rules" ? " · 규칙으로 처리" : ""}`, r.ops && r.ops.length ? "" : "err");
    } finally { busy = false; }
  }

  async function finish() {
    await doc.validateNow();
    const active = (doc.v ? doc.v.warnings : []).filter(w => (w.level === "warn" || w.level === "error") && !w.ignored);
    if (active.length && !await confirmBox("경고가 남아 있어요", `경고 ${active.length}개가 남아 있어요. 완성 도면의 '검토'에 그대로 표시돼요. 그래도 완성할까요?`, "그래도 완성")) return;
    await doc.bump({ status: "done", step: "done" });
    go(link2d(id, "done"));
  }

  replace(fr.content,
    wmsg("제품 · 집기를 실제 치수대로 놓는 단계예요. 옮길 때마다 시야각 · 통로 폭 · 전원 거리를 다시 재고, 문제가 생긴 곳은 번호로 표시해요.", { one: true }),
    toolbar,
    h("div", { class: "editor" }, planBox, panel));
  fr.setBottom(composer,
    h("button", { class: "btn lg soft", onclick: () => go(link2d(id, "zones")) }, icon("grid", 15), "존 구획"),
    h("button", { class: "btn lg", onclick: () => go(link2d(id, "products")) }, "이전"),
    h("button", { class: "btn lg primary", onclick: finish }, "2D 조감도 완성", icon("arrowR")));

  const offCh = doc.on(w => {
    if (w === "change") { pv.set({ project: doc.p }); drawToolbar(); drawInspector(); }
    if (w === "validation") { pv.set({ v: doc.v }); drawPanel(); }
  });
  const onKey = e => {
    if (e.target.closest("input,textarea,select")) return;
    const k = e.key;
    if ((e.metaKey || e.ctrlKey) && k.toLowerCase() === "z") { e.preventDefault(); e.shiftKey ? doc.redo() : doc.undo(); return; }
    if ((e.metaKey || e.ctrlKey) && k.toLowerCase() === "d") { e.preventDefault(); duplicate(); return; }
    if (k === "Escape") { setTool("select"); pv.select(null, null); return; }
    if (k === "v" || k === "V") setTool("select");
    if (k === "m" || k === "M") setTool("measure");
    if (!sel) return;
    if (k === "r" || k === "R") { handleCommit({ type: "rotate", kind: sel.kind, id: sel.id, delta: e.shiftKey ? -90 : 90 }); return; }
    if (k === "Delete" || k === "Backspace") { e.preventDefault(); removeSel(); return; }
    const st = (persisted.snap || 100) * (e.shiftKey ? 10 : 1);
    const mv = { ArrowLeft: [-st, 0], ArrowRight: [st, 0], ArrowUp: [0, -st], ArrowDown: [0, st] }[k];
    if (mv) { e.preventDefault(); handleCommit({ type: "move", kind: sel.kind, id: sel.id, dx: mv[0], dy: mv[1] }); }
  };
  document.addEventListener("keydown", onKey);
  pv.set({ project: doc.p });
  drawToolbar();
  drawPanel();
  if (!doc.p.placements.length && doc.p.lines.some(l => (l.qty || 0) > 0)) {
    const r = await api.post("/api/2d/layout", { project: doc.p, regenerate: null, fixtures: "auto", zones: "auto" });
    doc.replace(r.project, { v: r.validation });
  } else await doc.validateNow();
  return { beforeLeave: () => doc.flush(), unmount: () => { off(); offCh(); pv.destroy(); document.removeEventListener("keydown", onKey); }, dirty: () => doc.dirty() };
}
