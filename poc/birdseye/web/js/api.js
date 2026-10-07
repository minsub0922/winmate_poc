// 서버 API — JSON 요청 · 오류 문구 · 파일 내려받기
import { toast } from "./dom.js";

export class ApiError extends Error {
  constructor(status, msg) { super(msg); this.status = status; }
}

async function req(method, path, body, opts = {}) {
  const init = { method, headers: {} };
  if (body !== undefined) { init.headers["Content-Type"] = "application/json"; init.body = JSON.stringify(body); }
  let r;
  try { r = await fetch(path, init); }
  catch (e) { const err = new ApiError(0, "서버에 연결하지 못했어요 — run.py 가 켜져 있는지 확인해 주세요"); if (!opts.quiet) toast(err.message, "err"); throw err; }
  if (opts.raw) {
    if (!r.ok) { const t = await r.text(); let msg = t; try { msg = JSON.parse(t).error || t; } catch (_) { /* text */ } const err = new ApiError(r.status, msg); if (!opts.quiet) toast(msg, "err"); throw err; }
    return r;
  }
  const text = await r.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch (_) { data = { error: text }; }
  if (!r.ok) {
    const err = new ApiError(r.status, (data && data.error) || `오류 ${r.status}`);
    if (!opts.quiet) toast(err.message, "err");
    throw err;
  }
  return data;
}

export const api = {
  get: (p, o) => req("GET", p, undefined, o),
  post: (p, b = {}, o) => req("POST", p, b, o),
  put: (p, b, o) => req("PUT", p, b, o),
  del: (p, o) => req("DELETE", p, undefined, o),
  raw: (m, p, b, o = {}) => req(m, p, b, { ...o, raw: true }),
  async blob(method, path, body) {
    const r = await req(method, path, body, { raw: true });
    const cd = r.headers.get("Content-Disposition") || "";
    const m = /filename\*=UTF-8''([^;]+)/.exec(cd);
    return { blob: await r.blob(), name: m ? decodeURIComponent(m[1]) : null };
  },
};

// 자주 쓰는 공용 데이터(한 번만 받아 둠)
let _lib = null;
export async function library() { if (!_lib) _lib = await api.get("/api/library"); return _lib; }
const _prod = new Map();
export async function product(code) {
  if (!code) return null;
  if (!_prod.has(code)) _prod.set(code, api.get("/api/catalog/item?code=" + encodeURIComponent(code), { quiet: true }).catch(() => null));
  return _prod.get(code);
}
export async function products(codes) { const out = {}; await Promise.all([...new Set(codes)].map(async c => { out[c] = await product(c); })); return out; }
export function rememberProducts(items) { for (const p of items || []) if (p && p.code && !_prod.has(p.code)) _prod.set(p.code, Promise.resolve(p)); }
