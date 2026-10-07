// BR2 — 3D 조감도 2/3 · AI 구성 · 렌더링 (W가 정한 구성과 이유 · 참고 사례 · Blender 6단계 진행 · 클레이 미리보기)
import { api } from "../api.js";
import { h, icon, replace, wmsg, toast, aitag, confirmBox, ro } from "../dom.js";
import { go, link3d } from "../shell.js";
import { load3d, frame3d, labels, watchJob, activeJob } from "../ui3d.js";

export async function mount(id) {
  let p = await load3d(id);
  const L = await labels();
  const fr = frame3d(p, "build", { fill: true });
  let job = await activeJob(id);
  let unwatch = null, lostMsg = null;

  const userBox = h("div", {});
  const msgBox = h("div", {});
  const decisions = h("div", { class: "card pad", style: { overflow: "auto", minHeight: 0 } });
  const pipe = h("div", { class: "card pad", style: { overflow: "auto", minHeight: 0 } });

  function drawUser() {
    const inp = p.input || {};
    const short = (inp.text || "").split(/[.!?\n]/)[0].slice(0, 60);
    replace(userBox, h("div", { class: "row", style: { justifyContent: "flex-end", gap: "6px", flexWrap: "wrap" } },
      short ? h("div", { class: "umsg" }, short) : null,
      (inp.moods || []).map(m => h("span", { class: "tag" }, L.mood(m))),
      p.linked_2d ? h("span", { class: "tag pri" }, "2D 연결") : null,
      h("span", { class: "tag" }, L.space(inp.space_type))));
  }
  function drawMsg() {
    const b = p.brief;
    const refs = p.refs || {};
    const n = (refs.images || []).length;
    const running = job && ["queued", "running"].includes(job.status);
    let text;
    if (lostMsg) text = lostMsg;
    else if (!b) text = "요구사항을 읽고 있어요. 곧 구성을 정해 알려드릴게요.";
    else text = `요구사항을 ${ro(b.understanding || "요청하신 공간")} 이해했어요. ` +(n ? `공간 제품 배치 사례 ${n}건을 참고해 ` : "") +
      `아래처럼 구성을 정했고, ` + (running ? "지금 Blender에서 렌더링하고 있습니다. 다른 작업을 해도 계속 진행되고, 끝나면 결과 화면으로 넘어가요." : (p.status === "done" ? "렌더링을 마쳤어요." : "렌더링을 기다리고 있어요."));
    replace(msgBox, wmsg(text));
  }
  function drawDecisions() {
    const b = p.brief;
    if (!b) { replace(decisions, h("div", { class: "row small muted" }, h("span", { class: "spin" }), "구성을 정하는 중…")); return; }
    const src = b.meta && b.meta.source;
    const srcText = { llm: `AI(${b.meta.model})`, replay: "AI(저장된 응답)", rules: "규칙 기반" }[src] || src;
    const lay = p.layout || {};
    const nProd = (lay.placements || []).length;
    const kinds = new Set((lay.placements || []).map(x => x.product)).size;
    const furn = b.furniture || [];
    const who = src === "rules" ? "규칙 결정" : "AI 결정";
    const tag = t => h("span", { class: "tag" + (t === "AI 결정" ? " pri" : ""), title: t === "규칙 결정" ? "모델을 쓰지 않고 규칙으로 정했어요" : null }, t === "AI 결정" ? who : t);
    const dec = (k, v, why, t = "AI 결정") => h("div", { class: "decision" }, h("div", { class: "dk" }, k), h("div", { class: "dv" }, v), tag(t), why ? h("div", { class: "why" }, "근거 · " + why) : null);
    const refs = p.refs || {};
    replace(decisions,
      h("div", { class: "card-h" }, h("h3", {}, "W가 정한 구성"), h("span", { class: "sub" }, `${srcText}${p.linked_2d ? " · 제품 위치는 2D 기준" : ""}`)),
      h("div", { class: "xs muted", style: { margin: "4px 0 6px" } }, "요구사항과 참고 사례로 정한 내용이에요. 항목마다 이유를 함께 적었어요." + (src === "rules" && b.meta.reason ? ` (모델을 쓰지 않음 — ${b.meta.reason})` : "")),
      dec("콘셉트", L.concept(b.concept), b.concept_reason),
      dec("마감", `${L.floor(b.floor)} · ${L.wall(b.wall)} · ${L.accent(b.accent)}`, b.finish_reason),
      dec("조명", `${L.light(b.lighting)} · ${b.light_k}K 라인 조명`, b.lighting_reason),
      h("div", { class: "decision" }, h("div", { class: "dk" }, "가구"), h("div", { class: "dv" }, `${furn.length}종 자동 선정 · 배치`), tag("AI 결정"),
        h("div", { class: "why row", style: { flexWrap: "wrap", gap: "4px" } }, furn.map(f => h("span", { class: "tag", title: f.reason || "" }, `${L.furn(f.type)}${f.count > 1 ? " ×" + f.count : ""}`)))),
      dec("제품 위치", p.linked_2d ? `2D 배치 따름 · ${kinds}종 ${nProd}대` : (nProd ? `룰 권장 수량으로 배치 · ${kinds}종 ${nProd}대` : "배치 계산 중"), p.linked_2d ? "2D 조감도 연결됨 — 제품 위치 · 대수는 바꾸지 않아요" : "배치 룰(F2)로 대수 · 위치를 정했어요", p.linked_2d ? "2D 기준" : "룰"),
      h("div", { class: "decision" }, h("div", { class: "dk" }, "참고 사례"), h("div", { class: "dv" }, refs.available ? `${(refs.images || []).length}건${refs.level ? " · " + refs.level : ""}` : "없음"), tag("AI 결정"),
        h("div", { class: "why" }, refs.available ? (refs.note || "공간 제품 배치 이미지 DB에서 유사한 순") : (refs.note || "winmate-kb 연결 시 찾아요"),
          (refs.images || []).map(im => h("div", { class: "refimg" },
            h("div", { class: "ph" }, h("img", { src: im.url, alt: im.alt || "", loading: "lazy", referrerpolicy: "no-referrer", onerror: e => { e.target.style.display = "none"; } })),
            h("div", { style: { minWidth: 0 } }, h("div", { class: "row" }, h("span", { class: "tag" }, im.caption_rule), h("span", { class: "xs muted" }, `등급 ${im.grade}`)),
              h("a", { class: "xs ellipsis", href: im.page_url, target: "_blank", rel: "noopener", style: { display: "block", maxWidth: "380px" } }, im.title || im.page_url)))))),
      h("div", { class: "xs muted", style: { marginTop: "8px" } }, "구성은 AI가 정해요. 방향이 다르면 아래에 한 줄로 알려주세요."));
  }
  function drawPipe() {
    const j = job;
    if (!j) {
      const failed = p.status === "building";
      const last = (p.renders || []).filter(r => r.variant === "after").slice(-1)[0];
      replace(pipe, h("div", { class: "col", style: { gap: "10px" } },
        h("div", { class: "card-h" }, h("h3", {}, "Blender 파이프라인")),
        h("div", { class: "small muted" }, failed ? "렌더 작업이 끝나지 않은 채 멈췄어요 — 서버를 다시 켰다면 진행 중이던 작업이 사라져요." : (p.renders || []).length ? "진행 중인 렌더가 없어요. 마지막 렌더예요." : "아직 렌더를 시작하지 않았어요."),
        last ? h("div", { class: "render", style: { aspectRatio: "16 / 9", maxWidth: "560px" } }, h("img", { src: `/files/${id}/${last.file}`, alt: last.label }), aitag(),
          h("span", { class: "aitag cap", style: { left: "auto", right: "12px" } }, last.label)) : null,
        h("div", { class: "row" },
          h("button", { class: "btn primary", onclick: () => restart("full") }, icon("cube", 14), (p.renders || []).length ? "처음부터 다시 만들기" : "3D 조감도 만들기"),
          (p.renders || []).length ? h("button", { class: "btn", onclick: () => go(link3d(id, "result")) }, "결과 보기") : null)));
      drawBottom();
      return;
    }
    const doneSteps = j.steps.filter(s => s.status === "done" || s.status === "skip").length;
    const cuts = (j.result && j.result.cuts) || [];
    const cp = j.cuts || {};
    const curCut = Object.keys(cp).find(k => cp[k] < 100);
    const cutName = k => { const [c, l, v] = k.split("_"); return `${L.camera(c)} · ${L.light(l)}${v === "before" ? " · 도입 전" : ""}`; };
    const stIcon = s => s.status === "done" ? "✓" : s.status === "skip" ? "–" : s.status === "run" ? h("span", { class: "spin", style: { width: "12px", height: "12px" } }) : "";
    const statusText = { queued: "대기 중", running: "렌더링", done: "완료", failed: "실패", cancelled: "중지됨", lost: "사라짐" }[j.status] || j.status;
    replace(pipe,
      h("div", { class: "card-h" }, h("h3", {}, "Blender 파이프라인"), h("span", { class: "spacer" }),
        h("span", { class: "b", style: { color: "var(--pri)" } }, statusText), h("span", { class: "num b" }, ` ${j.pct}%`)),
      h("div", { class: "pbar", style: { margin: "8px 0 4px" } }, h("i", { style: { width: j.pct + "%" } })),
      h("div", { class: "xs muted" }, `6단계 중 ${doneSteps}단계 완료` + (curCut ? ` · ${cutName(curCut)} ${cp[curCut] ? (j.estimated ? "약 " : "") + cp[curCut] + "%" : "렌더 중"}` : "") + (j.estimated ? " · 진행률은 시간으로 어림" : "") + " · 중지해도 1–4단계 구성은 저장돼요"),
      j.error ? h("div", { class: "callout", style: { marginTop: "8px" } }, j.error) : null,
      h("div", { class: "steps6", style: { marginTop: "6px" } }, j.steps.map(s => h("div", { class: "s6 " + s.status },
        h("span", { class: "ic6" }, stIcon(s) || s.no),
        h("div", { style: { minWidth: 0 } }, h("div", { class: "nm" }, s.name), h("div", { class: "nt" }, s.note || "")),
        h("span", { class: "st" }, { done: "완료", run: "진행 중", skip: "건너뜀", wait: "대기" }[s.status] || s.status)))),
      h("div", { style: { display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: "10px", marginTop: "10px" } },
        h("div", { class: "render", style: { aspectRatio: "16 / 9" } },
          j.preview ? h("img", { src: j.preview, alt: "클레이 미리보기" }) : h("div", { style: { position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", color: "#596170", fontSize: "12px" } }, "미리보기 준비 중"),
          aitag(), h("span", { class: "tag cap", style: { position: "absolute", left: "12px", bottom: "10px", top: "auto", right: "auto" } }, "클레이 렌더 · 재질 적용 전")),
        h("div", { class: "col", style: { gap: "6px" } },
          h("b", { class: "small" }, `컷 ${cuts.length} · 배치 · 가구는 그대로`),
          cuts.map((c, i) => { const k = c.join("_"); const pc = cp[k]; return h("div", { class: "row small" }, h("span", { class: "wno info" }, i + 1), h("span", { class: "grow ellipsis" }, cutName(k)),
            h("span", { class: "xs " + (pc === 100 ? "" : "muted") }, pc === undefined ? "대기" : pc === 100 ? "완료" : pc ? `${j.estimated ? "약 " : ""}${pc}%` : "렌더 중")); }))));
    drawBottom();
  }
  async function refreshProject() { p = await load3d(id); drawUser(); drawMsg(); drawDecisions(); }
  function follow(j) {
    job = j;
    if (unwatch) unwatch();
    let lastStep = -1;
    unwatch = watchJob(j.id, async jj => {
      job = jj;
      const n = jj.steps.filter(s => s.status === "done" || s.status === "skip").length;
      if (n !== lastStep) { lastStep = n; await refreshProject(); }
      drawPipe();
    }, async jj => {
      job = jj;
      await refreshProject();
      drawPipe();
      if (jj.status === "done") { toast("3D 조감도가 완성됐어요"); setTimeout(() => { if (location.hash === link3d(id, "build")) go(link3d(id, "result")); }, 1200); }
      else if (jj.status === "failed") toast("렌더가 실패했어요 — 오류 내용을 확인해 주세요", "err");
      else if (jj.status === "lost") { lostMsg = jj.error; job = null; drawMsg(); drawPipe(); }
    });
  }
  async function restart(mode, text) {
    const r = await api.post(`/api/projects/${id}/render`, mode === "request" ? { mode, text, quality: (p.input || {}).quality } : { mode, quality: (p.input || {}).quality });
    lostMsg = null;
    follow(r);
  }
  async function cancel() {
    if (!job) return;
    await api.post(`/api/jobs/${job.id}/cancel`);
    toast("중지를 요청했어요");
  }

  const req = h("input", { placeholder: "예: 더 밝고 미니멀하게, 플랜터는 빼고", "aria-label": "방향 바꾸기" });
  const composer = h("div", { class: "composer" }, h("span", { class: "label" }, "방향 바꾸기"), req, h("button", { class: "send", "aria-label": "보내기", onclick: () => sendReq() }, icon("send", 15)));
  req.addEventListener("input", () => composer.classList.toggle("ready", !!req.value.trim()));
  req.addEventListener("keydown", e => { if (e.key === "Enter" && !e.isComposing) sendReq(); });
  async function sendReq() {
    const text = req.value.trim();
    if (!text) return;
    if (job && ["queued", "running"].includes(job.status)) {
      if (!await confirmBox("방향 바꾸기", "지금 렌더를 멈추고 요청을 반영해 다시 만들까요? 배치 · 가구는 그대로 두고 요청한 항목만 바꿔요.", "멈추고 다시 만들기")) return;
      await api.post(`/api/jobs/${job.id}/cancel`);
      for (let i = 0; i < 40; i++) { const jj = await api.get(`/api/jobs/${job.id}`, { quiet: true }).catch(() => null); if (!jj || !["queued", "running"].includes(jj.status)) break; await new Promise(r => setTimeout(r, 500)); }
    }
    req.value = ""; composer.classList.remove("ready");
    await restart(p.brief ? "request" : "full", text);
  }
  function drawBottom() {
    const running = job && ["queued", "running"].includes(job.status);
    fr.setBottom(composer,
      h("button", { class: "btn lg", onclick: () => go("#/") }, "작업 목록으로"),
      h("button", { class: "btn lg", disabled: !running, onclick: cancel }, icon("stop", 14), "중지"),
      h("button", { class: "btn lg primary", disabled: !(p.renders || []).length, onclick: () => go(link3d(id, "result")) }, "결과 보기", icon("arrowR")));
  }

  replace(fr.content,
    h("div", { class: "col", style: { gap: "10px", flex: "0 0 auto" } }, userBox, msgBox),
    h("div", { style: { display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1.05fr)", gap: "12px", marginTop: "12px", flex: "1 1 auto", minHeight: 0 } }, decisions, pipe));
  drawUser(); drawMsg(); drawDecisions(); drawPipe(); drawBottom();
  if (job) follow(job);
  else if (p.last_job && p.status === "building") {
    const jj = await api.get(`/api/jobs/${p.last_job}`, { quiet: true }).catch(() => null);
    if (jj && ["queued", "running"].includes(jj.status)) follow(jj);
  }
  return { unmount: () => { if (unwatch) unwatch(); } };
}
