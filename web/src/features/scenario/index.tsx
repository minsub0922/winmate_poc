/**
 * 공간 시나리오(SC) 기능 모듈 — 소유: scenario 서비스 세션. 수용 기준: docs/scenarios/09-scenario.md · 보드 docs/screens/webapp2/SC*.dc.html
 * 셸이 자동으로 등록한다(web/src/shell/registry.ts).
 *
 * 라우트(§2): /scenario(SC0) · /scenario/new(SC1) · new/template(SC1T) · new/birdseye(SC1B)
 *   :id/type(SC1) · :id/input(SC2) · :id/timeline(SC2E) · :id/solutions(SC3) · :id/solutions/recommend(SC3R)
 *   :id/generate/:jobId(SC4G) · :id/result(SC4) · :id/scenes/:sceneId(SC4E) · :id/send(SC5) · :id/birdseye(SC1B 변경 반영)
 *   uc(UC_SC 유스케이스 맵 — 개발용)
 *   spaces/new · spaces/:id — 새 흐름(공간 → 시나리오 → 장면, 보드 webapp1 SC2 · SC_Done)
 */
import { lazy, Suspense, type ReactNode } from 'react';
import { feature } from '@/shell/feature';
import { Spinner } from '@/ui';
import './scenario.css';

const ListPage = lazy(() => import('./pages/ListPage'));
const TypePage = lazy(() => import('./pages/TypePage'));
const TemplatePage = lazy(() => import('./pages/TemplatePage'));
const BirdseyePage = lazy(() => import('./pages/BirdseyePage'));
const InputPage = lazy(() => import('./pages/InputPage'));
const TimelinePage = lazy(() => import('./pages/TimelinePage'));
const SolutionsPage = lazy(() => import('./pages/SolutionsPage'));
const RecommendPage = lazy(() => import('./pages/RecommendPage'));
const GeneratePage = lazy(() => import('./pages/GeneratePage'));
const ResultPage = lazy(() => import('./pages/ResultPage'));
const ScenePage = lazy(() => import('./pages/ScenePage'));
const SendPage = lazy(() => import('./pages/SendPage'));
const OpenPage = lazy(() => import('./pages/OpenPage'));
const UseCasePage = lazy(() => import('./pages/UseCasePage'));
const SpacesPage = lazy(() => import('./spaces/SpacesPage').then((m) => ({ default: m.SpacesPage })));
const NewSpacesPage = lazy(() => import('./spaces/NewSpacesPage').then((m) => ({ default: m.NewSpacesPage })));

const L = (el: ReactNode) => (
  <Suspense fallback={<div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Spinner /></div>}>{el}</Suspense>
);

export default feature({
  code: 'SC',
  key: 'scenario',
  name: '공간 시나리오 생성',
  order: 5,
  home: { section: 'visual', title: '공간 시나리오', desc: '장면 · 솔루션 · 장면 이미지' },
  routes: [
    { index: true, element: L(<ListPage />) },
    { path: 'new', element: L(<TypePage />) },
    { path: 'new/template', element: L(<TemplatePage />) },
    { path: 'new/birdseye', element: L(<BirdseyePage />) },
    { path: 'uc', element: L(<UseCasePage />) },
    // 새 흐름(2026-10-08 보드 webapp1 SC2): 공간 → 시나리오(여러 개) → 장면 · 공간 / 시나리오별 제품 · 솔루션
    { path: 'spaces/new', element: L(<NewSpacesPage />) },
    { path: 'spaces/:id', element: L(<SpacesPage />) },
    { path: ':id', element: L(<OpenPage />) },
    { path: ':id/type', element: L(<TypePage />) },
    { path: ':id/input', element: L(<InputPage />) },
    { path: ':id/timeline', element: L(<TimelinePage />) },
    { path: ':id/solutions', element: L(<SolutionsPage />) },
    { path: ':id/solutions/recommend', element: L(<RecommendPage />) },
    { path: ':id/generate/:jobId', element: L(<GeneratePage />) },
    { path: ':id/result', element: L(<ResultPage />) },
    { path: ':id/scenes/:sceneId', element: L(<ScenePage />) },
    { path: ':id/send', element: L(<SendPage />) },
    { path: ':id/birdseye', element: L(<BirdseyePage resync />) },
  ],
});
