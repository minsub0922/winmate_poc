// 라우터 — 화면 코드(BE0 · BP1~BP5 · BR1~BR4)마다 한 모듈
import { initShell, refreshSidebar, setMainLoading, mainError } from "./shell.js";
import * as List from "./screens/list.js";
import * as UseCase from "./screens/usecase.js";
import * as Space from "./screens/bp1_space.js";
import * as PlanRecog from "./screens/bp1d_plan.js";
import * as Products from "./screens/bp2_products.js";
import * as Layout from "./screens/bp3_layout.js";
import * as Zones from "./screens/bp3z_zones.js";
import * as Done from "./screens/bp4_done.js";
import * as Export2D from "./screens/bp5_export.js";
import * as Brief from "./screens/br1_brief.js";
import * as Photos from "./screens/br1p_photos.js";
import * as Build from "./screens/br2_build.js";
import * as Result from "./screens/br3_result.js";
import * as Cuts from "./screens/br3v_cuts.js";
import * as Export3D from "./screens/br4_export.js";

const ROUTES = [
  [/^\/?$/, List, "list"],
  [/^\/map$/, UseCase, "map"],
  [/^\/2d\/([\w-]+)\/space$/, Space],
  [/^\/2d\/([\w-]+)\/plan$/, PlanRecog],
  [/^\/2d\/([\w-]+)\/products$/, Products],
  [/^\/2d\/([\w-]+)\/layout$/, Layout],
  [/^\/2d\/([\w-]+)\/zones$/, Zones],
  [/^\/2d\/([\w-]+)\/done$/, Done],
  [/^\/2d\/([\w-]+)\/export$/, Export2D],
  [/^\/3d\/([\w-]+)\/brief$/, Brief],
  [/^\/3d\/([\w-]+)\/photos$/, Photos],
  [/^\/3d\/([\w-]+)\/build$/, Build],
  [/^\/3d\/([\w-]+)\/result$/, Result],
  [/^\/3d\/([\w-]+)\/cuts$/, Cuts],
  [/^\/3d\/([\w-]+)\/export$/, Export3D],
];

let current = null;
let seq = 0;

async function route() {
  const my = ++seq;
  const path = (location.hash || "#/").slice(1).split("?")[0];
  if (current && current.beforeLeave) { try { await current.beforeLeave(); } catch (e) { console.warn(e); } }
  if (current && current.unmount) { try { current.unmount(); } catch (e) { console.warn(e); } }
  current = null;
  for (const [re, mod, nav] of ROUTES) {
    const m = re.exec(path);
    if (!m) continue;
    setMainLoading();
    refreshSidebar(m[1] || null, nav || null);
    try {
      const r = await mod.mount(...m.slice(1));
      if (my !== seq) { if (r && r.unmount) r.unmount(); return; }
      current = r || null;
    } catch (e) {
      console.error(e);
      if (my === seq) mainError(e.status === 404 ? "작업을 찾지 못했어요" : `화면을 열지 못했어요 — ${e.message}`);
    }
    return;
  }
  mainError("없는 화면이에요");
}

window.addEventListener("hashchange", route);
window.addEventListener("beforeunload", e => {
  if (current && current.dirty && current.dirty()) { e.preventDefault(); e.returnValue = ""; }
});
initShell(document.getElementById("root"));
route();
