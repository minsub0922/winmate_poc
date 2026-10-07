// 앱 틀 — 사이드바(작업 · 환경 상태) · 상단 바 · 단계 표시 · 본문 · 하단 바
import { api } from "./api.js";
import { h, icon, replace, popover, when, toast } from "./dom.js";

export const STEPS_2D = [["space", "공간 · 치수"], ["products", "제품 · 수량"], ["layout", "배치 · 동선"], ["done", "2D 조감도 완성"]];
export const STEPS_3D = [["brief", "요구사항"], ["build", "AI 구성 · 렌더링"], ["result", "3D 조감도 결과"]];
const ORDER_2D = { space: 0, plan: 0, products: 1, layout: 2, zones: 2, done: 3, export: 3 };
const ORDER_3D = { brief: 0, photos: 0, build: 1, result: 2, cuts: 2, export: 2 };

export const go = hash => { if (location.hash !== hash) location.hash = hash; else window.dispatchEvent(new HashChangeEvent("hashchange")); };
export const link2d = (id, step) => `#/2d/${id}/${step}`;
export const link3d = (id, step) => `#/3d/${id}/${step}`;
export function openProject(p) {
  if (p.kind === "2d") return go(link2d(p.id, p.status === "done" ? "done" : (p.step === "plan" ? "space" : p.step || "space")));
  if (p.status === "building") return go(link3d(p.id, "build"));
  return go(link3d(p.id, (p.renders && p.renders.length) || p.status === "done" ? "result" : (p.step === "photos" ? "photos" : "brief")));
}

let env = null;
let envWaiters = [];
export async function getEnv(refresh = false) {
  if (env && !refresh) return env;
  env = await api.get("/api/env", { quiet: true }).catch(() => null);
  envWaiters.forEach(f => f(env)); envWaiters = [];
  renderEnv();
  if (env && env.blender && env.blender.note === "확인 중…") setTimeout(() => getEnv(true), 1500);
  return env;
}

let sideRecent, sideEnv, mainEl, navList;
export function initShell(root) {
  sideRecent = h("div", { class: "side-recent side-sec" });
  sideEnv = h("div", { class: "side-env" });
  navList = h("div", { class: "side-sec" },
    h("a", { class: "side-a", href: "#/", "data-nav": "list" }, icon("list", 16), "작업 목록"),
    h("a", { class: "side-a", href: "#/map", "data-nav": "map" }, icon("map", 16), "유스케이스 맵"));
  mainEl = h("main", { class: "main" });
  replace(root, h("div", { class: "app" },
    h("aside", { class: "sidebar" },
      h("div", { class: "brand" }, h("div", { class: "wlogo" }, "W"), h("div", {}, h("div", { class: "t1" }, "Winmate"), h("div", { class: "t2" }, "공간 조감도 생성 · PoC"))),
      navList, h("div", { class: "side-h", style: { padding: "12px 20px 0" } }, "최근 작업"), sideRecent, sideEnv),
    mainEl));
  getEnv();
  setInterval(() => getEnv(true), 60000);
}

export async function refreshSidebar(currentId, nav) {
  for (const a of navList.querySelectorAll("[data-nav]")) a.classList.toggle("on", a.dataset.nav === nav);
  const d = await api.get("/api/projects", { quiet: true }).catch(() => ({ items: [] }));
  replace(sideRecent, d.items.slice(0, 9).map(p =>
    h("a", { class: "side-a" + (p.id === currentId ? " on" : ""), href: "#", title: p.title, onclick: e => { e.preventDefault(); openProject(p); } },
      h("span", { class: "kind" }, p.kind.toUpperCase()), h("span", { class: "ellipsis" }, p.title))));
  if (!d.items.length) replace(sideRecent, h("div", { class: "faint small", style: { padding: "4px 10px" } }, "아직 없어요"));
}

function envRows() {
  if (!env) return [["서버", false, "연결 안 됨"]];
  const llm = env.llm, i2t = env.i2t, b = env.blender, kb = env.kb;
  const modelTxt = m => m.available ? `${m.model}${m.mode !== "live" ? " · " + m.mode : ""}` : "규칙 기반";
  return [
    ["LLM", llm.available, modelTxt(llm), llm.reason],
    ["이미지", i2t.available, modelTxt(i2t), i2t.reason],
    ["Blender", !!b.kind, b.kind ? (b.version || "").split(" ")[0] : (b.note === "확인 중…" ? "확인 중…" : "없음"), b.note],
    ["KB", kb.available, kb.available ? "연결됨" : `내장 ${env.products_seed}종`, kb.path || "WKB_KB 미지정 — 내장 제품 시드만 사용"],
  ];
}
function renderEnv() {
  if (!sideEnv) return;
  replace(sideEnv, h("div", { class: "side-h", style: { padding: "0 0 4px" } }, "실행 환경"),
    envRows().map(([k, ok, v, why]) => h("div", { class: "envrow", title: why || "", "data-pop-anchor": "", onclick: e => envPop(e.currentTarget) },
      h("span", { class: "dot" + (ok ? " on" : "") }), h("span", { class: "envk" }, k), h("span", { class: "envv ellipsis" }, v))));
}
function envPop(anchor) {
  if (!env) return;
  const b = env.blender;
  const row = (k, v) => [h("div", { class: "k" }, k), h("div", {}, v)];
  const box = h("div", {},
    h("h4", {}, "실행 환경"),
    h("div", { class: "kv" },
      row(".env", env.env_file || "없음 — 기본값"), row("데이터", env.data_dir),
      row("LLM", `${env.llm.provider} · ${env.llm.model} · ${env.llm.mode}` + (env.llm.reason ? ` — ${env.llm.reason}` : "")),
      row("이미지 읽기", `${env.i2t.provider} · ${env.i2t.model}` + (env.i2t.reason ? ` — ${env.i2t.reason}` : "")),
      row("업로드 기본", env.upload_default_confidential ? "기밀(외부 모델로 안 보냄)" : "공개"),
      row("Blender", b.kind ? `${b.note}` : b.note), row("KB", env.kb.available ? env.kb.path : "연결 안 됨 — 내장 제품 시드 22종")),
    h("div", { class: "row", style: { marginTop: "12px", justifyContent: "flex-end" } },
      h("button", { class: "btn sm", onclick: async () => { await api.post("/api/env/refresh"); await getEnv(true); toast("환경을 다시 확인했어요"); } }, icon("refresh", 13), "다시 확인")));
  popover(anchor, box);
}

// ── 화면 틀 ──
export function frame({ project, title, crumb = "공간 조감도 생성", steps, cur, complete, fill = false, onRename }) {
  let saveEl = h("span", { class: "savest" });
  const ttl = onRename
    ? h("div", { class: "ttl grow" }, h("input", { value: title, "aria-label": "작업 이름", onchange: e => onRename(e.target.value.trim() || title) }))
    : h("div", { class: "ttl grow ellipsis" }, title);
  const top = h("header", { class: "topbar" }, h("span", { class: "crumb" }, h("a", { href: "#/" }, crumb), "  /"), ttl, saveEl,
    project ? h("span", { class: "tag " + (project.kind === "2d" ? "k2d" : "k3d") }, project.kind.toUpperCase()) : null);
  const content = h("section", { class: "content" + (fill ? " fill" : "") });
  const bottom = h("footer", { class: "bottombar hidden" });
  const parts = [top];
  if (steps && project) parts.push(stepper(project, steps, cur, complete));
  parts.push(content, bottom);
  replace(mainEl, parts);
  return {
    content, bottom,
    setBottom(...kids) { bottom.classList.toggle("hidden", !kids.length); replace(bottom, kids.length ? h("div", { class: "bar" }, kids) : []); },
    setSave(state) {
      const map = { saved: ["자동 저장됨", "on"], saving: ["저장 중…", "half"], dirty: ["바뀐 내용 있음", ""], error: ["저장 실패", ""] };
      const [t, d] = map[state] || ["", ""];
      replace(saveEl, t ? [h("span", { class: "dot " + d }), t] : []);
    },
  };
}

function stepper(project, steps, cur, complete) {
  const is2d = project.kind === "2d";
  const order = is2d ? ORDER_2D : ORDER_3D;
  const reached = complete ? steps.length - 1 : Math.max(order[project.step] ?? 0, order[cur] ?? 0, project.status === "done" ? steps.length - 1 : 0,
    !is2d && (project.renders || []).length ? 2 : 0);
  const curIdx = order[cur] ?? 0;
  const items = [];
  steps.forEach(([key, label], i) => {
    if (i) items.push(h("span", { class: "step-sep" }));
    const done = complete || i < curIdx;
    const canGo = i <= reached && i !== curIdx;
    items.push(h(canGo ? "a" : "span", {
      class: "step" + (i === curIdx && !complete ? " cur" : "") + (done ? " done" : "") + (canGo ? " link" : ""),
      href: canGo ? (is2d ? link2d(project.id, key) : link3d(project.id, key)) : null,
    }, h("span", { class: "n" }, done ? "✓" : i + 1), label));
  });
  return h("nav", { class: "stepper", "aria-label": "단계" }, items,
    h("span", { class: "kindchip small muted" }, is2d ? "정확한 배치 · 수치 — 사용자가 정해요" : "공간 분위기 · 개략 — AI가 정해요"));
}

export function setMainLoading(text = "불러오는 중…") {
  replace(mainEl, h("div", { class: "content", style: { display: "flex", alignItems: "center", justifyContent: "center", gap: "10px", color: "var(--muted)" } }, h("span", { class: "spin" }), text));
}
export function mainError(msg) {
  replace(mainEl, h("div", { class: "content" }, h("div", { class: "empty" }, h("div", { style: { fontSize: "15px", color: "var(--text)", marginBottom: "6px" } }, msg),
    h("a", { class: "btn", href: "#/" }, "작업 목록으로"))));
}
export { when };
