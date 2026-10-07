// BP4 — 2D 조감도 4/4 · 완성 (치수 · 범례 · 표제란 도면 + 제품 수량표 + 검토 + 3D로 분위기 보기)
import { api } from "../api.js";
import { h, icon, replace, fmt, wmsg, toast } from "../dom.js";
import { go, link2d, link3d } from "../shell.js";
import { Doc2D } from "../state.js";
import { frame2d } from "../ui2d.js";

const KIND = { viewing_angle: "시야각", traffic: "동선", power: "전원", overlap: "겹침", height: "높이", support: "설치", size: "크기" };
const layersOn = { dims: true, zones: true, flow: true, power: false };

export async function mount(id) {
  const doc = await Doc2D.load(id);
  const { fr, off } = frame2d(doc, "done", { fill: true });
  let qty = null, busy = false;
  const all = (await api.get("/api/projects")).items;
  const linked3d = all.filter(p => p.kind === "3d" && p.linked_2d === id);

  const img = h("img", { alt: "배치 도면", style: { width: "100%", height: "100%", objectFit: "contain", display: "block", background: "#fff" } });
  const drawWrap = h("div", { class: "planbox", style: { flex: "1 1 auto", minHeight: 0, background: "#fff" } }, img);
  const layerBar = h("div", { class: "row", style: { gap: "6px" } });
  const msg = h("div", {});
  const right = h("div", { class: "rpanel", style: { width: "400px" } });

  function drawingUrl(extra = "") {
    const L = ["fixtures", "labels", ...Object.keys(layersOn).filter(k => layersOn[k])];
    return `/api/projects/${id}/drawing.svg?kind=plan&paper=A3&layers=${L.join(",")}&v=${doc.p.version}-${Date.now()}${extra}`;
  }
  function drawLayers() {
    const t = (k, label) => h("button", { class: "toggle" + (layersOn[k] ? " on" : ""), onclick: () => { layersOn[k] = !layersOn[k]; drawLayers(); img.src = drawingUrl(); } }, layersOn[k] ? icon("check", 10, 3.4) : null, label);
    replace(layerBar, t("dims", "치수"), t("zones", "존 번호"), t("flow", "동선"), t("power", "전원"),
      h("span", { class: "vsep", style: { width: "1px", height: "18px", background: "var(--line)" } }),
      h("a", { class: "btn sm ghost", href: drawingUrl(), target: "_blank", rel: "noopener" }, icon("eye", 13), "크게 보기"));
  }

  async function load() {
    await doc.flush();
    qty = await api.get(`/api/projects/${id}/qty.json`);
    img.src = drawingUrl();
    draw();
  }
  function draw() {
    const v = qty.validation;
    const s = v.summary;
    const memos = v.warnings.filter(w => w.level === "memo");
    const active = v.warnings.filter(w => (w.level === "warn" || w.level === "error") && !w.ignored);
    const resolved = (doc.p.ignored || []).length;
    replace(msg, wmsg(h("span", {}, "2D 조감도가 완성되었어요. ", h("b", {}, active.length ? `경고 ${active.length}개 남음` : `검토 완료${s.memos ? " · 메모 " + s.memos : ""}`),
      active.length ? " — 배치 수정에서 확인해 주세요. " : (memos.length ? ` — 배선이 필요한 곳은 메모로 남겼어요. ` : " — "),
      `수량표는 이 도면의 실측 치수 기준이라 견적 근거로 그대로 쓸 수 있어요.`)));
    const zoneName = no => { const z = (doc.p.zones || []).find(z => z.no === no); return z ? `존 ${no}` : ""; };
    replace(right,
      h("div", { class: "card pad" },
        h("div", { class: "card-h" }, h("h3", {}, "제품 수량표"), h("span", { class: "sub" }, `도면 v${doc.p.version} 기준 · 단가 미포함`)),
        h("table", { class: "tbl", style: { marginTop: "8px" } },
          h("thead", {}, h("tr", {}, h("th", {}, "제품"), h("th", {}, "존"), h("th", { class: "r" }, "수량"))),
          h("tbody", {}, qty.rows.map(r => h("tr", {},
            h("td", {}, h("div", { class: "b" }, r.short), h("div", { class: "xs muted ellipsis", style: { maxWidth: "210px" }, title: `${r.name} · ${r.mount} · ${r.anchor}` }, `${r.mount} · ${r.anchor || r.screen}`)),
            h("td", { class: "small" }, r.zones || h("span", { class: "faint" }, "–")),
            h("td", { class: "r" }, h("span", { class: "num b" }, r.qty), " 대"))),
            h("tr", {}, h("td", { class: "b" }, `합계 · ${qty.kinds}종`), h("td", { class: "small" }, `존 ${(doc.p.zones || []).length}`), h("td", { class: "r" }, h("span", { class: "num b" }, qty.total), " 대")))),
        qty.fixtures.length ? h("div", { class: "xs muted", style: { marginTop: "8px" } },
          `집기 ${qty.fixtures.length}종 ${qty.fixtures.reduce((a, f) => a + f.count, 0)}개 (참고) · ` + qty.fixtures.map(f => `${f.label} ${f.count}`).join(" · ")) : null),
      h("div", { class: "card pad" },
        h("div", { class: "card-h" }, h("span", { class: "wno info", style: { width: "18px", height: "18px" } }, "!"), h("h3", {}, "검토"),
          h("span", { class: "sub" }, active.length ? `경고 ${active.length}` : "검토 완료"), h("span", { class: "spacer" }),
          h("span", { class: "xs muted" }, `경고 ${s.warnings} · 무시 ${resolved} · 메모 ${s.memos} · 참고 ${s.infos}`)),
        h("div", { class: "col", style: { gap: "4px", marginTop: "8px" } },
          [...active, ...memos].map(w => h("div", { class: "warn-item" },
            h("div", { class: "row", style: { gap: "8px" } }, h("span", { class: "wno" + (w.level === "memo" ? " memo" : "") }, w.level === "memo" ? "메모" : w.no),
              h("b", { class: "small" }, KIND[w.kind] || w.kind), h("span", { class: "small muted ellipsis" }, w.title)),
            h("div", { class: "wd" }, w.detail + (w.level === "memo" ? " · 시공 시 확인" : "")),
            h("div", { class: "wa" }, h("button", { class: "btn xs ghost", onclick: () => go(link2d(id, "layout")) }, "위치 보기")))),
          !active.length && !memos.length ? h("div", { class: "small muted" }, "시야각 · 통로 폭 · 문 앞 · 겹침 · 높이 · 전원 모두 통과") : null)),
      h("div", { class: "card pad col", style: { gap: "8px" } },
        h("div", { class: "card-h" }, h("h3", {}, "3D로 분위기 보기"), h("span", { class: "tag" }, "선택")),
        h("div", { class: "small muted" }, "이 배치로 3D 조감도를 만들면 제품 위치는 그대로 두고 인테리어 · 가구는 AI가 정해요."),
        linked3d.length ? h("div", { class: "row", style: { flexWrap: "wrap", gap: "6px" } }, linked3d.map(p => h("a", { class: "chip sm", href: link3d(p.id, (p.summary || {}).renders ? "result" : "brief") }, icon("cube", 12), p.title))) : null,
        h("button", { class: "btn soft", onclick: make3d }, icon("cube", 15), "이 배치로 3D 조감도 만들기")));
  }
  async function make3d() {
    await doc.flush();
    const p3 = await api.post(`/api/projects/${id}/to3d`);
    go(link3d(p3.id, "brief"));
  }

  const nl = h("input", { placeholder: "말로 수정 요청 (예: 라운지 소파 600 오른쪽으로)", "aria-label": "말로 수정 요청" });
  const composer = h("div", { class: "composer" }, nl, h("button", { class: "send", "aria-label": "보내기", onclick: () => sendNl() }, icon("send", 15)));
  nl.addEventListener("input", () => composer.classList.toggle("ready", !!nl.value.trim()));
  nl.addEventListener("keydown", e => { if (e.key === "Enter" && !e.isComposing) sendNl(); });
  async function sendNl() {
    const text = nl.value.trim();
    if (!text || busy) return;
    busy = true;
    try {
      const r = await api.post("/api/2d/nl", { project: doc.p, text });
      toast(r.reply, r.ops && r.ops.length ? "" : "err");
      if (r.ops && r.ops.length) { doc.replace(r.project, { v: r.validation }); nl.value = ""; await doc.bump(); await load(); }
    } finally { busy = false; }
  }

  replace(fr.content, msg,
    h("div", { style: { display: "flex", gap: "12px", marginTop: "12px", flex: "1 1 auto", minHeight: 0 } },
      h("div", { class: "col", style: { flex: "1 1 auto", minWidth: 0, gap: "8px" } },
        h("div", { class: "row" }, h("b", { class: "nowrap" }, "배치 도면"), h("span", { class: "tag" }, `v${doc.p.version}`),
          h("span", { class: "small muted ellipsis" }, `${fmt(doc.p.space.width)} × ${fmt(doc.p.space.depth)} mm · ${fmt(doc.p.space.width * doc.p.space.depth / 1e6, 0)} ㎡ · 층고 ${fmt(doc.p.space.height)}`),
          h("span", { class: "spacer" }), layerBar),
        drawWrap),
      right));
  fr.setBottom(
    h("button", { class: "btn lg", onclick: () => go(link2d(id, "layout")) }, "배치 수정"),
    h("button", { class: "btn lg", onclick: () => go(link2d(id, "zones")) }, "존 구획"),
    h("button", { class: "btn lg ghost", onclick: async () => { const p = await api.post(`/api/projects/${id}/duplicate`); toast("복제했어요 — 새 안에서 이어서 고쳐요"); go(link2d(p.id, "layout")); } }, icon("copy", 14), "복제해서 새 안"),
    composer,
    h("button", { class: "btn lg", onclick: async () => { await doc.bump(); toast(`v${doc.p.version}로 저장했어요`); load(); } }, "저장"),
    h("button", { class: "btn lg primary", onclick: async () => { await doc.flush(); go(link2d(id, "export")); } }, "내보내기 · 제안서로", icon("arrowR")));
  drawLayers();
  await load();
  return { beforeLeave: () => doc.flush(), unmount: () => off() };
}
