/** Spec 화면 공용 부품 — 대화 줄 · 도크 · 입력 · 아이콘 · 스텝바(보드 SP*.dc.html 그대로). 키트(@/ui)에 없는 것만 여기 둔다. */
import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import { useNavigate } from 'react-router';
import { Icon, PathIcon, cx, toast } from '@/ui';
import { useShellPage } from '@/shell/ShellContext';
import type { StepperConfig } from '@/shell/types';
import { addProducts, errText, useSheetCache, type Sheet } from './api';
import './spec.css';

export const STEPS = ['제품 입력', '항목 · 형식', '시트 생성'];
export const SECTION = 'Spec 시트 생성';

export function stepper(current: 1 | 2 | 3, complete = false): StepperConfig {
  return { steps: STEPS, current, complete };
}

/** 화면 틀: 위 대화(스크롤) + 아래 도크 */
export function SpPage({ children, dock, width }: { children: ReactNode; dock?: ReactNode; width?: number }) {
  return (
    <div className="sp-page">
      <div className="sp-scroll">
        <div className="sp-col" style={width ? { width } : undefined}>{children}</div>
      </div>
      {dock}
    </div>
  );
}

/** 에이전트 줄(W 로고 + 글 · 아래 부품) */
export function Agent({ text, children }: { text?: ReactNode; children?: ReactNode }) {
  return (
    <div className="sp-agent">
      <div className="sp-agent__logo" aria-hidden="true">W</div>
      <div className="sp-agent__body">
        {text && <div className="sp-agent__text">{text}</div>}
        {children}
      </div>
    </div>
  );
}

export function UserBubble({ children }: { children: ReactNode }) {
  return <div className="sp-user" data-testid="sp-user">{children}</div>;
}

/** 도크: 제목 줄(`{이름} · {요약} · {단계} / 3`) + 오른쪽 링크/칩 + 몸통 + 입력 줄 */
export function Dock({ title, meta, right, children, row }: { title: ReactNode; meta?: ReactNode; right?: ReactNode; children?: ReactNode; row?: ReactNode }) {
  return (
    <div className="sp-dock-wrap">
      <div className="sp-dock" role="region" aria-label="입력 도크">
        <div className="sp-dock__head">
          <div className="sp-dock__title" data-testid="sp-dock-title">{title}{meta && <small> · {meta}</small>}</div>
          {right && <div className="sp-dock__links">{right}</div>}
        </div>
        {children && <div className="sp-dock__body">{children}</div>}
        {row && <div className="sp-dock__row">{row}</div>}
      </div>
    </div>
  );
}

/** 도크 입력(시각 숨김 라벨 + placeholder + 보내기) — 한글 조합 중 Enter 무시 */
export function PromptInput({ label, placeholder, onSend, busy, sendLabel = '보내기', disabled }:
  { label: string; placeholder: string; onSend: (text: string) => void | Promise<void>; busy?: boolean; sendLabel?: string; disabled?: boolean }) {
  const [v, setV] = useState('');
  const id = useId();
  const ref = useRef<HTMLInputElement>(null);
  const send = async () => {
    const t = v.trim();
    if (!t || busy || disabled) return;
    await onSend(t);
    setV('');
    ref.current?.focus();
  };
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.nativeEvent.isComposing) return;
    if (e.key === 'Enter') { e.preventDefault(); void send(); }
  };
  return (
    <div className="sp-prompt">
      <label htmlFor={id} className="wm-sr-only">{label}</label>
      <input id={id} ref={ref} value={v} placeholder={placeholder} onChange={(e) => setV(e.target.value)} onKeyDown={onKey} disabled={disabled} />
      <button type="button" className={cx('sp-send', v.trim() && !busy && 'sp-send--on')} aria-label={sendLabel} onClick={() => void send()}
        disabled={!v.trim() || busy || disabled}>
        <PathIcon d="M12 19V5M6 11l6-6 6 6" size={15} strokeWidth={2.2} />
      </button>
    </div>
  );
}

export function BigButton({ children, onClick, disabled, title, arrow = true, busy }:
  { children: ReactNode; onClick?: () => void; disabled?: boolean; title?: string; arrow?: boolean; busy?: boolean }) {
  return (
    <button type="button" className="sp-bigbtn" onClick={onClick} disabled={disabled || busy} title={disabled ? title : undefined} aria-busy={busy || undefined}>
      <span>{children}</span>
      {arrow && <PathIcon d="M5 12h14M13 6l6 6-6 6" size={16} strokeWidth={2.2} />}
    </button>
  );
}

/** 켬/끔 칩(aria-pressed) */
export function Chip2({ on, children, onClick, h = 32, disabled, title, check = true }:
  { on: boolean; children: ReactNode; onClick?: () => void; h?: 34 | 32 | 30 | 28; disabled?: boolean; title?: string; check?: boolean }) {
  return (
    <button type="button" className={cx('sp-chip', h === 34 && 'sp-chip--h34', h === 30 && 'sp-chip--h30', h === 28 && 'sp-chip--h28')} aria-pressed={on} onClick={onClick} disabled={disabled} title={title}>
      {on && check && <Icon name="check" size={12} strokeWidth={2.6} />}{children}
    </button>
  );
}

/** 판정 · 조건 아이콘(ok · check · no) */
export function VIcon({ state, size = 14 }: { state: 'ok' | 'check' | 'no' | 'pass' | 'fail' | 'unknown'; size?: number }) {
  const s = state === 'pass' ? 'ok' : state === 'fail' ? 'no' : state === 'unknown' ? 'check' : state;
  const inner = s === 'ok' ? 'M5 12l5 5L20 7' : s === 'no' ? 'M7 7l10 10M17 7L7 17' : 'M12 7v6M12 17v.5';
  return (
    <span className={cx('sp-vicon', `sp-vicon--${s}`)} style={{ width: size, height: size }} aria-hidden="true">
      <PathIcon d={inner} size={size - 5} strokeWidth={3} />
    </span>
  );
}

/** 경고 · 확인 번호 */
export function NumBadge({ n, line }: { n: number; line?: boolean }) {
  return <span className={cx('sp-num', line && 'sp-num--line')}>{n}</span>;
}

/** SP0 상태 아이콘 + 문구 */
const ST_PATH: Record<string, string> = { done: 'M5 12l5 5L20 7', check: 'M12 6v8M12 18.5v.5', warn: 'M12 6v8M12 18.5v.5', draft: 'M7 12h10', run: 'M7 12h10' };
export function StatusIcon({ ui, text }: { ui: string; text: string }) {
  return (
    <span className={cx('sp-st', `sp-st--${ui}`)} data-status={ui}>
      <span className="sp-st__ic"><PathIcon d={ST_PATH[ui] ?? ST_PATH.draft} size={11} strokeWidth={3} /></span>
      {text}
    </span>
  );
}

export const TYPE_ICON: Record<string, string> = {
  compare: 'M4 5h16v14H4z M10 5v14 M15 5v14 M4 10h16',
  single: 'M6 3h8l5 5v13H6V3z M14 3v5h5 M9 13h7 M9 17h7',
  req: 'M6 3h8l5 5v13H6V3z M14 3v5h5 M9 13l2 2 4-4',
  find: 'M4 5h16l-6 7v6l-4 2v-8L4 5z',
};

export function Radio({ checked, onSelect, children, name }: { checked: boolean; onSelect: () => void; children: ReactNode; name?: string }) {
  return (
    <div role="radio" aria-checked={checked} tabIndex={0} className="sp-radio" data-name={name}
      onClick={onSelect} onKeyDown={(e) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); onSelect(); } }}>
      <span className="sp-radio__dot" />
      <span>{children}</span>
    </div>
  );
}

/** 체크 상자 줄(SP4 옵션) */
export function CheckLine({ checked, onChange, children }: { checked: boolean; onChange: (v: boolean) => void; children: ReactNode }) {
  const id = useId();
  return (
    <label className="sp-check-line" htmlFor={id}>
      <input id={id} type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      {children}
    </label>
  );
}

/**
 * 작업 화면 공통 셸 맥락(§4.4) — 제품 탐색 팝오버의 `현재 작업에 추가` 는 이 작업에 제품을 넣는다.
 * 이미 시트를 만든 뒤라면 새 열을 채우도록 SP1(`?mode=add`)로 보낸다.
 */
export function useSpecShell(s: Sheet | undefined, step: 1 | 2 | 3, opts: { complete?: boolean; title?: string } = {}) {
  const cache = useSheetCache();
  const nav = useNavigate();
  useShellPage({
    section: SECTION,
    title: opts.title ?? (s ? (s.title_confirmed ? s.title : '새 작업') : '새 작업'),
    hasTask: true,
    accepts: ['product'],
    addable: ['product'],
    added: (s?.products ?? []).map((p) => p.ref).filter((r) => r.startsWith('kb:')),
    onAdd: async (_type, refs) => {
      if (!s) return { added: [] };
      try {
        const r = await addProducts(s.id, refs, 'explorer');
        cache.put(r.sheet);
        if (r.added.length && s.generated_at) nav(`/spec/${s.id}/products?mode=add`);
        return { added: r.added };
      } catch (e) {
        toast(errText(e));
        return { added: [] };
      }
    },
    stepper: stepper(step, opts.complete),
    taskContext: { products: (s?.products ?? []).filter((p) => p.family_id).map((p) => ({ ref: `kb:family:${p.family_id}`, label: p.series_code ?? p.display_name })) },
  });
}
