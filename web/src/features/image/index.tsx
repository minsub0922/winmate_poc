/**
 * 이미지 생성(IMG) 기능 모듈 — 소유: image 서비스 세션. 수용 기준: docs/scenarios/07-image.md · 보드 docs/screens/webapp2/IMG*.dc.html
 * 셸이 자동으로 등록한다(web/src/shell/registry.ts).
 *
 * 라우트(§2): /image(IMG0) · /image/new(IMG1, ?work= · ?request=) · /image/new/references · /image/new/composite
 *   /image/w/:workId/conditions(IMG2) · references(IMG2R) · composite(IMG2P) · run/:runId(IMG3G · IMG3X) · result(IMG3, ?image=)
 *   edit/:imageId(IMG3E) · variants/:imageId(IMG3V) · export/:imageId(IMG4, ?version=)
 */
import { lazy, Suspense, type ReactNode } from 'react';
import { feature } from '@/shell/feature';
import { Spinner } from '@/ui';
import './image.css';

const ListPage = lazy(() => import('./pages/ListPage'));
const TypePage = lazy(() => import('./pages/TypePage'));
const StartPage = lazy(() => import('./pages/StartPage'));
const ConditionsPage = lazy(() => import('./pages/ConditionsPage'));
const ReferencesPage = lazy(() => import('./pages/ReferencesPage'));
const CompositePage = lazy(() => import('./pages/CompositePage'));
const RunPage = lazy(() => import('./pages/RunPage'));
const ResultPage = lazy(() => import('./pages/ResultPage'));
const EditPage = lazy(() => import('./pages/EditPage'));
const VariantsPage = lazy(() => import('./pages/VariantsPage'));
const ExportPage = lazy(() => import('./pages/ExportPage'));

const L = (el: ReactNode) => (
  <Suspense fallback={<div className="img-center"><Spinner /></div>}>{el}</Suspense>
);

export default feature({
  code: 'IMG',
  key: 'image',
  name: '이미지 생성',
  order: 3,
  home: { section: 'visual', title: '이미지 생성', desc: '공간 · 배경 · 시나리오 이미지' },
  routes: [
    { index: true, element: L(<ListPage />) },
    { path: 'new', element: L(<TypePage />) },
    { path: 'new/references', element: L(<StartPage start="references" />) },
    { path: 'new/composite', element: L(<StartPage start="composite" />) },
    { path: 'w/:workId/conditions', element: L(<ConditionsPage />) },
    { path: 'w/:workId/references', element: L(<ReferencesPage />) },
    { path: 'w/:workId/composite', element: L(<CompositePage />) },
    { path: 'w/:workId/run/:runId', element: L(<RunPage />) },
    { path: 'w/:workId/result', element: L(<ResultPage />) },
    { path: 'w/:workId/edit/:imageId', element: L(<EditPage />) },
    { path: 'w/:workId/variants/:imageId', element: L(<VariantsPage />) },
    { path: 'w/:workId/export/:imageId', element: L(<ExportPage />) },
  ],
});
