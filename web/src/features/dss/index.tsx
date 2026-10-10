/**
 * 공간별 제품 매칭 DSS(DS) 기능 모듈 — 소유: dss 서비스 세션. 수용 기준: docs/scenarios/11-content-flow.md(§1 · §4 · §6)
 * 보드 webapp1 v58: DS0(List) · DS1(Gate) · DS2 · DS2_AI(업종 · 공간 · 공간별 제품) · DS4 · DS4_AI(솔루션) · DS_Done. 셸이 자동으로 등록한다.
 * 라우트: /dss(DS0) · /dss/new(DS1 · `?sb=&auto=1`) · /dss/:id(DS2 → `?step=solution` DS4 → 저장 → DS_Done)
 */
import { feature } from '@/shell/feature';
import { DsEditPage, DsGateScreen, DsListScreen } from './DsPages';

export default feature({
  code: 'DS',
  key: 'dss',
  name: '공간별 제품 매칭 DSS',
  order: 3,
  home: { section: 'plan', title: '공간별 제품 매칭 DSS', desc: '업종 · 공간을 정하고 공간마다 제품 · 솔루션을 골라요.', feeds: '공간 시나리오 · Spec 시트' },
  routes: [
    { index: true, element: <DsListScreen /> },
    { path: 'new', element: <DsGateScreen /> },
    { path: ':id', element: <DsEditPage /> },
  ],
});
