/**
 * Value Proposition(VP) 기능 모듈 — 소유: vp 서비스 세션. 수용 기준: docs/scenarios/05-vp.md · 보드 docs/screens/webapp1/VP*.dc.html
 * 셸이 자동으로 등록한다(web/src/shell/registry.ts).
 * 라우트(새 흐름): /vp(VP0 List) · /vp/new(VP1 Gate) · /vp/values/:id(VP2) — 이전 흐름: /vp/legacy · /vp/legacy/new · /vp/rules(VPR) · /vp/:id/materials(VP1) · …/materials/review(VP1A) · …/questions(VP1Q) · …/structure(VP2)
 *        · …/generating?job=(VP3G) · …/result(VP3) · …/result/layout(VP3L) · …/result/numbers(VP3N) · …/result/images(VPI) · …/export(VP4)
 *        · /vp/:id → 작업의 resume_route
 *        · /vp/values/new · /vp/values/:id — 새 흐름(가치 · 고객의 니즈, 보드 VP2 · VpDetail · VP_Done)
 */
import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router';
import { feature } from '@/shell/feature';
import { ErrorState, Skeleton } from '@/ui';
import { errText, useVp } from './api';
import { ListPage } from './pages/List';
import { MaterialsPage } from './pages/Materials';
import { ReviewPage } from './pages/Review';
import { QuestionsPage } from './pages/Questions';
import { StructurePage } from './pages/Structure';
import { GeneratingPage } from './pages/Generating';
import { ResultPage } from './pages/Result';
import { LayoutPage } from './pages/Layout';
import { NumbersPage } from './pages/Numbers';
import { ImagesPage } from './pages/Images';
import { ExportPage } from './pages/Export';
import { NewValuesPage } from './values/NewValuesPage';
import { ValuesPage } from './values/ValuesPage';
import { VpGateScreen, VpListScreen } from './values/FlowPages';
import { Page, useVpShell } from './parts';
import './vp.css';

/** `/vp/:id` — 마지막 단계에서 이어 열기 */
function ResumePage() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const vp = useVp(id, { poll: false });
  useVpShell(vp.data, vp.data?.step ?? 1);
  useEffect(() => {
    if (vp.data?.resume_route && vp.data.resume_route !== `/vp/${id}`) nav(vp.data.resume_route, { replace: true });
  }, [vp.data?.resume_route, id, nav]);
  if (vp.isError) return <Page><ErrorState message={errText(vp.error)} onRetry={() => vp.refetch()} /></Page>;
  return <Page><Skeleton h={240} /></Page>;
}

export default feature({
  code: 'VP',
  key: 'vp',
  name: 'Value Proposition',
  order: 8,
  home: { section: 'plan', title: 'Value Proposition', desc: '메시지 · 레이아웃 · 이미지 · 수치' },
  routes: [
    // 새 콘텐츠 흐름(웹앱 ① v58): 목록(VP0) · 사전 작업 고르기(VP1) → 가치 · 고객의 니즈(VP2)
    { index: true, element: <VpListScreen /> },
    { path: 'new', element: <VpGateScreen /> },
    // 이전 VP 흐름(제안서 handoff 가 아직 읽는다) — /vp/legacy
    { path: 'legacy', element: <ListPage /> },
    { path: 'legacy/new', element: <MaterialsPage /> },
    { path: 'rules', element: <ListPage rules /> },
    // 새 흐름(2026-10-08 보드 VP2): 제품 · 솔루션마다 가치 여러 개 + 고객의 니즈
    { path: 'values/new', element: <NewValuesPage /> },
    { path: 'values/:id', element: <ValuesPage /> },
    { path: ':id', element: <ResumePage /> },
    { path: ':id/materials', element: <MaterialsPage /> },
    { path: ':id/materials/review', element: <ReviewPage /> },
    { path: ':id/questions', element: <QuestionsPage /> },
    { path: ':id/structure', element: <StructurePage /> },
    { path: ':id/generating', element: <GeneratingPage /> },
    { path: ':id/result', element: <ResultPage /> },
    { path: ':id/result/layout', element: <LayoutPage /> },
    { path: ':id/result/numbers', element: <NumbersPage /> },
    { path: ':id/result/images', element: <ImagesPage /> },
    { path: ':id/export', element: <ExportPage /> },
  ],
});
