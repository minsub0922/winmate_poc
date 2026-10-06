/**
 * 에이전트 판단 모드 칩 · 출처 카드 · 근거 패널 — 보드 MI2A · MIR · MI3S(03-mi §4.4 · §4.11), VPR 범례. 경쟁사 · VP · 제안서(PR7Q 수치 찾기)도 같은 모양.
 *
 *   <ModeChip mode="check" />                       // `확인 권장`
 *   <EvidencePanel title="출처 · 근거" sub="시장조사 탭 · 선택한 주장의 출처 2건" onClose={close}
 *     filters={{ items: [{ key: 'all', label: '전체', count: 2 }, …], value, onChange }}
 *     selected={{ text: '국내 F&B 매장…', meta: '출처 2건 · 원문 일치 1 · 확인 필요 1' }}>
 *     <SourceCard n={1} kind="공개 자료 · 시장 보고서" status="ok" title="…" meta="…" quote={{ before: '… ', highlight: '[00]% 증가', after: ' …' }}
 *       actions={[{ label: '원문 열기', icon: 'external', onClick }]} />
 *   </EvidencePanel>
 */
import type { ReactNode } from 'react';
import { CloseButton, cx } from './controls';
import { Icon, PathIcon, type IconName } from './icons';

export type JudgementMode = 'auto' | 'check' | 'ask' | 'pin';
/** 보드 원문(MIR · VPR 범례): 자동 · 확인 권장 · 선택 필요 · 고정 */
export const MODE_LABELS: Record<JudgementMode, string> = { auto: '자동', check: '확인 권장', ask: '선택 필요', pin: '고정' };
const MODE_FILL: Record<JudgementMode, string> = {
  auto: 'M13 2L4 14h7l-1 8 9-12h-7l1-8z',
  check: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm-1 5h2v7h-2zm0 9h2v2h-2z',
  ask: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm-1 14h2v2h-2zm1-10a4 4 0 0 1 4 4c0 2-3 2.5-3 4h-2c0-2.5 3-3 3-4a2 2 0 0 0-4 0H8a4 4 0 0 1 4-4z',
  pin: 'M9 2h6l-1 6 3 3v2h-4v7l-1 2-1-2v-7H7v-2l3-3z',
};

/** 판단 모드 칩(h22 r999 11/700, 채운 아이콘 10): auto 번개 · check 느낌표 원 · ask 물음표 원(검정) · pin 핀. `dim` = 흐림(.45) */
export function ModeChip({ mode, dim, children, title }: { mode: JudgementMode; dim?: boolean; children?: ReactNode; title?: string }) {
  return (
    <span className={cx('wm-mode', `wm-mode--${mode}`, dim && 'wm-mode--dim')} data-mode={mode} title={title}>
      <svg width={10} height={10} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" style={{ flexShrink: 0 }}><path d={MODE_FILL[mode]} fillRule="evenodd" /></svg>
      {children ?? MODE_LABELS[mode]}
    </span>
  );
}

export interface SourceCardAction {
  label: string;
  onClick?: () => void;
  href?: string;
  icon?: IconName;
  /** ghost = 테두리 없는 회색(`이 출처 빼기`) · primary = 파랑 채움 */
  tone?: 'default' | 'ghost' | 'primary';
  disabled?: boolean;
  title?: string;
}

const KIND_ICON = {
  web: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M3 12h18 M12 3a14 14 0 0 1 0 18 M12 3a14 14 0 0 0 0 18',
  doc: 'M6 3h8l5 5v13H6V3z M14 3v5h5 M9 13h7 M9 17h5',
};

export interface SourceCardProps {
  /** 각주 번호(없으면 `·`) */
  n?: number | string | null;
  /** 종류 라벨(`공개 자료 · 시장 보고서` · `사내 사례 DB`) */
  kind: ReactNode;
  /** 종류 아이콘: web(지구) · doc(문서) */
  kindIcon?: 'web' | 'doc';
  /** ok = `원문 일치`(brand) · warn = `확인 필요`(회색 알약, 카드 테두리 검정) */
  status: 'ok' | 'warn';
  /** 상태 배지 글(기본 `원문 일치` · `확인 필요`) */
  statusLabel?: string;
  title: ReactNode;
  /** 발행 · 쪽 · 확인일 줄 */
  meta?: ReactNode;
  /** 인용문 — highlight 부분이 `<mark>`. 문자열이면 그대로 “… {quote} …” */
  quote?: { before?: string; highlight?: string; after?: string } | string | null;
  /** 모델이 요약한 인용(기울임 · 흐림) */
  quoteFromModel?: boolean;
  /** 확인 필요 사유(정보 아이콘 줄) */
  reason?: ReactNode;
  /** 경고 한 줄(`--wm-warn` 11px) */
  flag?: ReactNode;
  actions?: SourceCardAction[];
  selected?: boolean;
  className?: string;
  'data-testid'?: string;
}

/** 출처 카드(MI3S): 번호 · 종류 · 상태 배지 · 제목 · 메타 · 인용(하이라이트) · 사유 · 동작 버튼 줄 */
export function SourceCard({ n, kind, kindIcon = 'web', status, statusLabel, title, meta, quote, quoteFromModel, reason, flag, actions = [], selected, className, ...rest }: SourceCardProps) {
  const ok = status === 'ok';
  const q = quote == null ? null
    : typeof quote === 'string' ? <>“… {quote} …”</>
      : <>“… {quote.before}{quote.highlight ? <mark>{quote.highlight}</mark> : null}{quote.after} …”</>;
  return (
    <div className={cx('wm-scard', !ok && 'wm-scard--warn', selected && 'wm-scard--sel', className)} data-status={status} data-testid={rest['data-testid']}>
      <div className="wm-scard__top">
        <span className="wm-scard__n">{n ?? '·'}</span>
        <span className="wm-scard__kind"><PathIcon d={KIND_ICON[kindIcon]} size={12} strokeWidth={2} />{kind}</span>
        {ok
          ? <span className="wm-scard__ok"><PathIcon d="M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M8 12l3 3 5-6" size={13} strokeWidth={2.4} />{statusLabel ?? '원문 일치'}</span>
          : <span className="wm-scard__warn"><PathIcon d="M12 4l9 16H3z M12 10v4 M12 17v.5" size={13} strokeWidth={2.4} />{statusLabel ?? '확인 필요'}</span>}
      </div>
      <div className="wm-scard__title" title={typeof title === 'string' ? title : undefined}>{title}</div>
      {meta && <div className="wm-scard__meta">{meta}</div>}
      {q && <div className={cx('wm-quote', !ok && 'wm-quote--weak', quoteFromModel && 'wm-quote--model')}>{q}</div>}
      {reason && <div className="wm-scard__reason"><PathIcon d="M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M12 8v5 M12 16v.5" size={14} strokeWidth={2.2} /><span>{reason}</span></div>}
      {flag && <div style={{ fontSize: 11, color: 'var(--wm-warn)' }}>{flag}</div>}
      {actions.length > 0 && (
        <div className="wm-scard__acts">
          {actions.map((a) => {
            const cls = cx('wm-mini', a.tone === 'ghost' && 'wm-mini--ghost', a.tone === 'primary' && 'wm-mini--primary');
            const inner = <>{a.icon && <Icon name={a.icon} size={12} strokeWidth={2.2} />}{a.label}</>;
            return a.href && !a.disabled
              ? <a key={a.label} className={cls} href={a.href} target={/^https?:/.test(a.href) ? '_blank' : undefined} rel={/^https?:/.test(a.href) ? 'noopener noreferrer' : undefined} title={a.title}>{inner}</a>
              : <button key={a.label} type="button" className={cls} onClick={a.onClick} disabled={a.disabled} title={a.title}>{inner}</button>;
          })}
        </div>
      )}
    </div>
  );
}

export interface EvidenceFilter { key: string; label: string; count?: number | string }

/**
 * 오른쪽 근거 패널(MI3S, 폭 420 · 높이 100%): 머리(문서 아이콘 · 제목 · 보조 줄 · 닫기) · 종류 필터 탭 · 선택한 주장 상자 · 본문(카드 목록) · 아래 줄.
 * 화면 오른쪽에 붙여 두는 패널이다(겹창 아님) — 겹창으로 열려면 `Modal variant="side"`.
 */
export function EvidencePanel({ title = '출처 · 근거', sub, filters, selected, onClose, closeLabel = '패널 닫기', footer, children, width = 420, ariaLabel, className }: {
  title?: ReactNode; sub?: ReactNode;
  filters?: { items: EvidenceFilter[]; value: string | null; onChange: (key: string) => void; label?: string };
  /** 선택한 주장 상자: 라벨(기본 `선택한 주장`) · 글 · 아래 줄 */
  selected?: { label?: string; text: ReactNode; meta?: ReactNode } | null;
  onClose?: () => void; closeLabel?: string; footer?: ReactNode; children?: ReactNode; width?: number; ariaLabel?: string; className?: string;
}) {
  return (
    <aside className={cx('wm-epanel', className)} role="complementary" aria-label={ariaLabel ?? (typeof title === 'string' ? title : '출처 · 근거')} style={width !== 420 ? { width } : undefined}>
      <div className="wm-epanel__head">
        <span style={{ color: 'var(--wm-brand)', display: 'inline-flex' }}><PathIcon d={KIND_ICON.doc} size={18} strokeWidth={2} /></span>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 1, flex: 1, minWidth: 0 }}>
          <div className="wm-epanel__title">{title}</div>
          {sub && <div className="wm-epanel__sub">{sub}</div>}
        </div>
        {onClose && <CloseButton label={closeLabel} onClick={onClose} />}
      </div>
      <div className="wm-epanel__body">
        {filters && (
          <div className="wm-efilters" role="tablist" aria-label={filters.label ?? '출처 종류'}>
            {filters.items.map((f) => (
              <button key={f.key} type="button" role="tab" className="wm-efilter" aria-selected={filters.value === f.key} onClick={() => filters.onChange(f.key)}>
                {f.label}{f.count !== undefined && <b>{f.count}</b>}
              </button>
            ))}
          </div>
        )}
        {selected && (
          <div className="wm-eclaim" data-testid="evidence-selected">
            <span className="wm-eclaim__label">{selected.label ?? '선택한 주장'}</span>
            <span className="wm-eclaim__text">{selected.text}</span>
            {selected.meta && <span className="wm-eclaim__meta">{selected.meta}</span>}
          </div>
        )}
        {children}
      </div>
      {footer && <div className="wm-epanel__foot">{footer}</div>}
    </aside>
  );
}
