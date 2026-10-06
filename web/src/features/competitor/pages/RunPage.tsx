/** CA3 — 분석 중 · 기준 자동(§4.7). analyze 잡 step `competitors` · progress → 경쟁사별 문장, 끝나면 CA4. `중지` → 부분 결과. */
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { cancelJob, useJob } from '@/api/jobs';
import { Button } from '@/ui';
import { qk, useAnalysis, useCriteria, type RunCompetitor } from '../api';
import { useCaShell } from '../hooks';
import { Agent, Bar, CaPage, Dot, ErrorCol, LoadingCol, ModeChip } from '../parts';

const SRC_LABEL: Record<string, string> = { requirements: '요구', industry_cases: '업종 사례', default: '기본', user: '직접' };

export function RunPage() {
  const { id: aid = '' } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const aq = useAnalysis(aid, { poll: 3000 });
  const a = aq.data;
  const cq = useCriteria(aid);
  useCaShell({ aid, title: a?.title, current: 3, added: a?.added_refs });
  const [comps, setComps] = useState<RunCompetitor[] | null>(null);
  const [pct, setPct] = useState<number | null>(null);
  const [stopping, setStopping] = useState(false);
  const analyzing = a?.status === 'analyzing';
  useJob(analyzing ? a?.current_job_id : null, {
    onEvent: (e) => {
      if (e.type === 'step' && e.data.step === 'competitors' && Array.isArray(e.data.competitors)) setComps(e.data.competitors as RunCompetitor[]);
      if (e.type === 'progress' && typeof e.data.progress === 'number') setPct(e.data.progress);
    },
    onDone: () => {
      void qc.invalidateQueries({ queryKey: ['ca'] });
    },
  });

  const fresh = aq.isFetchedAfterMount;
  useEffect(() => {
    if (!a || !fresh || a.status === 'analyzing') return;
    if (['done', 'upd', 'stopped'].includes(a.status)) nav(`/competitor/${aid}/result`, { replace: true });
    else if (a.status === 'confirming' || a.status === 'draft') nav(`/competitor/${aid}/candidates`, { replace: true });
    else if (a.status === 'failed') nav(a.version ? `/competitor/${aid}/result` : `/competitor/${aid}/candidates`, { replace: true });
    else nav(a.route, { replace: true });
  }, [a, aid, nav, fresh]);

  if (aq.isLoading) return <LoadingCol />;
  if (aq.isError || !a) return <ErrorCol message="작업을 찾지 못했어요" onRetry={() => aq.refetch()} />;

  const run = a.run;
  const list = comps ?? run?.competitors ?? [];
  const n = list.length || a.on_count;
  const crit = cq.data;
  const value = pct ?? run?.pct ?? 0;

  async function stop() {
    if (!a?.current_job_id) return;
    setStopping(true);
    await cancelJob(a.current_job_id);
    // 잡이 끝난 경쟁사만으로 부분 결과를 저장하면 상태가 바뀐다(위 effect 가 옮긴다)
    window.setTimeout(() => { void qc.invalidateQueries({ queryKey: qk.analysis(aid) }); }, 600);
  }

  return (
    <CaPage>
      <div className="ca-center ca-center--tight">
        <Agent title={`${n}곳을 분석하는 중`} desc={`${run?.eta_label || '약 2분'} · 끝나면 결과로 넘어가요`} />
        <Bar pct={Math.max(4, value)} wide />
        <div className="ca-critbox" aria-label="비교 기준">
          <div className="ca-critbox__head">
            <b>비교 기준 {crit?.on ?? crit?.total ?? '—'}</b>
            <span>{crit?.summary_text}</span>
            <ModeChip mode={crit?.mode ?? a.criteria_mode} />
            <span className="ca-grow" />
            <Link to={`/competitor/${aid}/criteria`} className="ca-linkbtn ca-linkbtn--brand" style={{ fontSize: 12.5 }}>바꾸기</Link>
          </div>
          <div className="ca-crits">
            {(crit?.items ?? []).filter((c) => c.enabled).map((c) => (
              <span key={c.id} className={`ca-crit ca-crit--${c.source}`}>{c.name}<small>{SRC_LABEL[c.source] ?? ''}</small></span>
            ))}
          </div>
        </div>
        <div className="ca-lines ca-lines--w560" role="list" aria-label="경쟁사별 진행">
          {list.map((c) => (
            <div key={c.id} className="ca-line" role="listitem" data-state={c.state}>
              <Dot state={c.state === 'run' ? 'run' : c.state} />
              <span className={`ca-line__text${c.state === 'wait' ? ' ca-line__text--wait' : ''}`}>{c.text}</span>
            </div>
          ))}
        </div>
        <div className="ca-row" style={{ gap: 16 }}>
          <Link to={`/competitor/${aid}/result`} className="ca-linkbtn">지금까지 결과 보기</Link>
          <Button h={36} className="ca-stop" onClick={stop} loading={stopping} disabled={!analyzing || !a.current_job_id}
            icon={<svg width="12" height="12" viewBox="0 0 24 24" fill="var(--wm-text-muted)" aria-hidden="true"><rect x="5" y="5" width="14" height="14" rx="2" /></svg>}>중지</Button>
        </div>
      </div>
    </CaPage>
  );
}

export default RunPage;
