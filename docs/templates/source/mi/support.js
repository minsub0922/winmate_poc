/*
 * Winmate 보드 오프라인 렌더러 — 아티팩트(claude.ai) 런타임 support.js 를 대신한다.
 *
 * docs/screens/webapp{1,2,3}/*.dc.html 은 원래 claude.ai 아티팩트 런타임이 그리는 템플릿이다.
 * 이 파일은 그 템플릿 문법만 구현해, 네트워크 없이(사내망에서도) 같은 화면을 그린다.
 *   - {{경로}}                 값 끼우기(글 · 속성). 속성 전체가 {{x}} 하나면 값 그대로(배열 · 객체) 넘긴다
 *   - <sc-for list as>        반복
 *   - <sc-if value>           조건
 *   - <dc-import name …>      다른 보드(컴포넌트)를 불러 그 자리에 그린다. 속성 이름은 camelCase props 로
 *   - <helmet>                <head> 로 옮긴다
 *   - <script data-dc-script> class Component extends DCLogic { renderVals() } · data-props 의 default
 * 상호작용(setState)은 첫 화면만 그린다. 다 그리면 window.__dcReady = true.
 *
 * 보기:  python3 -m http.server 5099 --directory docs  →  http://localhost:5099/screens/webapp1/CA4.dc.html
 *                                                            http://localhost:5099/templates/source/mi/L_MI_RT_B.dc.html
 *        (file:// 로 열면 브라우저가 dc-import 파일 읽기를 막는다)
 * 원본은 docs/screens/_runtime/support.js — docs/screens/webapp* · docs/templates/source/* 의 support.js 는 같은 파일의 복사본이다
 *   (render.mjs 가 복사하고 부모 폴더에 dc-dirs.json 을 쓴다).
 */
(function () {
  'use strict';

  class DCLogic {
    constructor(props) { this.props = props || {}; this.state = {}; }
    setState(s) { Object.assign(this.state, typeof s === 'function' ? s(this.state) : s); }
    renderVals() { return {}; }
  }
  window.DCLogic = DCLogic;

  const docCache = new Map();
  const dirsCache = new Map();
  const headDone = new Set();

  function baseDir(url) { return url.slice(0, url.lastIndexOf('/') + 1); }
  function parentDir(dir) { return dir.replace(/[^/]+\/$/, ''); }

  // 같은 묶음의 다른 폴더(예: webapp1 · 2 · 3, common · mi · vp …) — 부모 폴더의 dc-dirs.json
  async function siblingDirs(root) {
    if (!dirsCache.has(root)) {
      dirsCache.set(root, fetch(root + 'dc-dirs.json').then((r) => (r.ok ? r.json() : [])).catch(() => []));
    }
    return dirsCache.get(root);
  }

  async function loadBoard(name, fromUrl) {
    const here = baseDir(fromUrl);
    const root = parentDir(here);
    const tries = [here + name + '.dc.html', ...(await siblingDirs(root)).map((d) => root + d + '/' + name + '.dc.html')];
    for (const u of tries) {
      if (docCache.has(u)) return docCache.get(u);
      try {
        const r = await fetch(u);
        if (!r.ok) continue;
        const doc = new DOMParser().parseFromString(await r.text(), 'text/html');
        const hit = { doc, url: u };
        docCache.set(u, hit);
        return hit;
      } catch (e) { /* 다음 후보 */ }
    }
    return null;
  }

  function componentOf(doc) {
    const s = doc.querySelector('script[data-dc-script]');
    let spec = {};
    try { spec = JSON.parse((s && s.getAttribute('data-props')) || '{}'); } catch (e) { spec = {}; }
    const defaults = {};
    for (const [k, v] of Object.entries(spec)) {
      if (k.startsWith('$')) continue;
      if (v && typeof v === 'object' && 'default' in v) defaults[k] = v.default;
    }
    let Cls = DCLogic;
    if (s) {
      try { Cls = new Function('DCLogic', s.textContent + '\n;return Component;')(DCLogic); }
      catch (e) { console.error('[dc] script', e); }
    }
    return { Cls, defaults, preview: spec.$preview || null };
  }

  function evalExpr(expr, scope) {
    const e = expr.trim();
    if (/^[A-Za-z_$][\w$]*(\.[\w$]+)*$/.test(e)) {
      let v = scope;
      for (const k of e.split('.')) { if (v == null) return undefined; v = v[k]; }
      return v;
    }
    try { return new Function('scope', 'with (scope) { return (' + e + '); }')(scope); }
    catch (err) { return undefined; }
  }

  const WHOLE = /^\s*\{\{([\s\S]+?)\}\}\s*$/;
  function interpRaw(str, scope) {
    const m = WHOLE.exec(str);
    if (m) return evalExpr(m[1], scope);
    return interpStr(str, scope);
  }
  function interpStr(str, scope) {
    return str.replace(/\{\{([\s\S]+?)\}\}/g, (_, e) => {
      const v = evalExpr(e, scope);
      return v == null || v === false ? '' : String(v);
    });
  }
  const camel = (s) => s.replace(/-([a-z])/g, (_, c) => c.toUpperCase());

  async function renderChildren(parent, scope, ctx, out) {
    for (const n of Array.from(parent.childNodes)) await renderNode(n, scope, ctx, out);
  }

  async function renderNode(n, scope, ctx, out) {
    if (n.nodeType === 3) { out.appendChild(document.createTextNode(interpStr(n.textContent, scope))); return; }
    if (n.nodeType !== 1) return;
    const tag = n.tagName.toLowerCase();

    if (tag === 'script') return;
    if (tag === 'helmet') {
      if (!headDone.has(ctx.url)) {
        headDone.add(ctx.url);
        for (const h of Array.from(n.children)) document.head.appendChild(document.importNode(h, true));
      }
      return;
    }
    if (tag === 'sc-for') {
      const list = interpRaw(n.getAttribute('list') || '', scope);
      const as = n.getAttribute('as') || 'item';
      const arr = Array.isArray(list) ? list : (list && typeof list === 'object' ? Object.values(list) : []);
      for (let i = 0; i < arr.length; i++) await renderChildren(n, Object.assign(Object.create(scope), { [as]: arr[i], $index: i }), ctx, out);
      return;
    }
    if (tag === 'sc-if') {
      if (interpRaw(n.getAttribute('value') || '', scope)) await renderChildren(n, scope, ctx, out);
      return;
    }
    if (tag === 'dc-import') {
      const name = n.getAttribute('name');
      const props = {};
      for (const a of Array.from(n.attributes)) {
        if (a.name === 'name' || a.name.startsWith('hint-')) continue;
        props[camel(a.name)] = interpRaw(a.value, scope);
      }
      const wrap = document.createElement('div');
      wrap.setAttribute('data-dc-import', name);
      wrap.style.display = 'contents';
      out.appendChild(wrap);
      const hit = await loadBoard(name, ctx.url);
      if (!hit) { wrap.textContent = '[' + name + ' 없음]'; return; }
      await renderBoard(hit.doc, hit.url, props, wrap);
      return;
    }
    const el = n.cloneNode(false);
    for (const a of Array.from(el.attributes)) {
      if (a.value.includes('{{')) {
        const v = interpRaw(a.value, scope);
        if (v == null || v === false) el.removeAttribute(a.name);
        else el.setAttribute(a.name, typeof v === 'object' ? JSON.stringify(v) : String(v));
      }
    }
    out.appendChild(el);
    await renderChildren(tag === 'template' ? n.content : n, scope, ctx, el);
  }

  async function renderBoard(doc, url, props, out) {
    const { Cls, defaults } = componentOf(doc);
    const inst = new Cls(Object.assign({}, defaults, props || {}));
    let vals = {};
    try { vals = inst.renderVals() || {}; } catch (e) { console.error('[dc] renderVals', url, e); }
    const scope = Object.assign({ props: inst.props, state: inst.state }, vals);
    const root = doc.querySelector('x-dc');
    if (root) await renderChildren(root, scope, { url }, out);
  }

  async function main() {
    const root = document.querySelector('x-dc');
    if (!root) { window.__dcReady = true; return; }
    const src = root.cloneNode(true);
    const host = document.createElement('div');
    host.setAttribute('data-dc-root', '');
    host.style.display = 'contents';
    root.replaceWith(host);
    const shadowDoc = document.implementation.createHTMLDocument('');
    shadowDoc.body.appendChild(shadowDoc.importNode(src, true));
    const script = document.querySelector('script[data-dc-script]');
    if (script) shadowDoc.body.appendChild(shadowDoc.importNode(script, true));
    try { await renderBoard(shadowDoc, location.href, {}, host); }
    catch (e) { console.error('[dc] render', e); }
    window.__dcReady = true;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', main);
  else main();
})();
