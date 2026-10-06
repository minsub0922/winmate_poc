/**
 * 고객 요구사항(RQ) 기능 모듈 — 소유: requirements 서비스 세션. 수용 기준: docs/scenarios/01-requirements.md
 * 라우트(§2): /requirements(RQ0) · /new(RQ1) · /:rqId/form(RQ1G · RQ2) · /:rqId/deep/:sid(RQ3) · …/q(RQ3A · B) · …/result(RQ3C)
 *            /:rqId/saved(RQ4) · /:rqId/questions(RQ5) · /:rqId(RQ6) · /:rqId/reply(RQ7) · /:rqId/reply/:replyId(RQ7B)
 */
import { feature } from '@/shell/feature';
import './rq.css';
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
    { index: true, element: <ListPage /> },
    { path: 'new', element: <FormPage /> },
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
