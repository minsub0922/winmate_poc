// BR4 — 3D 조감도 내보내기 · 보내기 (렌더 이미지만 · 'AI 생성 · 개략' 표시는 항상 · 출처 메타데이터 포함 ZIP)
import { api } from "../api.js";
import { h, icon, replace, wmsg, toast, downloadBlob, loadImage } from "../dom.js";
import { go, link2d, link3d, getEnv } from "../shell.js";
import { load3d, frame3d, labels, fileUrl, patch3d } from "../ui3d.js";
import { makeZip } from "../zip.js";

export async function mount(id) {
  const p = await load3d(id);
  const L = await labels();
  const env = await getEnv();
  const fr = frame3d(p, "export", { complete: true });
  const rs = p.renders || [];
  const after = rs.filter(r => r.variant === "after");
  const before = rs.filter(r => r.variant === "before");
  const pairs = before.map(bf => [bf, after.slice().reverse().find(a => a.camera === bf.camera && a.lighting === bf.lighting)]).filter(x => x[1]);
  const items = [
    ...after.slice().reverse().map(r => ({ key: r.id, kind: "single", r, label: r.label, sub: `${r.res ? r.res.join("×") : ""}${r.quality ? " · " + r.quality : ""}` })),
    ...pairs.map(([bf, af]) => ({ key: `pair-${bf.id}`, kind: "pair", r: af, r0: bf, label: `도입 전 / 후 비교 · ${af.label}`, sub: "2컷 · 나란히 한 장" })),
    ...before.slice().reverse().map(r => ({ key: r.id, kind: "single", r, label: r.label, sub: `${r.res ? r.res.join("×") : ""}` })),
  ];
  const sel = new Set(items.slice(0, Math.min(3, items.length)).map(i => i.key));
  let fmtSel = "png", size = "orig", busy = false;
  let fname = (p.export_name || `${(p.title || "birdseye").replace(/\s+/g, "")}_3D조감도_rev${(p.brief || {}).rev || 1}`).replace(/[\\/:*?"<>|]/g, "_");

  const left = h("div", { class: "card pad col", style: { gap: "8px", flex: "1 1 0", minWidth: 0 } });
  const right = h("div", { class: "col", style: { gap: "10px", width: "440px", flexShrink: 0 } });

  function drawLeft() {
    replace(left,
      h("div", { class: "card-h" }, h("h3", {}, "렌더 이미지"), h("span", { class: "sub" }, `${sel.size} / ${items.length} 선택`)),
      items.length ? h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "10px" } }, items.map(it => h("label", { class: "col", style: { gap: "4px", cursor: "pointer" } },
        h("div", { class: "cut" + (sel.has(it.key) ? " on" : ""), style: { display: "flex" } },
          it.kind === "pair" ? [h("img", { src: fileUrl(id, it.r0.file), alt: "", style: { width: "50%" } }), h("img", { src: fileUrl(id, it.r.file), alt: "", style: { width: "50%" } })] : h("img", { src: fileUrl(id, it.r.file), alt: "" }),
          h("span", { class: "aitag" }, "AI 생성 · 개략")),
        h("div", { class: "row small" }, h("input", { type: "checkbox", checked: sel.has(it.key), onchange: e => { e.target.checked ? sel.add(it.key) : sel.delete(it.key); drawLeft(); drawBottom(); }, style: { accentColor: "var(--pri)" } }),
          h("b", { class: "ellipsis" }, it.label)),
        h("div", { class: "xs muted", style: { paddingLeft: "22px" } }, it.sub)))) : h("div", { class: "empty" }, "아직 렌더가 없어요"),
      h("div", { class: "divider" }),
      h("div", { class: "row", style: { flexWrap: "wrap", gap: "14px" } },
        h("div", { class: "row" }, h("span", { class: "small muted" }, "형식"), h("div", { class: "seg" }, [["png", "PNG"], ["jpg", "JPG"]].map(([k, l]) => h("button", { class: fmtSel === k ? "on" : "", onclick: () => { fmtSel = k; drawLeft(); } }, l)))),
        h("div", { class: "row" }, h("span", { class: "small muted" }, "크기"), h("div", { class: "seg" }, [["orig", "원본"], ["fhd", "FHD"]].map(([k, l]) => h("button", { class: size === k ? "on" : "", onclick: () => { size = k; drawLeft(); } }, l)))),
        h("label", { class: "check", title: "렌더할 때 이미지에 새겨 넣어 끌 수 없어요" }, h("input", { type: "checkbox", checked: true, disabled: true }), "AI 생성 표시 넣기", h("span", { class: "tag" }, "항상 켜짐"))),
      h("div", { class: "xs muted" }, "제안서 · 외부 공유 시 출처 표시 유지 — ZIP 안 provenance.json 에 콘셉트 · 렌더 설정 · 제품 치수 출처를 함께 넣어요. PDF 는 이미지를 열어 인쇄 · PDF로 저장하세요."),
      h("div", { class: "row small muted" }, icon("info", 13), "제품 수량표는 2D 조감도에서 내보내요",
        p.linked_2d ? h("a", { class: "btn sm", href: link2d(p.linked_2d, "export") }, "2D 내보내기") : null));
  }
  function drawRight() {
    const hasPair = pairs.length > 0;
    const rows = [["조감 45° · 주간", "공간 전경", "BV-A", after.some(r => r.camera === "aerial45")], ["도입 전 / 후", "두 시점 비교", "BV-B", hasPair], ["2D 존 사용", "존별 포인트", "ZP-A", !!p.linked_2d]];
    replace(right,
      h("div", { class: "card pad" },
        h("div", { class: "card-h" }, h("h3", {}, "B2B 제안서로 보내기"), h("span", { class: "sub ellipsis" }, p.proposal || "연결된 제안서 없음")),
        h("table", { class: "tbl", style: { marginTop: "8px" } },
          h("thead", {}, h("tr", {}, h("th", {}, "3D 결과"), h("th", {}, "제안서 '조감도'"), h("th", {}, "코드"))),
          h("tbody", {}, rows.map(([a, b, c, ok]) => h("tr", {}, h("td", {}, a), h("td", {}, b), h("td", {}, h("span", { class: "tag " + (ok ? "pri" : "") }, c), ok ? null : h("span", { class: "xs faint" }, " 컷 없음")))))),
        h("div", { class: "xs muted", style: { marginTop: "8px" } }, "'조감도' 섹션으로 들어가요 · 제안서 화면은 이 PoC 밖이라 ZIP 의 proposal_images.json 으로 넘겨요")),
      h("div", { class: "card pad col", style: { gap: "10px" } },
        nextRow("image", "이미지 생성에서 이 컷 다듬기", "조감 45° · 주간 컷을 참조 이미지로 가져가요"),
        nextRow("map", "공간 시나리오 장면 배경으로", "렌더를 시나리오 장면의 배경으로 써요"),
        h("div", { class: "xs muted" }, "다른 기능 화면이라 이 PoC 에선 버튼만 있어요")));
  }
  const nextRow = (ic, t, s) => h("div", { class: "row" }, h("span", { class: "iconbtn", style: { pointerEvents: "none" } }, icon(ic, 15)),
    h("div", { class: "grow" }, h("b", { class: "small" }, t), h("div", { class: "xs muted" }, s)), h("button", { class: "btn sm", disabled: true }, "열기"));

  async function toBlob(r) {
    const url = fileUrl(id, r.file);
    if (size === "orig" && r.file.toLowerCase().endsWith("." + (fmtSel === "jpg" ? "jpg" : "png"))) return (await fetch(url)).blob();
    const im = await loadImage(url);
    let W = im.naturalWidth, H = im.naturalHeight;
    if (size === "fhd" && W > 1920) { H = Math.round(H * 1920 / W); W = 1920; }
    const c = h("canvas", { width: W, height: H });
    c.getContext("2d").drawImage(im, 0, 0, W, H);
    return new Promise(res => c.toBlob(res, fmtSel === "jpg" ? "image/jpeg" : "image/png", 0.92));
  }
  async function pairBlob(r0, r1) {
    const [a, b] = await Promise.all([loadImage(fileUrl(id, r0.file)), loadImage(fileUrl(id, r1.file))]);
    let w = a.naturalWidth, hh = a.naturalHeight;
    if (size === "fhd" && w * 2 > 3840) { hh = Math.round(hh * 1920 / w); w = 1920; }
    const gap = Math.round(w * 0.012), top = Math.round(hh * 0.07);
    const c = h("canvas", { width: w * 2 + gap, height: hh + top });
    const ctx = c.getContext("2d");
    ctx.fillStyle = "#ffffff"; ctx.fillRect(0, 0, c.width, c.height);
    ctx.drawImage(a, 0, top, w, hh); ctx.drawImage(b, w + gap, top, w, hh);
    ctx.fillStyle = "#121417"; ctx.font = `700 ${Math.round(top * 0.45)}px "Apple SD Gothic Neo","Noto Sans KR","Malgun Gothic",sans-serif`; ctx.textBaseline = "middle";
    ctx.fillText("도입 전", Math.round(w * 0.015), top / 2); ctx.fillText("도입 후", w + gap + Math.round(w * 0.015), top / 2);
    return new Promise(res => c.toBlob(res, fmtSel === "jpg" ? "image/jpeg" : "image/png", 0.92));
  }
  async function download() {
    if (busy) return;
    const chosen = items.filter(i => sel.has(i.key));
    if (!chosen.length) { toast("이미지를 골라 주세요", "err"); return; }
    busy = true; drawBottom();
    try {
      const ext = fmtSel === "jpg" ? "jpg" : "png";
      const files = [];
      const prov = [];
      let n = 1;
      for (const it of chosen) {
        const name = `${String(n++).padStart(2, "0")}_${(it.kind === "pair" ? "도입전후_" : "") + it.r.cut}.${ext}`;
        files.push({ name, data: it.kind === "pair" ? await pairBlob(it.r0, it.r) : await toBlob(it.r) });
        prov.push({ file: name, label: it.label, ai_generated: true, stamp: "AI 생성 · 개략", kind: it.kind, renders: (it.kind === "pair" ? [it.r0, it.r] : [it.r]).map(r => ({ id: r.id, camera: r.camera, lighting: r.lighting, variant: r.variant, res: r.res, quality: r.quality, created: r.created, brief_rev: r.brief_rev, source_file: r.file })),
          proposal_code: it.kind === "pair" ? "BV-B" : (it.r.camera === "aerial45" && it.r.lighting === "day" ? "BV-A" : null) });
      }
      const b = p.brief || {};
      const meta = {
        project: { id: p.id, title: p.title, customer: p.customer, proposal: p.proposal, linked_2d: p.linked_2d },
        generator: { tool: "Winmate 공간 조감도 PoC", renderer: (env && env.blender && env.blender.note) || "Blender", engine: "Cycles", exported: new Date().toISOString() },
        notice: "AI 생성 · 개략 이미지 — 제품 위치 · 수량 · 크기는 실제와 다를 수 있어요. 정확한 배치는 2D 조감도 기준.",
        brief: { rev: b.rev, concept: b.concept, concept_label: L.concept(b.concept), floor: b.floor, wall: b.wall, accent: b.accent, light_k: b.light_k, source: b.meta && b.meta.source, model: b.meta && b.meta.model },
        products: "제품 외형 치수 = winmate-kb 스펙(samsung.com/sec/business 수집본) · 화면 콘텐츠는 일반 패턴(상표 · 로고 없음)",
        references: ((p.refs || {}).images || []).map(im => ({ url: im.url, page: im.page_url, caption_rule: im.caption_rule })),
        images: prov,
      };
      files.push({ name: "provenance.json", data: JSON.stringify(meta, null, 1) });
      files.push({ name: "proposal_images.json", data: JSON.stringify({ section: "조감도", items: prov.filter(x => x.proposal_code).map(x => ({ code: x.proposal_code, file: x.file, caption: x.label + " · AI 생성 · 개략" })) }, null, 1) });
      files.push({ name: "README.txt", data: `${p.title} — 3D 조감도 내보내기\n모든 이미지는 AI 생성 · 개략 이미지입니다(이미지 왼쪽 아래 표시).\nprovenance.json: 렌더 설정 · 콘셉트 · 출처 / proposal_images.json: 제안서 '조감도' 섹션(BV-A · BV-B)으로 넘길 목록\n` });
      const zip = await makeZip(files);
      downloadBlob(zip, `${fname}.zip`);
      patch3d(id, { export_name: fname }).catch(() => {});
      toast(`이미지 ${chosen.length}장을 ZIP 으로 내려받았어요`);
    } finally { busy = false; drawBottom(); }
  }
  function drawBottom() {
    const inp = h("input", { value: fname, "aria-label": "파일 이름", onchange: e => { fname = e.target.value.trim() || fname; } });
    fr.setBottom(
      h("div", { class: "col", style: { gap: 0, paddingLeft: "6px", minWidth: "190px" } }, h("b", {}, "내려받기"), h("span", { class: "xs muted" }, `이미지 ${sel.size}장 · AI 생성 표시 포함 · ZIP`)),
      h("div", { class: "composer" }, h("span", { class: "label" }, "파일 이름"), inp, h("span", { class: "small muted" }, ".zip")),
      h("button", { class: "btn lg", onclick: () => go(link3d(id, "result")) }, "이전"),
      h("button", { class: "btn lg primary", disabled: !sel.size || busy, onclick: download }, busy ? h("span", { class: "spin" }) : icon("download", 15), busy ? "만드는 중…" : "ZIP 내려받기"));
  }
  fr.content.append(h("div", { class: "col", style: { gap: "14px" } },
    wmsg("3D 조감도 이미지를 내려받거나 제안서로 보낼 수 있어요. 모든 이미지에 'AI 생성 · 개략' 표시가 함께 들어가요. 제품 수량표는 정확한 배치가 있는 2D 조감도에서 내보내요."),
    h("div", { style: { display: "flex", gap: "12px", alignItems: "flex-start" } }, left, right)));
  drawLeft(); drawRight(); drawBottom();
}
