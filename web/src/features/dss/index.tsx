/**
 * 공간별 제품 매칭 DSS(DS) 기능 모듈 — 소유: dss 서비스 세션. 수용 기준: docs/scenarios/11-content-flow.md(§1 · §4 · §6)
 * 보드 webapp1 v62: DS0(List) · 최종본(View content=dss · DS_View · DS_Draft) + 단계 팝업 DS1(Gate) · DS2 · DS2_AI · DS4 · DS4_AI · DS2_Edit · DS4_Edit.
 * 라우트: /dss(DS0) · /dss/new(빈 최종본 + ① 팝업 · `?sb=&auto=1`) · /dss/:id(최종본 · `?step=space|solution` 팝업)
 */
import { feature } from '@/shell/feature';
import { DsDetailPage, DsListScreen, DsNewPage } from './DsPages';

export default feature({
  code: 'DS',
  key: 'dss',
  name: '공간별 제품 매칭 DSS',
  order: 3,
  home: { section: 'plan', title: '공간별 제품 매칭 DSS', desc: '업종 · 공간을 정하고 공간마다 제품 · 솔루션을 골라요.', feeds: '공간 시나리오 · Spec 시트' },
  routes: [
    { index: true, element: <DsListScreen /> },
    { path: 'new', element: <DsNewPage /> },
    { path: ':id', element: <DsDetailPage /> },
  ],
});
