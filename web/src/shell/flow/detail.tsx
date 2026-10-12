/**
 * 콘텐츠 상세 = 최종본 한 장 + 단계 팝업(보드 webapp1 v62 — View · StepHead · *_Draft · *_Edit · 단계 보드는 모두 View 위 팝업).
 *
 *   콘텐츠 상세에는 페이지 이동이 없다. 늘 최종본(ContentDetail)이고, 단계 화면은 그 위에 뜨는 StepModal 이다.
 *   - 새로 만들기: 빈 최종본(status="new", 칸마다 StepSlot) + 1단계 팝업 → 「다음」은 팝업 안에서 다음 단계로 → 마지막 「저장」에서 팝업이 닫히고 최종본이 채워진다.
 *   - 중간에 닫으면 작성 중(status="draft") — 채운 칸만 보이고 다음 단계 칸에 「이어서」.
 *   - 저장된 콘텐츠: 머리의 단계 칩을 누르면 그 단계 팝업만 열려 고치고(저장하면 버전 +1) 닫힌다.
 *
 *   <ContentDetail content="dss" status="saved" title="…" refVer="DSS-01 v1" meta="…" sbIds={[…]} steps={CONTENT.dss.steps}
 *     done={3} onStep={(k) => open(k)} json="dss" follow={<DetailFollow … />}>…최종본 본문…</ContentDetail>
 *   <StepModal open={step != null} content="dss" title="…" mode="new" sbId="SB-05" note="…" steps={…} current={step} done={1}
 *     onStep={open} onClose={close}><SpacesStep … /></StepModal>
 */
import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router';
import { Button, Icon, JsonPopup, Modal, PathIcon, StepPopupContext, cx, focusablesIn } from '@/ui';
import { CONTENT, useFlow, useFlowsById, type ContentKey } from './api';
import { FlowBar, SBPopup, whenText } from './parts';
import './detail.css';

export type DetailStatus = 'saved' | 'new' | 'draft';

const SB_ICON = 'M4 5h16v14H4z M4 11h16 M10 11v8';
const CHECK = 'M5 12l5 5L20 7';

// ── 단계 칩(최종본 머리) ─────────────────────────────

/** 최종본 머리의 단계 칩(보드 View nav) — 저장됨: 「단계별 고치기」 · Storyboard 는 요약 팝업, 나머지는 그 단계 팝업.
 *  새로 · 작성 중: 「단계 n/N」 · 마친 단계와 다음 단계만 누를 수 있다. */
function StepNav({ steps, done, status, onStep, onSb }: { steps: readonly string[]; done: number; status: DetailStatus; onStep: (k: number) => void; onSb: (() => void) | null }) {
  const saved = status === 'saved';
  const n = steps.length;
  return (
    <nav className="fl-dnav" aria-label="단계">
      <span className="fl-dnav__label">{saved ? '단계별 고치기' : `단계 ${Math.min(n, done + (status === 'new' ? 1 : 0))}/${n}`}</span>
      {steps.map((label, i) => {
        const k = i + 1;
        const isDone = saved || k <= done;
        const next = !saved && k === done + 1;
        const sb = label === 'Storyboard';
        const can = saved || isDone || next;
        // 사전 작업(Storyboard)을 고른 뒤에는 그 칩이 연결된 Storyboard 요약 팝업이다(콘텐츠를 만든 뒤 Storyboard 는 바꾸지 않는다)
        const sbPop = sb && isDone && onSb;
        const tip = sbPop ? '연결된 Storyboard 요약' : saved ? `${label} 단계를 팝업으로 열어 고쳐요` : isDone ? `${label} 단계로 돌아가요` : next ? '이 단계를 팝업으로 열어요' : '앞 단계를 마치면 열려요';
        return (
          <span key={label} className="fl-dnav__item">
            {i > 0 && <Icon name="chevronRight" size={12} color="#b8bec8" strokeWidth={2.4} />}
            <button type="button" className={cx('fl-dstep', next && 'fl-dstep--next', !can && 'fl-dstep--off')} title={tip} disabled={!can}
              aria-label={`${label} · ${tip}`} data-step={k} onClick={() => (sbPop ? onSb() : onStep(k))}>
              <span className={cx('fl-dstep__c', isDone ? 'fl-dstep__c--done' : next ? 'fl-dstep__c--next' : 'fl-dstep__c--todo')}>
                {isDone ? <PathIcon d={CHECK} size={9} color="#fff" strokeWidth={3.4} /> : k}
              </span>
              <span className="fl-dstep__t">{label}</span>
              {saved && !sb && <PathIcon d="M4 20h4L19 9l-4-4L4 16v4z" size={11} color="#8a91a0" strokeWidth={2.4} />}
            </button>
          </span>
        );
      })}
    </nav>
  );
}

// ── 최종본 ───────────────────────────────────────────

export interface ContentDetailProps {
  content: ContentKey;
  status: DetailStatus;
  /** 콘텐츠 이름(보드 View h1) */
  title: string;
  /** 저장됨: `DSS-01 v1` · 새로 · 작성 중이면 비워 둔다(칩은 「새로 만들기」 · 「작성 중 n/N」) */
  refVer?: string | null;
  /** 머리 한 줄(저장 시각 · 수) — 비우면 상태 문구 */
  meta?: ReactNode;
  /** 연결된 Storyboard(첫째가 지금 Storyboard) — 비면 sbEmpty */
  sbIds: string[];
  sbNote?: ReactNode;
  sbEmpty?: string;
  /** 단계 이름(CONTENT[content].steps) */
  steps: readonly string[];
  /** 마친 단계 수(저장됨이면 무시 — 전부) */
  done: number;
  /** 단계 칩 · 자리표시 「이어서」 → 그 단계 팝업 */
  onStep: (k: number) => void;
  /** 머리 오른쪽 추가 버튼(Spec XLSX 내려받기 등 — 저장됨일 때만) */
  actions?: ReactNode;
  /** flow.json 버튼(저장됨 · Storyboard 가 있을 때) — 이 키의 stages 줄을 강조 */
  json?: ContentKey;
  /** 머리 아래 안내 줄(DSS 바뀜 · 저장하지 않은 고침 등) */
  notice?: ReactNode;
  /** 작성 중 머리 줄의 마지막 손댄 시각 */
  updatedAt?: string | null;
  /** 후속 작업 카드(저장됨일 때만 · DetailFollow) */
  follow?: ReactNode;
  children: ReactNode;
}

/** 콘텐츠 상세(보드 View) — 최종본 한 장. 본문은 기능이 그린다(칸이 비면 StepSlot). */
export function ContentDetail({ content, status, title, refVer, meta, sbIds, sbNote, sbEmpty, steps, done, onStep, actions, json, notice, follow, updatedAt, children }: ContentDetailProps) {
  const m = CONTENT[content];
  const saved = status === 'saved';
  const n = steps.length;
  const [sbPop, setSbPop] = useState<string | null>(null);
  const [jsonOpen, setJsonOpen] = useState(false);
  const sbId = sbIds[0] ?? null;
  const flow = useFlow(saved && json && jsonOpen ? sbId : null);
  const chip = saved ? (refVer ?? '') : status === 'new' ? '새로 만들기' : `작성 중 ${done}/${n}`;
  const metaLine = meta ?? (saved ? '' : status === 'new'
    ? `아직 저장 전 · 단계 ${Math.min(n, done + 1)}/${n} 진행 중 · 팝업을 닫아도 작성 중으로 남아요`
    : `작성 중 · ${n}단계 중 ${done}단계 마침${updatedAt ? ` · ${whenText(updatedAt)}` : ''} · 저장하면 ${content === 'rq' ? 'Storyboard가 만들어져요' : sbId ? `${sbId}에 연결돼요` : 'Storyboard에 연결돼요'}`);
  return (
    <div className="wm-flow fl-detail" data-status={status} data-content={content}>
      <FlowBar sbIds={sbIds} current={content} note={sbNote ?? (!saved && sbIds.length ? '저장하면 이 Storyboard에 연결돼요' : undefined)}
        emptyText={sbEmpty ?? (content === 'rq' ? '저장하면 이 요구사항으로 Storyboard가 자동으로 만들어져요' : '① Storyboard 단계에서 골라요')} />
      <section className="fl-dsec">
        <div className="fl-dhead">
          <span className="fl-dhead__ic" aria-hidden><PathIcon d={m.icon} size={21} color="var(--wm-brand)" strokeWidth={2} /></span>
          <span className="fl-dhead__t">
            <span className="fl-dhead__row"><h1>{title}</h1>{chip && <span className={cx('fl-dver', saved ? 'fl-dver--saved' : status === 'new' ? 'fl-dver--new' : 'fl-dver--draft')}>{chip}</span>}</span>
            {metaLine && <span className="fl-dhead__meta">{metaLine}</span>}
          </span>
          {saved && actions}
          <StepNav steps={steps} done={saved ? n : done} status={status} onStep={onStep} onSb={sbId ? () => setSbPop(sbId) : null} />
          {saved && json && sbId && (
            <button type="button" className="fl-dbtn" onClick={() => setJsonOpen(true)}><span className="fl-dbtn__mono">{'{ }'}</span>flow.json</button>
          )}
        </div>
        {notice}
        <div className="fl-dbody">{children}</div>
        {saved && follow && <div className="fl-dfollow"><span className="fl-dfollow__h">후속 작업</span>{follow}</div>}
      </section>
      <SBPopup id={sbPop} onClose={() => setSbPop(null)} />
      {json && <JsonPopup open={jsonOpen} onClose={() => setJsonOpen(false)} json={flow.data?.flow_json ?? {}} highlightKey={json}
        title={sbId ? `${sbId}/flow.json` : 'flow.json'} sub={`초록 줄이 이 콘텐츠(stages.${json})예요`} />}
    </div>
  );
}

/** 아직 비어 있는 칸(보드 View 자리표시) — 그 칸을 채우는 단계 · 다음 단계면 진한 테두리, 작성 중이면 「이어서 · 단계」 */
export function StepSlot({ n, label, what, next, cta, onOpen, big }: {
  n: number; label: string; what: string; next: boolean; cta?: boolean; onOpen?: () => void; big?: boolean;
}) {
  return (
    <div className={cx('fl-slot', next && 'fl-slot--next', big && 'fl-slot--big')} data-slot={n}>
      <span className="fl-slot__c">{n}</span>
      <span className="fl-slot__t"><b>{label} 단계</b><span>{what}{next ? ' — 이 단계를 마치면 여기에 채워져요' : ' — 앞 단계를 마치면 열려요'}</span></span>
      {next && cta && onOpen && <button type="button" className="fl-slot__cta" onClick={onOpen}>이어서 · {label}<Icon name="arrowRight" size={14} strokeWidth={2.2} /></button>}
    </div>
  );
}

/** 후속 작업 카드(보드 View: min-h 76 r14 · 아이콘 38 · 15/700 · 설명 12.5 · 이미 있으면 ref 칩 + 「열기」, 없으면 「만들기」) */
export function DetailFollow({ items }: { items: { to: string; icon: string; title: string; desc: string; ref?: string | null }[] }) {
  return (
    <div className="fl-dfollow__grid" style={{ gridTemplateColumns: `repeat(${Math.max(1, items.length)}, minmax(0, 1fr))` }}>
      {items.map((it) => (
        <Link key={it.title} className="fl-dnext" to={it.to}>
          <span className="fl-dnext__ic" aria-hidden><PathIcon d={it.icon} size={18} color="#fff" strokeWidth={2} /></span>
          <span className="fl-dnext__t"><b>{it.title}</b><span>{it.desc}</span></span>
          {it.ref && <span className="fl-dnext__ref">{it.ref}</span>}
          <span className="fl-dnext__cta">{it.ref ? '열기' : '만들기'}</span>
          <Icon name="arrowRight" size={16} color="var(--wm-brand)" strokeWidth={2.2} />
        </Link>
      ))}
    </div>
  );
}

// ── 단계 팝업 ────────────────────────────────────────

export interface StepModalProps {
  open: boolean;
  content: ContentKey;
  /** 팝업 머리 이름 */
  title: string;
  /** new: 「새로 만들기」 · 지난 단계로만 돌아간다 / edit: 「DSS-01 v1 고치기」 · Storyboard 밖 모든 단계로 옮겨 다닌다 */
  mode: 'new' | 'edit';
  /** edit 일 때 `DSS-01 v1` */
  ver?: string | null;
  /** 머리의 연결 Storyboard 칩(누르면 요약 팝업) */
  sbId?: string | null;
  note?: ReactNode;
  steps: readonly string[];
  /** 지금 단계(1부터) */
  current: number;
  /** 마친 단계 수(new) — edit 이면 전부 */
  done: number;
  onStep: (k: number) => void;
  onClose: () => void;
  children: ReactNode;
}

/**
 * 단계 팝업(보드 단계 보드 공통: 최종본 위 딤 · 1180×800 r18 · 머리 StepHead 72 · 본문 728).
 * 본문 안의 FlowScreen 은 Storyboard 바를 그리지 않고, useShellPage 는 팝업 맥락(작업 추가)만 얹는다(StepPopupContext).
 * 딤을 눌러도 닫히지 않는다(여러 단계 입력을 잃지 않게) — × · Esc(위에 다른 팝업이 없을 때)로 닫는다.
 */
export function StepModal({ open, content, title, mode, ver, sbId, note, steps, current, done, onStep, onClose, children }: StepModalProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [sbPop, setSbPop] = useState<string | null>(null);
  const sbq = useFlowsById(open && sbId ? [sbId] : []);
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    if (!open) return;
    const root = ref.current;
    const opener = document.activeElement as HTMLElement | null;
    const t = window.setTimeout(() => { if (root && !root.contains(document.activeElement)) (focusablesIn(root)[0] ?? root).focus({ preventScroll: true }); }, 0);
    // 이 팝업이 맨 위 대화상자일 때만(제품 고르기 · 확인창 등이 위에 있으면 그쪽이 처리)
    const top = () => { const all = Array.from(document.querySelectorAll('[role="dialog"][aria-modal="true"]')); return all[all.length - 1] === ref.current; };
    const onKey = (e: KeyboardEvent) => {
      const r = ref.current;
      if (!r || !top()) return;
      // 상단바 팝오버 · 상세 시트가 열려 있으면 그쪽이 Esc 를 받는다(이 팝업은 그대로)
      if (e.key === 'Escape' && !e.defaultPrevented && !e.isComposing && !document.querySelector('.sh-sheet, [data-popover]:not([aria-hidden="true"])')) { close.current(); return; }
      if (e.key !== 'Tab') return;
      const list = focusablesIn(r);
      if (!list.length) return;
      const cur = document.activeElement as HTMLElement | null;
      if (!cur || !r.contains(cur)) { e.preventDefault(); list[0].focus(); return; }
      if (e.shiftKey && cur === list[0]) { e.preventDefault(); list[list.length - 1].focus(); }
      else if (!e.shiftKey && cur === list[list.length - 1]) { e.preventDefault(); list[0].focus(); }
    };
    document.addEventListener('keydown', onKey, true);
    return () => {
      window.clearTimeout(t);
      document.removeEventListener('keydown', onKey, true);
      if (opener?.isConnected) window.setTimeout(() => opener.focus({ preventScroll: true }), 0);
    };
  }, [open]);
  if (!open) return null;
  const m = CONTENT[content];
  const edit = mode === 'edit';
  const n = steps.length;
  const fin = edit ? n : done;
  const sbName = sbId ? sbq[0]?.data?.name ?? sbId : null;
  return (
    <div className="wm-scrim fl-stepscrim">
      <div ref={ref} className="fl-stepdlg" role="dialog" aria-modal="true" tabIndex={-1} aria-label={`${title} · ${steps[current - 1] ?? ''}`} data-step={current}>
        <div className="fl-shead">
          <span className="fl-shead__ic" aria-hidden><PathIcon d={m.icon} size={18} color="var(--wm-brand)" strokeWidth={2} /></span>
          <span className="fl-shead__t">
            <span className="fl-shead__row"><b>{title}</b><span className={cx('fl-shead__mode', edit && 'fl-shead__mode--edit')}>{edit ? `${ver ?? m.short} 고치기` : '새로 만들기'}</span></span>
            <span className="fl-shead__row fl-shead__sub">
              {sbId && <button type="button" className="fl-shead__sb" onClick={() => setSbPop(sbId)} aria-label={`${sbName} 요약 보기`}><PathIcon d={SB_ICON} size={11} color="currentColor" strokeWidth={2.2} />{sbName}</button>}
              {note && <span className="fl-shead__note">{note}</span>}
            </span>
          </span>
          <span className="fl-shead__pos">단계 {current}/{n}</span>
          <nav className="fl-shead__steps" aria-label="단계">
            {steps.map((label, i) => {
              const k = i + 1;
              const active = k === current;
              const isDone = !active && k <= fin;
              // 사전 작업(Storyboard)은 콘텐츠를 만든 뒤 바꾸지 않는다 — 머리의 Storyboard 칩으로 요약만 본다
              const fixed = label === 'Storyboard';
              const can = !active && isDone && !fixed;
              return (
                <span key={label} className="fl-shead__item">
                  {i > 0 && <span className={cx('fl-shead__line', (k <= current || (edit && k <= n)) && 'fl-shead__line--on')} />}
                  <button type="button" className={cx('fl-sstep', active ? 'fl-sstep--on' : isDone ? 'fl-sstep--done' : 'fl-sstep--todo')} disabled={!can} aria-current={active ? 'step' : undefined}
                    title={active ? '지금 단계' : fixed ? '사전 작업은 여기서 바꾸지 않아요' : can ? '이 단계로 옮겨요' : '앞 단계를 마치면 열려요'} onClick={() => can && onStep(k)}>
                    <span className="fl-sstep__c">{isDone ? <PathIcon d={CHECK} size={10} color="#fff" strokeWidth={3.2} /> : k}</span>
                    <span className="fl-sstep__t">{label}</span>
                  </button>
                </span>
              );
            })}
          </nav>
          <button type="button" className="fl-shead__x" onClick={onClose} aria-label="팝업 닫기" title={edit ? '닫기 — 저장하지 않은 고침이 있으면 물어요' : '닫아도 작성 중으로 남아요'}>
            <Icon name="x" size={17} strokeWidth={2.2} />
          </button>
        </div>
        <div className="fl-sbody">
          <StepPopupContext.Provider value>{children}</StepPopupContext.Provider>
        </div>
      </div>
      <SBPopup id={sbPop} onClose={() => setSbPop(null)} />
    </div>
  );
}

// ── 주소의 단계(?step=) ──────────────────────────────

/**
 * 팝업 단계를 주소 `?step=<키>` 에 둔다(새로 고침 · 뒤로 가기에도 같은 팝업). keys[i] = i+1 단계의 키(예: ['sb', 'space', 'solution']).
 * 단계를 바꿔도 같은 주소(쿼리만 바뀜)라 최종본은 그대로이고 팝업 안만 바뀐다.
 */
export function useStepParam(keys: readonly string[]) {
  const [sp, setSp] = useSearchParams();
  const v = sp.get('step');
  const i = v ? keys.indexOf(v) : -1;
  const step = i >= 0 ? i + 1 : null;
  const set = (k: number | null, replace = true) => setSp((prev) => {
    const p = new URLSearchParams(prev);
    if (k && keys[k - 1]) p.set('step', keys[k - 1]); else p.delete('step');
    return p;
  }, { replace });
  return { step, open: (k: number) => set(k), close: () => set(null), raw: v };
}

// ── 고치기 팝업을 닫을 때 ────────────────────────────

/**
 * 저장된 콘텐츠의 고치기 팝업 — 열 때의 문서 판(version)을 기억해, 닫을 때 바뀌었으면 true(저장할지 묻는다).
 * 고침은 문서에 바로 들어가지만 Storyboard(허브)에는 「저장 · vN」 때 반영된다.
 */
export function useEditGuard(open: boolean, version: number | null | undefined) {
  const v0 = useRef<number | null>(null);
  useEffect(() => {
    if (open && version != null && v0.current == null) v0.current = version;
    if (!open) v0.current = null;
  }, [open, version]);
  return () => v0.current != null && version != null && version !== v0.current;
}

/** 고친 내용이 있을 때 닫기 물음 — 「계속 고치기」 · 「저장하지 않고 닫기」 · 「저장 · vN」 */
export function useCloseAsk() {
  const [st, setSt] = useState<{ title: string; message: ReactNode; saveLabel: string; resolve: (v: 'save' | 'leave' | 'stay') => void } | null>(null);
  const ask = useCallback((o: { title: string; message: ReactNode; saveLabel: string }) =>
    new Promise<'save' | 'leave' | 'stay'>((resolve) => setSt({ ...o, resolve })), []);
  const done = (v: 'save' | 'leave' | 'stay') => { st?.resolve(v); setSt(null); };
  const dialog = st ? (
    <Modal open onClose={() => done('stay')} variant="dialog" width={460} ariaLabel={st.title} bodyStyle={{ padding: '20px 22px 8px' }}
      footer={<>
        <Button h={38} onClick={() => done('stay')}>계속 고치기</Button>
        <Button h={38} onClick={() => done('leave')}>저장하지 않고 닫기</Button>
        <Button h={38} variant="primary" onClick={() => done('save')}>{st.saveLabel}</Button>
      </>}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <strong style={{ fontSize: 15 }}>{st.title}</strong>
        <div style={{ fontSize: 12.5, color: 'var(--wm-text-muted)', lineHeight: 1.5 }}>{st.message}</div>
      </div>
    </Modal>
  ) : null;
  return { ask, dialog };
}
