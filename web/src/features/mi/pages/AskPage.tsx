/** MI1Q — 업종이 두 갈래일 때 한 번 묻기 `/mi/:id/design/industry` (§4.16) · MI2A 업종 `바꾸기`(현재 값 선택 상태) */
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Thumb, cx, toast } from '@/ui';
import { answerJob, type JobEvent } from '@/api/jobs';
import { designMemo, errText, patchAnalysis, qk, useAnalysis, useDesign, useSegments, type Analysis } from '../api';
import { useJobWatch, useLastScreen } from '../hooks';
import { withRo } from '../lib';
import { Agent, BigButton, Dock, ErrorBand, Ic, LoadingCard, MiPage, ModeChip, P, PromptInput, SecButton, Spin, UserBubble, useAid, useMiShell } from '../parts';
import { RulesSheet } from './RulesPage';

interface Opt { key: string; segment: string; name: string; desc: string; score: number; codes: string; recommended?: boolean; thumbs?: string[]; mix?: { a: string; b: string; c: string } | null }
interface Ask {
  kind?: string; question?: string; agent_text?: string; diff?: number; gap_rule?: string; clues?: Array<{ t: string; code: string }>;
  options?: Opt[]; default?: string; default_text?: string; done?: string[]; footer?: string; hint?: string | null;
}

export function AskPage() {
  const aid = useAid();
  const nav = useNavigate();
  const qc = useQueryClient();
  const a = useAnalysis(aid);
  useMiShell(a.data, 2);
  useLastScreen(aid, 'design/industry');
  const [watch, setWatch] = useState<string | null>(null);
  const d = useDesign(aid, watch ? 2000 : false);
  const view = d.data;
  const asking = view?.status === 'ask' && !!view.ask;
  const running = view?.status === 'running';
  const [pick, setPick] = useState<string | null>(null);
  const [hints, setHints] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [rules, setRules] = useState(false);
  const segs = useSegments();

  useEffect(() => { if (view?.job_id && (asking || running)) setWatch(view.job_id); }, [view?.job_id, asking, running]);
  useJobWatch(watch, {
    onEvent: (e: JobEvent) => {
      if (e.type === 'awaiting_input' || e.type === 'status') void qc.invalidateQueries({ queryKey: qk.design(aid ?? '') });
    },
    onDone: (j) => {
      setWatch(null);
      void qc.invalidateQueries({ queryKey: qk.analysis(aid ?? '') });
      void qc.invalidateQueries({ queryKey: qk.design(aid ?? '') });
      const next = (j.result as { next_job_id?: string } | null)?.next_job_id;
      if (next) nav(`/mi/${aid}/run`);
      else if (j.status === 'succeeded') nav(`/mi/${aid}/design`, { replace: true });
      else if (j.status === 'failed') toast(j.error?.message || '설계를 마치지 못했어요');
    },
  });

  // 묻는 중이 아니면 현재 값으로 고르는 화면(MI2A `바꾸기`)
  const ask: Ask | null = asking ? (view!.ask as Ask) : null;
  const changeOpts = useMemo(() => (a.data && !ask ? changeOptions(a.data, segs.data?.items ?? []) : []), [a.data, ask, segs.data]);
  const opts: Opt[] = ask?.options ?? changeOpts;
  const current = ask ? (ask.default ?? opts[0]?.key) : currentKey(a.data, opts);
  useEffect(() => { setPick(null); }, [ask?.default, ask?.diff]);
  const chosen = opts.find((o) => o.key === (pick ?? current)) ?? opts[0];

  async function hint(text: string) {
    if (!aid) return;
    setHints((h) => [...h, text]);
    try {
      const r = await designMemo(aid, text);
      setWatch(r.job_id);
      void qc.invalidateQueries({ queryKey: qk.design(aid) });
    } catch (e) { toast(errText(e)); }
  }

  async function go() {
    if (!aid || !chosen) return;
    setBusy(true);
    try {
      if (ask && view?.job_id) {
        await answerJob(view.job_id, { segment: chosen.segment, mix: chosen.mix ?? null, start_analysis: true });
        setWatch(view.job_id);
        return;
      }
      const res = await patchAnalysis(aid, { segment: { code: chosen.segment === 'MIX' ? chosen.mix!.a : chosen.segment, mode: 'pin', mix: chosen.mix ?? null } });
      qc.setQueryData([...qk.analysis(aid), null], res);
      void qc.invalidateQueries({ queryKey: qk.design(aid) });
      nav(`/mi/${aid}/design`);
    } catch (e) {
      toast(errText(e));
    } finally {
      setBusy(false);
    }
  }

  const footer = ask?.footer ?? '업종 확인 · 업종 바꾸기';
  const [fTitle, ...fMeta] = footer.split(' · ');
  const top = opts[0]?.segment;
  return (
    <MiPage dock={
      <Dock title={fTitle} meta={fMeta.join(' · ')}
        right={<button type="button" className="mi-link" onClick={() => setRules(true)}>언제 묻는지 보기</button>}
        row={
          <div className="mi-dock__row">
            <PromptInput label="판단에 도움이 될 말" placeholder="판단에 도움이 될 말 (예: 결재는 호텔 F&B 팀장)" onSend={hint} busy={running} />
            <SecButton to={`/mi/${aid}/input`}>이전</SecButton>
            <BigButton onClick={() => void go()} busy={busy || (running && !!watch && !ask)} disabled={!chosen} testId="mi1q-go">
              {chosen ? (ask ? `${withRo(chosen.name)} 분석 시작` : `${withRo(chosen.name)} 바꾸기`) : '분석 시작'}
            </BigButton>
          </div>
        } />
    }>
      {hints.map((h, i) => <UserBubble key={i}>{h}</UserBubble>)}
      <Agent text={ask?.agent_text ?? '업종을 바꾸면 시장 · 비즈니스 · 사용자 레이아웃과 그 뒤 설계만 다시 정해요.'}>
        {d.isError && <ErrorBand onRetry={() => void d.refetch()} />}
        {!view && !d.isError && <LoadingCard lines={6} />}
        {view && opts.length > 0 && (
          <div className="mi-card" data-testid="mi1q-card">
            <div className="mi-card__head">
              <ModeChip mode={ask ? 'ask' : 'pin'} />
              <span className="mi-card__title">{ask?.question ?? '어느 업종 관점으로 분석할까요?'}</span>
              <span className="mi-grow" />
              {ask && <span className="mi-note">1 · 2위 차이 <b className="mi-num" style={{ color: 'var(--wm-text)' }}>{(ask.diff ?? 0).toFixed(2)}</b> · {ask.gap_rule}</span>}
              {running && <Spin size={16} />}
            </div>
            {(ask?.clues?.length ?? 0) > 0 && (
              <div className="mi-clues">
                <span className="mi-clues__label">읽힌 단서</span>
                {ask!.clues!.map((c, i) => <span key={c.t + i} className="mi-clue">{c.t}<b className={cx(c.code === top && 'mi-clue__top')}>{c.code}</b></span>)}
              </div>
            )}
            <div className="mi-opts" role="radiogroup" aria-label="업종 선택지">
              {opts.map((o) => {
                const on = o.key === chosen?.key;
                return (
                  <div key={o.key} role="radio" aria-checked={on} tabIndex={0} className="mi-opt" data-key={o.key}
                    onClick={() => setPick(o.key)} onKeyDown={(e) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); setPick(o.key); } }}>
                    <span className="mi-opt__radio" />
                    <div className="mi-opt__body">
                      <div className="mi-row"><span className="mi-opt__name">{o.name}</span>{o.recommended && <span className="mi-rec">추천</span>}</div>
                      <span className="mi-opt__desc">{o.desc}</span>
                      <div className="mi-row">
                        <div className={cx('mi-score', o.recommended && 'mi-score--top')}><div style={{ width: `${Math.round((o.score ?? 0) * 100)}%` }} /></div>
                        <span className="mi-num" style={{ fontSize: 12, fontWeight: 700 }}>{(o.score ?? 0).toFixed(2)}</span>
                        <span className="mi-opt__codes">{o.codes}</span>
                      </div>
                    </div>
                    <div className="mi-opt__thumbs">
                      {(o.thumbs ?? ['barline', 'process', 'journey']).map((k) => <div key={k} className="mi-thumb"><Thumb kind={k} n={3} /></div>)}
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="mi-ask-foot">
              <Ic d={P.clock} size={14} w={2} />
              <span className="mi-ell">{ask?.default_text ?? '결과 화면의 업종 칩에서 언제든 바꿀 수 있어요.'}</span>
            </div>
          </div>
        )}
        {(ask?.done?.length ?? 0) > 0 && (
          <div className="mi-done-chips">
            <span>자동으로 정한 것</span>
            {ask!.done!.map((t) => <span key={t} className="mi-done-chip"><svg width="9" height="9" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z" /></svg>{t}</span>)}
          </div>
        )}
        {view && !ask && !opts.length && view.status !== 'running' && (
          <div className="mi-note">고를 업종 후보가 없어요. <Link to={`/mi/${aid}/industry`}>업종 직접 고르기</Link></div>
        )}
      </Agent>
      <RulesSheet open={rules} onClose={() => setRules(false)} />
    </MiPage>
  );
}

function changeOptions(a: Analysis, items: Array<{ code: string; short: string; case_count?: number }>): Opt[] {
  const c = (a.segment?.candidates ?? []).filter((x) => x.code !== 'GEN');
  const name = (code: string) => items.find((s) => s.code === code)?.short ?? code;
  const n = (code: string) => items.find((s) => s.code === code)?.case_count;
  const out: Opt[] = c.slice(0, 2).map((x, i) => ({
    key: x.code, segment: x.code, name: name(x.code), desc: n(x.code) !== undefined ? `사례 ${n(x.code)}건` : '', score: x.confidence,
    codes: `MI-${x.code}-A · B · C`, recommended: i === 0, thumbs: ['barline', 'process', 'journey'],
  }));
  const code = a.segment?.code;
  if (code && code !== 'GEN' && !out.some((o) => o.key === code)) {
    out.unshift({ key: code, segment: code, name: name(code), desc: n(code) !== undefined ? `사례 ${n(code)}건` : '', score: a.segment?.confidence ?? 0,
      codes: `MI-${code}-A · B · C`, recommended: false, thumbs: ['barline', 'process', 'journey'] });
  }
  if (out.length >= 2) {
    const [x, y] = out;
    out.push({ key: 'MIX', segment: 'MIX', name: '섞어서 보기', desc: `시장 · 비즈니스는 ${x.name}, 사용자 여정은 ${y.name}`,
      score: Math.round(((x.score + y.score) / 2) * 100) / 100, codes: `MI-${x.segment}-A · B + MI-${y.segment}-C`, mix: { a: x.segment, b: x.segment, c: y.segment },
      thumbs: ['barline', 'process', 'journey'] });
  }
  return out;
}

function currentKey(a: Analysis | undefined, opts: Opt[]): string | undefined {
  if (!a) return opts[0]?.key;
  if (a.segment?.mix) return 'MIX';
  return a.segment?.code ?? opts[0]?.key;
}
