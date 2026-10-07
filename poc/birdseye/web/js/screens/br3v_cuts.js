// BR3V — 시점 · 조명 컷 (배치 · 가구는 그대로, 카메라와 조명만 바꾼 컷 · 도입 전/후 비교)
import { api } from "../api.js";
import { h, icon, replace, wmsg, toast, aitag } from "../dom.js";
import { go, link3d } from "../shell.js";
import { load3d, frame3d, labels, fileUrl, watchJob, activeJob, CAMS, LIGHTS } from "../ui3d.js";

export async function mount(id) {
  let p = await load3d(id);
  const L = await labels();
  const fr = frame3d(p, "cuts", { fill: true });
  let job = await activeJob(id);
  let unwatch = null;
  let mode = "side", swipe = 50;
  const pickCams = new Set(["eye"]), pickLights = new Set(["day"]);
  let withBefore = false;
  const rs = () => p.renders || [];
  let A = null, B = null;
  defaultPair();

  function defaultPair() {
    const before = rs().filter(r => r.variant === "before");
    const after = rs().filter(r => r.variant === "after");
    if (before.length) {
      const bf = before[before.length - 1];
      A = bf.id;
      const match = after.slice().reverse().find(r => r.camera === bf.camera && r.lighting === bf.lighting) || after[after.length - 1];
      B = match ? match.id : null;
    } else { A = after[0] ? after[0].id : null; B = after[1] ? after[1].id : (after[0] || {}).id || null; }
  }
  const msgBox = h("div", {});
  const viewer = h("div", { class: "col", style: { gap: "8px", flex: "1 1 auto", minWidth: 0 } });
  const side = h("div", { class: "rpanel", style: { width: "380px" } });

  function card(r, label) {
    if (!r) return h("div", { class: "compare", style: { display: "flex", alignItems: "center", justifyContent: "center", color: "var(--muted)", fontSize: "13px" } }, "컷을 골라 주세요");
    return h("div", { class: "col", style: { gap: "4px", minWidth: 0 } },
      h("div", { class: "compare" }, h("img", { src: fileUrl(id, r.file), alt: r.label }), h("div", { style: { position: "absolute", left: "10px", top: "10px" } }, aitag())),
      h("div", { class: "row small" }, h("b", {}, label), h("span", { class: "muted ellipsis" }, r.label)));
  }
  function drawViewer() {
    const ra = rs().find(r => r.id === A), rb = rs().find(r => r.id === B);
    let body;
    if (mode === "side") body = h("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" } }, card(ra, ra && ra.variant === "before" ? "도입 전" : "왼쪽"), card(rb, rb && rb.variant === "after" && ra && ra.variant === "before" ? "도입 후" : "오른쪽"));
    else {
      const wrap = h("div", { class: "compare" });
      if (ra && rb) {
        const clip = h("div", { class: "clip", style: { clipPath: `inset(0 ${100 - swipe}% 0 0)` } }, h("img", { src: fileUrl(id, ra.file), alt: ra.label }));
        const handle = h("div", { class: "handle", style: { left: swipe + "%" } });
        wrap.append(h("img", { src: fileUrl(id, rb.file), alt: rb.label }), clip, handle, h("div", { style: { position: "absolute", left: "10px", top: "10px" } }, aitag()),
          h("span", { class: "aitag", style: { position: "absolute", left: "10px", bottom: "10px" } }, ra.variant === "before" ? "도입 전" : ra.label),
          h("span", { class: "aitag", style: { position: "absolute", right: "10px", bottom: "10px" } }, rb.variant === "after" && ra.variant === "before" ? "도입 후" : rb.label));
        const onMove = e => { const r = wrap.getBoundingClientRect(); swipe = Math.max(0, Math.min(100, (e.clientX - r.left) / r.width * 100)); clip.style.clipPath = `inset(0 ${100 - swipe}% 0 0)`; handle.style.left = swipe + "%"; };
        wrap.addEventListener("pointerdown", e => { wrap.setPointerCapture(e.pointerId); onMove(e); wrap.onpointermove = onMove; });
        wrap.addEventListener("pointerup", () => { wrap.onpointermove = null; });
        wrap.style.cursor = "ew-resize";
      }
      body = h("div", { style: { maxWidth: "860px" } }, wrap);
    }
    replace(viewer,
      h("div", { class: "row" },
        h("div", { class: "seg" }, h("button", { class: mode === "side" ? "on" : "", onclick: () => { mode = "side"; drawViewer(); } }, "나란히"), h("button", { class: mode === "swipe" ? "on" : "", onclick: () => { mode = "swipe"; drawViewer(); } }, "겹쳐 밀기")),
        h("span", { class: "small muted" }, "아래 컷의 '왼쪽 · 오른쪽'으로 비교할 두 컷을 골라요"), h("span", { class: "spacer" }),
        ra && rb && ra.variant === "before" ? h("span", { class: "tag pri" }, "BV-B · 두 시점 비교로 보낼 수 있어요") : null),
      body,
      grid());
  }
  function grid() {
    const list = rs().slice().reverse();
    const cp = (job && job.cuts) || {};
    const pending = job && ["queued", "running"].includes(job.status) ? ((job.result && job.result.cuts) || []).map(c => c.join("_")).filter(k => (cp[k] ?? 0) < 100) : [];
    const cutName = k => { const [c, l, v] = k.split("_"); return `${L.camera(c)} · ${L.light(l)}${v === "before" ? " · 도입 전" : ""}`; };
    return h("div", { class: "col", style: { gap: "6px", minHeight: 0 } },
      h("div", { class: "row" }, h("b", {}, "만든 컷"), h("span", { class: "small muted" }, `· ${list.length}${pending.length ? ` · 만드는 중 ${pending.length}` : ""}`)),
      h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: "8px", overflow: "auto" } },
        pending.map(k => h("div", { class: "col", style: { gap: "4px" } },
          h("div", { class: "cut", style: { cursor: "default", display: "flex", alignItems: "center", justifyContent: "center", background: "#e9ecf1" } },
            h("div", { class: "col", style: { alignItems: "center", gap: "4px" } }, h("span", { class: "spin" }), h("span", { class: "xs muted" }, cp[k] === undefined ? "대기" : (cp[k] ? `생성 중 ${cp[k]}%` : "생성 중"))),
            h("span", { class: "lbl" }, cutName(k))))),
        list.map(r => h("div", { class: "col", style: { gap: "4px" } },
          h("div", { class: "cut" + (r.id === A || r.id === B ? " on" : ""), onclick: () => { B = r.id; drawViewer(); } },
            h("img", { src: fileUrl(id, r.file), alt: "", loading: "lazy" }), h("span", { class: "aitag" }, "AI 생성 · 개략"), h("span", { class: "lbl" }, r.label)),
          h("div", { class: "row", style: { gap: "4px" } },
            h("button", { class: "btn xs" + (r.id === A ? " soft" : ""), onclick: () => { A = r.id; drawViewer(); } }, "왼쪽"),
            h("button", { class: "btn xs" + (r.id === B ? " soft" : ""), onclick: () => { B = r.id; drawViewer(); } }, "오른쪽"),
            r.id === A || r.id === B ? h("span", { class: "xs", style: { color: "var(--pri)" } }, "비교 중") : null)))));
  }
  function combos() {
    const out = [];
    for (const c of CAMS.map(x => x[0])) if (pickCams.has(c)) for (const l of LIGHTS.map(x => x[0])) if (pickLights.has(l)) {
      out.push([c, l, "after"]);
      if (withBefore) out.push([c, l, "before"]);
    }
    return out;
  }
  const exists = c => rs().some(r => r.camera === c[0] && r.lighting === c[1] && r.variant === c[2] && r.brief_rev === (p.brief || {}).rev);
  function drawSide() {
    const list = combos();
    const fresh = list.filter(c => !exists(c));
    const running = job && ["queued", "running"].includes(job.status);
    replace(side,
      h("div", { class: "card pad col", style: { gap: "10px" } },
        h("div", { class: "card-h" }, h("h3", {}, "시점 · 조명 컷"), h("span", { class: "sub" }, `새로 만들 컷 ${fresh.length}`)),
        h("div", { class: "row", style: { flexWrap: "wrap", gap: "4px" } }, h("span", { class: "xs muted", style: { width: "30px" } }, "시점"),
          CAMS.map(([k, l]) => h("button", { class: "chip sm" + (pickCams.has(k) ? " on" : ""), onclick: () => { pickCams.has(k) ? pickCams.delete(k) : pickCams.add(k); drawSide(); drawBottom(); } }, l))),
        h("div", { class: "row", style: { flexWrap: "wrap", gap: "4px" } }, h("span", { class: "xs muted", style: { width: "30px" } }, "조명"),
          LIGHTS.map(([k, l]) => h("button", { class: "chip sm" + (pickLights.has(k) ? " on" : ""), onclick: () => { pickLights.has(k) ? pickLights.delete(k) : pickLights.add(k); drawSide(); drawBottom(); } }, l))),
        h("label", { class: "check" }, h("input", { type: "checkbox", checked: withBefore, onchange: e => { withBefore = e.target.checked; drawSide(); drawBottom(); } }), "도입 전 컷도", h("span", { class: "xs muted" }, "같은 시점 · 제품 · 가구를 뺀 모습")),
        h("div", { class: "xs muted" }, "배치 · 가구는 그대로 두고 카메라와 조명만 바꿔요"),
        list.length ? h("div", { class: "col", style: { gap: "3px" } }, list.map(c => h("div", { class: "row small" }, h("span", { class: "tag" + (exists(c) ? "" : " pri") }, exists(c) ? "있음" : "새로"),
          `${L.camera(c[0])} · ${L.light(c[1])}${c[2] === "before" ? " · 도입 전" : ""}`))) : h("div", { class: "small muted" }, "시점과 조명을 하나 이상 골라 주세요"),
        running ? h("div", { class: "row small" }, h("span", { class: "spin" }), `렌더 중 · ${job.pct}% — 끝나면 위에 추가돼요`) : null),
      h("div", { class: "card pad small muted" }, h("b", { style: { color: "var(--text)" } }, "제안서로 · "), "도입 전 / 후 2컷은 '조감도' 섹션의 두 시점 비교(BV-B)로, 조감 45° 주간 컷은 공간 전경(BV-A)으로 들어가요."));
  }
  async function generate() {
    const fresh = combos().filter(c => !exists(c));
    if (!fresh.length) { toast("이미 있는 컷이에요 — 다른 시점 · 조명을 골라 주세요"); return; }
    const r = await api.post(`/api/projects/${id}/render`, { mode: "cuts", cuts: fresh, quality: (p.input || {}).quality });
    follow(r);
  }
  function follow(j) {
    job = j; drawAll();
    if (unwatch) unwatch();
    let last = 0;
    unwatch = watchJob(j.id, async jj => {
      job = jj;
      const done = Object.values(jj.cuts || {}).filter(v => v === 100).length;
      if (done !== last) { last = done; }
      drawSide(); drawViewer(); drawBottom();
    }, async jj => {
      job = null;
      p = await load3d(id);
      if (jj.status === "done") {
        const news = rs().filter(r => r.job === jj.id);
        const bf = news.find(r => r.variant === "before");
        if (bf) { A = bf.id; const af = rs().slice().reverse().find(r => r.variant === "after" && r.camera === bf.camera && r.lighting === bf.lighting); if (af) B = af.id; }
        else if (news.length) B = news[news.length - 1].id;
        toast(`컷 ${news.length}개를 만들었어요`);
      } else if (jj.status === "failed") toast("컷을 만들지 못했어요 — " + (jj.error || ""), "err");
      drawAll();
    });
  }
  function drawBottom() {
    const fresh = combos().filter(c => !exists(c));
    const running = job && ["queued", "running"].includes(job.status);
    fr.setBottom(
      h("div", { class: "col grow", style: { gap: 0, paddingLeft: "6px" } }, h("b", {}, `시점 · 조명 컷 · 새로 만들 컷 ${fresh.length}`),
        h("span", { class: "small muted" }, fresh.length ? fresh.map(c => `${L.camera(c[0])} · ${L.light(c[1])}${c[2] === "before" ? " · 도입 전" : ""}`).join(", ") : "이미 있는 컷은 다시 만들지 않아요")),
      h("button", { class: "btn lg", onclick: () => go(link3d(id, "result")) }, "결과로"),
      h("button", { class: "btn lg primary", disabled: !fresh.length || running, onclick: generate }, icon("camera", 15), running ? "렌더 중…" : `선택한 ${fresh.length}컷 생성`));
  }
  function drawAll() {
    replace(msgBox, wmsg("배치 · 가구는 그대로 두고 카메라와 조명만 바꿔요. 도입 전 컷은 같은 시점에서 제품 · 가구를 뺀 모습이라 지금 공간과 나란히 비교할 수 있어요.", { one: true }));
    drawViewer(); drawSide(); drawBottom();
  }
  replace(fr.content, msgBox, h("div", { style: { display: "flex", gap: "12px", marginTop: "12px", flex: "1 1 auto", minHeight: 0 } }, h("div", { class: "col", style: { flex: "1 1 auto", minWidth: 0, overflow: "auto" } }, viewer), side));
  drawAll();
  if (job && job.kind === "render") follow(job);
  return { unmount: () => { if (unwatch) unwatch(); } };
}
