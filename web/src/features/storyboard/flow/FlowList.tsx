/**
 * SB0 — Storyboard 목록(보드 webapp1 SB0 v61). 허브 `GET /v1/flows`(메인 바로 아래 분기, 최근 수정 순).
 * 가운데 「새 고객 요구사항으로 시작」(1100×156) → 44 → 작업 내역 그리드(260 × 4 · 간격 20).
 * 카드 = 썸네일(진행 8칸 + 요약본 앞부분 `summary_head`) · 이름 · 코드 · 고객 · n/8 단계 · Key message · 수정.
 */
import { Link } from 'react-router';
import { HistoryHead, ListHero, SegLegend, StepMeter, ThumbFrame, useShellPage, useFlows, whenText, type FlowListItem, type SegState } from '@/shell';
import { ErrorState, Skeleton, cx } from '@/ui';
import { ORDER8, SECTION, TRACK_LABEL, isDone, stageName, stageText } from './model';
import './sbf.css';

/** 썸네일 안(472 폭을 반으로) — 보드 SB0: 진행 8칸(입력됨 = 브랜드 · 아직 = 점선) + 요약본 앞 9줄 */
function Mini({ r }: { r: FlowListItem }) {
  const head = (r.summary_head ?? []).slice(0, 9);
  return (
    <>
      <span className="sbf-mtrack">
        {ORDER8.map((k, i) => {
          const c = r.cells.find((x) => x.key === k);
          const on = c?.state === 'done';
          return <span key={k} className={cx('sbf-mcell', on && 'sbf-mcell--on', (i === 2 || i === 7) && 'sbf-mcell--gap')}><b>{TRACK_LABEL[k]}</b><small>{on ? c?.ref ?? '—' : '—'}</small></span>;
        })}
      </span>
      <span className="sbf-mmd">
        {head.map((ln, i) => <span key={i} className={cx(ln.startsWith('# ') && 'sbf-mmd--h1', ln.startsWith('## ') && 'sbf-mmd--h2')}>{ln}</span>)}
      </span>
    </>
  );
}

function Card({ r }: { r: FlowListItem }) {
  const from = r.is_branch ? `${r.parent ?? ''} · ${stageName(r.branch_point?.stage as string | undefined)}에서 분기` : '';
  const sub = [r.id, r.customer, from].filter(Boolean).join(' · ');
  const n = ORDER8.filter((k) => isDone(r.cells, k)).length;
  const segs: SegState[] = ORDER8.map((k) => (isDone(r.cells, k) ? 'done' : 'todo'));
  return (
    <li className="fl-card sbf-card" data-sb={r.id}>
      <Link to={`/storyboard/flow/${r.id}`} className="sbf-cardlink">
        <ThumbFrame badge={r.is_branch ? '분기' : undefined} tone="line"><Mini r={r} /></ThumbFrame>
        <span className="fl-cardbody">
          <span className="sbf-cardname"><b>{r.name}</b><small>{sub}</small></span>
          <StepMeter n={n} total={8} text={stageText(r.cells)} segs={segs} gaps={[2, 7]} />
          <span className="sbf-cardfoot">
            <span className={cx('sbf-km', r.key_message && 'sbf-km--on')}>{r.key_message ? `Key message · ${r.key_message}` : 'Key message 아직 없음'}</span>
            <span className="fl-when">{whenText(r.updated_at)}</span>
          </span>
        </span>
      </Link>
    </li>
  );
}

export function FlowListScreen() {
  useShellPage({ section: SECTION, title: '', hasTask: false, sidebarGroup: 'storyboard' });
  const q = useFlows();
  const rows = q.data?.items ?? [];
  return (
    <div className="fl-list sbf-list">
      <div className="fl-listhead">
        <div className="fl-listtitles">
          <h1>전략 수립 Storyboard</h1>
          <span className="sbf-listdesc">제안서 흐름 전체를 담는 context예요. 고객 요구사항을 저장하면 생기고, 콘텐츠의 복제본을 만들면 분기돼요.</span>
        </div>
      </div>
      <ListHero to="/requirements/new" label="새 고객 요구사항으로 시작" steps={['고객 요구사항', 'Storyboard 생성', 'DSS · 콘텐츠', '제안서']} note="저장하면 Storyboard가 자동으로 생겨요" />
      <HistoryHead count={rows.length} legend={<SegLegend items={[['done', '입력됨'], ['todo', '아직']]} tail="요구사항 → DSS → MI · 경쟁사 · VP · Spec · 시나리오 → 제안서" />} />
      {q.isLoading && <Skeleton h={320} r={14} />}
      {q.isError && <ErrorState message="Storyboard 목록을 불러오지 못했어요" onRetry={() => void q.refetch()} />}
      {!q.isLoading && !q.isError && rows.length === 0 && (
        <div className="fl-empty fl-empty--hist"><b>아직 Storyboard가 없어요</b><span>위 「새 고객 요구사항으로 시작」 — 고객 요구사항을 저장하면 Storyboard가 자동으로 만들어져요.</span></div>
      )}
      {rows.length > 0 && <ul className="fl-grid" aria-label="Storyboard 작업 내역">{rows.map((r) => <Card key={r.id} r={r} />)}</ul>}
    </div>
  );
}
