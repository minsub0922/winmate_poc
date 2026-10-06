/** MI3V — 확정 필요 수치 · 사내 자료 `/mi/:id/verify?fix=` (§4.12) */
import { useEffect, useMemo, useRef, useState, type DragEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { cx, toast } from '@/ui';
import { uploadFile } from '@/api/client';
import {
  applyFix, cancelFix, errText, fixQuestion, isApiError, parseFix, patchFix, qk, revertFix, scanFix, useAnalysis, useFixItems, type FixItem, type FixSuggestion,
} from '../api';
import { useJobWatch, useLastScreen } from '../hooks';
import { copyText } from '../lib';
import { Agent, BigButton, Dock, ErrorBand, Ic, LoadingCard, MiPage, P, PromptInput, SecButton, Spin, UserBubble, useAid, useMiShell } from '../parts';

type View = 'all' | 'open' | 'ok';
type Cls = 'internal' | 'customer' | 'confidential';

export function VerifyPage() {
  const aid = useAid();
  const nav = useNavigate();
  const qc = useQueryClient();
  const [sp] = useSearchParams();
  const focus = sp.get('fix');
  const a = useAnalysis(aid);
  useMiShell(a.data, 3);
  useLastScreen(aid, 'verify');
  const [poll, setPoll] = useState<number | false>(false);
  const fx = useFixItems(aid, poll);
  const items = fx.data?.items ?? [];
  useEffect(() => { setPoll(items.some((x) => x.status === 'wait') ? 1500 : false); }, [items]);
  const [view, setView] = useState<View>('all');
  const [carry, setCarry] = useState(true);
  const [sugg, setSugg] = useState<Record<string, FixSuggestion>>({});
  const [said, setSaid] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [jobs, setJobs] = useState<string[]>([]);
  const [cls, setCls] = useState<Cls>('internal');
  const [over, setOver] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const rowFile = useRef<{ fix: string | null }>({ fix: null });

  const counts = fx.data?.counts ?? {};
  const total = counts.all ?? items.length;
  const okN = counts.ok ?? items.filter((x) => x.status === 'ok').length;
  const waitN = counts.wait ?? items.filter((x) => x.status === 'wait').length;
  const openN = counts.open ?? items.filter((x) => x.status !== 'ok').length;
  const shown = useMemo(() => items.filter((x) => (view === 'all' ? true : view === 'ok' ? x.status === 'ok' : x.status !== 'ok')), [items, view]);

  const refresh = () => { void qc.invalidateQueries({ queryKey: qk.fix(aid ?? '') }); };
  const lastJob = jobs[jobs.length - 1] ?? null;
  useJobWatch(lastJob, { onDone: (j) => {
    setJobs((x) => x.filter((y) => y !== j.id));
    refresh();
    if (j.status === 'failed') toast(j.error?.message || '올린 자료를 읽지 못했어요');
  } });

  async function upload(f: File, fixIds: string[] | null) {
    if (!aid) return;
    try {
      const up = await uploadFile(f, { confidential: cls !== 'customer', purpose: 'mi.fix' });
      const r = await scanFix(aid, { file_id: up.id, classification: cls, fix_ids: fixIds });
      setJobs((x) => [...x, r.job_id]);
      refresh();
    } catch (e) { toast(errText(e)); }
  }
  function onPick(fl: FileList | null) {
    const f = fl?.[0];
    if (f) void upload(f, rowFile.current.fix ? [rowFile.current.fix] : null);
    rowFile.current.fix = null;
  }
  function onDrop(e: DragEvent) {
    e.preventDefault();
    setOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) void upload(f, null);
  }

  async function tell(text: string) {
    if (!aid) return;
    setSaid((s) => [...s, text]);
    try {
      const r = await parseFix(aid, text);
      const map: Record<string, FixSuggestion> = {};
      for (const s of r.suggestions) map[s.fix_id] = s;
      setSugg((cur) => ({ ...cur, ...map }));
      if (!r.suggestions.length) toast('맞는 항목을 찾지 못했어요 · 값을 직접 넣어 주세요');
    } catch (e) { toast(errText(e)); }
  }

  async function apply() {
    if (!aid) return;
    setBusy(true);
    try {
      await applyFix(aid, carry);
      void qc.invalidateQueries({ queryKey: ['mi'] });
      nav(`/mi/${aid}/result`);
    } catch (e) { toast(errText(e)); } finally { setBusy(false); }
  }

  return (
    <MiPage dock={
      <Dock title="수치 확정" meta={`남은 ${openN}건`}
        right={<label className="mi-check"><input type="checkbox" checked={carry} onChange={(e) => setCarry(e.target.checked)} />남은 값은 [확정 필요]로 표시하고 제안서의 사실 확인 목록에 넘기기</label>}
        row={
          <div className="mi-dock__row">
            <PromptInput label="값 알려주기" placeholder="말로 알려주셔도 돼요 (예: 시장 규모는 내부 보고서 기준으로)" onSend={tell} />
            <SecButton to={`/mi/${aid}/result?panel=sources`}>출처 패널</SecButton>
            <BigButton onClick={() => void apply()} busy={busy} disabled={waitN > 0} reason="올린 자료를 읽는 중이에요" testId="mi3v-apply">확정값 반영하고 결과 보기</BigButton>
          </div>
        } />
    }>
      <Agent text={`제안서에 넣기 전에 확정이 필요한 값이 ${total}건 있습니다. 값을 직접 넣거나 사내 자료를 올려주시면 해당 문장에 반영하고, 출처를 그 자료로 바꿔 둡니다.`}>
        {fx.isError && <ErrorBand onRetry={() => void fx.refetch()} />}
        {!fx.data && !fx.isError && <LoadingCard lines={6} />}
        {fx.data && (
          <div className="mi-card" data-testid="mi3v-card">
            <div className="mi-vhead">
              <span className="mi-card__title">검증 목록</span>
              <div className="mi-row mi-grow">
                <div className="mi-vbar"><div style={{ width: `${total ? (okN / total) * 100 : 0}%` }} /></div>
                <span className="mi-note" style={{ whiteSpace: 'nowrap' }} data-testid="mi3v-progress"><b className="mi-num" style={{ color: 'var(--wm-text)', fontWeight: 800 }}>{okN} / {total}</b> 확정 · 확인 중 {waitN}</span>
              </div>
              <div className="mi-seg" role="tablist" aria-label="보기">
                {([['all', `전체 ${total}`], ['open', `남은 것 ${openN}`], ['ok', `확정 ${okN}`]] as Array<[View, string]>).map(([k, label]) => (
                  <button key={k} type="button" role="tab" aria-selected={view === k} onClick={() => setView(k)}>{label}</button>
                ))}
              </div>
            </div>
            <div className="mi-vcols"><span /><span>항목 · 근거 상태</span><span>확정 값</span><span>자료 · 다음 할 일</span></div>
            {shown.map((x) => (
              <FixRow key={x.id} aid={aid!} x={x} focus={focus === x.id} sugg={sugg[x.id]} onChanged={refresh} nav={nav}
                onAttach={() => { rowFile.current.fix = x.id; fileRef.current?.click(); }} />
            ))}
            {!shown.length && <div className="mi-wait">{view === 'ok' ? '아직 확정한 값이 없어요' : '확정이 필요한 값이 없어요'}</div>}
            <div className={cx('mi-upload', over && 'mi-upload--over')} onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)} onDrop={onDrop}
              data-testid="mi3v-upload">
              <div className="mi-upload__icon"><Ic d={P.upload} size={17} w={2} /></div>
              <div className="mi-grow" style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <div className="mi-upload__title">사내 자료 올리기 <span className="mi-sub">· PDF · XLSX · PPTX</span></div>
                <div className="mi-upload__desc">내부 시장조사 · 구축 결과 보고서 · 고객 제공 자료를 끌어다 놓으면 위 항목의 값을 찾아 채웁니다</div>
              </div>
              <select value={cls} onChange={(e) => setCls(e.target.value as Cls)} aria-label="자료 분류">
                <option value="internal">사내 자료</option><option value="customer">고객 자료</option><option value="confidential">대외비</option>
              </select>
              <button type="button" className="mi-mini mi-mini--primary" style={{ height: 34, padding: '0 12px', fontSize: 12.5 }}
                onClick={() => { rowFile.current.fix = null; fileRef.current?.click(); }}>파일 선택</button>
              <input ref={fileRef} type="file" hidden accept=".pdf,.xlsx,.pptx,.docx,.txt" data-testid="mi3v-file" onChange={(e) => { onPick(e.target.files); e.target.value = ''; }} />
            </div>
          </div>
        )}
      </Agent>
      {said.map((t, i) => <UserBubble key={i}>{t}</UserBubble>)}
      {Object.keys(sugg).length > 0 && <Agent text="말씀하신 값을 항목에 맞춰 두었어요. 행의 제안 값을 누르면 확정돼요." />}
    </MiPage>
  );
}

const ICON: Record<string, string> = { warn: P.warn, ok: P.ok, wait: P.clock };

function FixRow({ aid, x, focus, sugg, onChanged, onAttach, nav }:
  { aid: string; x: FixItem; focus: boolean; sugg?: FixSuggestion; onChanged: () => void; onAttach: () => void; nav: ReturnType<typeof useNavigate> }) {
  const [val, setVal] = useState(x.value ?? '');
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { setVal(x.value ?? ''); }, [x.value]);
  useEffect(() => { if (focus) ref.current?.scrollIntoView({ block: 'center' }); }, [focus]);

  async function save(v: string, unit?: string | null) {
    const t = v.trim();
    if (!t || (t === (x.value ?? '') && x.status === 'ok')) return;
    setSaving(true);
    setErr(null);
    try {
      await patchFix(aid, x.id, { value: t, unit: unit ?? x.unit ?? null });
      onChanged();
    } catch (e) {
      setErr(isApiError(e) && e.status === 422 ? e.message : errText(e));
    } finally { setSaving(false); }
  }

  async function act(label: string) {
    try {
      if (label === '출처 보기' || label === '출처 비교') {
        nav(`/mi/${aid}/result?tab=${x.tab}&panel=sources${x.claim_id ? `&claim=${x.claim_id}` : ''}`);
      } else if (label === '되돌리기') {
        await revertFix(aid, x.id);
        onChanged();
      } else if (label === '고객 질문 복사') {
        const q = await fixQuestion(aid, x.id);
        toast((await copyText(q.question)) ? '고객 질문을 복사했어요' : q.question);
      } else if (label === 'Spec 시트에서') {
        nav(x.samsung_model ? `/spec/new?models=${encodeURIComponent(x.samsung_model)}&from=${encodeURIComponent(`mi:${aid}`)}` : '/spec/new');
      } else if (label === '취소') {
        await cancelFix(aid, x.id);
        onChanged();
      }
    } catch (e) { toast(errText(e)); }
  }

  const fileShown = !!x.file_name && (x.status === 'wait' || x.value_source === 'file');
  const isInput = !fileShown && x.input_kind !== 'file_only';
  const label = x.title.replace(/"/g, '인치');
  return (
    <div ref={ref} className={cx('mi-vrow', x.status === 'ok' && 'mi-vrow--ok', focus && 'mi-vrow--focus')} data-fix={x.id} data-status={x.status} data-testid="mi3v-row">
      <span style={{ color: x.status === 'ok' ? 'var(--wm-brand)' : x.status === 'wait' ? 'var(--wm-text-subtle)' : 'var(--wm-text)', display: 'flex' }}>
        <Ic d={ICON[x.status] ?? P.warn} size={18} w={2.2} />
      </span>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
        <div className="mi-vrow__title" title={x.title}>{x.title}</div>
        <div className="mi-row" style={{ gap: 6 }}>
          <span className="mi-vrow__tab">{x.tab_label}</span>
          <span className={cx('mi-vrow__sub', x.status === 'ok' && 'mi-vrow__sub--ok', x.status === 'wait' && 'mi-vrow__sub--wait')} title={x.sub_text}>{x.sub_text}</span>
        </div>
        {sugg && x.status !== 'ok' && (
          <button type="button" className="mi-vrow__sugg" onClick={() => void save(sugg.value, sugg.unit)} title={sugg.basis}>제안 값 {sugg.value}{sugg.unit ?? ''} · 눌러서 확정</button>
        )}
      </div>
      <div style={{ minWidth: 0 }}>
        {isInput && (
          <>
            <div className={cx('mi-vinput', err && 'mi-vinput--err')}>
              <input aria-label={`${label} 확정 값`} placeholder={x.input_kind === 'ratio' ? (x.placeholder || '직영 : 가맹') : (x.placeholder || '값 입력')} value={val}
                onChange={(e) => setVal(e.target.value)} onBlur={() => void save(val)} disabled={x.status === 'wait'}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) (e.target as HTMLInputElement).blur(); }} />
              {saving ? <Spin size={12} /> : x.unit ? <span>{x.unit}</span> : null}
            </div>
            {err && <div className="mi-verr" role="alert">{err}</div>}
          </>
        )}
        {fileShown && (
          <div className="mi-vfile">
            <div className="mi-vfile__name"><Ic d={P.file} size={13} w={2} /><span className="mi-ell">{x.file_name}</span></div>
            {x.status === 'wait' && <div className="mi-vfile__bar"><div /></div>}
          </div>
        )}
      </div>
      <div className="mi-row" style={{ gap: 6 }}>
        {x.actions.map((l) => (
          (l === '출처 보기' || l === '출처 비교') && x.claim_id
            ? <Link key={l} className="mi-mini" style={{ height: 30, borderRadius: 7 }} to={`/mi/${aid}/result?tab=${x.tab}&panel=sources&claim=${x.claim_id}`}>{l}</Link>
            : <button key={l} type="button" className="mi-mini" style={{ height: 30, borderRadius: 7 }} onClick={() => void act(l)}>{l}</button>
        ))}
        <button type="button" className="mi-iconbtn" aria-label={`${label} 근거 파일 첨부`} title="파일로 확정" onClick={onAttach} disabled={x.status === 'wait'}>
          <Ic d={P.attach} size={14} w={2} />
        </button>
      </div>
    </div>
  );
}
