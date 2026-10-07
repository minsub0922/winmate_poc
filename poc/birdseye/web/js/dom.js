// 작은 DOM 도우미 — 프레임워크 없이 화면을 그린다.
export const SVGNS = "http://www.w3.org/2000/svg";

export function h(tag, props, ...kids) {
  const isSvg = tag.startsWith("svg:");
  const el = isSvg ? document.createElementNS(SVGNS, tag.slice(4)) : document.createElement(tag);
  setProps(el, props, isSvg);
  append(el, kids);
  return el;
}

export function s(tag, props, ...kids) { return h("svg:" + tag, props, ...kids); }

function setProps(el, props, isSvg) {
  if (!props) return;
  for (const [k, v] of Object.entries(props)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") { isSvg ? el.setAttribute("class", v) : (el.className = v); }
    else if (k === "style" && typeof v === "object") { for (const [sk, sv] of Object.entries(v)) { if (sv !== null && sv !== undefined) el.style.setProperty(sk.replace(/[A-Z]/g, m => "-" + m.toLowerCase()), sv); } }
    else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === "html") el.innerHTML = v;
    else if (k === "ref" && typeof v === "function") v(el);
    else if (!isSvg && (k === "value" || k === "checked" || k === "disabled" || k === "selected" || k === "multiple" || k === "accept")) el[k] = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
}

export function append(el, kids) {
  for (const k of kids.flat(Infinity)) {
    if (k === null || k === undefined || k === false || k === true) continue;
    el.appendChild(k instanceof Node ? k : document.createTextNode(String(k)));
  }
  return el;
}

export function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); return el; }
export function replace(el, ...kids) { clear(el); return append(el, kids); }
export const $ = (sel, root = document) => root.querySelector(sel);

// ── 숫자 · 문구 ──
export const fmt = (v, d = 0) => (v === null || v === undefined || Number.isNaN(+v)) ? "–" : (+v).toLocaleString("ko-KR", { minimumFractionDigits: d, maximumFractionDigits: d });
export const mm = v => fmt(Math.round(+v || 0));
export const m1 = v => fmt((+v || 0) / 1000, 1);
export const pyeong = m2 => Math.round(m2 / 3.3058);
export function when(iso) {
  if (!iso) return "";
  const d = new Date(iso), now = new Date();
  const hm = d.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", hour12: false });
  const day = Math.floor((new Date(now.toDateString()) - new Date(d.toDateString())) / 86400000);
  if (day === 0) return `오늘 ${hm}`;
  if (day === 1) return `어제 ${hm}`;
  return `${d.getMonth() + 1}월 ${d.getDate()}일 ${hm}`;
}
export function hasBatchim(word) {
  const w = (word || "").trim().replace(/["'”’)\]\s]+$/, "");
  const c = w.slice(-1);
  if (!c) return false;
  const code = c.charCodeAt(0);
  if (code >= 0xac00 && code <= 0xd7a3) return (code - 0xac00) % 28 !== 0;
  if (/[0-9]/.test(c)) return "013678".includes(c);
  return /[lmnr]/i.test(c);
}
export const josa = (w, pair) => { const [a, b] = pair.split("/"); return w + (hasBatchim(w) ? a : b); };
// '(으)로' — 받침이 ㄹ 이거나 없으면 '로'
export function ro(word) {
  const c = (word || "").replace(/["'”’)\]\s]+$/, "").slice(-1);
  const code = c.charCodeAt(0);
  if (code >= 0xac00 && code <= 0xd7a3) { const j = (code - 0xac00) % 28; return word + (j === 0 || j === 8 ? "로" : "으로"); }
  if (/[0-9]/.test(c)) return word + ("036".includes(c) ? "으로" : "로");
  return word + "로";
}

export function debounce(fn, ms) {
  let t = null;
  const f = (...a) => { clearTimeout(t); t = setTimeout(() => { t = null; fn(...a); }, ms); };
  f.flush = (...a) => { if (t) { clearTimeout(t); t = null; return fn(...a); } };
  f.cancel = () => { clearTimeout(t); t = null; };
  f.pending = () => t !== null;
  return f;
}

// ── 아이콘(인라인 SVG) ──
const P = {
  pointer: "M5 3l14 8-6 1.5L10 19z",
  rotate: "M20 12a8 8 0 1 1-2.3-5.6M20 4v5h-5",
  ruler: "M3 17l14-14 4 4L7 21z M7 13l2 2M10 10l2 2M13 7l2 2",
  zone: "M4 4h16v16H4z",
  check: "M5 12l5 5 9-10",
  plus: "M12 5v14M5 12h14",
  minus: "M5 12h14",
  x: "M6 6l12 12M18 6L6 18",
  arrowR: "M5 12h14M13 6l6 6-6 6",
  arrowL: "M19 12H5M11 6l-6 6 6 6",
  up: "M12 19V5M6 11l6-6 6 6",
  undo: "M9 14L4 9l5-5M4 9h10a6 6 0 0 1 0 12h-3",
  redo: "M15 14l5-5-5-5M20 9H10a6 6 0 0 0 0 12h3",
  fit: "M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5",
  upload: "M12 16V4M7 9l5-5 5 5M4 20h16",
  download: "M12 4v12M7 11l5 5 5-5M4 20h16",
  wand: "M4 20L14 10M15 2v3M15 9v3M11 6h-1M20 6h-1",
  more: "M5 12h.01M12 12h.01M19 12h.01",
  info: "M12 8h.01M11 12h1v5h1M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z",
  search: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20 20l-4-4",
  trash: "M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13",
  copy: "M8 8h12v12H8zM4 16V4h12",
  image: "M4 5h16v14H4zM4 15l4-4 4 4 3-3 5 5M15 9h.01",
  cube: "M12 3l8 4.5v9L12 21l-8-4.5v-9zM12 12l8-4.5M12 12v9M12 12L4 7.5",
  plan: "M4 4h16v16H4zM4 10h7v10M11 4v4",
  stop: "M7 7h10v10H7z",
  refresh: "M20 12a8 8 0 1 1-2.3-5.6M20 4v5h-5",
  camera: "M4 8h3l2-3h6l2 3h3v11H4zM12 10a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7z",
  sun: "M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10zM12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4",
  send: "M12 19V5M6 11l6-6 6 6",
  grid: "M3 3h8v8H3zM13 3h8v5h-8zM13 10h8v11h-8zM3 13h8v8H3z",
  doc: "M6 3h9l4 4v14H6zM14 3v5h5",
  link: "M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1",
  eye: "M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12zM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
  map: "M9 4L3 6v14l6-2 6 2 6-2V4l-6 2-6-2zM9 4v14M15 6v14",
  list: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
  pin: "M12 21s-7-6.2-7-12a7 7 0 0 1 14 0c0 5.8-7 12-7 12zM12 7a2 2 0 1 0 0 4 2 2 0 0 0 0-4z",
  plug: "M9 3v5M15 3v5M6 8h12v3a6 6 0 0 1-12 0zM12 17v4",
  sofa: "M4 10V8a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v2M3 11h18v5H3zM5 16v2M19 16v2",
  print: "M7 8V3h10v5M5 8h14v8h-3M8 13h8v8H8z",
};
export function icon(name, size = 15, sw = 2.1) {
  const el = document.createElementNS(SVGNS, "svg");
  el.setAttribute("width", size); el.setAttribute("height", size); el.setAttribute("viewBox", "0 0 24 24");
  el.setAttribute("fill", "none"); el.setAttribute("stroke", "currentColor"); el.setAttribute("stroke-width", sw);
  el.setAttribute("stroke-linecap", "round"); el.setAttribute("stroke-linejoin", "round"); el.setAttribute("aria-hidden", "true");
  el.classList.add("ic");
  const p = document.createElementNS(SVGNS, "path");
  p.setAttribute("d", P[name] || P.info);
  el.appendChild(p);
  return el;
}

export const wlogo = () => h("div", { class: "wlogo", "aria-hidden": "true" }, "W");
export const wmsg = (text, opts = {}) => h("div", { class: "wmsg" + (opts.one ? " one" : "") }, wlogo(), h("div", { class: "txt", title: opts.one ? (typeof text === "string" ? text : "") : null }, text));
export const aitag = (t = "AI 생성 · 개략") => h("span", { class: "aitag" }, t);

// ── 토스트 ──
export function toast(msg, kind = "") {
  let box = document.getElementById("toasts");
  if (!box) { box = h("div", { id: "toasts" }); document.body.appendChild(box); }
  const t = h("div", { class: "toast " + kind, role: "status" }, msg);
  box.appendChild(t);
  setTimeout(() => t.remove(), kind === "err" ? 6000 : 3200);
}

// ── 팝오버 · 메뉴 · 모달 ──
let openPop = null;
export function closePop() { if (openPop) { openPop.remove(); openPop = null; } }
document.addEventListener("pointerdown", e => { if (openPop && !openPop.contains(e.target) && !e.target.closest("[data-pop-anchor]")) closePop(); }, true);
document.addEventListener("keydown", e => { if (e.key === "Escape") closePop(); });

export function popover(anchor, content, cls = "pop") {
  closePop();
  const el = h("div", { class: cls }, content);
  document.body.appendChild(el);
  const r = anchor.getBoundingClientRect();
  const w = el.offsetWidth, hh = el.offsetHeight;
  let x = Math.min(r.left, window.innerWidth - w - 12);
  let y = r.bottom + 6;
  if (y + hh > window.innerHeight - 10) y = Math.max(10, r.top - hh - 6);
  el.style.left = Math.max(10, x) + "px";
  el.style.top = y + "px";
  openPop = el;
  return el;
}

export function menu(anchor, items) {
  const box = h("div", {}, items.map(it => it === "-" ? h("div", { class: "sep" }) :
    h("button", { class: it.danger ? "danger" : "", disabled: it.disabled, onclick: () => { closePop(); it.run(); } }, it.icon ? icon(it.icon, 14) : null, it.label,
      it.hint ? h("span", { class: "faint small", style: { marginLeft: "auto" } }, it.hint) : null)));
  return popover(anchor, box, "menu");
}

export function modal(title, body, actions = []) {
  return new Promise(resolve => {
    const bg = h("div", { class: "modal-bg" });
    const close = v => { bg.remove(); document.removeEventListener("keydown", onKey); resolve(v); };
    const onKey = e => { if (e.key === "Escape") close(null); };
    document.addEventListener("keydown", onKey);
    bg.addEventListener("pointerdown", e => { if (e.target === bg) close(null); });
    const box = h("div", { class: "modal", role: "dialog", "aria-label": title },
      h("h3", {}, title), body,
      h("div", { class: "acts" }, actions.map(a => h("button", { class: "btn " + (a.cls || ""), onclick: () => close(a.value !== undefined ? a.value : a.label) }, a.label))));
    bg.appendChild(box);
    document.body.appendChild(bg);
    const f = box.querySelector("input,textarea,button.primary");
    if (f) setTimeout(() => f.focus(), 30);
  });
}
export const confirmBox = (title, text, ok = "확인", cls = "primary") =>
  modal(title, h("p", { class: "muted", style: { margin: "4px 0 0" } }, text), [{ label: "취소", value: false }, { label: ok, value: true, cls }]);

// ── 파일 ──
export function downloadBlob(blob, name) {
  const a = h("a", { href: URL.createObjectURL(blob), download: name });
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}
export const readAsDataURL = file => new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result); r.onerror = rej; r.readAsDataURL(file); });
export function loadImage(src) {
  return new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => rej(new Error("이미지를 열지 못했어요")); im.src = src; });
}
// 긴 변을 maxSide 로 줄여 JPEG data URL — 업로드 전 브라우저에서(I2T_MAX_IMAGE_SIDE_PX)
export async function resizeImage(file, maxSide = 1536, quality = 0.86) {
  const url = await readAsDataURL(file);
  if (file.type === "application/pdf") return { url, w: 0, h: 0, pdf: true };
  const im = await loadImage(url);
  const k = Math.min(1, maxSide / Math.max(im.naturalWidth, im.naturalHeight));
  const w = Math.round(im.naturalWidth * k), hh = Math.round(im.naturalHeight * k);
  const c = h("canvas", { width: w, height: hh });
  c.getContext("2d").drawImage(im, 0, 0, w, hh);
  return { url: c.toDataURL("image/jpeg", quality), w, h: hh, ow: im.naturalWidth, oh: im.naturalHeight };
}
export function pickFiles(accept, multiple = false) {
  return new Promise(res => {
    const inp = h("input", { type: "file", accept, multiple, style: { display: "none" } });
    inp.addEventListener("change", () => { res([...inp.files]); inp.remove(); });
    document.body.appendChild(inp);
    inp.click();
  });
}
