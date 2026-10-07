// BP1D — 도면 인식 확인 (I2T 로 벽 · 창 · 문 · 기둥 · 콘센트를 읽고, 확인이 필요한 곳만 사용자가 정한다)
import { api } from "../api.js";
import { h, icon, replace, fmt, wmsg, pyeong, toast, resizeImage, pickFiles } from "../dom.js";
import { go, link2d, getEnv } from "../shell.js";
import { Doc2D } from "../state.js";
import { PlanView } from "../plan.js";
import { frame2d, numInput, unitField } from "../ui2d.js";

export async function mount(id) {
  const doc = await Doc2D.load(id);
  const env = await getEnv();
  const { fr, off } = frame2d(doc, "space", { fill: true });
  const st = { file: null, img: null, busy: false, res: null, overlay: false, confidential: env ? env.upload_default_confidential : true, answers: {}, space: null };

  const planBox = h("div", { class: "planbox", style: { flex: "1 1 auto", minHeight: "0" } });
  const pv = new PlanView(planBox, { mode: "recog", editable: false, layers: { dims: true, grid: true, labels: true } });
  const left = h("div", { class: "col", style: { flex: "1 1 auto", minWidth: 0, gap: "8px" } });
  const right = h("div", { class: "rpanel", style: { width: "380px" } });

  async function upload() {
    const [f] = await pickFiles("image/*,application/pdf");
    if (!f) return;
    st.file = { name: f.name, size: f.size, type: f.type };
    st.img = await resizeImage(f, 2048, 0.9);
    st.res = null;
    draw();
    recognize();
  }
  async function recognize() {
    if (!st.img) return;
    st.busy = true; draw();
    try {
      st.res = await api.post("/api/2d/plan", { image: st.img.url, confidential: st.confidential });
      if (st.res.ok) { st.space = JSON.parse(JSON.stringify(st.res.space)); st.answers = {}; }
    } finally { st.busy = false; draw(); }
  }
  function flags() {
    const out = [];
    const sp = st.space;
    if (!sp || !st.res) return out;
    (st.res.uncertain || []).forEach((u, i) => {
      const o = (sp.openings || []).find(o => (u.item || "").includes(o.label || "@@")) || null;
      let x = sp.width / 2, y = sp.depth / 2;
      if (o) { const mid = o.start + o.length / 2; [x, y] = o.wall === "front" ? [mid, 400] : o.wall === "back" ? [mid, sp.depth - 400] : o.wall === "left" ? [400, mid] : [sp.width - 400, mid]; }
      else { x = sp.width * (0.25 + 0.2 * i); y = sp.depth * 0.5; }
      out.push({ x, y, no: i + 1, text: st.answers[i] ? null : "확인 필요" });
    });
    return out;
  }
  function draw() {
    const sp = st.space;
    pv.setOpt({ bg: st.overlay && st.img && !st.img.pdf ? { url: st.img.url, opacity: 0.4 } : null });
    if (sp) pv.set({ project: { space: { ...sp, name: doc.p.space.name || "공간" } }, flags: flags() });
    const fileLine = st.file ? h("div", { class: "row" }, icon("doc", 15), h("b", { class: "small" }, st.file.name), h("span", { class: "xs muted" }, `${fmt(st.file.size / 1048576, 1)} MB`)) : null;
    if (!st.img) {
      replace(left, h("div", { class: "drop", style: { flex: "1 1 auto", aspectRatio: "auto" }, onclick: upload,
        ondragover: e => { e.preventDefault(); e.currentTarget.classList.add("over"); }, ondragleave: e => e.currentTarget.classList.remove("over"),
        ondrop: async e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) { st.file = { name: f.name, size: f.size, type: f.type }; st.img = await resizeImage(f, 2048, 0.9); draw(); recognize(); } } },
        icon("upload", 28, 1.6), h("b", { style: { fontSize: "15px" } }, "도면 파일을 끌어 놓거나 눌러서 고르세요"), h("span", {}, "이미지(PNG · JPG) 또는 PDF · DWG 는 PDF/이미지로 내보내 올려 주세요")));
    } else {
      replace(left,
        h("div", { class: "row" }, fileLine, h("span", { class: "spacer" }),
          sp ? h("span", { class: "small muted" }, `${st.res.scale_text ? "축척 " + st.res.scale_text + " 감지 · " : ""}면적 ${fmt(sp.width * sp.depth / 1e6, 0)} ㎡ (약 ${pyeong(sp.width * sp.depth / 1e6)}평)`) : null,
          sp && !st.img.pdf ? h("button", { class: "toggle" + (st.overlay ? " on" : ""), onclick: () => { st.overlay = !st.overlay; draw(); } }, "원본 겹쳐 보기") : null),
        sp ? planBox : h("div", { class: "planbox", style: { flex: "1 1 auto", display: "flex", alignItems: "center", justifyContent: "center", background: "#fff" } },
          st.img.pdf ? h("div", { class: "muted" }, icon("doc", 28), " PDF 도면") : h("img", { src: st.img.url, alt: "올린 도면", style: { maxWidth: "100%", maxHeight: "100%", objectFit: "contain" } }),
          st.busy ? h("div", { class: "busy" }, h("span", { class: "spin" }), "도면을 읽고 있어요…") : null));
    }
    drawRight();
  }
  function drawRight() {
    const r = st.res, sp = st.space;
    const confBox = h("label", { class: "check small" }, h("input", { type: "checkbox", checked: st.confidential, onchange: e => { st.confidential = e.target.checked; drawRight(); } }),
      "기밀 도면 — 외부 모델로 보내지 않아요");
    const i2t = env && env.i2t;
    const head = h("div", { class: "card pad col", style: { gap: "8px" } },
      h("div", { class: "card-h" }, h("h3", {}, "도면 읽기"), h("span", { class: "sub" }, i2t ? `${i2t.provider} · ${i2t.model}` : "")),
      confBox,
      st.confidential && i2t && !i2t.reason ? h("div", { class: "xs muted" }, "기밀 표시면 I2T_ALLOW_CONFIDENTIAL=true(사내 모델)일 때만 읽어요.") : null,
      i2t && i2t.reason ? h("div", { class: "callout" }, `이미지 모델을 쓸 수 없어요 — ${i2t.reason}`) : null,
      h("div", { class: "row" },
        h("button", { class: "btn sm", onclick: upload }, icon("upload", 13), st.img ? "다른 도면 올리기" : "도면 올리기"),
        st.img ? h("button", { class: "btn sm", disabled: st.busy, onclick: recognize }, icon("refresh", 13), "다시 인식") : null));
    if (!r) { replace(right, head, h("div", { class: "card pad small muted" }, "도면을 올리면 벽 · 창 · 문 · 기둥 · 콘센트를 읽어 와요. 읽은 값은 다음 단계의 제품 위치 · 수량 · 동선 계산 기준이 돼요. 지어내지 않고, 못 읽은 값은 '확인 필요'로 남겨요.")); return; }
    if (!r.ok) {
      replace(right, head, h("div", { class: "card pad col", style: { gap: "10px" } },
        h("b", {}, "도면을 읽지 못했어요"), h("div", { class: "small muted" }, r.reason || ""),
        h("div", { class: "small" }, "치수를 직접 넣어도 똑같이 진행돼요."),
        h("button", { class: "btn soft", onclick: () => go(link2d(id, "space")) }, "치수 직접 입력으로")));
      return;
    }
    const ops = sp.openings || [];
    const cnt = k => ops.filter(o => o.kind === k).length;
    const uncertain = r.uncertain || [];
    replace(right, head,
      h("div", { class: "card pad" }, h("div", { class: "card-h" }, h("h3", {}, "인식한 요소"), h("span", { class: "sub" }, `${uncertain.length ? "확인 " + uncertain.length : "확인할 것 없음"} · 신뢰도 ${r.confidence != null ? Math.round(r.confidence * 100) + "%" : "–"}`)),
        h("div", { class: "kv", style: { marginTop: "10px" } },
          h("div", { class: "k" }, "벽"), h("div", {}, "외벽 4면"),
          h("div", { class: "k" }, "창"), h("div", {}, cnt("window") ? `유리창 ${cnt("window")}구간` : "없음"),
          h("div", { class: "k" }, "문"), h("div", {}, `출입구 ${cnt("entrance")} · 문 ${cnt("door")}`),
          h("div", { class: "k" }, "기둥"), h("div", {}, (sp.pillars || []).length ? `${sp.pillars.length}개 · ${fmt(sp.pillars[0].w)} × ${fmt(sp.pillars[0].d)} mm` : "없음"),
          h("div", { class: "k" }, "콘센트"), h("div", {}, (sp.outlets || []).length ? `${sp.outlets.length}개` : "못 읽음 — 다음 화면에서 찍어 주세요"),
          h("div", { class: "k" }, "층고"), h("div", {}, r.height_read ? `${fmt(sp.height)} mm` : "도면에 없음 — 확인 필요"))),
      uncertain.map((u, i) => h("div", { class: "card pad col", style: { gap: "8px" } },
        h("div", { class: "row" }, h("span", { class: "wno" }, i + 1), h("b", { class: "small" }, u.question || u.item)),
        u.item && u.question ? h("div", { class: "xs muted" }, u.item) : null,
        h("div", { class: "row", style: { flexWrap: "wrap", gap: "6px" } }, (u.options && u.options.length ? u.options : ["맞아요", "다르게 입력할게요"]).map(op =>
          h("button", { class: "chip sm" + (st.answers[i] === op ? " on" : ""), onclick: () => { st.answers[i] = op; applyAnswer(u, op); draw(); } }, op))))),
      h("div", { class: "card pad col", style: { gap: "8px" } },
        h("div", { class: "card-h" }, h("h3", {}, "치수 보정"), h("span", { class: "sub" }, r.scale_text ? `도면 표기 축척 ${r.scale_text}` : "축척 표기 없음")),
        h("div", { class: "row" },
          unitField("가로", numInput(sp.width, v => { st.space.width = v; draw(); }, { sm: true, min: 1000 })),
          unitField("세로", numInput(sp.depth, v => { st.space.depth = v; draw(); }, { sm: true, min: 1000 })),
          unitField("층고", numInput(sp.height, v => { st.space.height = v; draw(); }, { sm: true, min: 2000 })))));
  }
  function applyAnswer(u, op) {
    const sp = st.space;
    const door = (sp.openings || []).find(o => o.kind === "door" && (u.item || "").includes(o.label || "@@")) || (sp.openings || []).find(o => o.kind === "door");
    if (door && /문/.test(u.item + u.question)) {
      if (/비상/.test(op)) door.door_type = "emergency";
      else if (/백오피스|직원/.test(op)) door.door_type = "backoffice";
      else if (/벽/.test(op)) door.door_type = "wall";
    }
  }

  replace(fr.content,
    wmsg("도면에서 공간 구조를 읽어요. 여기서 확정한 치수가 다음 단계의 제품 위치 · 수량 · 동선 계산 기준이 돼요. 벽 · 창 · 문 · 기둥 · 콘센트가 맞는지 보시고, 확인이 필요한 곳을 정해 주세요."),
    h("div", { style: { display: "flex", gap: "12px", marginTop: "14px", flex: "1 1 auto", minHeight: 0 } }, left, right));
  fr.setBottom(
    h("div", { class: "col grow", style: { gap: 0, paddingLeft: "6px" } }, h("b", {}, "공간 인식 확인 · 1 / 4"), h("span", { class: "small muted" }, "읽은 구조는 다음 화면에서 언제든 고칠 수 있어요")),
    h("button", { class: "btn lg", onclick: () => go(link2d(id, "space")) }, "치수 직접 입력"),
    h("button", { class: "btn lg primary", onclick: async () => {
      if (!st.space) { toast("먼저 도면을 올려 주세요", "err"); return; }
      const keep = doc.p.space;
      doc.commit(p => {
        p.space = { ...st.space, name: keep.name, space_type: keep.space_type, source: "plan_upload", recog_answers: st.answers };
        p.step = "products"; p.space_changed = true;
      }, { validate: false });
      await doc.flush();
      go(link2d(id, "products"));
    } }, "이 구조로 계속", icon("arrowR")));
  draw();
  return { beforeLeave: () => doc.flush(), unmount: () => { off(); pv.destroy(); } };
}
