/**
 * 고객 요구사항(RQ) 기능 모듈 — 소유: requirements 서비스 세션. 수용 기준: docs/scenarios/11-content-flow.md(새 흐름) · 01-requirements.md(이전 흐름)
 * 라우트(새 흐름 · 보드 webapp1 v63): /requirements(RQ0 List) · /new(RQ1 — 사전 작업이 없어 팝업 없이 바로 빈 최종본) · /flow/:id(상세 한 장 — RQ_Draft · RQ_View · RQ1_Edit)
 * 이전 흐름(제안서 handoff 가 아직 읽는다): /legacy(RQ0) · /legacy/new(RQ1) · /:rqId/form(RQ1G · RQ2) · /:rqId/deep/:sid(RQ3) · …/q(RQ3A · B)
 *            · …/result(RQ3C) · /:rqId/saved(RQ4) · /:rqId/questions(RQ5) · /:rqId(RQ6) · /:rqId/reply(RQ7) · /:rqId/reply/:replyId(RQ7B)
 */
import { feature } from '@/shell/feature';
import './rq.css';
import { RqFlowPage, RqListScreen } from './flow/RqFlowPages';
import { AskPage, GapsPage, ResultPage } from './pages/DeepPages';
import { DocPage, QuestionsPage, SavedPage } from './pages/DocPages';
import { FormPage } from './pages/FormPage';
import { ListPage } from './pages/ListPage';
import { ReplyPage, ReplyReviewPage } from './pages/ReplyPages';

export default feature({
  code: 'RQ',
  key: 'requirements',
  name: '고객 요구사항',
  order: 1,
  home: { section: 'plan', title: '고객 요구사항', desc: '요청서 · 회의록 · 메모를 넣으면 요구사항 정의서로 정리해 드려요.', feeds: '모든 콘텐츠가 함께 써요', mark: 'start' },
  routes: [
    // 새 콘텐츠 흐름(v63 · 2026-10-12): 목록(RQ0) → 빈 최종본(RQ1)에 바로 입력 → 저장(첫 저장에 Storyboard 자동 생성) → 같은 화면이 저장됨(RQ_View)
    { index: true, element: <RqListScreen /> },
    { path: 'new', element: <RqFlowPage /> },
    { path: 'flow/:id', element: <RqFlowPage /> },
    // 이전 흐름 — 목록 · 새로 만들기만 /legacy 로 옮겼다(나머지 /:rqId/... 그대로)
    { path: 'legacy', element: <ListPage /> },
    { path: 'legacy/new', element: <FormPage /> },
    { path: ':rqId', element: <DocPage /> },
    { path: ':rqId/form', element: <FormPage /> },
    { path: ':rqId/deep/:sid', element: <GapsPage /> },
    { path: ':rqId/deep/:sid/q', element: <AskPage /> },
    { path: ':rqId/deep/:sid/result', element: <ResultPage /> },
    { path: ':rqId/saved', element: <SavedPage /> },
    { path: ':rqId/questions', element: <QuestionsPage /> },
    { path: ':rqId/reply', element: <ReplyPage /> },
    { path: ':rqId/reply/:replyId', element: <ReplyReviewPage /> },
  ],
});
