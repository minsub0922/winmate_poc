/**
 * Market Intelligence(MI) 기능 모듈 — 소유: mi 서비스 세션. 수용 기준: docs/scenarios/03-mi.md
 * 셸이 자동으로 등록한다(web/src/shell/registry.ts).
 * 라우트(§2): /mi(MI0) · /mi/rules(MIR) · /mi/new(MI1) · /mi/new/industry(MI1I) · /mi/:id → 작업의 route
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
  return <MiPage>{err ? <ErrorBand message={err} onRetry={() => nav('/mi')} /> : <LoadingCard lines={4} />}</MiPage>;
}

export default feature({
  code: 'MI',
  key: 'mi',
  name: 'Market Intelligence',
  order: 6,
  home: { section: 'plan', title: 'Market Intelligence', desc: '업종 · 시장 · 고객 · 경쟁 분석' },
  routes: [
    { index: true, element: <ListPage /> },
    { path: 'rules', element: <RulesPage /> },
    { path: 'new', element: <InputPage /> },
    { path: 'new/industry', element: <IndustryPage /> },
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
