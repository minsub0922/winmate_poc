/** SP1C — 조건으로 모델 찾기(`/spec/new/find` → `/spec/:id/find`, 06-spec §4.5) */
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { useJob } from '@/api/jobs';
import { useShellPage } from '@/shell/ShellContext';
import { Icon, PathIcon, Toggle, cx, toast } from '@/ui';
import {
  commitFinder, createSheet, errText, parseFinder, putFinder, useSheet, useSheetCache, type FinderCandidate, type FinderConditions, type FinderState, type Sheet,
} from './api';
import { Agent, BigButton, Chip2, Dock, PromptInput, SECTION, SpPage, UserBubble, VIcon, stepper } from './ui';

const SIZES = [['43', '43"'], ['50', '50"'], ['55', '55"'], ['65', '65"'], ['75+', '75" 이상']] as const;
const BRIGHT = [['any', '상관없음'], ['desc', '높은 순'], ['outdoor', '실외용']] as const;
const USAGE = [['menu_board', '메뉴보드'], ['wayfinding', '안내'], ['monitoring', '관제 · 모니터링'], ['meeting', '회의']] as const;
const INSTALL = [['wall', '벽걸이'], ['stand', '스탠드'], ['ceiling', '천장'], ['portrait', '세로 설치']] as const;
const REQ_BASE = [['continuous_operation', '24시간 운영'], ['wall', '벽걸이'], ['magicinfo', 'MagicINFO 호환']] as const;
const REQ_LABEL: Record<string, string> = { continuous_operation: '24시간 운영', wall: '벽걸이', magicinfo: 'MagicINFO 호환', stand: '스탠드', outdoor: '실외용',
  ceiling: '천장', portrait: '세로 설치' };
const reqLabel = (k: string) => (k.startsWith('size:') ? (k === 'size:75+' ? '75" 이상' : `${k.slice(5)}"`) : REQ_LABEL[k] ?? k);
const EMPTY: FinderConditions = { sizes: [], brightness: 'desc', usage: [], install: [], required: [], off: [] };

type Cond = Required<FinderConditions>;
const toggle = <T,>(xs: T[], v: T) => (xs.includes(v) ? xs.filter((x) => x !== v) : [...xs, v]);

export default function FindPage() {
  const { id } = useParams();
  const nav = useNavigate();
  const [sp, setSp] = useSearchParams();
  const sheetQ = useSheet(id, { poll: (x) => (x?.finder?.status === 'running' ? 1500 : false) });
  const s = sheetQ.data;
  const cache = useSheetCache();
  const st: FinderState | null | undefined = s?.finder;
  const cond = { ...EMPTY, ...(st?.conditions ?? {}) } as Cond;
  const [job, setJob] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [reqMenu, setReqMenu] = useState(false);
  const creating = useRef<Promise<Sheet> | null>(null);
  const j = useJob(job, { onDone: (r) => { setJob(null); void cache.refresh(r.ref ?? id ?? ''); if (r.status === 'failed') toast(r.error?.message ?? '조건을 해석하지 못했어요.'); } });

  const ensure = async (): Promise<Sheet> => {
    if (s) return s;
    if (!creating.current) creating.current = createSheet({ start: 'find' });
    const made = await creating.current;
    cache.put(made);
    nav(`/spec/${made.id}/find`, { replace: true });
    return made;
  };

  const put = async (body: Parameters<typeof putFinder>[1]) => {
    try {
      const sheet = await ensure();
      const next = await putFinder(sheet.id, body);
      cache.qc.setQueryData(['spec', 'sheet', sheet.id], (old: Sheet | undefined) => (old ? { ...old, finder: next } : old));
    } catch (e) { toast(errText(e)); }
  };
  const setCond = (patch: Partial<Cond>, offTag?: string, turnedOff?: boolean) => {
    let off = [...(cond.off ?? [])];
    if (offTag) off = turnedOff ? Array.from(new Set([...off, offTag])) : off.filter((x) => x !== offTag);
    void put({ conditions: { ...cond, ...patch, off } });
  };

  // 다른 화면에서 온 preset(대안 보기 · 대안 모델 찾기 · 다른 후보 찾기)
  const presetDone = useRef(false);
  useEffect(() => {
    const preset = sp.get('preset');
    if (!id || !preset || presetDone.current) return;
    presetDone.current = true;
    void put({ preset }).then(() => { const n = new URLSearchParams(sp); n.delete('preset'); setSp(n, { replace: true }); });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const send = async (text: string) => {
    try {
      const sheet = await ensure();
      const r = await parseFinder(sheet.id, text);
      cache.qc.setQueryData(['spec', 'sheet', sheet.id], (old: Sheet | undefined) =>
        (old ? { ...old, finder: { ...(old.finder ?? { conditions: EMPTY }), query_text: text, status: 'running' } as FinderState } : old));
      setJob(r.job_id);
    } catch (e) { toast(errText(e)); }
  };

  const selected = st?.selected ?? (st?.candidates ?? []).filter((c) => c.selected).map((c) => c.ref);
  const n = selected.length;
  const pick = (c: FinderCandidate) => void put({ selected: toggle(selected, c.ref) });
  const commit = async (to: 'items' | 'products') => {
    if (!s) return;
    setBusy(true);
    try {
      const u = await commitFinder(s.id, selected, to);
      cache.put(u);
      nav(to === 'items' ? `/spec/${s.id}/items` : `/spec/${s.id}/products`);
    } catch (e) { toast(errText(e)); } finally { setBusy(false); }
  };

  const running = !!job || st?.status === 'running';
  const cands = st?.candidates ?? [];
  const view = st?.view ?? 'cards';
  const userText = st?.query_text || null;
  const required = cond.required ?? [];
  const extraReq = required.filter((r) => !REQ_BASE.some(([k]) => k === r));
  const canRequire = [
    ...(cond.sizes ?? []).map((v) => `size:${v}`), ...(cond.install ?? []).filter((i) => i !== 'wall'), ...(cond.brightness === 'outdoor' ? ['outdoor'] : []),
  ].filter((k) => !required.includes(k));

  useShellPage({ section: SECTION, title: s?.title_confirmed ? s.title : '새 작업', hasTask: true, stepper: stepper(1) });

  let agent: string;
  if (running) agent = '조건을 해석하고 사내 카탈로그에서 후보를 찾고 있어요…';
  else if (st?.status === 'failed') agent = `조건을 해석하지 못했어요. ${st.error ?? ''} 칩으로 조건을 골라도 돼요.`;
  else if (st?.agent_text && cands.length) agent = st.agent_text;
  else if (st?.agent_text) agent = '조건에 맞는 후보를 찾지 못했어요. 조건을 줄이거나 바꿔 보세요.';
  else agent = '어떤 디스플레이가 필요한지 말해 주세요. 크기 · 밝기 · 용도 · 설치 조건으로 후보를 찾아 드려요.';

  return (
    <SpPage
      dock={
        <Dock title="조건으로 찾기" meta={`${n}개 선택 · 1 / 3`}
          right={<button type="button" className="sp-link" disabled={!n || busy} onClick={() => void commit('products')}>모델명으로 직접 입력</button>}
          row={
            <>
              <PromptInput label="조건 추가" placeholder="조건을 말로 더하기 (예: 베젤이 얇은 모델, 비디오월 구성 가능)" sendLabel="후보 다시 찾기"
                onSend={send} busy={running} />
              <BigButton onClick={() => void commit('items')} disabled={!n} busy={busy} title="시트에 넣을 모델을 골라 주세요">
                {n === 1 ? '1개로 시트 만들기' : `${n}개로 비교표 만들기`}
              </BigButton>
            </>
          }>
          <ChipGroup label="크기">
            {SIZES.map(([v, l]) => (
              <Chip2 key={v} on={(cond.sizes ?? []).includes(v)} onClick={() => setCond({ sizes: toggle(cond.sizes ?? [], v) }, `size:${v}`, (cond.sizes ?? []).includes(v))}>{l}</Chip2>
            ))}
          </ChipGroup>
          <ChipGroup label="밝기">
            {BRIGHT.map(([v, l]) => <Chip2 key={v} on={cond.brightness === v} onClick={() => setCond({ brightness: v }, 'brightness', false)}>{l}</Chip2>)}
          </ChipGroup>
          <ChipGroup label="용도">
            {USAGE.map(([v, l]) => (
              <Chip2 key={v} on={(cond.usage ?? []).includes(v)} onClick={() => setCond({ usage: toggle(cond.usage ?? [], v) }, `usage:${v}`, (cond.usage ?? []).includes(v))}>{l}</Chip2>
            ))}
          </ChipGroup>
          <ChipGroup label="설치">
            {INSTALL.map(([v, l]) => (
              <Chip2 key={v} on={(cond.install ?? []).includes(v)} onClick={() => setCond({ install: toggle(cond.install ?? [], v) }, `install:${v}`, (cond.install ?? []).includes(v))}>{l}</Chip2>
            ))}
          </ChipGroup>
          <ChipGroup label="필수">
            {[...REQ_BASE.map(([k]) => k), ...extraReq].map((k) => (
              <Chip2 key={k} on={required.includes(k)} onClick={() => setCond({ required: toggle(required, k) }, `required:${k}`, required.includes(k))}>{reqLabel(k)}</Chip2>
            ))}
            <span style={{ position: 'relative' }}>
              <button type="button" className="sp-chip" aria-haspopup="menu" aria-expanded={reqMenu} onClick={() => setReqMenu((v) => !v)} disabled={!canRequire.length}
                title={!canRequire.length ? '필수로 올릴 조건이 없어요' : undefined}>+ 필수로 지정</button>
              {reqMenu && (
                <div className="sp-menu" role="menu" style={{ bottom: 38, left: 0 }}>
                  {canRequire.map((k) => (
                    <button key={k} type="button" role="menuitem" onClick={() => { setReqMenu(false); setCond({ required: [...required, k] }, `required:${k}`, false); }}>{reqLabel(k)}</button>
                  ))}
                </div>
              )}
            </span>
            <span className="sp-note" style={{ marginLeft: 6 }}>필수를 못 맞춘 모델은 조건 밖으로 표시</span>
          </ChipGroup>
          {(st?.extra?.length ?? 0) > 0 && (
            <div className="sp-chiprow">
              {st!.extra!.map((e) => (
                <span key={e.id} className="sp-chip sp-chip--h28" style={{ cursor: 'default' }}>
                  {e.label}
                  <button type="button" aria-label={`${e.label} 제거`} className="sp-icbtn" style={{ width: 18, height: 18, color: 'var(--wm-text-muted)' }}
                    onClick={() => void put({ extra: st!.extra!.filter((x) => x.id !== e.id) })}><Icon name="x" size={11} /></button>
                </span>
              ))}
            </div>
          )}
        </Dock>
      }>
      {userText && <UserBubble>{userText}</UserBubble>}
      <Agent text={agent}>
        {cands.length > 0 && (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 13, fontWeight: 600 }} data-testid="sp1c-head">후보 {cands.length}개 · 조건 일치순</span>
              <span className="sp-note">사내 카탈로그 {st?.catalog_version} 기준</span>
              <span style={{ flex: 1 }} />
              <button type="button" className="sp-minibtn" aria-pressed={view === 'table'} onClick={() => void put({ view: view === 'table' ? 'cards' : 'table' })}>
                {view === 'table' ? '카드로 보기' : '표로 비교'}
              </button>
              <Toggle checked={!!st?.hide_out} onChange={(v) => void put({ hide_out: v })} label="조건 밖 후보 숨기기" />
            </div>
            {view === 'table' ? <CandTable cands={cands} onPick={pick} /> : (
              <div className="sp-cards" data-testid="sp1c-cards">
                {cands.map((c) => <CandCard key={c.ref} c={c} dup={cands.filter((x) => x.display_name === c.display_name).length > 1} onPick={() => pick(c)} />)}
              </div>
            )}
          </>
        )}
      </Agent>
    </SpPage>
  );
}

function ChipGroup({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="sp-chiprow" role="group" aria-label={label}>
      <span className="sp-chiprow__label">{label}</span>
      {children}
    </div>
  );
}

function CandCard({ c, onPick, dup }: { c: FinderCandidate; onPick: () => void; dup?: boolean }) {
  const big = (c.size_inch ?? 0) >= 60;
  const all = c.ok === c.total;
  return (
    <div className={cx('sp-cand', c.selected && 'sp-cand--sel', c.out && 'sp-cand--out')} data-testid="sp1c-card" data-model={c.display_name} data-out={c.out ? '1' : '0'}>
      <button type="button" className={cx('sp-selbox', c.selected && 'sp-selbox--on')} aria-label={`${c.display_name} 선택`} aria-pressed={!!c.selected} onClick={onPick}>
        {c.selected && <PathIcon d="M5 12l5 5L20 7" size={12} strokeWidth={3} />}
      </button>
      <div className="sp-cand__top">
        <span className="sp-screen" style={{ width: big ? 74 : 64, height: big ? 42 : 36 }} data-testid="sp1c-screen" />
        <div style={{ minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <span className="sp-cand__name">{c.display_name}</span>
            <span className={cx('sp-cand__score', all && 'sp-cand__score--all')}>조건 {c.ok}/{c.total}</span>
          </div>
          <div className="sp-cand__series">{c.series_label}{dup && c.model_code ? ` · ${c.model_code}` : ''}</div>
        </div>
      </div>
      <div className="sp-bars" aria-hidden="true">
        {(c.rows ?? []).map((r) => <span key={r.key} className={cx('sp-bar', r.state === 'ok' && 'sp-bar--ok', r.state === 'no' && 'sp-bar--no')} />)}
      </div>
      <div className="sp-conds">
        {(c.rows ?? []).map((r) => (
          <div key={r.key} className="sp-cond" data-key={r.key} data-state={r.state}>
            <VIcon state={r.state} />
            <span className="sp-cond__name">{r.label}</span>
            <span className={cx('sp-cond__v', r.state === 'check' && 'sp-cond__v--check', r.state === 'no' && 'sp-cond__v--no')}>{r.value_text}</span>
          </div>
        ))}
      </div>
      <button type="button" className={cx('sp-addbtn', c.selected && 'sp-addbtn--on')} onClick={onPick}>{c.selected ? '선택됨' : '+ 시트에 담기'}</button>
    </div>
  );
}

function CandTable({ cands, onPick }: { cands: FinderCandidate[]; onPick: (c: FinderCandidate) => void }) {
  const keys = Array.from(new Set(cands.flatMap((c) => (c.rows ?? []).map((r) => r.key))));
  const label = (k: string) => cands.flatMap((c) => c.rows ?? []).find((r) => r.key === k)?.label ?? k;
  const cols = `90px 1.2fr ${keys.map(() => '1fr').join(' ')} 0.9fr 0.8fr 0.9fr 0.8fr 104px`;
  return (
    <div className="sp-card">
      <div className="sp-grid" style={{ gridTemplateColumns: cols, fontSize: 12 }}>
        <div className="sp-th">모델</div><div className="sp-th">계열</div>
        {keys.map((k) => <div key={k} className="sp-th">{label(k)}</div>)}
        <div className="sp-th">밝기</div><div className="sp-th">운영</div><div className="sp-th">소비전력</div><div className="sp-th">무게</div><div className="sp-th" />
        {cands.map((c) => (
          <Fragmentish key={c.ref}>
            <div style={{ fontWeight: 700 }} className={c.out ? 'sp-muted' : undefined}>{c.display_name}</div>
            <div>{c.series_label}</div>
            {keys.map((k) => {
              const r = (c.rows ?? []).find((x) => x.key === k);
              return <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>{r && <VIcon state={r.state} size={12} />}{r?.value_text ?? '—'}</div>;
            })}
            <div>{c.brightness_nit != null ? `${c.brightness_nit} nit` : '—'}</div>
            <div>{c.operation ?? '—'}</div>
            <div>{c.power_text ?? '—'}</div>
            <div>{c.weight_text ?? '—'}</div>
            <div><button type="button" className={cx('sp-addbtn', c.selected && 'sp-addbtn--on')} style={{ height: 26, padding: '0 8px' }} onClick={() => onPick(c)}>
              {c.selected ? '선택됨' : '+ 담기'}</button></div>
          </Fragmentish>
        ))}
      </div>
    </div>
  );
}

function Fragmentish({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
