/** MI2A — 분석 설계 자동 제안 `/mi/:id/design` (§4.15) */
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Modal, Thumb, cx, toast } from '@/ui';
import { useFeatureItems } from '@/shell';
import type { JobEvent } from '@/api/jobs';
import {
  designMemo, errText, patchAnalysis, qk, startDesign, startRun, useAnalysis, useDesign, type Analysis, type Decision, type DesignView, type Mode,
} from '../api';
import { useJobWatch, useLastScreen } from '../hooks';
import { Agent, BigButton, Dock, ErrorBand, Ic, LoadingCard, MiPage, ModeChip, P, Pill, PromptInput, SecButton, Spin, UserBubble, useAid, useMiShell } from '../parts';
import { RulesSheet } from './RulesPage';

const STEP_LABELS = ['입력 읽기', '첨부 읽기', '업종 판별', '쓰임', '범위 정하기', '경쟁사 찾기', '설계 정리'];

export function DesignPage() {
  const aid = useAid();
  const nav = useNavigate();
  const qc = useQueryClient();
  const a = useAnalysis(aid);
  useMiShell(a.data, 2);
  useLastScreen(aid, 'design');
  const [jobId, setJobId] = useState<string | null>(null);
  const d = useDesign(aid, jobId ? 2500 : false);
  const [steps, setSteps] = useState<Array<{ label: string; status: string }>>([]);
  const [memoBusy, setMemoBusy] = useState(false);
  const [lastMemo, setLastMemo] = useState<string | null>(null);
  const [rules, setRules] = useState(false);
  const [sheet, setSheet] = useState<'usage' | 'internal' | null>(null);
  const [runBusy, setRunBusy] = useState(false);
  const started = useRef(false);
  const prev = useRef<Record<string, string>>({});
  const [flash, setFlash] = useState<string[]>([]);

  const view = d.data;
  const running = view?.status === 'running' || (!!jobId && view?.status !== 'done' && view?.status !== 'ask' && view?.status !== 'failed');

  // 들어왔는데 설계가 없으면 시작 · 돌고 있으면 그 잡을 구독 · 묻는 중이면 MI1Q 로
  useEffect(() => {
    if (!aid || !view) return;
    if (view.status === 'ask') { nav(`/mi/${aid}/design/industry`, { replace: true }); return; }
    if (view.status === 'running' && view.job_id && view.job_id !== jobId) setJobId(view.job_id);
    if (view.status === 'none' && !started.current) {
      started.current = true;
      startDesign(aid).then((r) => setJobId(r.job_id)).catch((e) => toast(errText(e)));
    }
  }, [aid, view, jobId, nav]);

  useJobWatch(jobId, {
    onEvent: (e: JobEvent) => {
      if (e.type === 'step' && e.data.label) {
        setSteps((s) => {
          const rest = s.filter((x) => x.label !== e.data.label);
          return [...rest, { label: String(e.data.label), status: String(e.data.status ?? 'run') }];
        });
      }
      if (e.type === 'awaiting_input') nav(`/mi/${aid}/design/industry`);
    },
    onDone: (j) => {
      setJobId(null);
      setSteps([]);
      void qc.invalidateQueries({ queryKey: qk.design(aid ?? '') });
      void qc.invalidateQueries({ queryKey: qk.analysis(aid ?? '') });
      void qc.invalidateQueries({ queryKey: qk.competitors(aid ?? '') });
      void qc.invalidateQueries({ queryKey: qk.criteria(aid ?? '') });
      const next = (j.result as { next_job_id?: string } | null)?.next_job_id;
      if (next) nav(`/mi/${aid}/run`);
      if (j.status === 'failed') toast(j.error?.message || '설계를 마치지 못했어요');
    },
  });

  // 메모 반영 뒤 바뀐 행만 잠깐 강조(제안)
  useEffect(() => {
    if (!view?.decisions?.length || running) return;
    const now: Record<string, string> = {};
    for (const x of view.decisions) now[x.key] = `${x.display_value}|${x.mode}|${x.reason}`;
    const before = prev.current;
    if (Object.keys(before).length) {
      const changed = Object.keys(now).filter((k) => before[k] !== undefined && before[k] !== now[k]);
      if (changed.length) {
        setFlash(changed);
        const t = window.setTimeout(() => setFlash([]), 1800);
        prev.current = now;
        return () => window.clearTimeout(t);
      }
    }
    prev.current = now;
  }, [view, running]);

  async function sendMemo(text: string) {
    if (!aid) return;
    setMemoBusy(true);
    setLastMemo(text);
    try {
      const r = await designMemo(aid, text);
      setJobId(r.job_id);
    } catch (e) {
      toast(errText(e));
    } finally {
      setMemoBusy(false);
    }
  }

  async function run() {
    if (!aid) return;
    setRunBusy(true);
    try {
      await startRun(aid, { mode: 'full' });
      void qc.invalidateQueries({ queryKey: qk.analysis(aid) });
      nav(`/mi/${aid}/run`);
    } catch (e) {
      if ((e as { code?: string }).code === 'RUN_IN_PROGRESS') nav(`/mi/${aid}/run`);
      else toast(errText(e));
    } finally {
      setRunBusy(false);
    }
  }

  const tally = view?.tally ?? {};
  return (
    <MiPage dock={
      <Dock title="분석 설계" meta="2 / 3 · 바꿀 것만 고르세요"
        right={<>
          <Pill to={`/mi/${aid}/scope`}>범위 직접 고르기</Pill>
          <Pill to={`/mi/${aid}/competitors`}>경쟁사 · 비교 기준</Pill>
          <Pill onClick={() => setRules(true)}>판단 규칙</Pill>
        </>}
        row={
          <div className="mi-dock__row">
            <PromptInput label="설계에 덧붙일 말" placeholder="설계에 덧붙일 말 (예: 경쟁사는 클라우드 CMS 업체 위주로)" onSend={sendMemo} busy={memoBusy || running} />
            <SecButton to={`/mi/${aid}/input`}>이전</SecButton>
            <BigButton onClick={() => void run()} busy={runBusy} disabled={running || !view?.decisions?.length} reason="설계를 마치면 시작할 수 있어요"
              testId="mi2a-run">{view?.run_label || '분석 시작 (약 3분)'}</BigButton>
          </div>
        } />
    }>
      {lastMemo && <UserBubble>{lastMemo}</UserBubble>}
      <Agent text={running ? '요구사항과 연결된 자료를 읽고 있어요' : '요구사항과 연결된 자료를 읽고 분석 설계를 정했어요. 바꾸고 싶은 것만 고르세요 — 나머지는 이대로 진행합니다.'}>
        {d.isError && <ErrorBand onRetry={() => void d.refetch()} />}
        {view?.status === 'failed' && !running && (
          <ErrorBand message={(view.error as { message?: string } | null)?.message || '설계를 마치지 못했어요.'}
            onRetry={() => { if (aid) startDesign(aid).then((r) => setJobId(r.job_id)).catch((e) => toast(errText(e))); }} />
        )}
        {running && <DesignProgress steps={steps} />}
        {!running && !view && !d.isError && <LoadingCard lines={7} />}
        {!running && view && view.decisions.length > 0 && (
          <>
            <div className="mi-card" data-testid="mi2a-design">
              <div className="mi-card__head" style={{ height: 46 }}>
                <Ic d={P.route} size={16} w={2} className="mi-brand" />
                <span className="mi-card__title">에이전트가 정한 분석 설계</span>
                <span className="mi-grow" />
                {(['auto', 'check', 'ask'] as Mode[]).map((m) => (
                  <ModeChip key={m} mode={m} dim={!tally[m]}>{m === 'auto' ? '자동' : m === 'check' ? '확인 권장' : '선택 필요'} {tally[m] ?? 0}</ModeChip>
                ))}
              </div>
              {view.decisions.map((x) => (
                <DecisionRow key={x.key} x={x} aid={aid!} flash={flash.includes(x.key)} onSheet={setSheet} />
              ))}
            </div>
            <SheetsPreview view={view} />
          </>
        )}
      </Agent>
      <RulesSheet open={rules} onClose={() => setRules(false)} />
      {a.data && sheet === 'usage' && <UsageSheet a={a.data} onClose={() => setSheet(null)} />}
      {a.data && sheet === 'internal' && <InternalSheet a={a.data} onClose={() => setSheet(null)} />}
    </MiPage>
  );
}

function DesignProgress({ steps }: { steps: Array<{ label: string; status: string }> }) {
  const st = (l: string) => steps.find((s) => s.label === l)?.status;
  const firstOpen = STEP_LABELS.find((l) => st(l) !== 'done');
  return (
    <div className="mi-card" aria-busy="true" data-testid="mi2a-loading">
      <div className="mi-loading">
        <div className="mi-steps-mini">
          {STEP_LABELS.map((l) => {
            const s = st(l) === 'done' ? 'done' : l === firstOpen ? 'run' : 'wait';
            return (
              <div key={l} className={cx('mi-steps-mini__row', s === 'done' && 'mi-steps-mini__row--done', s === 'run' && 'mi-steps-mini__row--run')}>
                {s === 'done' ? <span className="mi-dot-done mi-dot-done--sm"><Ic d={P.check} size={9} w={3.4} /></span> : s === 'run' ? <Spin size={18} /> : <span className="mi-dot-wait mi-dot-wait--sm" />}
                {l}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function DecisionRow({ x, aid, flash, onSheet }: { x: Decision; aid: string; flash: boolean; onSheet: (s: 'usage' | 'internal') => void }) {
  const route = x.change_route || '';
  const sheetKey = route === '#usage' ? 'usage' : route === '#internal' ? 'internal' : null;
  return (
    <div className={cx('mi-dec', flash && 'mi-dec--flash')} data-key={x.key} data-testid={`mi2a-row-${x.key}`}>
      <span className="mi-dec__k">{x.label}</span>
      <span className="mi-dec__v" title={x.display_value}>{x.display_value}</span>
      <span className="mi-dec__why" title={x.reason}>{x.reason}</span>
      <ModeChip mode={x.mode as Mode} />
      {sheetKey
        ? <button type="button" className="mi-dec__chg" onClick={() => onSheet(sheetKey)} aria-label={`${x.label} 바꾸기`}>바꾸기</button>
        : <Link to={route || `/mi/${aid}/scope`} className="mi-dec__chg" aria-label={`${x.label} 바꾸기`}>바꾸기</Link>}
    </div>
  );
}

export function SheetsPreview({ view }: { view: DesignView }) {
  if (!view.sheets_preview.length) return null;
  return (
    <div className="mi-sheets" data-testid="mi-sheets-preview">
      <div className="mi-sheets__head">
        <span className="mi-sheets__title">결과가 들어갈 시트 <span className="mi-sub">· {view.sheets_head}</span></span>
        <span className="mi-sheets__hint">분석이 끝나면 데이터 모양을 보고 한 번 더 골라요</span>
      </div>
      <div className="mi-sheets__grid">
        {view.sheets_preview.map((s) => (
          <div key={s.code + s.sheet} className="mi-sheet" data-code={s.code}>
            <div className="mi-thumb"><Thumb kind={s.thumb} n={3} code={s.code} /></div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
              <span className="mi-sheet__name">{s.sheet}</span>
              <span className="mi-sheet__code">{s.code}</span>
              <span className={cx('mi-sheet__note', s.industry && 'mi-sheet__note--ind')}>{s.note}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const USAGES: Array<{ value: 'standard' | 'solution' | 'quickwin' | 'exec_onepager' | 'none'; label: string; desc: string }> = [
  { value: 'standard', label: '표준 제안서', desc: 'MI 섹션 3시트 (시장 · 고객 · 경쟁)' },
  { value: 'solution', label: 'Solution형 제안서', desc: '대규모 MI 5~6시트 + 시사점' },
  { value: 'quickwin', label: '퀵윈 제안서', desc: 'MI 섹션 없음 → 리포트 + VP 재료로' },
  { value: 'exec_onepager', label: '경영진 한 장', desc: 'IM-B 1장 + 부록 2장' },
  { value: 'none', label: '연결 없음', desc: '리포트 · 보낼 때 다시 매핑' },
];

/** 쓰임 고르기 시트(Q10 제안) — 연결할 제안서 또는 쓰임만 */
function UsageSheet({ a, onClose }: { a: Analysis; onClose: () => void }) {
  const qc = useQueryClient();
  const prs = useFeatureItems('PR', 20);
  const [val, setVal] = useState(a.usage?.value ?? 'none');
  const [pid, setPid] = useState<string | null>(a.links?.proposal_id ?? null);
  const [busy, setBusy] = useState(false);
  const items = prs.data?.items ?? [];
  async function save() {
    setBusy(true);
    try {
      const p = items.find((x) => x.item_id === pid);
      const res = await patchAnalysis(a.id, { usage: { value: val, mode: 'pin', proposal_id: p?.item_id ?? null, proposal_title: p?.title ?? null } });
      qc.setQueryData([...qk.analysis(a.id), null], res);
      void qc.invalidateQueries({ queryKey: qk.design(a.id) });
      onClose();
    } catch (e) { toast(errText(e)); } finally { setBusy(false); }
  }
  return (
    <Modal open onClose={onClose} title="쓰임 바꾸기" width={560} footer={
      <div className="mi-row" style={{ justifyContent: 'flex-end', gap: 8 }}>
        <SecButton onClick={onClose}>취소</SecButton>
        <BigButton onClick={() => void save()} busy={busy} arrow={false}>이대로 정하기</BigButton>
      </div>}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div role="radiogroup" aria-label="쓰임" style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {USAGES.map((u) => (
            <div key={u.value} role="radio" aria-checked={val === u.value} tabIndex={0} className="mi-opt" style={{ padding: 10 }}
              onClick={() => setVal(u.value)} onKeyDown={(e) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); setVal(u.value); } }}>
              <span className="mi-opt__radio" />
              <div className="mi-opt__body"><span className="mi-opt__name" style={{ fontSize: 13.5 }}>{u.label}</span><span className="mi-opt__desc">{u.desc}</span></div>
            </div>
          ))}
        </div>
        {val !== 'none' && val !== 'exec_onepager' && (
          <label className="mi-field" style={{ marginTop: 6 }}>
            <span className="mi-field__label">연결할 제안서</span>
            <select value={pid ?? ''} onChange={(e) => setPid(e.target.value || null)} className="mi-select__btn" style={{ width: '100%' }}>
              <option value="">연결 안 함</option>
              {items.map((p) => <option key={p.item_id} value={p.item_id}>{p.title}</option>)}
            </select>
          </label>
        )}
      </div>
    </Modal>
  );
}

/** 사내 자료 고르기 시트(Q10 제안) — 첨부 중 분석에 쓸 사내 자료 */
function InternalSheet({ a, onClose }: { a: Analysis; onClose: () => void }) {
  const qc = useQueryClient();
  const files = a.files ?? [];
  const excluded = useMemo(() => new Set(a.internal?.excluded_file_ids ?? []), [a.internal]);
  const [on, setOn] = useState<Record<string, boolean>>(() => Object.fromEntries(files.map((f) => [f.file_id, !excluded.has(f.file_id) && f.include !== false])));
  const [busy, setBusy] = useState(false);
  async function save() {
    setBusy(true);
    try {
      const inc = files.filter((f) => on[f.file_id]).map((f) => f.file_id);
      const exc = files.filter((f) => !on[f.file_id]).map((f) => f.file_id);
      const res = await patchAnalysis(a.id, { internal: { included_file_ids: inc, excluded_file_ids: exc } });
      qc.setQueryData([...qk.analysis(a.id), null], res);
      void qc.invalidateQueries({ queryKey: qk.design(a.id) });
      onClose();
    } catch (e) { toast(errText(e)); } finally { setBusy(false); }
  }
  return (
    <Modal open onClose={onClose} title="사내 자료" width={520} footer={
      <div className="mi-row" style={{ justifyContent: 'flex-end', gap: 8 }}>
        <SecButton onClick={onClose}>취소</SecButton>
        <BigButton onClick={() => void save()} busy={busy} arrow={false}>이대로 정하기</BigButton>
      </div>}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 13 }}>
        <div className="mi-note">사내 사례 DB · {a.internal?.summary || `도입사례 ${a.internal?.kb_case_count ?? 0}건`} — 대외비 수치는 고객 제출물에 넣지 않아요.</div>
        {!files.length && <div className="mi-note">첨부한 자료가 없어요.</div>}
        {files.map((f) => (
          <label key={f.file_id} className="mi-check">
            <input type="checkbox" checked={!!on[f.file_id]} onChange={(e) => setOn((o) => ({ ...o, [f.file_id]: e.target.checked }))} />
            <span className="mi-ell">{f.name || f.file_id}</span>
            <span className="mi-tag">{f.classification === 'confidential' ? '대외비' : f.classification === 'public' ? '공개' : '사내'}</span>
          </label>
        ))}
      </div>
    </Modal>
  );
}
