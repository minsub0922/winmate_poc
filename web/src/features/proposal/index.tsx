/**
 * B2B 제안서(PR) 기능 모듈 — 웹 세션 소유(proposal-web). 수용 기준: docs/scenarios/10-proposal.md · 보드 docs/screens/webapp3/*.dc.html
 * 셸이 자동 등록한다(web/src/shell/registry.ts). 경로는 셸 기능 키 `proposal` 아래(§2 표의 `/proposals/…` 구조 그대로). 화면 ↔ 보드: README.md
 */
import type { ComponentType } from 'react';
import { useParams } from 'react-router';
import { feature } from '@/shell/feature';
import './proposal.css';
import { ListPage } from './pages/ListPage';
import { NewPage, OpenPage } from './pages/StartPages';
import { CustomerPage } from './pages/CustomerPage';
import { TypePage } from './pages/TypePage';
import { ComposePage } from './pages/ComposePage';
import { SectionPage } from './section/SectionPage';
import { DesignPage } from './pages/DesignPage';
import { RfpPage } from './pages/RfpPage';
import { WorksPage } from './pages/WorksPage';
import { IndustryPage } from './pages/IndustryPage';
import { ReuseStartPage } from './reuse/ReuseStartPage';
import { ReuseAnalysisPage, ReuseCriterionPage } from './reuse/ReuseAnalysisPage';
import { ReusePlanPage } from './reuse/ReusePlanPage';
import { ReuseSummaryPage } from './reuse/ReuseSummaryPage';
import { ResultPage } from './pages/ResultPage';
import { OneClickPage } from './pages/OneClickPage';
import { PreviewPage } from './pages/PreviewPage';
import { ConfirmPage } from './pages/ConfirmPage';
import { ReviewPage } from './pages/ReviewPage';
import { VersionsPage } from './pages/VersionsPage';

/** 다른 제안서 · 섹션으로 옮겨 가면 화면 상태를 새로 시작한다 */
function Keyed({ C }: { C: ComponentType }) {
  const { id, key, sheetId, importId, no } = useParams();
  return <C key={`${id ?? ''}:${key ?? ''}:${sheetId ?? ''}:${importId ?? ''}:${no ?? ''}`} />;
}
const k = (C: ComponentType) => <Keyed C={C} />;
/** 같은 제안서 안에서 시트만 바뀌는 화면(레일 스크롤 · 패널 상태 유지) */
function KeyedId({ C }: { C: ComponentType }) {
  const { id } = useParams();
  return <C key={id ?? ''} />;
}
const kid = (C: ComponentType) => <KeyedId C={C} />;

export default feature({
  code: 'PR',
  key: 'proposal',
  name: 'B2B 제안서 생성',
  order: 10,
  home: { section: 'hero', title: 'B2B 제안서 만들기', desc: '요구사항부터 제안서 PPTX 까지 단계별로' },
  routes: [
    { index: true, element: <ListPage /> },
    { path: 'new', element: <NewPage /> },
    { path: ':id', element: k(OpenPage) },
    { path: ':id/customer', element: k(CustomerPage) },
    { path: ':id/rfp', element: k(RfpPage) },
    { path: ':id/works', element: k(WorksPage) },
    { path: ':id/reuse', element: k(ReuseStartPage) },
    { path: ':id/reuse/analysis', element: k(ReuseAnalysisPage) },
    { path: ':id/reuse/analysis/:no', element: k(ReuseCriterionPage) },
    { path: ':id/reuse/plan', element: k(ReusePlanPage) },
    { path: ':id/reuse/summary', element: k(ReuseSummaryPage) },
    { path: ':id/type', element: k(TypePage) },
    { path: ':id/compose', element: k(ComposePage) },
    { path: ':id/industry', element: k(IndustryPage) },
    { path: ':id/sections/:key', element: k(SectionPage) },
    { path: ':id/sections/:key/sheets/:sheetId/template', element: k(SectionPage) },
    { path: ':id/sections/:key/imports/:importId', element: k(SectionPage) },
    { path: ':id/design', element: k(DesignPage) },
    { path: ':id/result', element: k(ResultPage) },
    { path: ':id/one-click/:jobId', element: k(OneClickPage) },
    { path: ':id/preview', element: kid(PreviewPage) },
    { path: ':id/preview/:no', element: kid(PreviewPage) },
    { path: ':id/confirm', element: k(ConfirmPage) },
    { path: ':id/review', element: kid(ReviewPage) },
    { path: ':id/review/:no', element: kid(ReviewPage) },
    { path: ':id/versions', element: k(VersionsPage) },
  ],
});
