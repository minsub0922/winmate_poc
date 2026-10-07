// BR3 — 3D 조감도 3/3 · 결과 (렌더 + 2D 존 번호 · 컷 · AI 구성 요약 · 품질 확인 · 다른 안 2개 · 한 줄 요청)
import { api } from "../api.js";
import { h, icon, replace, wmsg, toast, aitag, josa } from "../dom.js";
import { go, link2d, link3d } from "../shell.js";
import { load3d, frame3d, labels, fileUrl, watchJob, activeJob, CAMS, LIGHTS } from "../ui3d.js";

export async function mount(id) {
  let p = await load3d(id);
  const L = await labels();
  const fr = frame3d(p, "result", { fill: true });
  const renders = () => (p.renders || []);
  let cur = pickDefault();
  let zonesOn = true, altJob = null, unwatch = null;
  let qcam = "eye", qlight = "day";

  function pickDefault() {
    const rs = renders();
    const after = rs.filter(r => r.variant === "after");
    return (after.slice().reverse().find(r => r.camera === "aerial45" && r.lighting === "day") || after[after.length - 1] || rs[rs.length - 1] || {}).id;
  }
  const msgBox = h("div", {});
  const viewer = h("div", { class: "col", style: { gap: "10px", minWidth: 0, flex: "1 1 auto" } });
  const side = h("div", { class: "rpanel", style: { width: "340px" } });

  function drawMsg() {
    const b = p.brief || {};
    const r = renders().find(x => x.id === cur);
    const lay = p.layout || {};
    const kinds = new Set((lay.placements || []).map(x => x.product)).size;
    const furn = (b.furniture || []).length;
    if (!r) { replace(msgBox, wmsg("아직 렌더가 없어요. 요구사항에서 3D 조감도를 만들어 주세요.")); return; }
    replace(msgBox, wmsg(`3D 조감도가 완성됐어요. ${L.concept(b.concept)} 콘셉트의 ${r.label} 컷이에요. 제품 ${kinds}종은 ${p.linked_2d ? "2D 배치대로 두었고" : "배치 룰로 공간에 맞춰 놓았고"}, 가구 ${furn}종은 AI가 골랐어요.`));
  }
  function drawViewer() {
    const rs = renders();
    const r = rs.find(x => x.id === cur);
    if (!r) {
      replace(viewer, h("div", { class: "card pad empty" }, "렌더가 없어요", h("div", { style: { marginTop: "10px" } }, h("button", { class: "btn primary", onclick: () => go(link3d(id, "brief")) }, "요구사항으로"))));
      return;
    }
    const ar = r.res ? `${r.res[0]} / ${r.res[1]}` : "16 / 9";
    const pins = zonesOn && r.variant === "after" ? (r.zones || []).filter(z => z.in_frame) : [];
    const box = h("div", { class: "render", style: { aspectRatio: ar, width: "100%", maxHeight: "calc(100vh - 380px)", margin: "0 auto" } },
      h("img", { src: fileUrl(id, r.file), alt: `${p.title} 3D 조감도 — ${r.label} (AI 생성 · 개략)` }),
      pins.map(z => h("div", { class: "zonepin", style: { left: (z.u * 100) + "%", top: (z.v * 100) + "%", opacity: z.visible === false ? 0.75 : 1 } }, h("b", {}, z.no), h("span", {}, z.name))),
      aitag(),
      h("span", { class: "aitag cap", style: { left: "auto", right: "12px" } }, `${r.label} · ${r.res ? r.res.join("×") : ""}`));
    // 높이에 맞춰 너비를 줄인다(16:9 유지)
    box.style.width = "auto"; box.style.height = "min(calc(100vh - 380px), calc((100vw - 248px - 64px - 352px) * 9 / 16))";
    const hasZones = (r.zones || []).length > 0;
    replace(viewer,
      h("div", { style: { display: "flex", justifyContent: "center" } }, box),
      h("div", { class: "row" },
        h("div", { class: "row grow", style: { overflowX: "auto", gap: "8px", paddingBottom: "2px" } },
          rs.slice().reverse().map(x => h("button", { class: "cut" + (x.id === cur ? " on" : ""), style: { width: "132px", flexShrink: 0, padding: 0 }, title: x.label, onclick: () => { cur = x.id; drawAll(); } },
            h("img", { src: fileUrl(id, x.file), alt: "", loading: "lazy" }), h("span", { class: "aitag" }, "AI 생성 · 개략"), h("span", { class: "lbl" }, x.label))),
          h("button", { class: "drop", style: { width: "110px", flexShrink: 0, aspectRatio: "16 / 9" }, onclick: () => go(link3d(id, "cuts")) }, icon("plus", 16), "컷 추가")),
        hasZones ? h("button", { class: "toggle" + (zonesOn ? " on" : ""), onclick: () => { zonesOn = !zonesOn; drawViewer(); } }, zonesOn ? icon("check", 10, 3.4) : null, p.linked_2d ? "존 번호 (2D)" : "존 번호") : null),
      h("div", { class: "row small muted" }, icon("info", 13),
        h("span", { class: "grow" }, "개략 이미지예요. 제품 위치 · 수량 · 크기는 실제와 다를 수 있어요 — 정확한 배치는 2D 조감도에서."),
        p.linked_2d ? h("a", { class: "btn sm", href: link2d(p.linked_2d, "done") }, "2D 조감도 열기") : null));
  }
  function drawSide() {
    const b = p.brief || {};
    const lay = p.layout || {};
    const kinds = new Set((lay.placements || []).map(x => x.product)).size;
    const qc = p.qc;
    const alts = (p.alternatives || {}).items || [];
    const altRunning = altJob && ["queued", "running"].includes(altJob.status);
    replace(side,
      h("div", { class: "card pad" },
        h("div", { class: "card-h" }, h("h3", {}, "AI 구성"), h("span", { class: "sub" }, b.meta ? ({ llm: "AI", replay: "AI(저장 응답)", rules: "규칙 기반" }[b.meta.source] || "") : ""), h("span", { class: "spacer" }),
          h("span", { class: "tag" }, `rev ${b.rev || 1}`)),
        h("div", { class: "b", style: { fontSize: "15px", marginTop: "6px" } }, L.concept(b.concept)),
        h("div", { class: "xs muted" }, `${L.floor(b.floor)} · ${L.wall(b.wall)} · ${L.accent(b.accent)} · ${b.light_k || ""}K`),
        h("div", { class: "row", style: { flexWrap: "wrap", gap: "4px", marginTop: "8px" } },
          h("span", { class: "tag" }, `가구 ${(b.furniture || []).length}종`), h("span", { class: "tag" }, `제품 ${kinds}종${p.linked_2d ? " · 2D 배치" : ""}`),
          h("span", { class: "tag" }, `참고 사례 ${((p.refs || {}).images || []).length}`)),
        h("div", { class: "xs muted", style: { marginTop: "8px" } }, "개별 편집 없이 AI가 정해요 · 바꾸고 싶으면 한 줄 요청이나 다른 안으로")),
      qc ? h("div", { class: "card pad" },
        h("div", { class: "card-h" }, h("h3", {}, "품질 확인"), h("span", { class: "sub" }, qc.ok ? "모두 통과" : "확인 필요 항목 있음")),
        h("div", { class: "col", style: { gap: "4px", marginTop: "6px" } }, qc.items.map(it => h("div", { class: "row small", style: { alignItems: "flex-start" } },
          h("span", { class: "tag " + (it.ok ? "ok" : "dark"), style: { flexShrink: 0 } }, it.ok ? "통과" : "확인"),
          h("div", { style: { minWidth: 0 } }, h("b", {}, it.name), h("div", { class: "xs muted" }, it.detail)))))) : null,
      h("div", { class: "card pad col", style: { gap: "8px" } },
        h("div", { class: "card-h" }, h("h3", {}, "시점 · 조명 컷 추가"), h("span", { class: "sub" }, "배치 · 가구는 그대로")),
        h("div", { class: "row", style: { flexWrap: "wrap", gap: "4px" } }, h("span", { class: "xs muted", style: { width: "28px" } }, "시점"),
          CAMS.map(([k, l]) => h("button", { class: "chip sm" + (qcam === k ? " on" : ""), onclick: () => { qcam = k; drawSide(); } }, l))),
        h("div", { class: "row", style: { flexWrap: "wrap", gap: "4px" } }, h("span", { class: "xs muted", style: { width: "28px" } }, "조명"),
          LIGHTS.map(([k, l]) => h("button", { class: "chip sm" + (qlight === k ? " on" : ""), onclick: () => { qlight = k; drawSide(); } }, l))),
        h("div", { class: "row" },
          h("button", { class: "btn sm soft", onclick: () => makeCut([[qcam, qlight, "after"]]) }, icon("camera", 13), "이 컷 만들기"),
          h("button", { class: "btn sm ghost", onclick: () => go(link3d(id, "cuts")) }, "여러 컷 · 도입 전 컷"))),
      h("div", { class: "card pad col", style: { gap: "8px" } },
        h("div", { class: "card-h" }, h("h3", {}, "다른 안"), h("span", { class: "sub" }, "같은 시점 · 같은 조명으로 콘셉트만 바꿔요")),
        altRunning ? h("div", { class: "col", style: { gap: "6px" } }, h("div", { class: "row small" }, h("span", { class: "spin" }), `다른 안 만드는 중 · ${altJob.pct}%`),
          h("div", { class: "pbar" }, h("i", { style: { width: altJob.pct + "%" } })), h("div", { class: "xs muted" }, (altJob.steps.find(s => s.status === "run") || {}).note || "")) : null,
        !altRunning && alts.length ? h("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" } }, alts.map(a => h("div", { class: "col", style: { gap: "4px" } },
          h("div", { class: "cut", style: { cursor: "default" } }, h("img", { src: fileUrl(id, a.file), alt: a.label }), h("span", { class: "aitag" }, "AI 생성 · 개략"), h("span", { class: "lbl" }, a.label)),
          h("button", { class: "btn xs outline", onclick: () => pick(a) }, "이 안으로")))) : null,
        !altRunning ? h("button", { class: "btn sm", onclick: makeAlts }, icon("refresh", 13), alts.length ? "다른 안 2개 다시 만들기" : "다른 안 2개 보기") : null));
  }
  async function makeCut(cuts) {
    const r = await api.post(`/api/projects/${id}/render`, { mode: "cuts", cuts, quality: (p.input || {}).quality });
    if (r && r.id) { toast("컷을 만들기 시작했어요"); go(link3d(id, "cuts")); }
  }
  async function makeAlts() {
    const r = await api.post(`/api/projects/${id}/alternatives`, { quality: "draft" });
    followAlt(r);
  }
  function followAlt(j) {
    altJob = j; drawSide();
    if (unwatch) unwatch();
    unwatch = watchJob(j.id, jj => { altJob = jj; drawSide(); }, async jj => {
      altJob = null; p = await load3d(id); drawAll();
      if (jj.status === "done") toast("다른 안 2개를 만들었어요"); else if (jj.status === "failed") toast("다른 안을 만들지 못했어요 — " + (jj.error || ""), "err");
    });
  }
  async function pick(a) {
    p = await api.post(`/api/projects/${id}/alternatives/${a.id}/pick`);
    cur = renders()[renders().length - 1].id;
    toast(`${josa(a.label, "으로/로")} 바꿨어요 — 다른 시점 컷은 '컷 추가'로 다시 만들어요`);
    drawAll();
  }

  const req = h("input", { placeholder: "한 줄 요청 (예: 조명을 더 따뜻하게, 식물은 빼고, 더 미니멀하게)", "aria-label": "한 줄 요청" });
  const composer = h("div", { class: "composer" }, h("span", { class: "label" }, "한 줄 요청"), req, h("button", { class: "send", "aria-label": "보내기", onclick: () => sendReq() }, icon("send", 15)));
  req.addEventListener("input", () => composer.classList.toggle("ready", !!req.value.trim()));
  req.addEventListener("keydown", e => { if (e.key === "Enter" && !e.isComposing) sendReq(); });
  async function sendReq() {
    const text = req.value.trim();
    if (!text) return;
    const r = await api.post(`/api/projects/${id}/render`, { mode: "request", text, quality: (p.input || {}).quality });
    if (r && r.id) go(link3d(id, "build"));
  }

  function drawAll() { drawMsg(); drawViewer(); drawSide(); }
  replace(fr.content, msgBox,
    h("div", { style: { display: "flex", gap: "12px", marginTop: "12px", flex: "1 1 auto", minHeight: 0 } }, viewer, side));
  fr.setBottom(composer,
    h("button", { class: "btn lg", onclick: () => go(link3d(id, "brief")) }, "요구사항"),
    h("button", { class: "btn lg", onclick: () => go(link3d(id, "cuts")) }, icon("camera", 15), "시점 · 조명 컷"),
    h("button", { class: "btn lg primary", disabled: !renders().length, onclick: () => go(link3d(id, "export")) }, "내보내기 · 제안서로", icon("arrowR")));
  drawAll();
  const aj = await activeJob(id);
  if (aj && aj.kind === "alternatives") followAlt(aj);
  else if (aj && aj.kind === "render") toast("렌더가 진행 중이에요 — 끝나면 컷이 추가돼요");
  else if (location.hash.includes("alt=1") && renders().length) makeAlts();
  return { unmount: () => { if (unwatch) unwatch(); } };
}
