/**
 * Spec 시트 생성(SP) 기능 모듈 — 소유: spec 서비스 세션. 셸이 자동으로 등록한다(web/src/shell/registry.ts).
 * 새 흐름(2026-10-08 · docs/scenarios/11-content-flow.md §6 · 보드 webapp1 SP0 · SP1 · SP2 · SP_Done) — ./flow/
 *   /spec(SP0 List) · /spec/new(SP1 Gate · `?sb=&auto=1`) · /spec/flow/:id(SP2 시트 작성 → SP_Done)
 * 이전 흐름(제안서 handoff 가 아직 읽는다 · 수용 기준 docs/scenarios/06-spec.md):
 *   /spec/legacy(목록) · /spec/legacy/new(/find · /requirements) — `/spec/new?models=|from=|pop=` 도 이리로 · /spec/:id/*(그대로)
 */
import { useRef, type ComponentType } from 'react';
import { Navigate, useLocation, useParams } from 'react-router';
import { feature } from '@/shell/feature';
import EditPage from './EditPage';
import ExportPage from './ExportPage';
import FindPage from './FindPage';
import FormatPage from './FormatPage';
import GeneratingPage from './GeneratingPage';
import ItemsPage from './ItemsPage';
import ListPage from './ListPage';
import ProductsPage from './ProductsPage';
import RequirementsPage from './RequirementsPage';
import ResultPage from './ResultPage';
import WarningsPage from './WarningsPage';
import { SpGateScreen, SpListScreen } from './flow/FlowPages';
import { SheetPage } from './flow/SheetPage';

/**
 * 다른 작업으로 옮겨 가면 화면 상태를 새로 시작한다(같은 라우트 · 다른 :id).
 * `/spec/legacy/new…` 에서 첫 입력으로 작업이 막 만들어져 `/spec/:id/…` 로 바뀔 때는 같은 화면을 이어 간다(진행 중인 잡 · 입력 유지).
 */
function Keyed({ C }: { C: ComponentType }) {
  const { id } = useParams();
  const st = useRef<{ gen: number; isNew: boolean; adopted?: string; id?: string }>({ gen: 0, isNew: !id, id });
  const s = st.current;
  if (!id) {
    if (!s.isNew || s.adopted) Object.assign(s, { gen: s.gen + 1, isNew: true, adopted: undefined, id: undefined });
  } else if (s.isNew) {
    if (!s.adopted) s.adopted = id;
    else if (s.adopted !== id) Object.assign(s, { gen: s.gen + 1, isNew: false, adopted: undefined, id });
  } else if (s.id !== id) Object.assign(s, { gen: s.gen + 1, id });
  return <C key={s.gen} />;
}
const k = (C: ComponentType) => <Keyed C={C} />;

/** 옛 주소 `/spec/new/find` · `/spec/new/requirements` → 이전 흐름 `/spec/legacy/new/…`(쿼리 유지) */
function ToLegacy({ sub }: { sub: string }) {
  const loc = useLocation();
  return <Navigate to={`/spec/legacy/new/${sub}${loc.search}`} replace state={loc.state} />;
}

export default feature({
  code: 'SP',
  key: 'spec',
  name: 'Spec 시트 생성',
  order: 9,
  home: { section: 'plan', title: 'Spec 시트', desc: '조건으로 모델 찾기 · 스펙 대응표' },
  routes: [
    { index: true, element: <SpListScreen /> },
    { path: 'new', element: <SpGateScreen /> },
    { path: 'flow/:id', element: <SheetPage /> },
    // 이전 흐름 — 목록 · 새로 만들기만 /legacy 로 옮겼다(나머지 /:id/... 그대로)
    { path: 'legacy', element: <ListPage /> },
    { path: 'legacy/new', element: k(ProductsPage) },
    { path: 'legacy/new/find', element: k(FindPage) },
    { path: 'legacy/new/requirements', element: k(RequirementsPage) },
    { path: 'new/find', element: <ToLegacy sub="find" /> },
    { path: 'new/requirements', element: <ToLegacy sub="requirements" /> },
    { path: ':id', element: k(ResultPage) },
    { path: ':id/products', element: k(ProductsPage) },
    { path: ':id/find', element: k(FindPage) },
    { path: ':id/requirements', element: k(RequirementsPage) },
    { path: ':id/items', element: k(ItemsPage) },
    { path: ':id/format', element: k(FormatPage) },
    { path: ':id/generating', element: k(GeneratingPage) },
    { path: ':id/warnings', element: k(WarningsPage) },
    { path: ':id/edit', element: k(EditPage) },
    { path: ':id/export', element: k(ExportPage) },
  ],
});
