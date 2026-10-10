/**
 * SB0 — Storyboard 목록 · 어디까지 입력됐나(보드 webapp1 SB0). 허브 `GET /v1/flows`(메인 바로 아래 분기, 최근 수정 순).
 * 칸: Storyboard minmax(0,1fr) · 어디까지 입력됐나 300 · Key message 120 · 수정 110(간격 16).
 */
import { Link } from 'react-router';
import { useShellPage, useFlows, whenText, type FlowListItem } from '@/shell';
import { ErrorState, Icon, Skeleton, cx } from '@/ui';
import { ORDER8, SECTION, isDone, stageName, stageText } from './model';
import './sbf.css';

const BRANCH_D = 'M6 3v10a4 4 0 0 0 4 4h8 M15 14l3 3-3 3';

function Row({ r }: { r: FlowListItem }) {
  const from = r.is_branch ? `${r.parent ?? ''} · ${stageName(r.branch_point?.stage as string | undefined)}에서 분기` : '';
  const sub = [r.id, r.customer, from].filter(Boolean).join(' · ');
  return (
    <Link to={`/storyboard/flow/${r.id}`} className="sbf-tr sbf-row" role="row" data-sb={r.id}>
      <div className={cx('sbf-name', r.is_branch && 'sbf-name--branch')} role="cell">
        {r.is_branch && <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--wm-text-subtle)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }} aria-label="분기"><path d={BRANCH_D} /></svg>}
        <span className="sbf-nametxt"><b>{r.name}</b><small>{sub}</small></span>
      </div>
      <div className="sbf-prog" role="cell">
        <span className="sbf-dots" aria-label={`입력됨 ${ORDER8.filter((k) => isDone(r.cells, k)).length} / 8`}>
          {ORDER8.map((k, i) => <span key={k} data-key={k} className={cx('sbf-dot', (i === 2 || i === 7) && 'sbf-dot--gap', isDone(r.cells, k) && 'sbf-dot--on')} />)}
        </span>
        <span className="sbf-stage">{stageText(r.cells)}</span>
      </div>
      <span role="cell" className={cx('sbf-km', r.key_message && 'sbf-km--on')}>{r.key_message || '아직 없음'}</span>
      <span role="cell" className="sbf-when">{whenText(r.updated_at)}</span>
    </Link>
  );
}

export function FlowListScreen() {
  useShellPage({ section: SECTION, title: '', hasTask: false, sidebarGroup: 'storyboard' });
  const q = useFlows();
  const rows = q.data?.items ?? [];
  return (
    <div className="sbf-list">
      <div className="sbf-listhead">
        <div className="sbf-listtitles">
          <h1>전략 수립 Storyboard</h1>
          <span>제안서 흐름 전체를 담는 context예요. 고객 요구사항을 저장하면 생기고, 콘텐츠의 복제본을 만들면 분기돼요.</span>
        </div>
        <Link to="/requirements/new" className="sbf-newbtn"><Icon name="plus" size={15} strokeWidth={2.4} />새 고객 요구사항으로 시작</Link>
      </div>
      {q.isLoading && <Skeleton h={300} r={14} />}
      {q.isError && <ErrorState message="Storyboard 목록을 불러오지 못했어요" onRetry={() => void q.refetch()} />}
      {!q.isLoading && !q.isError && rows.length === 0 && (
        <div className="sbf-empty"><b>아직 Storyboard가 없어요</b><span>고객 요구사항을 저장하면 Storyboard가 자동으로 만들어져요.</span></div>
      )}
      {rows.length > 0 && (
        <div className="sbf-table" role="table" aria-label="Storyboard 목록">
          <div className="sbf-tr sbf-th" role="row"><span role="columnheader">Storyboard</span><span role="columnheader">어디까지 입력됐나</span><span role="columnheader">Key message</span><span role="columnheader">수정</span></div>
          {rows.map((r) => <Row key={r.id} r={r} />)}
        </div>
      )}
      <div className="sbf-legend">
        <span><i className="on" />입력됨</span>
        <span><i />아직</span>
        <span>순서 · 요구사항 → DSS → MI · 경쟁사 · VP · Spec · 시나리오 → 제안서</span>
      </div>
    </div>
  );
}
