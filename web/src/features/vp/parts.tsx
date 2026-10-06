/**
 * VP 화면 공용 부품 — 판단 모드 칩 · 레이아웃 코드 칩 · 출처 태그 · 에이전트 말 · 말풍선 · 아래 도크 · 썸네일 · 셸 맥락.
 */
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Link, useNavigate } from 'react-router';
import { useShellPage } from '@/shell/ShellContext';
import { Icon, PathIcon, Thumb, cx } from '@/ui';
import { useJob, type JobSnapshot } from '@/api/jobs';
import type { Mode, VPDoc } from './api';

export const STEPS = ['재료', '가치 구조', '결과'];
export const SECTION = 'Value Proposition';

const BOLT = 'M13 2L4 14h7l-1 8 9-12h-7l1-8z';
const INFO = 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm-1 5h2v7h-2zm0 9h2v2h-2z';
const QMARK = 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm.1 15.2a1.2 1.2 0 1 1 0-2.4 1.2 1.2 0 0 1 0 2.4zm1.6-5.9c-.8.5-.9.8-.9 1.4v.4h-1.9v-.5c0-1.2.4-1.9 1.4-2.5.8-.5 1.1-.8 1.1-1.4 0-.6-.5-1.1-1.3-1.1-.9 0-1.4.5-1.5 1.3H8.7c.1-1.9 1.4-3 3.4-3 1.9 0 3.2 1.1 3.2 2.7 0 1.1-.5 1.8-1.6 2.7z';
const PIN = 'M16 3l5 5-4 1-4 4 1 5-2 2-4-6-6 6-1-1 6-6-6-4 2-2 5 1 4-4z';
export const MODE_LABEL: Record<Mode, string> = { auto: '자동', check: '확인 권장', ask: '선택 필요', pin: '고정' };

/** 판단 모드 칩(§3.3) — 자동(번개) · 확인 권장(!) · 선택 필요(?) · 고정(핀). */
export function ModeChip({ mode, small }: { mode?: string | null; small?: boolean }) {
  const m = (mode || 'auto') as Mode;
  const d = m === 'auto' ? BOLT : m === 'check' ? INFO : m === 'ask' ? QMARK : PIN;
  return (
    <span className={cx('vp-mode', `vp-mode--${m}`, small && 'vp-mode--sm')} data-mode={m}>
      <svg width={small ? 10 : 11} height={small ? 10 : 11} viewBox="0 0 24 24" aria-hidden="true"><path d={d} fill="currentColor" /></svg>
      {MODE_LABEL[m] ?? m}
    </span>
  );
}

/** 레이아웃 칩(VP0 · VPC) — 코드 · `{코드} 고정` · 업종판(파랑) · 코드 아닌 말(점선). */
export function CodeChip({ t, kind }: { t: string; kind?: string }) {
  return <span className={cx('vp-code', `vp-code--${kind || 'code'}`)}>{t}</span>;
}

const SRC_NAME: Record<string, string> = { SB: 'Storyboard', MI: 'MI', RFP: 'RFP', CS: '유관 사례', RQ: '고객 요구사항', QT: '견적', USER: '메모', KB: 'KB', VP: '이전 가치 제안' };
export const srcName = (t: string) => SRC_NAME[t] ?? t;

/** 출처 태그 SB · MI · RFP · CS … */
export function SrcTag({ tag, title }: { tag: string; title?: string }) {
  return <span className={cx('vp-src', `vp-src--${tag}`)} title={title ?? srcName(tag)}>{tag}</span>;
}

/** 에이전트 말(W 로고 + 글 + 아래 카드) */
export function Agent({ text, children }: { text?: ReactNode; children?: ReactNode }) {
  return (
    <div className="vp-agent">
      <span className="vp-agent__logo" aria-hidden="true">W</span>
      <div className="vp-agent__body">
        {text && <div className="vp-agent__text">{text}</div>}
        {children}
      </div>
    </div>
  );
}

/** 사용자 말풍선(오른쪽) `{굵게} · {나머지}` */
export function UserBubble({ head, rest }: { head: ReactNode; rest?: ReactNode }) {
  return (
    <div className="vp-user">
      <div className="vp-user__bubble"><b>{head}</b>{rest && <span>· {rest}</span>}</div>
    </div>
  );
}

/** 카드 머리 */
export function CardHead({ title, meta, right, plain, children }: { title: ReactNode; meta?: ReactNode; right?: ReactNode; plain?: boolean; children?: ReactNode }) {
  return (
    <div className={cx('vp-card__head', plain && 'vp-card__head--plain')}>
      <span className="vp-card__title">{title}{meta !== undefined && meta !== null && meta !== '' && <small> · {meta}</small>}</span>
      {children}
      <span className="vp-grow" />
      {right}
    </div>
  );
}

/** 화면 틀: 본문(가운데 800) + 아래 도크 */
export function Page({ children, dock }: { children: ReactNode; dock?: ReactNode }) {
  return (
    <div className="vp-page">
      <div className="vp-body"><div className="vp-col">{children}</div></div>
      {dock && <div className="vp-dockwrap">{dock}</div>}
    </div>
  );
}

/** 아래 도크 — 머리(제목 · 메타 · 오른쪽) + 입력 줄(입력 · 버튼) */
export function Dock({ title, meta, headRight, children, input, actions }: {
  title: ReactNode; meta?: ReactNode; headRight?: ReactNode; children?: ReactNode;
  input?: { placeholder: string; label: string; onSend: (text: string) => Promise<void> | void; busy?: boolean; disabled?: boolean };
  actions?: ReactNode;
}) {
  return (
    <div className="vp-dock" role="region" aria-label={typeof title === 'string' ? title : '입력'}>
      <div className="vp-dock__head">
        <div className="vp-dock__title">{title}{meta !== undefined && meta !== null && meta !== '' && <small> · {meta}</small>}</div>
        {headRight}
      </div>
      {children}
      {(input || actions) && (
        <div className="vp-dock__row">
          {input ? <AskInput {...input} /> : <span className="vp-grow" />}
          {actions}
        </div>
      )}
    </div>
  );
}

export function AskInput({ placeholder, label, onSend, busy, disabled }: { placeholder: string; label: string; onSend: (text: string) => Promise<void> | void; busy?: boolean; disabled?: boolean }) {
  const [v, setV] = useState('');
  const send = async () => {
    const t = v.trim();
    if (!t || busy || disabled) return;
    await onSend(t);
    setV('');
  };
  return (
    <div className="vp-ask">
      <label className="wm-sr-only" htmlFor="vp-ask">{label}</label>
      <input id="vp-ask" value={v} placeholder={placeholder} disabled={disabled} onChange={(e) => setV(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) { e.preventDefault(); void send(); } }} />
      <button type="button" className="vp-ask__send" aria-label="보내기" onClick={() => void send()} disabled={busy || disabled || !v.trim()}>
        {busy ? <span className="vp-spin" /> : <Icon name="send" size={15} />}
      </button>
    </div>
  );
}

export function BtnLink({ to, children, primary, title, onClick }: { to: string; children: ReactNode; primary?: boolean; title?: string; onClick?: () => void }) {
  return (
    <Link to={to} className={cx('vp-btn', primary && 'vp-btn--primary')} title={title} onClick={onClick}>
      {children}{primary && <Icon name="arrowRight" size={15} />}
    </Link>
  );
}

export function Btn({ children, primary, onClick, disabled, reason, busy, title }: { children: ReactNode; primary?: boolean; onClick?: () => void; disabled?: boolean; reason?: string; busy?: boolean; title?: string }) {
  return (
    <button type="button" className={cx('vp-btn', primary && 'vp-btn--primary')} onClick={onClick} disabled={disabled || busy} title={disabled ? reason : title}>
      {busy && <span className="vp-spin" />}
      {children}{primary && !busy && <Icon name="arrowRight" size={15} />}
    </button>
  );
}

/** 템플릿 썸네일(코드가 있으면 export 썸네일 먼저) */
export function VThumb({ code, kind, n, dim, title }: { code?: string; kind?: string; n?: number; dim?: boolean; title?: string }) {
  return <Thumb code={code} kind={kind || 'table'} n={n || 3} dim={dim} title={title} />;
}

/** 화면마다 셸 맥락(브레드크럼 · 스텝바) */
export function useVpShell(doc: VPDoc | undefined, step: number, opts: { complete?: boolean; title?: string } = {}) {
  useShellPage({
    section: SECTION,
    title: opts.title ?? doc?.title ?? '새 작업',
    hasTask: true,
    taskContext: doc?.industry?.kr_vertical_id ? { verticalId: doc.industry.kr_vertical_id, verticalName: doc.industry.name } : undefined,
    stepper: { steps: STEPS, current: step, complete: opts.complete },
  });
}

/** 잡 진행 구독 + 끝나면 콜백(한 번) */
export function useJobDone(jobId: string | null | undefined, onDone: (job: JobSnapshot) => void) {
  const done = useRef<string | null>(null);
  const cb = useRef(onDone);
  cb.current = onDone;
  const j = useJob(jobId, {
    onDone: (job) => {
      if (done.current === job.id) return;
      done.current = job.id;
      cb.current(job);
    },
  });
  return j;
}

/** `/vp/:id` → 작업의 resume_route 로 */
export function useGo() {
  const nav = useNavigate();
  return (to: string, replace = false) => nav(to, { replace });
}

/** 입력 멈춤 뒤 저장(600ms) */
export function useDebounced<T>(value: T, ms: number, fn: (v: T) => void) {
  const first = useRef(true);
  const cb = useRef(fn);
  cb.current = fn;
  useEffect(() => {
    if (first.current) { first.current = false; return; }
    const t = setTimeout(() => cb.current(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
}

/** 작은 아이콘(보드 path) */
export function PIcon({ d, size = 16 }: { d: string; size?: number }) {
  return <PathIcon d={d} size={size} />;
}

export const ICONS = {
  edit: 'M4 20h4L19 9l-4-4L4 16v4z',
  sb: 'M4 5h16v14H4z M4 11h16 M10 11v8',
  mi: 'M4 20V10 M10 20V4 M16 20v-8 M22 20H2',
  clone: 'M8 8h11v13H8z M5 16V3h11',
  folder: 'M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z M9 14h6',
  rq: 'M6 3h8l5 5v13H6V3z M14 3v5h5 M9 13h7 M9 17h7',
  pptx: 'M3 4h18v12H3z M8 20h8 M12 16v4',
  pdf: 'M6 3h8l5 5v13H6V3z M14 3v5h5 M9 13h7 M9 17h7',
  copy: 'M8 8h11v13H8z M5 16V3h11',
  link: 'M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1 M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1',
  scene: 'M4 6h16v12H4z M10 9l5 3-5 3V9z',
  spark: 'M12 3l2.2 5.6L20 10l-5.8 1.4L12 17l-2.2-5.6L4 10l5.8-1.4z',
  clip: 'M21 12l-8.5 8.5a5 5 0 0 1-7-7L14 5a3.5 3.5 0 0 1 5 5l-8.5 8.5a2 2 0 0 1-3-3L16 7',
  monitor: 'M3 4h18v12H3z M8 20h8 M12 16v4',
  diamond: 'M6 4h12l3 5-9 11L3 9l3-5z M3 9h18',
};

export const SOURCE_ICON: Record<string, string> = { storyboard: ICONS.sb, mi: ICONS.mi, requirements: ICONS.rq, case: ICONS.folder, vp: ICONS.clone };

export function Spinner({ label }: { label?: string }) {
  return <span className="vp-busy"><span className="vp-spin" />{label}</span>;
}
