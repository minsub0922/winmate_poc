/**
 * Market Intelligence(MI) 기능 모듈 — 소유: mi 서비스 세션. 수용 기준: docs/scenarios/11-content-flow.md(새 흐름) · 03-mi.md(이전 흐름)
 * 셸이 자동으로 등록한다(web/src/shell/registry.ts).
 * 라우트(새 흐름 · 보드 webapp1 v58): /mi(MI0 List) · /mi/new(MI1 Gate · MI1_Branch) · /mi/flow/:id(MI2_Loading → MI2 → MI3 → MI_Done)
 * 이전 흐름(제안서 handoff 가 아직 읽는다): /mi/legacy(MI0) · /mi/legacy/new(MI1) · /mi/legacy/new/industry(MI1I · 옛 주소 /mi/new/industry 도 연다)
 *   /mi/rules(MIR) · /mi/:id → 작업의 route
 *   /mi/:id/input(MI1) · industry(MI1I) · design(MI2A) · design/industry(MI1Q) · scope(MI2) · competitors(MI2C) · run(MI3G)
 *   result(MI3 · `?panel=sources` MI3S) · verify(MI3V) · revise(MI3R) · slides(MI3P) · slides/:sheet(MI3L) · export(MI4) · shared(공유 화면)
 */
import { useEffect, useState, type ComponentType } from 'react';
import { useNavigate, useParams } from 'react-router';
import { feature } from '@/shell/feature';
import { getAnalysis } from './api';
import { ErrorBand, LoadingCard, MiPage } from './parts';
import { AskPage } from './pages/AskPage';
import { CompetitorsPage } from './pages/CompetitorsPage';
import { DesignPage } from './pages/DesignPage';
import { ExportPage } from './pages/ExportPage';
import { IndustryPage } from './pages/IndustryPage';
import { InputPage } from './pages/InputPage';
import { LayoutPage } from './pages/LayoutPage';
import { ListPage } from './pages/ListPage';
import { ResultPage } from './pages/ResultPage';
import { RevisePage } from './pages/RevisePage';
import { RulesPage } from './pages/RulesPage';
import { RunPage } from './pages/RunPage';
import { ScopePage } from './pages/ScopePage';
import { SharedPage } from './pages/SharedPage';
import { SlidesPage } from './pages/SlidesPage';
import { VerifyPage } from './pages/VerifyPage';
import { MiFlowPage, MiGateScreen, MiListScreen } from './flow/MiFlowPages';
import './mi.css';

/** 다른 작업으로 옮겨 가면 화면 상태를 새로 시작한다(같은 라우트 · 다른 :id). MI1 은 만들 때 주소만 바뀌므로 감싸지 않는다 */
function Keyed({ C }: { C: ComponentType }) {
  const { id, sheet } = useParams();
  return <C key={`${id ?? 'new'}:${sheet ?? ''}`} />;
}
const k = (C: ComponentType) => <Keyed C={C} />;

/** `/mi/:id` — 작업 상태 · 마지막으로 머문 화면(§3.4 route)으로 */
function OpenAnalysis() {
  const { id } = useParams();
  const nav = useNavigate();
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    if (!id) return;
    getAnalysis(id).then((a) => nav(a.route || `/mi/${id}/input`, { replace: true })).catch(() => setErr('작업을 찾지 못했어요'));
  }, [id, nav]);
  return <MiPage>{err ? <ErrorBand message={err} onRetry={() => nav('/mi/legacy')} /> : <LoadingCard lines={4} />}</MiPage>;
}

export default feature({
  code: 'MI',
  key: 'mi',
  name: 'Market Intelligence',
  order: 6,
  home: { section: 'plan', title: 'Market Intelligence', desc: '업종 · 시장 · 고객 · 경쟁 분석' },
  routes: [
    // 새 콘텐츠 흐름(웹앱 ① v58): 목록(MI0) · 사전 작업 고르기(MI1) → 분석 로딩 · 검색(MI2) → 정제(MI3) → 완료
    { index: true, element: <MiListScreen /> },
    { path: 'new', element: <MiGateScreen /> },
    { path: 'flow/:id', element: <MiFlowPage /> },
    // 이전 MI 흐름 — 목록 · 새로 만들기만 /legacy 로 옮겼다(나머지 /:id/... 그대로)
    { path: 'legacy', element: <ListPage /> },
    { path: 'legacy/new', element: <InputPage /> },
    { path: 'legacy/new/industry', element: <IndustryPage /> },
    { path: 'new/industry', element: <IndustryPage /> },
    { path: 'rules', element: <RulesPage /> },
    { path: ':id', element: <OpenAnalysis /> },
    { path: ':id/input', element: <InputPage /> },
    { path: ':id/industry', element: k(IndustryPage) },
    { path: ':id/design', element: k(DesignPage) },
    { path: ':id/design/industry', element: k(AskPage) },
    { path: ':id/scope', element: k(ScopePage) },
    { path: ':id/competitors', element: k(CompetitorsPage) },
    { path: ':id/run', element: k(RunPage) },
    { path: ':id/result', element: k(ResultPage) },
    { path: ':id/verify', element: k(VerifyPage) },
    { path: ':id/revise', element: k(RevisePage) },
    { path: ':id/slides', element: k(SlidesPage) },
    { path: ':id/slides/:sheet', element: k(LayoutPage) },
    { path: ':id/export', element: k(ExportPage) },
    { path: ':id/shared', element: k(SharedPage) },
  ],
});
