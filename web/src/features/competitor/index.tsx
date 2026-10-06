/**
 * 경쟁사 분석(CA) 기능 모듈 — 소유: competitor 서비스 세션. 수용 기준: docs/scenarios/04-competitor.md
 * 셸이 자동으로 등록한다(web/src/shell/registry.ts).
 * 라우트(§2): /competitor(CA0) · /competitor/new(CA1 · `?input=requirements&rq=` CA1R) · /competitor/:id → 작업의 route
 *   /competitor/:id/input(CA1 · CA1R) · finding(CA1G) · ask(CA2Q) · candidates(CA2) · run(CA3) · criteria(CA3C)
 *   result(CA4 · `?view=overview|table|strengths`) · competitors/:cmp(CA4D) · send(CA5)
 */
import { useEffect, useState, type ComponentType } from 'react';
import { useNavigate, useParams } from 'react-router';
import { feature } from '@/shell/feature';
import { getAnalysis } from './api';
import { ErrorCol, LoadingCol } from './parts';
import { AskPage } from './pages/AskPage';
import { CandidatesPage } from './pages/CandidatesPage';
import { CriteriaPage } from './pages/CriteriaPage';
import { DetailPage } from './pages/DetailPage';
import { FindingPage } from './pages/FindingPage';
import { InputPage } from './pages/InputPage';
import { ListPage } from './pages/ListPage';
import { ResultPage } from './pages/ResultPage';
import { RunPage } from './pages/RunPage';
import { SendPage } from './pages/SendPage';
import './ca.css';

/** 다른 작업 · 경쟁사로 옮겨 가면 화면 상태를 새로 시작한다. CA1 은 만들 때 주소만 바뀌므로 감싸지 않는다 */
function Keyed({ C }: { C: ComponentType }) {
  const { id, cmp } = useParams();
  return <C key={`${id ?? 'new'}:${cmp ?? ''}`} />;
}
const k = (C: ComponentType) => <Keyed C={C} />;

/** `/competitor/:id` — 작업 상태 · 마지막으로 머문 화면(§3.4 route)으로 */
function OpenAnalysis() {
  const { id } = useParams();
  const nav = useNavigate();
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    if (!id) return;
    getAnalysis(id).then((a) => nav(a.route || `/competitor/${id}/input`, { replace: true })).catch(() => setErr('작업을 찾지 못했어요'));
  }, [id, nav]);
  return err ? <ErrorCol message={err} onRetry={() => nav('/competitor')} /> : <LoadingCol lines={3} />;
}

export default feature({
  code: 'CA',
  key: 'competitor',
  name: '경쟁사 분석',
  order: 7,
  home: { section: 'plan', title: '경쟁사 분석', desc: '경쟁사 찾기 · 비교 기준 · 신뢰도', mark: 'new' },
  routes: [
    { index: true, element: <ListPage /> },
    { path: 'new', element: <InputPage /> },
    { path: ':id', element: <OpenAnalysis /> },
    { path: ':id/input', element: <InputPage /> },
    { path: ':id/finding', element: k(FindingPage) },
    { path: ':id/ask', element: k(AskPage) },
    { path: ':id/candidates', element: k(CandidatesPage) },
    { path: ':id/run', element: k(RunPage) },
    { path: ':id/criteria', element: k(CriteriaPage) },
    { path: ':id/result', element: k(ResultPage) },
    { path: ':id/competitors/:cmp', element: k(DetailPage) },
    { path: ':id/send', element: k(SendPage) },
  ],
});
