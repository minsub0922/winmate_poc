/**
 * 공간 시나리오(SC) 기능 모듈 — 소유: scenario 서비스 세션. 수용 기준: docs/scenarios/11-content-flow.md §3 · §6(새 흐름) · 09-scenario.md(이전 흐름)
 * 보드: docs/screens/webapp1/SC*.dc.html(새 흐름) · webapp2/SC*.dc.html(이전 흐름). 셸이 자동으로 등록한다(web/src/shell/registry.ts).
 *
 * 라우트 — 새 콘텐츠 흐름(웹앱 ① v58, Storyboard 허브):
 *   /scenario(SC0 List content=sc) · /scenario/new(SC1 Gate · `?sb=&auto=1` 바로 만들기) · /scenario/spaces/:id(SC2 · SC_Done)
 * 이전 흐름(제안서 handoff 가 아직 읽는다): /scenario/legacy(SC0) · legacy/new(SC1) · legacy/new/template(SC1T) · legacy/new/birdseye(SC1B)
 *   :id/type(SC1) · :id/input(SC2) · :id/timeline(SC2E) · :id/solutions(SC3) · :id/solutions/recommend(SC3R)
 *   :id/generate/:jobId(SC4G) · :id/result(SC4) · :id/scenes/:sceneId(SC4E) · :id/send(SC5) · :id/birdseye(SC1B 변경 반영)
 *   uc(UC_SC 유스케이스 맵 — 개발용)
 * 옛 주소(다른 기능 화면 · 서버 handoff 가 만드는 링크)는 주소를 바꾸지 않고 이전 화면을 그대로 연다:
 *   /scenario?image_version=(IMG4 장면 이미지 돌려받기 → 이전 목록) · /scenario/new?sb=sb_…(이전 Storyboard SB4) · ?from=|mi=|project=(MI4 · VP4 재료) → 이전 SC1
 *   new/template · new/birdseye(조감도 「시나리오로 이어 만들기」) → 이전 SC1T · SC1B. spaces/new → /scenario/new.
 */
import { lazy, Suspense, type ReactNode } from 'react';
import { Navigate, useLocation, useSearchParams } from 'react-router';
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
const ScListScreen = lazy(() => import('./spaces/FlowPages').then((m) => ({ default: m.ScListScreen })));
const ScGateScreen = lazy(() => import('./spaces/FlowPages').then((m) => ({ default: m.ScGateScreen })));

/** 옛 주소 → 새 주소(쿼리 그대로) */
function Moved({ to }: { to: string }) {
  const loc = useLocation();
  return <Navigate to={`${to}${loc.search}`} replace state={loc.state} />;
}

/** `/scenario` — IMG4 돌려받기(`?image_version=`)는 이전 목록이 처리한다 */
function ListEntry() {
  const [sp] = useSearchParams();
  return sp.get('image_version') ? L(<ListPage />) : L(<ScListScreen />);
}

/** 새 흐름 Storyboard(허브) 번호 — 이전 Storyboard 는 `sb_…` */
const HUB_SB = /^SB-\d+$/;

/** `/scenario/new` — 허브 Storyboard(`?sb=SB-01&auto=1`)나 아무 재료 없음 = Gate, 이전 handoff(`?sb=sb_…` · `?from=` · `?mi=` · `?project=`) = 이전 SC1 */
function NewEntry() {
  const [sp] = useSearchParams();
  const sb = sp.get('sb');
  const legacy = sb ? !HUB_SB.test(sb) : !!(sp.get('from') || sp.get('mi') || sp.get('project'));
  return legacy ? L(<TypePage />) : L(<ScGateScreen />);
}

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
    // 새 콘텐츠 흐름(웹앱 ① v58): 목록(SC0) · 사전 작업 고르기(SC1) → 공간 → 시나리오 → 장면(SC2) → 완료(SC_Done)
    { index: true, element: <ListEntry /> },
    { path: 'new', element: <NewEntry /> },
    { path: 'spaces/new', element: <Moved to="/scenario/new" /> },
    { path: 'spaces/:id', element: L(<SpacesPage />) },
    // 이전 흐름 — /scenario/legacy(제안서 handoff 가 아직 읽는다)
    { path: 'legacy', element: L(<ListPage />) },
    { path: 'legacy/new', element: L(<TypePage />) },
    { path: 'legacy/new/template', element: L(<TemplatePage />) },
    { path: 'legacy/new/birdseye', element: L(<BirdseyePage />) },
    { path: 'new/template', element: L(<TemplatePage />) },       // 옛 주소(같은 화면)
    { path: 'new/birdseye', element: L(<BirdseyePage />) },
    { path: 'uc', element: L(<UseCasePage />) },
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
