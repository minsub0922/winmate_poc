/** MI 화면 공용 부품 — 대화 줄 · 입력 카드 · 모드 칩 · 탭 · 비교표 · 인용 칩(보드 MI*.dc.html 그대로). 키트(@/ui)에 없는 것만 여기 둔다. */
import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import { Link, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { PathIcon, Skeleton, cx, toast } from '@/ui';
import { useShellPage } from '@/shell';
import type { DragType } from '@/shell';
import { addRefs, errText, qk, type Analysis, type ClaimRef, type CompareTable, type Mode, type Strength, type TabInfo, type Area } from './api';
import { MODE_LABEL } from './lib';
import './mi.css';

export const STEPS = ['고객 요구사항', '분석 범위', '분석 결과'];
export const SECTION = 'Market Intelligence';

// ── 아이콘 ──────────────────────────────────────────────
export const P = {
  arrow: 'M5 12h14M13 6l6 6-6 6',
  send: 'M12 19V5M6 11l6-6 6 6',
  ok: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M8 12l3 3 5-6',
  okSmall: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M8 12l3 3 5-6',
  check: 'M5 12l5 5L20 7',
  warn: 'M12 4l9 16H3z M12 10v4 M12 17v.5',
  clock: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M12 7v5l3 2',
  info: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M12 8v5 M12 16v.5',
  refresh: 'M20 11a8 8 0 1 0-2.3 5.7 M20 4v7h-7',
  x: 'M6 6l12 12M18 6L6 18',
  plus: 'M12 5v14M5 12h14',
  chevR: 'M9 6l6 6-6 6',
  chevD: 'M6 9l6 6 6-6',
  attach: 'M21 12l-8.5 8.5a5 5 0 0 1-7-7L14 5a3.5 3.5 0 0 1 5 5l-8.5 8.5a2 2 0 0 1-3-3L16 7',
  grid: 'M4 4h7v7H4z M13 4h7v7h-7z M4 13h7v7H4z M13 13h7v7h-7z',
  search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14z M20 20l-4-4',
  more: 'M5 12h.01 M12 12h.01 M19 12h.01',
  monitor: 'M3 4h18v12H3z M8 20h8 M12 16v4',
  doc: 'M6 3h8l5 5v13H6V3z M14 3v5h5 M9 13h7 M9 17h5',
  globe: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M3 12h18 M12 3a14 14 0 0 1 0 18 M12 3a14 14 0 0 0 0 18',
  external: 'M14 4h6v6 M20 4l-9 9 M18 14v6H4V6h6',
  undo: 'M9 14L4 9l5-5 M4 9h10a6 6 0 0 1 0 12h-3',
  upload: 'M12 16V4M6 10l6-6 6 6M4 20h16',
  chart: 'M4 20V10 M10 20V4 M16 20v-8 M22 20H2',
  route: 'M6 3v6a6 6 0 0 0 6 6h6 M14 11l4 4-4 4 M6 21v-4',
  storyboard: 'M4 5h16v14H4z M4 11h16 M10 11v8',
  stop: 'M7 7h10v10H7z',
  edit: 'M4 20h4L19 9l-4-4L4 16v4z',
  file: 'M6 3h8l5 5v13H6V3z M14 3v5h5',
  link: 'M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1 M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1',
  table: 'M4 4h16v16H4z M4 10h16 M4 15h16 M10 4v16',
  scenario: 'M4 6h16v12H4z M10 9l5 3-5 3V9z',
  grip: 'M9 6h.01 M15 6h.01 M9 12h.01 M15 12h.01 M9 18h.01 M15 18h.01',
};

const MODE_FILL: Record<Mode, string> = {
  auto: 'M13 2L4 14h7l-1 8 9-12h-7l1-8z',
  check: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm-1 5h2v7h-2zm0 9h2v2h-2z',
  ask: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm-1 14h2v2h-2zm1-10a4 4 0 0 1 4 4c0 2-3 2.5-3 4h-2c0-2.5 3-3 3-4a2 2 0 0 0-4 0H8a4 4 0 0 1 4-4z',
  pin: 'M9 2h6l-1 6 3 3v2h-4v7l-1 2-1-2v-7H7v-2l3-3z',
};

/** 채운 아이콘(보드 판단 모드 칩) */
export function FillIcon({ d, size = 10 }: { d: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" style={{ flexShrink: 0 }}>
      <path d={d} fillRule="evenodd" />
    </svg>
  );
}

export function Ic({ d, size = 14, w = 2.2, className }: { d: string; size?: number; w?: number; className?: string }) {
  return <span className={className} style={{ display: 'inline-flex', flexShrink: 0 }} aria-hidden="true"><PathIcon d={d} size={size} strokeWidth={w} /></span>;
}

export function Spin({ size = 14 }: { size?: number }) {
  return (
    <svg className="mi-spin" width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9" stroke="var(--wm-line-step)" strokeWidth="3" />
      <path d="M12 3a9 9 0 0 1 9 9" stroke="var(--wm-brand)" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

/** 판단 모드 칩(§3.3) — 자동 · 확인 권장 · 선택 필요 · 고정 */
export function ModeChip({ mode, dim, children, title }: { mode: Mode; dim?: boolean; children?: ReactNode; title?: string }) {
  return (
    <span className={cx('mi-mode', `mi-mode--${mode}`, dim && 'mi-mode--dim')} data-mode={mode} title={title}>
      <FillIcon d={MODE_FILL[mode]} />{children ?? MODE_LABEL[mode]}
    </span>
  );
}

// ── 셸 맥락 ─────────────────────────────────────────────

export function useAid(): string | undefined {
  return useParams().id;
}

/**
 * MI 작업 화면 공통 셸 맥락(§4.0) — `현재 작업에 추가` 로 제품 · 솔루션은 경쟁사 비교의 삼성 쪽 제품으로, 사례는 사내 사례 DB 출처로(§6.13).
 * 드롭 영역은 없다(accepts 비움). 작업이 아직 없으면 `ensure` 로 먼저 만든다(MI1).
 */
export function useMiShell(a: Analysis | null | undefined, step: 1 | 2 | 3, opts: { complete?: boolean; title?: string; ensure?: () => Promise<string | null> } = {}) {
  const qc = useQueryClient();
  const aRef = useRef(a);
  aRef.current = a;
  useShellPage({
    section: SECTION,
    title: opts.title ?? (a?.title || '새 작업'),
    hasTask: true,
    accepts: [],
    added: (a?.samsung_products ?? []).map((p) => p.ref).filter((r): r is string => !!r),
    addable: ['product', 'solution', 'case'],
    onAdd: async (type: DragType, refs: string[]) => {
      if (type !== 'product' && type !== 'solution' && type !== 'case') return { added: [] };
      let id = aRef.current?.id ?? null;
      if (!id && opts.ensure) id = await opts.ensure();
      if (!id) return { added: [] };
      try {
        const r = await addRefs(id, type, refs);
        void qc.invalidateQueries({ queryKey: qk.analysis(id) });
        return { added: r.added };
      } catch (e) {
        toast(errText(e));
        return { added: [] };
      }
    },
    stepper: { steps: STEPS, current: step, complete: opts.complete },
    sidebarGroup: 'mi',
  });
}

// ── 뼈대 ───────────────────────────────────────────────

export function MiPage({ children, dock, narrow, gap22 }: { children: ReactNode; dock?: ReactNode; narrow?: boolean; gap22?: boolean }) {
  return (
    <div className="mi-page">
      <div className="mi-scroll">
        <div className={cx('mi-col', narrow && 'mi-col--narrow', gap22 && 'mi-col--gap22')}>{children}</div>
      </div>
      {dock}
    </div>
  );
}

export function Agent({ text, children, testId }: { text?: ReactNode; children?: ReactNode; testId?: string }) {
  return (
    <div className="mi-agent">
      <div className="mi-agent__logo" aria-hidden="true">W</div>
      <div className="mi-agent__body">
        {text && <div className="mi-agent__text" data-testid={testId}>{text}</div>}
        {children}
      </div>
    </div>
  );
}

export function UserBubble({ children, chip }: { children: ReactNode; chip?: boolean }) {
  return <div className={cx('mi-user', chip && 'mi-user--chip')} data-testid="mi-user">{children}</div>;
}

export function Dock({ title, meta, right, children, row, narrow, label = '입력 카드' }:
  { title: ReactNode; meta?: ReactNode; right?: ReactNode; children?: ReactNode; row?: ReactNode; narrow?: boolean; label?: string }) {
  return (
    <div className="mi-dock-wrap">
      <div className={cx('mi-dock', narrow && 'mi-dock--narrow')} role="region" aria-label={label}>
        <div className="mi-dock__head">
          <div className="mi-dock__title" data-testid="mi-dock-title">{title}{meta && <span className="mi-sub"> · {meta}</span>}</div>
          {right && <div className="mi-dock__links">{right}</div>}
        </div>
        {children}
        {row}
      </div>
    </div>
  );
}

/** 입력 줄(시각 숨김 라벨 + placeholder + 보내기). 한글 조합 중 Enter 무시 */
export function PromptInput({ label, placeholder, onSend, busy, disabled, initial = '' }:
  { label: string; placeholder: string; onSend: (text: string) => void | boolean | Promise<void | boolean>; busy?: boolean; disabled?: boolean; initial?: string }) {
  const [v, setV] = useState(initial);
  const id = useId();
  const ref = useRef<HTMLInputElement>(null);
  const send = async () => {
    const t = v.trim();
    if (!t || busy || disabled) return;
    const keep = await onSend(t);
    if (keep !== false) setV('');
    ref.current?.focus();
  };
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.nativeEvent.isComposing) return;
    if (e.key === 'Enter') { e.preventDefault(); void send(); }
  };
  const on = !!v.trim() && !busy && !disabled;
  return (
    <div className="mi-prompt">
      <label htmlFor={id} className="wm-sr-only">{label}</label>
      <input id={id} ref={ref} value={v} placeholder={placeholder} onChange={(e) => setV(e.target.value)} onKeyDown={onKey} disabled={disabled} />
      <button type="button" className={cx('mi-send', on && 'mi-send--on')} aria-label="보내기" onClick={() => void send()} disabled={!on}>
        {busy ? <Spin size={14} /> : <PathIcon d={P.send} size={15} strokeWidth={2.2} />}
      </button>
    </div>
  );
}

/** 오른쪽 아래 큰 버튼(삼성 블루) — `to` 가 있으면 링크 */
export function BigButton({ children, onClick, disabled, reason, busy, to, arrow = true, icon, testId }:
  { children: ReactNode; onClick?: () => void; disabled?: boolean; reason?: string; busy?: boolean; to?: string; arrow?: boolean; icon?: ReactNode; testId?: string }) {
  const inner = (
    <>
      {icon}
      <span>{children}</span>
      {busy ? <Spin size={14} /> : arrow && <PathIcon d={P.arrow} size={16} strokeWidth={2.2} />}
    </>
  );
  if (to && !disabled && !busy) return <Link to={to} className="mi-btn mi-btn--primary" data-testid={testId}>{inner}</Link>;
  return (
    <button type="button" className="mi-btn mi-btn--primary" onClick={onClick} disabled={disabled || busy} title={disabled ? reason : undefined}
      aria-busy={busy || undefined} data-testid={testId}>{inner}</button>
  );
}

export function SecButton({ children, onClick, to, disabled, title, icon }: { children: ReactNode; onClick?: () => void; to?: string; disabled?: boolean; title?: string; icon?: ReactNode }) {
  if (to && !disabled) return <Link to={to} className="mi-btn" title={title}>{icon}{children}</Link>;
  return <button type="button" className="mi-btn" onClick={onClick} disabled={disabled} title={title}>{icon}{children}</button>;
}

export function Pill({ children, onClick, to, pressed, disabled, title }: { children: ReactNode; onClick?: () => void; to?: string; pressed?: boolean; disabled?: boolean; title?: string }) {
  if (to && !disabled) return <Link to={to} className="mi-pill" title={title}>{children}</Link>;
  return <button type="button" className="mi-pill" onClick={onClick} aria-pressed={pressed} disabled={disabled} title={title}>{children}</button>;
}

/** API 오류 띠(§4.0 제안): `잠시 후 다시 시도해 주세요` + `다시 시도` */
export function ErrorBand({ message, onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <div className="mi-errband" role="alert">
      <Ic d={P.warn} size={15} />
      <span className="mi-grow">{message || '잠시 후 다시 시도해 주세요'}</span>
      {onRetry && <button type="button" className="mi-mini" onClick={onRetry}>다시 시도</button>}
    </div>
  );
}

export function LoadingCard({ lines = 4 }: { lines?: number }) {
  return (
    <div className="mi-card" aria-busy="true">
      <div className="mi-skel">
        {Array.from({ length: lines }, (_, i) => <Skeleton key={i} w={`${90 - i * 12}%`} h={14} />)}
      </div>
    </div>
  );
}

// ── 결과 탭 · 인용 ───────────────────────────────────────

/** 출처 번호 칩 — 누르면 그 주장을 MI3S 에서 연다 */
export function Cites({ ns, on, onClick, claimId }: { ns: number[]; on?: boolean; onClick?: (claimId: string) => void; claimId?: string }) {
  if (!ns?.length) return null;
  return (
    <>
      {ns.map((n) => (
        <button key={n} type="button" className={cx('mi-cite', on && 'mi-cite--on')} aria-label={`출처 ${n}`}
          onClick={(e) => { e.stopPropagation(); if (claimId && onClick) onClick(claimId); }}>{n}</button>
      ))}
    </>
  );
}

/** 주장 문장 + 출처 번호 — 확인 안 된 수치는 점선 밑줄 + `확인 필요` 툴팁(제안) */
export function ClaimText({ claim, onCite, hl, sel }: { claim: ClaimRef | null | undefined; onCite?: (id: string) => void; hl?: boolean; sel?: string | null }) {
  if (!claim) return <span className="mi-claim mi-cmp__cell--ph">[확인 필요]</span>;
  const unverified = claim.unverified_numbers || (claim.status !== 'matched' && claim.status !== 'confirmed' && /\d/.test(claim.text));
  return (
    <span className={cx('mi-claim', claim.inferred && 'mi-claim--inferred', hl && 'mi-claim--hl')} data-claim={claim.id} data-status={claim.status}>
      <span className={cx(unverified && 'mi-unverified')} title={unverified ? '확인 필요' : undefined}>{claim.text}</span>
      {claim.inferred && <span className="mi-ai" title="사례 DB로 채운 값">추론</span>}
      <Cites ns={claim.ns ?? []} claimId={claim.id} onClick={onCite} on={sel === claim.id} />
    </span>
  );
}

export function ResultTabs({ tabs, value, onChange, badges, revArea, previewMode }:
  { tabs: TabInfo[]; value: Area; onChange: (a: Area) => void; badges?: Partial<Record<Area, number>>; revArea?: Area | null; previewMode?: boolean }) {
  return (
    <div className="mi-tabs" role="tablist" aria-label="분석 영역">
      {tabs.map((t) => {
        const pending = previewMode && t.status !== 'done' && t.status !== 'reused' && t.status !== 'preview';
        const n = badges?.[t.area as Area] ?? 0;
        return (
          <button key={t.area} type="button" role="tab" className="mi-tab" aria-selected={value === t.area} disabled={pending}
            onClick={() => onChange(t.area as Area)} data-area={t.area}>
            {t.label}
            {pending && <span className="mi-tab__pending">정리 중</span>}
            {!!n && <span className="mi-tab__badge" title={`확인 필요 ${n}건`}>{n}</span>}
            {revArea === t.area && <span className="mi-tab__rev">재분석</span>}
          </button>
        );
      })}
    </div>
  );
}

/** 경쟁사 비교표(§4.7) — 열 `요구사항 항목` · 경쟁사(글자 + 실명 보조) · `삼성` */
export function CompareGrid({ table, onCite, renderRowHead, renderCell, extraRows, selected }:
  { table: CompareTable; onCite?: (id: string) => void; renderRowHead?: (row: CompareTable['rows'][number]) => ReactNode;
    renderCell?: (row: CompareTable['rows'][number], col: CompareTable['columns'][number]) => ReactNode | undefined; extraRows?: ReactNode; selected?: string | null }) {
  const cols = `1.3fr ${table.columns.map(() => '1fr').join(' ')}`;
  return (
    <div className="mi-cmp" style={{ gridTemplateColumns: cols }} role="table" aria-label="경쟁사 비교표">
      <div className="mi-cmp__th" role="columnheader">요구사항 항목</div>
      {table.columns.map((c) => (
        <div key={c.key} role="columnheader" className={cx('mi-cmp__th', c.samsung && 'mi-cmp__th--samsung')}>
          {c.label}{c.sub && <small>{c.sub}</small>}
        </div>
      ))}
      {table.rows.map((r) => (
        <RowCells key={r.criterion_id} row={r} table={table} onCite={onCite} renderRowHead={renderRowHead} renderCell={renderCell} selected={selected} />
      ))}
      {extraRows}
    </div>
  );
}

function RowCells({ row, table, onCite, renderRowHead, renderCell, selected }:
  { row: CompareTable['rows'][number]; table: CompareTable; onCite?: (id: string) => void; renderRowHead?: (row: CompareTable['rows'][number]) => ReactNode;
    renderCell?: (row: CompareTable['rows'][number], col: CompareTable['columns'][number]) => ReactNode | undefined; selected?: string | null }) {
  return (
    <>
      {renderRowHead ? renderRowHead(row) : <div role="rowheader">{row.name}</div>}
      {table.columns.map((c) => {
        const custom = renderCell?.(row, c);
        if (custom !== undefined) return custom;
        const cell = row.cells[c.key];
        const text = cell?.text ?? '[확인 필요]';
        return (
          <div key={c.key} role="cell" className={cx(c.samsung ? 'mi-cmp__cell--samsung' : 'mi-cmp__cell', cell?.placeholder && 'mi-cmp__cell--ph')}
            data-verdict={cell?.verdict ?? undefined}>
            <span className={cx(!cell?.placeholder && cell?.status && cell.status !== 'matched' && cell.status !== 'confirmed' && /\d/.test(text) && 'mi-unverified')}>{text}</span>
            {cell && <Cites ns={cell.ns ?? []} claimId={cell.claim_ids?.[0]} onClick={onCite} on={!!selected && cell.claim_ids?.includes(selected)} />}
          </div>
        );
      })}
    </>
  );
}

export function Strengths({ items, onCite }: { items: Strength[]; onCite?: (id: string) => void }) {
  if (!items.length) return null;
  return (
    <div className="mi-block">
      <div className="mi-strengths__title">도출된 삼성 강점 {items.length}</div>
      <div className="mi-strengths">
        {items.map((s) => (
          <div key={s.id} className="mi-strength" data-testid="mi-strength">
            <b>{s.title}</b> — {s.note}
            {s.claims?.[0] && <Cites ns={s.claims.flatMap((c) => c.ns ?? [])} claimId={s.claims[0].id} onClick={onCite} />}
          </div>
        ))}
      </div>
    </div>
  );
}

/** 짧은 시간 동안 값이 바뀐 행을 연파랑으로 강조(MI2A 메모 반영, 제안) */
export function useFlash<T>(value: T, ms = 1600): boolean {
  const [flash, setFlash] = useState(false);
  const first = useRef(true);
  useEffect(() => {
    if (first.current) { first.current = false; return; }
    setFlash(true);
    const t = window.setTimeout(() => setFlash(false), ms);
    return () => window.clearTimeout(t);
  }, [value, ms]);
  return flash;
}
