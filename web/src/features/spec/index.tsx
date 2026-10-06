/**
 * Spec 시트 생성(SP) 기능 모듈 — 소유: spec 서비스 세션. 수용 기준: docs/scenarios/06-spec.md
 * 셸이 자동으로 등록한다(web/src/shell/registry.ts). 라우트: /spec(목록) · /spec/new(/find · /requirements) · /spec/:id/*
 */
import { useRef, type ComponentType } from 'react';
import { useParams } from 'react-router';
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

/**
 * 다른 작업으로 옮겨 가면 화면 상태를 새로 시작한다(같은 라우트 · 다른 :id).
 * `/spec/new…` 에서 첫 입력으로 작업이 막 만들어져 `/spec/:id/…` 로 바뀔 때는 같은 화면을 이어 간다(진행 중인 잡 · 입력 유지).
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

export default feature({
  code: 'SP',
  key: 'spec',
  name: 'Spec 시트 생성',
  order: 9,
  home: { section: 'plan', title: 'Spec 시트', desc: '조건으로 모델 찾기 · 스펙 대응표' },
  routes: [
    { index: true, element: <ListPage /> },
    { path: 'new', element: k(ProductsPage) },
    { path: 'new/find', element: k(FindPage) },
    { path: 'new/requirements', element: k(RequirementsPage) },
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
