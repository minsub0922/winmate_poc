// 2D 화면 공통 조각 — 숫자 입력, 2D 단계 틀, 제품 이름
import { h, fmt } from "./dom.js";
import { frame, STEPS_2D } from "./shell.js";
import { bindSave } from "./state.js";
import { api } from "./api.js";

export const parseNum = v => { const n = parseFloat(String(v ?? "").replace(/[,\s]/g, "")); return Number.isFinite(n) ? n : null; };

// 콤마 숫자 입력 — 값이 바뀌면 onChange(number)
export function numInput(value, onChange, opts = {}) {
  const inp = h("input", {
    class: "inp num" + (opts.sm ? " sm" : ""), inputmode: "decimal", value: value === null || value === undefined ? "" : fmt(value, opts.dec || 0),
    "aria-label": opts.label || null, style: opts.width ? { width: opts.width } : null, disabled: opts.disabled,
  });
  inp.addEventListener("focus", () => { inp.value = String(inp.value).replace(/,/g, ""); inp.select(); });
  const commit = () => {
    const n = parseNum(inp.value);
    if (n === null) { inp.value = value === null || value === undefined ? "" : fmt(value, opts.dec || 0); return; }
    let v = opts.min !== undefined ? Math.max(opts.min, n) : n;
    if (opts.max !== undefined) v = Math.min(opts.max, v);
    inp.value = fmt(v, opts.dec || 0);
    if (v !== value) { value = v; onChange(v); }
  };
  inp.addEventListener("blur", commit);
  inp.addEventListener("keydown", e => { if (e.key === "Enter") { commit(); inp.blur(); } if (e.key === "Escape") { inp.value = fmt(value, opts.dec || 0); inp.blur(); } });
  return inp;
}
export const unitField = (label, input, unit = "mm") => h("div", { class: "field" }, h("label", {}, label), h("div", { class: "unit" }, input, unit ? h("span", {}, unit) : null));

export function frame2d(doc, cur, opts = {}) {
  const fr = frame({
    project: doc.p, title: doc.p.title, steps: STEPS_2D, cur, complete: opts.complete, fill: opts.fill,
    onRename: t => { doc.commit(p => { p.title = t; }, { validate: false }); },
  });
  const off = bindSave(doc, fr);
  return { fr, off };
}

export const WALL_NAMES = { front: "정면", back: "후면", left: "왼쪽 벽", right: "오른쪽 벽" };
export const KIND_NAMES = { window: "유리창", entrance: "출입구", door: "문" };
export const DOOR_TYPES = { normal: "일반 문", emergency: "비상구", backoffice: "백오피스 출입", corridor: "복도 문", wall: "벽으로 처리" };

export async function catalogSearch(q, limit = 12) {
  return (await api.get(`/api/catalog?q=${encodeURIComponent(q)}&limit=${limit}`, { quiet: true }).catch(() => ({ items: [] }))).items;
}
export const sizeText = p => p ? `${fmt(p.w, 0)} × ${fmt(p.h, 0)}${p.d ? " × " + fmt(p.d, 0) : ""}` : "";
export const inchOf = p => { const m = /(\d{2,3})(?:"|인치|형|")/.exec(p.name || ""); return m ? m[1] + '"' : ""; };
