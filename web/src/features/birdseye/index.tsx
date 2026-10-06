/**
 * 공간 조감도 생성(BE) 기능 모듈 — 소유: birdseye 서비스 세션. 수용 기준: docs/scenarios/08-birdseye.md · 보드 docs/screens/webapp2/BE*.dc.html
 * 셸이 자동으로 등록한다(web/src/shell/registry.ts).
 *
 * 라우트(§2): /birdseye(BE0) · /birdseye/new(BE1) · new/plan · new/photos(도면 · 사진으로 시작) · :id/space(BE1) · :id/space/plan(BE1D) ·
 *   :id/space/photos(BE1P) · :id/products(BE2) · :id/furniture(BE3) · :id/layout(BE4) · :id/layout/edit(BE4E) · :id/render/:jobId(BE5G) ·
 *   :id/result(BE5) · :id/views(BE5V) · :id/zones(BE5Z) · :id/export(BE6) · m/:token(휴대폰 사진 올리기) · uc(UC_BE 유스케이스 맵)
 */
import { lazy, Suspense, type ReactNode } from 'react';
import { feature } from '@/shell/feature';
import { Spinner } from '@/ui';
import './be.css';

const ListPage = lazy(() => import('./pages/ListPage'));
const SpacePage = lazy(() => import('./pages/SpacePage'));
const PlanPage = lazy(() => import('./pages/PlanPage'));
const PhotosPage = lazy(() => import('./pages/PhotosPage'));
const ProductsPage = lazy(() => import('./pages/ProductsPage'));
const FurniturePage = lazy(() => import('./pages/FurniturePage'));
const LayoutPage = lazy(() => import('./pages/LayoutPage'));
const EditPage = lazy(() => import('./pages/EditPage'));
const RenderPage = lazy(() => import('./pages/RenderPage'));
const ResultPage = lazy(() => import('./pages/ResultPage'));
const ViewsPage = lazy(() => import('./pages/ViewsPage'));
const ZonesPage = lazy(() => import('./pages/ZonesPage'));
const ExportPage = lazy(() => import('./pages/ExportPage'));
const MobileUploadPage = lazy(() => import('./pages/MobileUploadPage'));
const UseCasePage = lazy(() => import('./pages/UseCasePage'));

const L = (el: ReactNode) => <Suspense fallback={<div className="be-center"><Spinner /></div>}>{el}</Suspense>;

export default feature({
  code: 'BE',
  key: 'birdseye',
  name: '공간 조감도 생성',
  order: 4,
  home: { section: 'visual', title: '공간 조감도', desc: '도면 · 제품 배치 · 3D 조감도' },
  routes: [
    { index: true, element: L(<ListPage />) },
    { path: 'new', element: L(<SpacePage />) },
    { path: 'new/plan', element: L(<PlanPage />) },
    { path: 'new/photos', element: L(<PhotosPage />) },
    { path: 'uc', element: L(<UseCasePage />) },
    { path: 'm/:token', element: L(<MobileUploadPage />) },
    { path: ':id/space', element: L(<SpacePage />) },
    { path: ':id/space/plan', element: L(<PlanPage />) },
    { path: ':id/space/photos', element: L(<PhotosPage />) },
    { path: ':id/products', element: L(<ProductsPage />) },
    { path: ':id/furniture', element: L(<FurniturePage />) },
    { path: ':id/layout', element: L(<LayoutPage />) },
    { path: ':id/layout/edit', element: L(<EditPage />) },
    { path: ':id/render/:jobId', element: L(<RenderPage />) },
    { path: ':id/result', element: L(<ResultPage />) },
    { path: ':id/views', element: L(<ViewsPage />) },
    { path: ':id/zones', element: L(<ZonesPage />) },
    { path: ':id/export', element: L(<ExportPage />) },
  ],
  publicRoutes: [{ path: '/m/upload/:token', element: L(<MobileUploadPage />) }], // 셸 밖 QR 업로드(로그인 없음) — workspace 셸이 등록
});
