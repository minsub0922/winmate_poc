/** CA4 — 결과 · 한눈에 / 비교표 / 삼성 강점(§4.8). 부분 결과(분석 중 · 중지)는 회색 행 + 띠. */
import { useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Button, Icon, cx } from '@/ui';
import { errText, startRun, useAnalysis, useChanges, useResult, type ResultOut, type ResultRow, type View } from '../api';
import { useCaShell } from '../hooks';
import { Band, BigButton, CaPage, CmpName, ErrorCol, Flags, FootBar, Head, Letter, LoadingCol, VerdictChips } from '../parts';

const VIEWS: Array<{ value: View; label: string }> = [
  { value: 'overview', label: '한눈에' },
  { value: 'table', label: '비교표' },
  { value: 'strengths', label: '삼성 강점' },
];

export function ResultPage() {
  const { id: aid = '' } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const [sp, setSp] = useSearchParams();
  const view = (VIEWS.find((v) => v.value === sp.get('view'))?.value ?? 'overview') as View;
  const aq = useAnalysis(aid, { poll: 5000 });
  const a = aq.data;
  const analyzing = a?.status === 'analyzing';
  const rq = useResult(aid, view, analyzing ? 3000 : false);
  const res = rq.data;
  const ch = useChanges(aid, a?.status === 'upd');
  useCaShell({ aid, title: a?.title, current: 4, added: a?.added_refs });
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  if (aq.isLoading || rq.isLoading) return <LoadingCol lines={5} />;
  if (aq.isError || rq.isError || !a || !res) return <ErrorCol message="결과를 불러오지 못했어요" onRetry={() => { void aq.refetch(); void rq.refetch(); }} />;

  async function rerun(mode: 'full' | 'resume' | 'changed_only' | 'rejudge', ids?: string[]) {
    setBusy(mode);
    setErr(null);
    try {
      await startRun(aid, mode, ids ?? null);
      void qc.invalidateQueries({ queryKey: ['ca'] });
      nav(`/competitor/${aid}/run`);
    } catch (e) {
      setErr(errText(e, '다시 분석하지 못했어요'));
      setBusy(null);
    }
  }
  const setView = (v: View) => {
    const next = new URLSearchParams(sp);
    if (v === 'overview') next.delete('view'); else next.set('view', v);
    setSp(next, { replace: true });
  };
  const changeIds = (ch.data?.items ?? []).map((c) => c.competitor_id).filter(Boolean) as string[];

  return (
    <CaPage>
      <Head kicker={res.header?.kicker || '결과'} title={res.header?.title} desc={res.header?.desc} />
      <div className="ca-tabs ca-tabs--view" role="tablist" aria-label="결과 보기">
        {VIEWS.map((v) => <button key={v.value} type="button" role="tab" aria-selected={view === v.value} className="ca-tab" onClick={() => setView(v.value)}>{v.label}</button>)}
      </div>
      {a.status === 'upd' && ch.data?.summary && (
        <Band action={<Button h={32} variant="primary" loading={busy === 'changed_only'} onClick={() => rerun('changed_only', changeIds)}>다시 분석</Button>}>
          <b>다시 분석을 권해요.</b> {ch.data.summary}
        </Band>
      )}
      {a.needs_rejudge && !analyzing && (
        <Band action={<Button h={32} variant="primary" loading={busy === 'rejudge'} onClick={() => rerun('rejudge')}>다시 판정</Button>}>
          추가한 삼성 제품 · 사례를 판정에 넣으려면 다시 판정해요 · 모은 경쟁사 사실은 그대로 써요
        </Band>
      )}
      {res.partial?.stopped && (
        <Band tone="muted" action={<Button h={32} variant="primary" loading={busy === 'resume'} onClick={() => rerun('resume')}>이어서 분석</Button>}>{res.partial?.text}</Band>
      )}
      {res.partial?.analyzing && <Band action={<Link to={`/competitor/${aid}/run`} className="ca-linkbtn ca-linkbtn--brand">분석 화면으로</Link>}>{res.partial?.text}</Band>}
      {view === 'overview' && <Overview aid={aid} res={res} />}
      {view === 'table' && <TableBody res={res} />}
      {view === 'strengths' && <StrengthsBody res={res} />}
      {err && <Band tone="danger">{err}</Band>}
      <div className="ca-foot">
        <span className="ca-footer" title={res.footer?.text}>{res.footer?.text}</span>
        <span className="ca-grow" />
        <Button h={48} className="ca-big2" onClick={() => rerun('full')} loading={busy === 'full'} disabled={analyzing || !res.competitors.length}
          disabledReason="분석하는 중이에요" icon={<Icon name="refresh" size={14} strokeWidth={2.2} color="var(--wm-text-muted)" />}>다시 분석</Button>
        <BigButton onClick={() => nav(`/competitor/${aid}/send`)} disabled={!res.can_send} disabledReason={analyzing ? '분석이 끝나면 보낼 수 있어요' : '결과가 없어요'}>저장 · 보내기</BigButton>
      </div>
    </CaPage>
  );
}

function Overview({ aid, res }: { aid: string; res: ResultOut }) {
  const ok = (r: ResultRow) => r.state === 'done' || r.state === 'partial';
  return (
    <>
      <div className="ca-list" role="list" aria-label="경쟁사">
        {!res.competitors.length && <div className="ca-empty">아직 분석한 경쟁사가 없어요</div>}
        {res.competitors.map((r) => {
          const inner = (
            <>
              <Letter letter={r.letter} size={30} off={!ok(r)} />
              <div className="ca-res__who">
                <span className="ca-res__name"><CmpName letter={r.letter} real={r.real_name} /></span>
                <span className="ca-res__kind">{r.kind}</span>
              </div>
              {ok(r)
                ? <>
                  <span className="ca-res__pos" title={r.positioning}>{r.positioning || '[확인 필요]'}</span>
                  <VerdictChips up={r.up} eq={r.eq} dn={r.dn} />
                  <span className="ca-res__src">출처 {r.sources}</span>
                  <Icon name="chevronRight" size={14} strokeWidth={2.4} color="var(--wm-text-subtle)" />
                </>
                : <span className="ca-res__pos">{r.state_label}</span>}
            </>
          );
          return ok(r)
            ? <Link key={r.id} to={`/competitor/${aid}/competitors/${r.id}`} className="ca-res" role="listitem" data-letter={r.letter}>{inner}</Link>
            : <div key={r.id} className={cx('ca-res', 'ca-res--gray')} role="listitem" data-letter={r.letter} aria-disabled="true">{inner}</div>;
        })}
      </div>
      <Flags chips={res.chips} />
      <div className="ca-two">
        <div className="ca-box" aria-label="삼성 강점">
          <div className="ca-box__head">삼성 강점<b>{(res.strengths ?? []).length}</b></div>
          {!(res.strengths ?? []).length && <span className="ca-pt ca-pt--none">아직 이긴 기준이 없어요</span>}
          {(res.strengths ?? []).map((s) => (
            <div key={s.title} className="ca-pt"><Icon name="check" size={11} strokeWidth={3} color="var(--wm-ok)" /><b>{s.title}</b><span title={s.note}>{s.note}</span></div>
          ))}
        </div>
        <div className="ca-box" aria-label="주의할 점">
          <div className="ca-box__head">주의할 점<b className="warn">{(res.cautions ?? []).length}</b></div>
          {!(res.cautions ?? []).length && <span className="ca-pt ca-pt--none">삼성이 밀리는 기준이 없어요</span>}
          {(res.cautions ?? []).map((c) => (
            <div key={c.competitor_id + c.note} className="ca-pt"><span className="ca-pt__dot" /><b>{c.display}</b><span title={c.note}>{c.note}</span></div>
          ))}
        </div>
      </div>
    </>
  );
}

const VERDICT_WORD: Record<string, string> = { samsung_better: '우위', similar: '비슷', samsung_worse: '열위', unknown: '판정 없음' };

function TableBody({ res }: { res: ResultOut }) {
  const t = res.table;
  if (!t || !t.columns.length) return <div className="ca-list"><div className="ca-empty">비교표를 만들 결과가 없어요</div></div>;
  return (
    <>
      <div className="ca-table">
        <table aria-label="비교표">
          <thead>
            <tr>
              <th scope="col">비교 기준</th>
              {t.columns.map((c) => <th key={c.id} scope="col" className={c.samsung ? 'ca-table__sam' : undefined}>{c.label}</th>)}
            </tr>
          </thead>
          <tbody>
            {t.criteria.map((k, i) => (
              <tr key={k.id}>
                <th scope="row">{k.name}<small>중요도 {k.importance}</small></th>
                {t.cells[i]?.map((cell, j) => {
                  const col = t.columns[j];
                  return (
                    <td key={col?.id ?? j} className={col?.samsung ? 'ca-table__sam' : undefined}>
                      <span className={cx('ca-cell', cell.tbd && 'ca-cell--tbd')}>
                        {!col?.samsung && <span className={cx('ca-vdot', cell.verdict && `ca-vdot--${cell.verdict}`)} title={VERDICT_WORD[cell.verdict ?? 'unknown']}
                          aria-label={VERDICT_WORD[cell.verdict ?? 'unknown']} role="img" />}
                        <span>{cell.text}{(cell.source_ns?.length ?? 0) > 0 && <sup className="ca-sup"> {cell.source_ns!.join(',')}</sup>}</span>
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="ca-legend" aria-label="판정 표시">
        <span><span className="ca-vdot ca-vdot--samsung_better" />삼성 우위</span>
        <span><span className="ca-vdot ca-vdot--similar" />비슷</span>
        <span><span className="ca-vdot ca-vdot--samsung_worse" />삼성 열위</span>
        <span><span className="ca-vdot" />판정 없음</span>
      </div>
    </>
  );
}

function StrengthsBody({ res }: { res: ResultOut }) {
  return (
    <>
      <div className="ca-sec">
        <div className="ca-sec__head"><span>삼성 강점 <small>· 중요도 × 이긴 경쟁사 수가 큰 순서</small></span></div>
        {!(res.strengths ?? []).length && <div className="ca-list"><div className="ca-empty">아직 이긴 기준이 없어요</div></div>}
        {(res.strengths ?? []).map((s) => (
          <div key={s.title} className="ca-scard">
            <div className="ca-scard__title"><Icon name="check" size={13} strokeWidth={3} color="var(--wm-ok)" />{s.title}</div>
            <div className="ca-scard__note">{s.note}</div>
            <div className="ca-scard__meta">
              {(s.criterion_names ?? []).map((n) => <span key={n} className="ca-crit ca-crit--requirements" style={{ height: 22, fontSize: 11.5 }}>{n}</span>)}
              {(s.competitor_letters?.length ?? 0) > 0 && <span>이긴 경쟁사 {s.competitor_letters!.map((l) => `경쟁사 ${l}`).join(' · ')}</span>}
              {s.sources_label && <span>{s.sources_label}</span>}
            </div>
          </div>
        ))}
      </div>
      <div className="ca-sec">
        <div className="ca-sec__head"><span>주의할 점 <small>· 삼성이 밀리는 기준(중요도 순)</small></span></div>
        {!(res.cautions ?? []).length && <div className="ca-list"><div className="ca-empty">삼성이 밀리는 기준이 없어요</div></div>}
        {(res.cautions ?? []).map((c) => (
          <div key={c.competitor_id + c.note} className="ca-scard">
            <div className="ca-scard__title"><span className="ca-pt__dot" />{c.display}</div>
            <div className="ca-scard__note">{c.note}</div>
            <div className="ca-scard__meta">
              {(c.criterion_names ?? []).map((n) => <span key={n} className="ca-v ca-v--dn">{n}</span>)}
              {c.sources_label && <span>{c.sources_label}</span>}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

export default ResultPage;
