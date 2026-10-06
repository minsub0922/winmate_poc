/** CA1G — 찾는 중(§4.5). find 잡 SSE: step `lines` → 작업 줄, awaiting_input → CA2Q, 성공 → CA2. */
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { useJob } from '@/api/jobs';
import { Button } from '@/ui';
import { errText, qk, startFind, useAnalysis, type FindLine } from '../api';
import { useCaShell } from '../hooks';
import { Agent, Bar, CaPage, Dot, ErrorCol, LoadingCol } from '../parts';

const DEFAULT_LINES: FindLine[] = [
  { n: 1, text: '입력 읽기 — 고객사 · 업종 · 장소 · 제품', state: 'active' },
  { n: 2, text: '같은 업종 도입사례의 제품군으로 후보 찾기', state: 'wait' },
  { n: 3, text: '공개 자료 검색', state: 'wait' },
  { n: 4, text: '후보 정리 · 근거 붙이기', state: 'wait' },
];
const STATE_LABEL = { done: '완료', active: '진행 중', wait: '대기' } as const;

export function FindingPage() {
  const { id: aid = '' } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const q = useAnalysis(aid, { poll: 4000 });
  const a = q.data;
  useCaShell({ aid, title: a?.title || '새 분석', current: 1, added: a?.added_refs });
  const [lines, setLines] = useState<FindLine[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const jobId = a && (a.status === 'finding' || a.status === 'ask') ? a.current_job_id : null;
  const job = useJob(jobId, {
    onEvent: (e) => {
      if (e.type === 'step' && e.data.step === 'lines' && Array.isArray(e.data.lines)) setLines(e.data.lines as FindLine[]);
      if (e.type === 'awaiting_input') nav(`/competitor/${aid}/ask`, { replace: true });
    },
    onDone: () => { void qc.invalidateQueries({ queryKey: qk.analysis(aid) }); void qc.invalidateQueries({ queryKey: qk.candidates(aid) }); },
  });

  // 작업 상태 → 화면(끝남 · 묻기 · 분석으로 이어짐 · 취소) — 이 화면에서 새로 읽은 값으로만 옮긴다
  const fresh = q.isFetchedAfterMount;
  useEffect(() => {
    if (!a || !fresh) return;
    if (a.status === 'confirming') nav(`/competitor/${aid}/candidates`, { replace: true });
    else if (a.status === 'ask') nav(`/competitor/${aid}/ask`, { replace: true });
    else if (a.status === 'analyzing') nav(`/competitor/${aid}/run`, { replace: true });
    else if (a.status === 'draft') nav(`/competitor/${aid}/input`, { replace: true });
    else if (['done', 'upd', 'stopped'].includes(a.status)) nav(a.route, { replace: true });
  }, [a, aid, nav, fresh]);
  useEffect(() => { if (job.status === 'awaiting_input') nav(`/competitor/${aid}/ask`, { replace: true }); }, [job.status, aid, nav]);

  if (q.isLoading) return <LoadingCol />;
  if (q.isError || !a) return <ErrorCol message="작업을 찾지 못했어요" onRetry={() => q.refetch()} />;

  const failed = a.status === 'failed' || job.status === 'failed';
  const shown = lines ?? (a.find?.lines?.length ? a.find.lines : DEFAULT_LINES);
  const done = shown.filter((l) => l.state === 'done').length;
  const active = shown.some((l) => l.state === 'active') ? 0.5 : 0;
  const pct = Math.max(6, ((done + active) / Math.max(1, shown.length)) * 100);

  async function retry() {
    setBusy(true);
    setErr(null);
    try {
      await startFind(aid);
      setLines(null);
      await qc.invalidateQueries({ queryKey: qk.analysis(aid) });
    } catch (e) {
      setErr(errText(e, '다시 찾지 못했어요'));
    } finally {
      setBusy(false);
    }
  }

  if (failed) {
    return (
      <CaPage>
        <div className="ca-center">
          <Agent title="경쟁사를 찾지 못했어요" desc={a.find?.error || job.job?.error?.message || '공개 자료에서 후보를 찾지 못했어요'} />
          <div className="ca-row">
            <Button h={44} variant="primary" onClick={retry} loading={busy}>다시 찾기</Button>
            <Button h={44} onClick={() => nav(`/competitor/${aid}/candidates`)}>직접 추가하기</Button>
            <Button h={44} variant="ghost" onClick={() => nav(`/competitor/${aid}/input`)}>입력 바꾸기</Button>
          </div>
          {err && <span className="ca-adderr">{err}</span>}
        </div>
      </CaPage>
    );
  }

  return (
    <CaPage>
      <div className="ca-center">
        <Agent title="경쟁사를 찾는 중" desc={`${a.find?.eta_label || '약 30초'} · 끝나면 후보 확인으로 넘어가요`} />
        <Bar pct={pct} />
        <div className="ca-lines" role="list" aria-label="찾는 단계">
          {shown.map((l) => (
            <div key={l.n} className="ca-line" role="listitem" data-state={l.state}>
              <Dot state={l.state === 'active' ? 'active' : l.state} />
              <span className={`ca-line__text${l.state === 'wait' ? ' ca-line__text--wait' : ''}${l.state === 'active' ? ' ca-line__text--active' : ''}`}>{l.text}</span>
              <span className={`ca-line__tag${l.state === 'active' ? ' ca-line__tag--active' : ''}`}>{STATE_LABEL[l.state]}</span>
            </div>
          ))}
        </div>
        <Link to={`/competitor/${aid}/candidates`} className="ca-linkbtn">지금까지 찾은 후보 보기</Link>
      </div>
    </CaPage>
  );
}

export default FindingPage;
