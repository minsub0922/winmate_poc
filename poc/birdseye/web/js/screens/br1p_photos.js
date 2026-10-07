// BR1P — 3D 조감도 · 현장 사진으로 (사진에서 구조 · 분위기를 읽음 · 치수는 추정값 · 못 읽은 것은 지어내지 않음)
import { api } from "../api.js";
import { h, icon, replace, wmsg, toast, resizeImage, pickFiles, s } from "../dom.js";
import { go, link2d, link3d, getEnv } from "../shell.js";
import { load3d, patch3d, frame3d, labels } from "../ui3d.js";

export async function mount(id) {
  let p = await load3d(id);
  const L = await labels();
  const env = await getEnv();
  const fr = frame3d(p, "photos", { fill: true });
  const st = {
    photos: (p.input.photos || []).map(x => ({ ...x, url: null, status: x.ok === false ? "issue" : (x.ok ? "ok" : "saved") })),
    read: p.input.photo_read || null, busy: false, err: null,
    confidential: env ? env.upload_default_confidential : true, extra: p.input.photo_text || "",
  };

  const guide = h("div", { class: "card pad col", style: { gap: "8px" } });
  const grid = h("div", {});
  const known = h("div", { class: "card pad col", style: { gap: "8px" } });

  function guideSvg() {
    const n = st.photos.length;
    const pos = [[16, 16, 45], [144, 16, 135], [144, 104, 225], [16, 104, 315]];
    return s("svg", { viewBox: "0 0 160 120", width: "100%", height: "120" },
      s("rect", { x: 10, y: 10, width: 140, height: 100, fill: "#fff", stroke: "#8a91a0", "stroke-width": 2 }),
      s("rect", { x: 40, y: 8, width: 80, height: 5, fill: "#1428a0" }),
      s("text", { x: 80, y: 24, "font-size": 8, "text-anchor": "middle", fill: "#596170" }, "주요 벽"),
      pos.map(([x, y, a], i) => s("g", { transform: `translate(${x},${y}) rotate(${a})`, opacity: i < n ? 1 : 0.35 },
        s("path", { d: "M0,0 L22,-9 L22,9 Z", fill: "rgba(20,40,160,.15)", stroke: "#1428a0", "stroke-width": 1 }),
        s("circle", { cx: 0, cy: 0, r: 6, fill: i < n ? "#1428a0" : "#fff", stroke: "#1428a0" }),
        s("text", { x: 0, y: 3, "font-size": 7, "text-anchor": "middle", fill: i < n ? "#fff" : "#1428a0", "font-weight": 800, transform: `rotate(${-a})` }, i + 1))));
  }
  function drawGuide() {
    const views = st.photos.map(x => x.view || "").join(" ");
    const noCeil = st.photos.length && !/천장/.test(views);
    replace(guide,
      h("div", { class: "card-h" }, h("h3", {}, "촬영 가이드"), h("span", { class: "sub" }, "위에서 본 모습")),
      guideSvg(),
      ["모서리에 서서 맞은편 벽까지 담기", "가로로 넓게, 천장도 한 장", "창이 있는 벽은 역광 피하기", "밝을 때 · 사람이 적을 때 찍기"].map(t => h("div", { class: "note" }, t)),
      h("div", { class: "row small" }, h("b", {}, "찍은 방향"), h("span", { class: "num b" }, `${Math.min(4, st.photos.length)} / 4`), noCeil ? h("span", { class: "xs muted" }, "· 천장 없음") : null),
      h("div", { class: "xs muted" }, "휴대폰 QR 업로드는 이 PoC 에선 빠졌어요 — PC 에서 끌어 놓아 주세요."));
  }
  async function addFiles(files) {
    const imgs = files.filter(f => /^image\//.test(f.type)).slice(0, 6 - st.photos.length);
    if (!imgs.length) return;
    for (const f of imgs) {
      const r = await resizeImage(f, 1536, 0.86);
      const t = await thumbOf(r.url);
      st.photos.push({ name: f.name, url: r.url, thumb: t, status: "new" });
    }
    drawAll();
    readPhotos();
  }
  async function thumbOf(url) {
    const im = await new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = url; });
    const k = 320 / Math.max(im.naturalWidth, im.naturalHeight);
    const c = h("canvas", { width: Math.round(im.naturalWidth * k), height: Math.round(im.naturalHeight * k) });
    c.getContext("2d").drawImage(im, 0, 0, c.width, c.height);
    return c.toDataURL("image/jpeg", 0.72);
  }
  async function readPhotos() {
    const withData = st.photos.filter(x => x.url);
    if (!withData.length || st.busy) return;
    st.busy = true; st.err = null;
    for (const x of st.photos) if (x.url && x.status === "new") x.status = "reading";
    drawAll();
    try {
      const res = await api.post("/api/3d/photos", { project_id: id, images: withData.map(x => x.url), text: st.extra, confidential: st.confidential });
      if (res.ok) {
        (res.photos || []).forEach(ph => { const x = withData[ph.index]; if (x) { x.view = ph.view || x.view; x.ok = ph.ok; x.issue = ph.issue; x.status = ph.ok ? "ok" : "issue"; } });
        for (const x of withData) if (x.status === "reading") x.status = "ok";
        st.read = res.project ? res.project.input.photo_read : null;
        p = res.project || p;
      } else {
        st.err = res.reason || "사진을 읽지 못했어요";
        for (const x of withData) if (x.status === "reading") x.status = "unread";
      }
      await savePhotos();
    } finally { st.busy = false; drawAll(); }
  }
  async function savePhotos() {
    p = await patch3d(id, { input: { photos: st.photos.map(x => ({ name: x.name, thumb: x.thumb, view: x.view || null, ok: x.status === "kept" ? true : (x.ok ?? null), issue: x.issue || null })), photo_text: st.extra } });
  }
  function drawGrid() {
    const label = x => ({ ok: [x.view || "읽음", ""], issue: [x.view || "확인 필요", x.issue || "다시 찍으면 좋아요"], reading: ["읽는 중", ""], new: ["대기", ""], unread: ["못 읽음", ""], saved: [x.view || "저장된 사진", "다시 읽으려면 원본을 다시 올려 주세요"], kept: [x.view || "그대로 사용", x.issue || ""] }[x.status] || ["", ""]);
    const nOk = st.photos.filter(x => x.status === "ok" || x.status === "kept").length, nIss = st.photos.filter(x => x.status === "issue").length, nRead = st.photos.filter(x => x.status === "reading").length;
    replace(grid,
      h("div", { class: "row", style: { marginBottom: "8px" } }, h("b", {}, `사진 ${st.photos.length}장`),
        h("span", { class: "small muted" }, [nOk ? `읽음 ${nOk}` : null, nIss ? `확인 필요 ${nIss}` : null, nRead ? `읽는 중 ${nRead}` : null].filter(Boolean).join(" · ")),
        h("span", { class: "spacer" }),
        h("label", { class: "check small" }, h("input", { type: "checkbox", checked: st.confidential, onchange: e => { st.confidential = e.target.checked; } }), "기밀 사진(외부 모델로 안 보냄)"),
        h("button", { class: "btn sm", disabled: st.busy || !st.photos.some(x => x.url), onclick: readPhotos }, icon("refresh", 13), "다시 읽기")),
      st.err ? h("div", { class: "callout", style: { marginBottom: "8px" } }, h("b", {}, "사진을 읽지 못했어요 — "), st.err, h("div", { class: "xs", style: { marginTop: "4px" } }, "지어내지 않고 넘어가요. 요구사항 · 대략 규모만으로도 3D 조감도를 만들 수 있어요.")) : null,
      h("div", { style: { display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "10px" } },
        st.photos.map((x, i) => {
          const [t1, t2] = label(x);
          return h("div", { class: "col", style: { gap: "4px" } },
            h("div", { class: "photo" }, x.thumb || x.url ? h("img", { src: x.url || x.thumb, alt: x.name || "" }) : null,
              h("span", { class: "wno pno" + (x.status === "issue" ? "" : " info") }, i + 1),
              h("div", { class: "pst" }, h("b", {}, t1), t2 ? h("div", { class: "xs" }, t2) : null,
                x.status === "reading" ? h("span", { class: "spin", style: { position: "absolute", right: "8px", bottom: "8px" } }) : null)),
            x.status === "issue" ? h("div", { class: "row", style: { gap: "4px" } },
              h("button", { class: "btn xs", onclick: async () => { const [f] = await pickFiles("image/*"); if (!f) return; const r = await resizeImage(f, 1536, 0.86); x.url = r.url; x.thumb = await thumbOf(r.url); x.status = "new"; x.name = f.name; drawAll(); readPhotos(); } }, "다시 찍기"),
              h("button", { class: "btn xs ghost", onclick: async () => { x.status = "kept"; await savePhotos(); drawAll(); } }, "그대로 사용")) : null,
            h("button", { class: "btn xs ghost", style: { alignSelf: "flex-start" }, onclick: async () => { st.photos.splice(i, 1); await savePhotos(); drawAll(); } }, "빼기"));
        }),
        st.photos.length < 6 ? h("div", { class: "drop", onclick: async () => addFiles(await pickFiles("image/*", true)),
          ondragover: e => { e.preventDefault(); e.currentTarget.classList.add("over"); }, ondragleave: e => e.currentTarget.classList.remove("over"),
          ondrop: e => { e.preventDefault(); e.currentTarget.classList.remove("over"); addFiles([...e.dataTransfer.files]); } },
          icon("upload", 22, 1.6), h("b", {}, "사진 끌어 놓기"), h("span", { class: "xs" }, "JPG · PNG · 최대 6장")) : null),
      h("div", { class: "xs muted", style: { marginTop: "8px" } }, "긴 변 1536 px로 줄여 보내요 · 천장 사진이 없으면 층고는 추정값으로 진행해도 괜찮아요."));
  }
  function drawKnown() {
    const r = st.read;
    const est = (r && r.estimate) || {};
    replace(known,
      h("div", { class: "card-h" }, h("h3", {}, "지금까지 파악한 공간"), h("span", { class: "tag" }, "추정값")),
      r ? h("div", { class: "xs muted" }, r.basis || "") : h("div", { class: "small muted" }, "사진을 올리면 구조와 분위기를 읽어 여기에 적어요."),
      r ? h("div", { class: "col", style: { gap: "8px" } },
        h("div", {}, h("div", { class: "flabel" }, "구조"), h("div", { class: "row", style: { flexWrap: "wrap", gap: "4px", marginTop: "4px" } }, (r.structure || []).map(t => h("span", { class: "tag" }, t)))),
        h("div", {}, h("div", { class: "flabel" }, "분위기"), h("div", { class: "row", style: { flexWrap: "wrap", gap: "4px", marginTop: "4px" } }, (r.mood || []).map(t => h("span", { class: "tag" }, t)))),
        r.finishes && Object.keys(r.finishes).length ? h("div", { class: "xs muted" }, "마감 후보 · " + [r.finishes.floor && L.floor(r.finishes.floor), r.finishes.wall && L.wall(r.finishes.wall), r.finishes.accent && L.accent(r.finishes.accent)].filter(Boolean).join(" · ")) : null,
        est.width_mm_est ? h("div", { class: "xs muted" }, `추정 크기 ${(est.width_mm_est / 1000).toFixed(1)} × ${(est.depth_mm_est / 1000).toFixed(1)} m${est.height_mm_est ? ` · 층고 ${(est.height_mm_est / 1000).toFixed(1)} m` : ""}`) : null,
        (r.needs || []).length ? h("div", { class: "callout" }, (r.needs || []).map(t => h("div", {}, "· " + t))) : null) : null,
      h("div", { class: "xs muted" }, "추정값 — 3D 조감도는 개략 이미지라 충분해요. 정확한 치수가 필요하면 2D 조감도로."));
  }
  function drawAll() { drawGuide(); drawGrid(); drawKnown(); }

  const extra = h("input", { placeholder: "사진에 없는 정보 (예: 차분한 톤, 상황판은 더 크게)", "aria-label": "사진에 없는 정보", value: st.extra, oninput: e => { st.extra = e.target.value; } });
  replace(fr.content,
    (p.input.text ? h("div", { class: "row", style: { justifyContent: "flex-end", marginBottom: "10px" } }, h("div", { class: "umsg" }, p.input.text)) : null),
    wmsg(st.photos.length || st.read
      ? `사진${st.photos.length ? " " + st.photos.length + "장" : ""}에서 ${L.space(p.input.space_type)}의 구조와 분위기를 읽어요. 3D 조감도는 개략 이미지라 크기는 추정값이면 충분합니다.`
      : "현장 사진을 올려 주세요. 구조(넓이 · 층고 · 창 · 문)와 분위기(조명 · 바닥 · 가구 톤)를 읽어 3D 구성에 써요. 크기는 추정값이에요."),
    h("div", { style: { display: "grid", gridTemplateColumns: "260px minmax(0, 1fr) 320px", gap: "12px", marginTop: "12px", flex: "1 1 auto", minHeight: 0 } },
      h("div", { style: { overflow: "auto" } }, guide), h("div", { class: "card pad", style: { overflow: "auto" } }, grid), h("div", { style: { overflow: "auto" } }, known)));
  fr.setBottom(
    h("div", { class: "col", style: { gap: 0, paddingLeft: "6px", minWidth: "200px" } }, h("b", {}, `현장 사진 · ${st.photos.length}장`), h("span", { class: "xs muted" }, "구조와 분위기를 읽어요 · 1 / 3")),
    h("div", { class: "composer" }, extra),
    h("button", { class: "btn lg ghost", onclick: async () => { const n = await api.post("/api/projects", { kind: "2d" }); go(link2d(n.id, "space")); } }, "정확한 배치는 2D로"),
    h("button", { class: "btn lg", onclick: async () => { await patch3d(id, { input: { photo_text: st.extra } }); go(link3d(id, "brief")); } }, "이전"),
    h("button", { class: "btn lg primary", disabled: !(env && env.blender && env.blender.kind), onclick: async () => {
      await patch3d(id, { input: { photo_text: st.extra } });
      const r = await api.post(`/api/projects/${id}/render`, { mode: "full", quality: p.input.quality });
      if (r && r.id) go(link3d(id, "build"));
    } }, icon("cube", 15), "이 사진으로 3D 만들기"));
  drawAll();
}
