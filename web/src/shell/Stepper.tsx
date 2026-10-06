/**
 * 스텝바(00-shell §5.11, 보드 Stepper) — 단계(done · active · todo · auto) + 딸깍 버튼/팝오버.
 * 셸은 버튼·팝오버 UI 와 이벤트(onRun)만 낸다. 실행은 proposal(잡 생성 → SSE).
 */
import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { BoltIcon, CheckChip, Icon } from '@/ui';
import type { StepperConfig } from './types';

type StepState = 'done' | 'active' | 'todo' | 'auto';

const CIRCLE: Record<StepState, CSSProperties> = {
  auto: { background: 'var(--wm-dark)', color: '#fff' },
  done: { background: 'var(--wm-brand)', color: '#fff' },
  active: { border: '2px solid var(--wm-brand)', background: '#fff', color: 'var(--wm-brand)' },
  todo: { border: '2px solid var(--wm-line-step)', background: '#fff', color: 'var(--wm-text-subtle)' },
};

export function Stepper({ config }: { config: StepperConfig }) {
  const { steps, current, complete = false, autoFrom = 0, auto = [], onStep, oneClick, right } = config;
  const n = steps.length;
  const showBtn = !!oneClick && !complete && current <= n && !(autoFrom > 0);
  const [openState, setOpen] = useState(!!config.oneClickOpen);
  useEffect(() => { if (config.oneClickOpen) setOpen(true); }, [config.oneClickOpen]);
  const open = showBtn && openState;
  const [markInferred, setMarkInferred] = useState(true);
  const [collectReview, setCollectReview] = useState(true);
  const wrap = useRef<HTMLDivElement>(null);
  const split = showBtn || !!right;

  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => { if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false); };
    const k = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', h);
    window.addEventListener('keydown', k);
    return () => { document.removeEventListener('mousedown', h); window.removeEventListener('keydown', k); };
  }, [open]);

  const gap = n > 5 ? 8 : 12;
  const lineW = n > 5 ? 28 : n > 3 ? 40 : 56;
  const rows = config.planRows?.length ? config.planRows
    : steps.slice(Math.max(0, current - 1)).map((label, i) => ({ label, note: i === 0 ? '입력한 내용까지 반영하고 나머지 추론' : '추론해 자동 완성' }));
  const confirmed = config.planConfirmed ?? steps.slice(0, Math.max(0, current - 1));
  const summary = config.planSummary || `남은 ${rows.length}단계`;

  return (
    <div className={split ? 'sh-stepper sh-stepper--split' : 'sh-stepper'} ref={wrap}>
      <ol className="sh-steps" aria-label="단계">
        {steps.map((text, i) => {
          const k = i + 1;
          const done = complete || k < current;
          const isActive = !complete && k === current;
          const isAuto = done && ((autoFrom > 0 && k >= autoFrom) || auto.includes(k));
          const st: StepState = isAuto ? 'auto' : done ? 'done' : isActive ? 'active' : 'todo';
          const label = (
            <>
              <span className="sh-step__circle" style={CIRCLE[st]} data-state={st}>
                {st === 'auto' ? <BoltIcon size={11} color="#fff" /> : st === 'done' ? <Icon name="check" size={11} color="#fff" strokeWidth={3} /> : k}
              </span>
              <span style={{ fontSize: n > 5 ? 12.5 : 13, whiteSpace: 'nowrap', color: isActive ? 'var(--wm-text)' : done ? 'var(--wm-text-muted)' : 'var(--wm-text-subtle)', fontWeight: isActive ? 600 : 400 }}>{text}</span>
            </>
          );
          return (
            <li key={`${i}-${text}`} style={{ display: 'flex', alignItems: 'center' }} aria-current={isActive ? 'step' : undefined} data-step={k}>
              {onStep
                ? <button type="button" className="sh-step" onClick={() => onStep(k)}>{label}</button>
                : <span className="sh-step">{label}</span>}
              {i < n - 1 && <span className="sh-step__line" aria-hidden="true" style={{ width: lineW, margin: `0 ${gap}px`, background: complete || k < current ? 'var(--wm-brand)' : 'var(--wm-line-step)' }} />}
            </li>
          );
        })}
      </ol>
      {(showBtn || right) && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {right}
          {showBtn && oneClick && (
            <button type="button" className={open ? 'sh-oneclick sh-oneclick--open' : 'sh-oneclick'} aria-expanded={open} aria-haspopup="dialog"
              title="남은 단계를 AI가 추론해 최종 제안서를 바로 만듭니다" disabled={oneClick.disabled} onClick={() => setOpen(!open)}>
              <BoltIcon size={14} />
              <span style={{ fontSize: 13.5, fontWeight: 800, letterSpacing: '-0.01em' }}>{oneClick.label ?? '딸깍'}</span>
              <span style={{ width: 1, height: 14, background: 'var(--wm-dark-divider)' }} />
              <span style={{ fontSize: 12, color: 'var(--wm-dark-text-2)', fontWeight: 500 }}>{oneClick.running ? '실행 중' : '나머지 자동 완성'}</span>
            </button>
          )}
        </div>
      )}
      {open && oneClick && (
        <div className="sh-ocpop" role="dialog" aria-label="딸깍 — 나머지 자동 완성">
          <div style={{ padding: '16px 18px 12px 18px', display: 'flex', gap: 12, borderBottom: '1px solid var(--wm-line)' }}>
            <span style={{ width: 36, height: 36, borderRadius: 10, background: 'var(--wm-dark)', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><BoltIcon size={18} /></span>
            <span style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <span style={{ fontSize: 15, fontWeight: 700 }}>딸깍으로 나머지를 완성할까요?</span>
              <span style={{ fontSize: 12.5, color: 'var(--wm-text-muted)', lineHeight: 1.5 }}>지금까지 확정한 내용은 그대로 두고, 남은 단계는 AI가 추론해 채운 뒤 최종 PPTX까지 만듭니다.</span>
            </span>
          </div>
          {confirmed.length > 0 && (
            <div style={{ padding: '12px 18px 0 18px', display: 'flex', flexDirection: 'column', gap: 6 }} data-confirmed="">
              <span style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--wm-text-muted)' }}>확정된 내용 · 그대로 사용</span>
              <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>{confirmed.map((c) => <CheckChip key={c}>{c}</CheckChip>)}</div>
            </div>
          )}
          <div style={{ padding: '12px 18px 0 18px', display: 'flex', flexDirection: 'column', gap: 4 }} data-plan="">
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11.5, fontWeight: 600, color: 'var(--wm-text-muted)' }}>
              <span>딸깍이 추론해 채울 부분</span><span data-summary="">{summary}</span>
            </div>
            {rows.map((r) => (
              <div key={r.label} className="sh-ocrow" data-plan-row={r.label}>
                <BoltIcon size={11} color="var(--wm-brand)" />
                <span style={{ fontWeight: 600, flexShrink: 0, whiteSpace: 'nowrap' }}>{r.label}</span>
                <span className="sh-ell" style={{ flex: 1, textAlign: 'right', color: 'var(--wm-text-muted)', fontSize: 12 }}>{r.note}</span>
              </div>
            ))}
          </div>
          <div style={{ padding: '12px 18px 0 18px', display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12.5 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <input type="checkbox" checked={markInferred} onChange={(e) => setMarkInferred(e.target.checked)} style={{ accentColor: 'var(--wm-brand)', margin: 0 }} />
              추론한 시트에 '추론' 표시와 근거 노트 남기기
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <input type="checkbox" checked={collectReview} onChange={(e) => setCollectReview(e.target.checked)} style={{ accentColor: 'var(--wm-brand)', margin: 0 }} />
              완료 후 검토가 필요한 곳 모아 보기
            </label>
          </div>
          <div style={{ padding: '14px 18px 16px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
            <span style={{ fontSize: 12, color: 'var(--wm-text-muted)' }}>약 1–2분 · 진행 중에도 다른 작업 가능</span>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="button" className="wm-btn wm-btn--h38" onClick={() => setOpen(false)}>취소</button>
              <button type="button" className="wm-btn wm-btn--h38 wm-btn--dark" style={{ gap: 6 }}
                onClick={() => { setOpen(false); oneClick.onRun({ markInferred, collectReview }); }}>
                <BoltIcon size={13} />딸깍, 완성하기
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
