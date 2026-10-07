// 3D 화면 공통 — 작업 불러오기 · 부분 저장 · 렌더 작업 지켜보기 · 라벨
import { api, library } from "./api.js";
import { frame, STEPS_3D } from "./shell.js";

export async function load3d(id) {
  const p = await api.get(`/api/projects/${id}`);
  if (p.kind !== "3d") throw Object.assign(new Error("3D 작업이 아니에요"), { status: 400 });
  return p;
}
export const patch3d = (id, set) => api.post(`/api/projects/${id}/patch`, { set });

export function frame3d(p, cur, opts = {}) {
  return frame({
    project: p, title: p.title, steps: STEPS_3D, cur, complete: opts.complete, fill: opts.fill,
    onRename: t => patch3d(p.id, { title: t }),
  });
}

export async function labels() {
  const lib = await library();
  const m = lib.materials;
  const lab = (obj, k) => (obj && obj[k] && (obj[k].label || obj[k])) || k;
  return {
    lib,
    concept: k => lab(m.concepts, k), floor: k => lab(m.floors, k), wall: k => lab(m.walls, k), accent: k => lab(m.accents, k),
    fabric: k => lab(m.fabrics, k), mood: k => lab(m.moods, k), light: k => lab(m.lighting, k), camera: k => lab(m.cameras, k),
    plants: k => ({ none: "식물 없음", few: "식물 조금", some: "식물 적당히", many: "식물 많이" }[k] || k),
    content: k => lab(m.screen_contents, k),
    furn: t => { const f = lib.furniture.find(x => x.type === t); return f ? f.label : t; },
    space: c => { const s = lib.space_types.find(x => x.code === c); return s ? s.label : c; },
  };
}

// 렌더 작업 지켜보기 — 1초마다 상태를 받아 onUpdate(job). 끝나면 onDone(job).
export function watchJob(jid, onUpdate, onDone) {
  let stop = false, t = null;
  const tick = async () => {
    if (stop) return;
    try {
      const j = await api.get(`/api/jobs/${jid}`, { quiet: true });
      onUpdate(j);
      if (["done", "failed", "cancelled"].includes(j.status)) { stop = true; if (onDone) onDone(j); return; }
    } catch (e) {
      if (e.status === 404) { stop = true; if (onDone) onDone({ id: jid, status: "lost", error: "작업 정보를 찾지 못했어요 — 서버를 다시 켰다면 사라져요" }); return; }
    }
    t = setTimeout(tick, 1000);
  };
  tick();
  return () => { stop = true; clearTimeout(t); };
}

export async function activeJob(pid) {
  const r = await api.get(`/api/projects/${pid}/jobs`, { quiet: true }).catch(() => ({ items: [] }));
  return r.items[0] || null;
}

export const fileUrl = (pid, rel) => `/files/${pid}/${rel}`;
export const CAMS = [["aerial45", "조감 45°"], ["entrance", "입구"], ["eye", "눈높이"], ["top", "탑뷰"]];
export const LIGHTS = [["day", "주간"], ["evening", "저녁"], ["night", "야간"]];
export const cutLabel = r => r.label || `${r.camera} · ${r.lighting}`;
export const QUALITY_TIME = { draft: "컷당 약 30초–1분", standard: "컷당 약 1–4분", high: "컷당 수 분–수십 분 (GPU 권장)" };
