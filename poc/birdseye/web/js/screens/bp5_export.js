// BP5 — 2D 조감도 내보내기 · 보내기 (도면 · 존 구획도 · 동선도 · 수량표 · CAD → ZIP, PNG/인쇄, 제안서 시트 매핑)
import { api } from "../api.js";
import { h, icon, replace, fmt, wmsg, toast, downloadBlob, loadImage } from "../dom.js";
import { go, link2d, link3d } from "../shell.js";
import { Doc2D } from "../state.js";
import { frame2d } from "../ui2d.js";

export async function mount(id) {
  const doc = await Doc2D.load(id);
  const { fr, off } = frame2d(doc, "export", { complete: true });
  const qty = await api.get(`/api/projects/${id}/qty.json`);
  const payload = await api.get(`/api/projects/${id}/payload.json`);
  const sel = { plan: true, zones: true, flow: true, qty: true, cad: false };
  let paper = "A3", fmtSel = "svg", withFx = true;
  const nZones = (doc.p.zones || []).length;
  const sp = doc.p.space;
  let fname = (doc.p.export_name || `${(doc.p.title || "birdseye").replace(/\s+/g, "")}_2D_v${doc.p.version}`).replace(/[\\/:*?"<>|]/g, "_");

  const ITEMS = [
    ["plan", "배치 도면", `${paper} · 치수 · 범례 · 표제란 포함`, "SVG"],
    ["zones", "존 구획도", `번호 ${nZones}곳 · 존 이름 · 존별 면적`, "SVG"],
    ["flow", "동선도", `주출입구 → 존 1 – ${nZones} 순서 · 통로 폭`, "SVG"],
    ["qty", "제품 수량표", `존별 · ${qty.kinds}종 ${qty.total}대 · 모델 · 설치 방식 · 위치`, "Excel"],
    ["cad", "CAD 파일", "협력사 전달용 · 레이어 (벽 · 개구부 · 제품 · 집기 · 존 · 치수)", "DXF"],
  ];
  const left = h("div", { class: "card pad col", style: { gap: "8px", flex: "1 1 0", minWidth: 0 } });
  const right = h("div", { class: "col", style: { gap: "10px", width: "460px", flexShrink: 0 } });

  function drawLeft() {
    const n = Object.values(sel).filter(Boolean).length;
    replace(left,
      h("div", { class: "card-h" }, h("h3", {}, "내보낼 항목"), h("span", { class: "sub" }, `${n} / ${ITEMS.length} 선택`)),
      ITEMS.map(([k, name, sub, f]) => h("label", { class: "row", style: { padding: "10px 12px", borderRadius: "12px", border: "1px solid " + (sel[k] ? "var(--pri-line)" : "var(--line)"), background: sel[k] ? "var(--pri-soft)" : "#fff", cursor: "pointer" } },
        h("input", { type: "checkbox", checked: sel[k], onchange: e => { sel[k] = e.target.checked; drawLeft(); drawBottom(); }, style: { width: "16px", height: "16px", accentColor: "var(--pri)" } }),
        h("div", { class: "grow" }, h("b", {}, name), h("div", { class: "xs muted" }, k === "plan" ? `${paper} · 치수 · 범례 · 표제란 포함` : sub)),
        h("span", { class: "tag" }, k === "qty" ? "Excel · CSV" : (["plan", "zones", "flow"].includes(k) ? (fmtSel === "png" ? "PNG" : "SVG") : f)),
        ["plan", "zones", "flow"].includes(k) ? h("a", { class: "btn xs ghost", href: `/api/projects/${id}/drawing.svg?kind=${k}&paper=${paper}`, target: "_blank", rel: "noopener", onclick: e => e.stopPropagation() }, "보기") : null)),
      h("div", { class: "divider" }),
      h("div", { class: "row", style: { flexWrap: "wrap", gap: "14px" } },
        h("div", { class: "row" }, h("span", { class: "small muted" }, "도면 형식"),
          h("div", { class: "seg" }, [["svg", "SVG(벡터)"], ["png", "PNG"]].map(([k, l]) => h("button", { class: fmtSel === k ? "on" : "", onclick: () => { fmtSel = k; drawLeft(); } }, l)))),
        h("div", { class: "row" }, h("span", { class: "small muted" }, "크기"),
          h("div", { class: "seg" }, ["A3", "A4"].map(k => h("button", { class: paper === k ? "on" : "", onclick: () => { paper = k; drawLeft(); } }, k)))),
        h("label", { class: "check" }, h("input", { type: "checkbox", checked: withFx, onchange: e => { withFx = e.target.checked; } }), `수량표에 집기 포함`, h("span", { class: "xs muted" }, `(참고 행 · ${doc.p.fixtures.length}개)`))),
      h("div", { class: "row", style: { marginTop: "6px", flexWrap: "wrap" } },
        h("button", { class: "btn sm", onclick: () => printSheet("plan") }, icon("print", 13), "배치 도면 인쇄 · PDF"),
        h("button", { class: "btn sm", onclick: () => printSheet("zones") }, icon("print", 13), "존 구획도 인쇄 · PDF"),
        h("span", { class: "xs muted" }, "PDF 는 브라우저 인쇄에서 'PDF로 저장' · 100% 배율이면 표제란 축척과 맞아요")),
      h("div", { class: "xs muted" }, "단가 · 견적 미포함 · 치수 · 사양은 winmate-kb 원문 값, 배치 룰 계수는 PoC 임시값"));
  }
  function printSheet(kind) {
    const w = window.open("", "_blank");
    if (!w) { toast("팝업이 막혔어요 — 허용해 주세요", "err"); return; }
    w.document.write(`<!doctype html><title>${doc.p.title} · ${kind}</title><style>@page{size:${paper} landscape;margin:0}html,body{margin:0}img{width:100%;display:block}</style><img src="/api/projects/${id}/drawing.svg?kind=${kind}&paper=${paper}" onload="setTimeout(()=>print(),300)">`);
    w.document.close();
  }
  function drawRight() {
    const sheets = payload.sheets || {};
    const rows = [["배치 도면 · 존", "공간 맵", "SM-A"], ["제품 수량표", "공간별 제품 수량", "SM-B"], ["존 구획 · 포인트", "존별 포인트", "ZP-A"]];
    replace(right,
      h("div", { class: "card pad" },
        h("div", { class: "card-h" }, h("h3", {}, "B2B 제안서로 보내기"), h("span", { class: "sub ellipsis" }, doc.p.proposal || "연결된 제안서 없음")),
        h("table", { class: "tbl", style: { marginTop: "8px" } },
          h("thead", {}, h("tr", {}, h("th", {}, "2D 결과"), h("th", {}, "제안서 시트"), h("th", {}, "코드"))),
          h("tbody", {}, rows.map(([a, b, c]) => h("tr", {}, h("td", {}, a), h("td", {}, b), h("td", {}, h("span", { class: "tag pri" }, c), sheets[c] ? null : h("span", { class: "xs faint" }, " 데이터 없음")))))),
        h("div", { class: "xs muted", style: { marginTop: "8px" } }, `수량은 도면 v${doc.p.version} 그대로 · 단가는 제안서에서 입력 · 제안서 화면은 이 PoC 밖이라 proposal_payload.json 으로 넘겨요`),
        h("div", { class: "row", style: { marginTop: "8px" } },
          h("button", { class: "btn sm", onclick: () => downloadBlob(new Blob([JSON.stringify(payload, null, 1)], { type: "application/json" }), `${fname}_proposal_payload.json`) }, icon("download", 13), "제안서 데이터(JSON)"))),
      h("div", { class: "card pad col", style: { gap: "10px" } },
        nextRow("cube", "이 배치로 3D 조감도 만들기", "제품 위치는 그대로 · 인테리어 · 가구는 AI가", "시작", async () => { await doc.flush(); const p3 = await api.post(`/api/projects/${id}/to3d`); go(link3d(p3.id, "brief")); }),
        nextRow("map", "공간 시나리오로 이어 만들기", `존 ${nZones}곳 → 장면 ${nZones}개 · 동선 순서 그대로`, "데이터 보기", () => showJson("시나리오로 넘길 존", (doc.p.zones || []).map(z => ({ no: z.no, name: z.name, point: z.point })))),
        nextRow("doc", "Spec 시트 만들기", `제품 ${qty.kinds}종으로 스펙 비교표를 만들어요`, "데이터 보기", () => showJson("Spec 시트로 넘길 제품", qty.rows.map(r => ({ code: r.code, name: r.name, qty: r.qty, dims: r.dims, power_w: r.power_w, source: r.source })))),
        h("div", { class: "xs muted" }, "시나리오 · Spec 시트 화면은 다른 기능이라 이 PoC 에선 넘길 데이터만 보여줘요")));
  }
  const nextRow = (ic, title, sub, btn, fn) => h("div", { class: "row" }, h("span", { class: "iconbtn", style: { pointerEvents: "none" } }, icon(ic, 15)),
    h("div", { class: "grow" }, h("b", { class: "small" }, title), h("div", { class: "xs muted" }, sub)), h("button", { class: "btn sm", onclick: fn }, btn));
  function showJson(title, data) {
    import("../dom.js").then(({ modal }) => modal(title, h("pre", { class: "formula", style: { maxHeight: "50vh", overflow: "auto" } }, JSON.stringify(data, null, 1)), [{ label: "닫기", cls: "primary" }]));
  }

  async function svgToPng(url, scale = 2) {
    const r = await fetch(url);
    const text = await r.text();
    const m = /viewBox="0 0 ([\d.]+) ([\d.]+)"/.exec(text);
    const wmm = m ? +m[1] : 420, hmm = m ? +m[2] : 297;
    const pxPerMm = 150 / 25.4 * scale / 2; // 150 dpi
    const W = Math.round(wmm * pxPerMm), H = Math.round(hmm * pxPerMm);
    const svgUrl = URL.createObjectURL(new Blob([text.replace(/width="[\d.]+mm" height="[\d.]+mm"/, `width="${W}" height="${H}"`)], { type: "image/svg+xml" }));
    const im = await loadImage(svgUrl);
    const c = h("canvas", { width: W, height: H });
    const ctx = c.getContext("2d");
    ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, W, H); ctx.drawImage(im, 0, 0, W, H);
    URL.revokeObjectURL(svgUrl);
    return new Promise(res => c.toBlob(res, "image/png"));
  }

  async function download() {
    const items = Object.keys(sel).filter(k => sel[k]);
    if (!items.length) { toast("내보낼 항목을 골라 주세요", "err"); return; }
    doc.commit(p => { p.export_name = fname; }, { validate: false });
    await doc.flush();
    const { blob } = await api.blob("POST", `/api/projects/${id}/export.zip`, { items, paper, include_fixtures: withFx, filename: fname });
    if (fmtSel === "png" && items.some(k => ["plan", "zones", "flow"].includes(k))) {
      // PNG 도면은 브라우저에서 그려 따로 받는다(서버는 표준 라이브러리만 써서 래스터화 도구가 없음)
      for (const k of items.filter(k => ["plan", "zones", "flow"].includes(k))) {
        const png = await svgToPng(`/api/projects/${id}/drawing.svg?kind=${k}&paper=${paper}`);
        downloadBlob(png, `${fname}_${k}.png`);
      }
    }
    downloadBlob(blob, `${fname}.zip`);
    toast("내려받기를 시작했어요");
  }
  function drawBottom() {
    const items = Object.keys(sel).filter(k => sel[k]);
    const files = [];
    if (sel.plan) files.push("도면"); if (sel.zones) files.push("존 구획도"); if (sel.flow) files.push("동선도"); if (sel.qty) files.push("수량표"); if (sel.cad) files.push("DXF");
    const inp = h("input", { value: fname, "aria-label": "파일 이름", onchange: e => { fname = e.target.value.trim() || fname; } });
    fr.setBottom(
      h("div", { class: "col", style: { gap: 0, paddingLeft: "6px", minWidth: "160px" } }, h("b", {}, "내려받기"), h("span", { class: "xs muted" }, `${files.join(" · ") || "선택 없음"} · ZIP`)),
      h("div", { class: "composer" }, h("span", { class: "label" }, "파일 이름"), inp, h("span", { class: "small muted" }, ".zip")),
      h("button", { class: "btn lg", onclick: () => go(link2d(id, "done")) }, "이전"),
      h("button", { class: "btn lg primary", disabled: !items.length, onclick: download }, icon("download", 15), "ZIP 내려받기"));
  }

  fr.content.append(h("div", { class: "col", style: { gap: "14px" } },
    wmsg(`2D 조감도를 내려받거나 제안서 · 다른 작업으로 보낼 수 있어요. 도면은 치수 · 범례 · 표제란이 들어간 ${paper} 도면으로 나가고, 수량표는 도면 v${doc.p.version} 기준이라 견적 근거로 쓸 수 있어요.`),
    h("div", { style: { display: "flex", gap: "12px", alignItems: "flex-start" } }, left, right)));
  drawLeft(); drawRight(); drawBottom();
  return { beforeLeave: () => doc.flush(), unmount: () => off() };
}
