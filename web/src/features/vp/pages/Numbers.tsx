/**
 * VP3N — 수치 보강(`/vp/:id/result/numbers?sheet=`): 기대 효과 수치 표 · 자동 전환 규칙 · 고객 데이터 요청 초안 · `이대로 반영`.
 */
import { useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Skeleton, ErrorState, Icon, toast } from '@/ui';
import { applyMetrics, dataRequestDraft, errText, isJob, patchMetric, postMessage, useMetrics, useRefresh, useVp, vpKeys, type Metric } from '../api';
import { Agent, Btn, CardHead, Dock, ModeChip, Page, Spinner, VThumb, useJobDone, useVpShell } from '../parts';

const HANDLING: Array<{ k: 'request' | 'industry_avg' | 'exclude'; label: string }> = [
  { k: 'request', label: '요청하기' }, { k: 'industry_avg', label: '업종 평균' }, { k: 'exclude', label: '빼기' },
];

export function NumbersPage() {
  const { id = '' } = useParams();
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const vp = useVp(id);
  const doc = vp.data;
  useVpShell(doc, 3);
  const ef = sp.get('sheet') || doc?.sheets?.find((s) => s.role === 'EF')?.id || '';
  const mv = useMetrics(id, ef);
  const refresh = useRefresh(id);
  const draft = useQuery({ queryKey: ['vp', 'draft', id, ef, mv.dataUpdatedAt], queryFn: () => dataRequestDraft(id, ef || undefined), enabled: !!id && !!ef });
  const [busy, setBusy] = useState('');
  const [err, setErr] = useState('');
  const [job, setJob] = useState<string | null>(null);
  const [applyJob, setApplyJob] = useState<string | null>(null);
  useJobDone(job, async (snap) => {
    setJob(null);
    await refresh();
    const nc = snap.result?.needs_clarification as string | undefined;
    if (nc) setErr(nc);
  });
  const aj = useJobDone(applyJob, async () => { await refresh(); nav(`/vp/${id}/result`); });

  if (!doc || mv.isLoading) return <Page><Skeleton h={360} /></Page>;
  if (mv.isError || !mv.data) return <Page><ErrorState message={errText(mv.error)} onRetry={() => mv.refetch()} /></Page>;
  const v = mv.data;
  const curCode = v.code;
  const next = v.rule.would_switch_to;

  const handle = async (m: Metric, h: 'request' | 'industry_avg' | 'exclude') => {
    setBusy(m.id);
    setErr('');
    try {
      const view = await patchMetric(id, m.id, { handling: h });
      qc.setQueryData(vpKeys.metrics(id, ef), view);
      await refresh();
    } catch (e) { setErr(errText(e)); } finally { setBusy(''); }
  };
  const apply = async () => {
    setBusy('apply');
    try {
      const r = await applyMetrics(id, v.sheet_id);
      if (isJob(r.data)) setApplyJob(r.data.job_id);
      else { await refresh(); nav(`/vp/${id}/result`); }
    } catch (e) { setErr(errText(e)); setBusy(''); }
  };
  const send = async (text: string) => {
    setErr('');
    try { const r = await postMessage(id, { text, context: 'numbers', sheet_id: v.sheet_id }); setJob(r.job_id); } catch (e) { setErr(errText(e)); }
  };
  const copy = async () => {
    if (!draft.data) return;
    try { await navigator.clipboard.writeText(draft.data.text); toast('요청 초안을 복사했어요'); } catch { toast('복사하지 못했어요 — 글을 직접 골라 복사해 주세요'); }
  };

  return (
    <Page dock={
      <Dock title="수치 보강" meta={`선택 필요 ${v.pending_ask} · 확인 권장 ${v.pending_check} · 답이 없으면 '업종 평균'으로 채우고 [추정] 표시`}
        input={{ placeholder: '아는 값이 있으면 바로 입력 (예: 오출고율 지금 0.8%)', label: '수치 직접 입력', onSend: send, busy: !!job }}
        actions={<>
          {err && <span className="vp-err">{err}</span>}
          <Link to={`/vp/${id}/result`} className="vp-btn">결과로</Link>
          {applyJob ? <Spinner label={`바꾸는 중 · ${aj.progress}%`} /> : <Btn primary onClick={apply} busy={busy === 'apply'}>이대로 반영</Btn>}
        </>} />
    }>
      <Agent text={v.intro}>
        <div className="vp-card" data-testid="vp-metrics">
          <CardHead title="기대 효과 수치" meta={`${v.counts.total} · 확보 ${v.counts.secured} · 추정 ${v.counts.estimated} · 비어 있음 ${v.counts.missing}`}
            right={<span className="vp-card__sub">찾는 순서 · 고객 자료 → 유관 사례 → 업종 평균 → 고객에게 요청</span>} />
          <div className="vp-mrow vp-mrow--head"><span>지표</span><span>지금</span><span>도입 후</span><span>출처</span><span>처리</span></div>
          {v.metrics.map((m) => {
            const ask = m.status === 'ask';
            return (
              <div key={m.id} className={ask ? 'vp-mrow vp-mrow--ask' : 'vp-mrow'} data-status={m.status}>
                <span className="vp-mrow__label" title={m.label}>{m.label}</span>
                <span className={m.before.display.includes('[') ? 'vp-mrow__v vp-mrow__v--ph' : 'vp-mrow__v'}>{m.before.display}</span>
                <span className={m.after.display.includes('[') ? 'vp-mrow__v vp-mrow__v--ph' : 'vp-mrow__v vp-mrow__v--after'}>{m.after.display}</span>
                <span className="vp-mrow__src" title={m.source_label}>{m.source_label || '—'}</span>
                <span className="vp-mrow__how">
                  {ask
                    ? HANDLING.map((h, i) => (
                      <button key={h.k} type="button" className={i === 0 ? 'vp-mini vp-mini--primary' : 'vp-mini'} disabled={busy === m.id || (h.k === 'industry_avg' && !m.industry_avg_available && false)}
                        title={h.k === 'industry_avg' && !m.industry_avg_available ? '같은 업종 사례 수치가 없어 값은 [00]으로 남아요' : undefined}
                        onClick={() => handle(m, h.k)}>{h.label}</button>
                    ))
                    : <>
                      <ModeChip mode={m.status === 'secured' ? 'auto' : m.status === 'estimated' ? 'check' : 'pin'} small />
                      <span title={m.how}>{m.status_label === '확보' || m.status_label === '추정' ? m.how : `${m.status_label} · ${m.how}`}</span>
                    </>}
                </span>
              </div>
            );
          })}
        </div>
        <div className="vp-card">
          <div className="vp-rule">
            <span className="vp-rule__text">
              <span className="vp-rule__k">자동 전환 규칙</span>
              <span className="vp-rule__main">쓸 수 있는 수치가 3개 미만이면 기대 효과를 EF-C(정량 + 정성)로 바꿔요.</span>
              <span className="vp-rule__line" data-testid="vp-rule">{v.rule.text}</span>
            </span>
            <span className="vp-rule__thumbs">
              <span className="vp-rule__thumb vp-rule__thumb--cur"><span style={{ width: 120, height: 68 }}><VThumb code={curCode} kind={curCode === 'EF-C' ? 'split' : 'hbars'} n={3} /></span><b>{curCode} · 지금</b></span>
              <Icon name="arrowRight" size={14} />
              <span className="vp-rule__thumb vp-rule__thumb--next"><span style={{ width: 120, height: 68 }}><VThumb code={next ?? (curCode === 'EF-C' ? 'EF-A' : 'EF-C')} kind={(next ?? (curCode === 'EF-C' ? 'EF-A' : 'EF-C')) === 'EF-C' ? 'split' : 'hbars'} n={3} /></span>
                <span>{next ? `${next} · 반영하면` : curCode === 'EF-C' ? 'EF-A · 3개 이상이면' : 'EF-C · 2개 이하면'}</span></span>
            </span>
          </div>
        </div>
        <div className="vp-card" data-testid="vp-data-request">
          <CardHead title="고객 데이터 요청 초안" meta="보내기는 직접 · 답이 오면 [추정]을 실제 값으로 바꿔요"
            right={<span style={{ display: 'flex', gap: 6 }}>
              <button type="button" className="vp-mini" onClick={copy} disabled={!draft.data}>복사</button>
              <a className="vp-mini" href={draft.data?.mailto ?? '#'} style={{ display: 'inline-flex', alignItems: 'center' }}>메일로 열기</a>
            </span>} />
          <div className="vp-draft">{draft.data?.text ?? '…'}</div>
        </div>
      </Agent>
    </Page>
  );
}
