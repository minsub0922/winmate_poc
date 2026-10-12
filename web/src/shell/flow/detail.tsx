/**
 * 콘텐츠 상세(보드 webapp1 v63 View · *_View · *_Edit · *_Draft) — 최종본 한 장에서 바로 입력 · 수정 · 저장한다. 단계 팝업은 없다.
 *
 *   <ContentDetail content="dss" saved={!!doc.ver} changes={doc.changes} empty={…} title={doc.title} refCode={doc.code} ver={doc.ver}
 *     savedAt={doc.saved_at} updatedAt={doc.updated_at} facts={['공간 7', '제품 12', '솔루션 3']} sbIds={[doc.sb_id]}
 *     onSave={save} onRevert={revert} nexts={[…]}>
 *     {본문 — 높이를 채우고 패널 안에서만 스크롤}
 *   </ContentDetail>
 *
 * 상태(보드 View status): saved(저장됨 · 고친 곳 없음) · editing(저장됨 · 고친 곳 n — 머리에 「고친 곳 n · 되돌리기 · 저장 · vN+1」)
 *   · new(아직 저장 전 · 비어 있음) · draft(아직 저장 전 · 무언가 씀 — 작성 중으로 자동 저장).
 * 저장된 것을 고치다 다른 화면으로 가면 저장할지 묻는다(useBlocker). 팝업은 기능이 따로 하는 일(고르기 · MI 검색)에만 쓴다.
 * 인라인 편집 공용 클래스(detail.css): cd-in · cd-in--chg · cd-pend · cd-aib · cd-ok · cd-x · cd-add · cd-tag--*.
 */
import { useEffect, useLayoutEffect, useRef, useState, type ChangeEvent, type FocusEvent, type HTMLAttributes, type KeyboardEvent, type MutableRefObject, type ReactNode, type Ref } from 'react';
import { Link, useBlocker } from 'react-router';
import { useShellPage } from '../ShellContext';
import type { ShellPageConfig } from '../types';
import { FlowScreen, Icon, JsonPopup, Modal, PathIcon, cx, josaRo, toast } from '@/ui';
import { CONTENT, useFlow, useFlowInvalidate, type ContentKey } from './api';
import { FlowBar, whenText } from './parts';
import './detail.css';

export type DetailMode = 'saved' | 'editing' | 'new' | 'draft';

export interface NextCard {
  /** 후속 콘텐츠 키(아이콘) */
  key: ContentKey;
  title: string;
  desc: string;
  /** 그 Storyboard 에 이미 있으면 「참조 vN」 · 열기, 없으면 만들기 */
  ref?: string | null;
  to: string;
}

export function detailMode({ saved, changes, empty }: { saved: boolean; changes?: number | null; empty?: boolean }): DetailMode {
  if (saved) return (changes ?? 0) > 0 ? 'editing' : 'saved';
  return empty ? 'new' : 'draft';
}

const PILL: Record<DetailMode, string> = { saved: 'cd-ref--saved', editing: 'cd-ref--editing', new: 'cd-ref--new', draft: 'cd-ref--draft' };

export function ContentDetail<T = unknown>({
  content, saved, changes = 0, empty = false, title, refCode, ver, savedAt, updatedAt, facts, sbIds, onSave, onRevert,
  saveLabel, actions, nexts = [], canSave = true, children, savedToast, shell,
}: {
  content: ContentKey;
  /** 한 번이라도 저장했는가(ver 있음) */
  saved: boolean;
  /** 저장 뒤 고친 곳 수(서버 changes) */
  changes?: number | null;
  /** 저장 전인데 아직 비어 있으면 「새로 만들기」, 무언가 있으면 「작성 중」 */
  empty?: boolean;
  title: string;
  refCode?: string | null;
  ver?: number | null;
  savedAt?: string | null;
  updatedAt?: string | null;
  /** 머리 한 줄의 수(저장됨: 「오늘 10:10 저장 · 공간 7 · 제품 12」, 작성 중: 「작성 중 · 공간 6 · 제품 9 · …」) */
  facts: string[];
  sbIds: string[];
  /** 저장(완료) — 끝나면 상위가 문서를 새로 읽는다 */
  onSave: () => Promise<T>;
  /** 저장한 판으로 되돌리기(고친 곳이 있을 때) */
  onRevert?: () => Promise<unknown>;
  saveLabel?: string;
  /** 머리 오른쪽에 더할 버튼(Spec 시트 XLSX 내려받기 등) */
  actions?: ReactNode;
  nexts?: NextCard[];
  /** false 거나 이유 문구면 저장 버튼을 막는다(예: 제품 없는 공간이 있어요) */
  canSave?: boolean | string;
  /** 저장 뒤 토스트(기본 「저장했어요」) */
  savedToast?: (out: T) => string;
  /** 셸에 더 넘길 값 — 셸 시트 · 팝오버의 「현재 작업에 추가」(hasTask · onAdd · addable · added · taskContext) · 끌어 놓기(accepts). section · title 은 이 틀이 정한다 */
  shell?: Omit<ShellPageConfig, 'section' | 'title'>;
  children: ReactNode;
}) {
  const m = CONTENT[content];
  const mode = detailMode({ saved, changes, empty });
  const sb = sbIds[0] ?? null;
  const nSb = sbIds.length;
  const inval = useFlowInvalidate();
  const [busy, setBusy] = useState<'save' | 'revert' | null>(null);
  const [json, setJson] = useState(false);
  const flow = useFlow(json ? sb : null);
  const refText = refCode ? `${refCode}${ver ? ` v${ver}` : ''}` : m.short;
  useShellPage({ hasTask: false, ...shell, section: m.label, title: saved ? (refCode ?? m.short) : mode === 'new' ? '새로 만들기' : title || m.short });

  const link = content === 'rq' ? '저장하면 이 요구사항으로 Storyboard가 만들어져요' : sb ? `저장하면 ${sb}에 연결돼요` : '저장하면 Storyboard에 연결돼요';
  const meta = mode === 'saved' ? [savedAt ? `${whenText(savedAt)} 저장` : '저장됨', ...facts].join(' · ')
    : mode === 'editing' ? `${refText} 고치는 중 · 저장하면 v${(ver ?? 0) + 1} · ${nSb > 1 ? `연결된 Storyboard ${nSb}개에 모두 반영돼요` : sb ? `${sb}에 반영돼요` : '요약본에 반영돼요'}`
      : mode === 'new' ? `새로 만드는 중 · 쓰는 대로 작성 중으로 남아요 · ${link}`
        : ['작성 중', ...facts, updatedAt ? `${whenText(updatedAt)} 자동 저장` : '', link].filter(Boolean).join(' · ');
  const pill = mode === 'saved' ? refText : mode === 'editing' ? `${refText} · 고치는 중` : mode === 'new' ? '새로 만들기' : '작성 중';
  const label = saveLabel ?? (mode === 'editing' ? `저장 · v${(ver ?? 0) + 1}` : content === 'rq' && !saved ? '저장 · Storyboard 만들기' : '저장');
  const blockReason = typeof canSave === 'string' ? canSave : canSave ? null : '저장할 수 없어요';

  const save = async () => {
    if (busy || blockReason) { if (blockReason) toast(blockReason); return false; }
    setBusy('save');
    try {
      const out = await onSave();
      inval();
      toast(savedToast ? savedToast(out) : '저장했어요');
      return true;
    } catch (e) {
      toast((e as Error)?.message || '저장하지 못했어요');
      return false;
    } finally { setBusy(null); }
  };
  const revert = async () => {
    if (!onRevert || busy) return false;
    setBusy('revert');
    try { await onRevert(); toast(`${refText}${josaRo(refText)} 되돌렸어요`); return true; } catch (e) { toast((e as Error)?.message || '되돌리지 못했어요'); return false; } finally { setBusy(null); }
  };

  // 저장된 것을 고치다 나가면 묻는다(같은 화면 안 주소 바뀜 — 쿼리 · 탭 — 은 묻지 않음)
  const blocker = useBlocker(({ currentLocation, nextLocation }) => mode === 'editing' && currentLocation.pathname !== nextLocation.pathname);
  useEffect(() => {
    if (mode !== 'editing') return;
    const h = (e: BeforeUnloadEvent) => { e.preventDefault(); };
    window.addEventListener('beforeunload', h);
    return () => window.removeEventListener('beforeunload', h);
  }, [mode]);

  const sbNote = mode === 'editing' ? (nSb > 1 ? '저장하면 모두 반영' : '저장하면 반영돼요')
    : !saved && content !== 'rq' ? '저장하면 이 Storyboard에 연결돼요 · 사전 작업에서 골랐어요' : undefined;
  return (
    <FlowScreen className="cd" pad="20px 40px 22px" gap={14}
      bar={<FlowBar sbIds={sbIds} current={content} note={sbNote} emptyText="저장하면 이 요구사항으로 Storyboard가 자동으로 만들어져요" />}>
      <div className="cd-head" data-mode={mode}>
        <span className="cd-ic" aria-hidden><PathIcon d={m.icon} size={21} color="var(--wm-brand)" strokeWidth={2} /></span>
        <span className="cd-titles">
          <span className="cd-titlerow"><h1 className="cd-h1">{title || m.newLabel}</h1><span className={cx('cd-ref', PILL[mode])}>{pill}</span></span>
          <span className="cd-meta">{meta}</span>
        </span>
        {mode === 'saved' && <span className="cd-hint"><Icon name="edit" size={13} strokeWidth={2.2} />눌러서 바로 고쳐요</span>}
        {mode === 'editing' && <>
          <span className="cd-chg" role="status"><i aria-hidden />고친 곳 {changes}</span>
          {onRevert && <button type="button" className="cd-btn" onClick={() => void revert()} disabled={!!busy}>{busy === 'revert' ? '되돌리는 중…' : '되돌리기'}</button>}
        </>}
        {actions}
        {saved && <button type="button" className="cd-btn" onClick={() => setJson(true)} disabled={!sb}><span className="cd-json" aria-hidden>{'{ }'}</span>flow.json</button>}
        {mode !== 'saved' && (
          <button type="button" className="cd-save" onClick={() => void save()} disabled={!!busy} aria-disabled={!!blockReason || undefined} title={blockReason ?? undefined}>
            <Icon name="check" size={15} strokeWidth={2.4} />{busy === 'save' ? '저장하는 중…' : label}
          </button>
        )}
      </div>
      <div className="cd-body">{children}</div>
      {saved && nexts.length > 0 && (
        <div className="cd-next">
          <span className="cd-nexth">후속 작업</span>
          <div className="cd-nextgrid" style={{ gridTemplateColumns: `repeat(${nexts.length}, minmax(0, 1fr))` }}>
            {nexts.map((n) => (
              <Link key={n.key} to={n.to} className="cd-nextcard">
                <span className="cd-nextic" aria-hidden><PathIcon d={CONTENT[n.key].icon} size={18} color="#fff" strokeWidth={2} /></span>
                <span className="cd-nexttxt"><b>{n.title}</b><span>{n.desc}</span></span>
                {n.ref && <span className="cd-nextref">{n.ref}</span>}
                <span className="cd-nextcta">{n.ref ? '열기' : '만들기'}</span>
                <Icon name="arrowRight" size={16} strokeWidth={2.2} color="var(--wm-brand)" />
              </Link>
            ))}
          </div>
        </div>
      )}
      <JsonPopup open={json} onClose={() => setJson(false)} json={flow.data?.flow_json ?? {}} highlightKey={content} title={sb ? `${sb}/flow.json` : 'flow.json'}
        sub={`초록 줄이 이 콘텐츠(stages.${content})예요`} />
      <LeaveDialog open={blocker.state === 'blocked'} changes={changes ?? 0} busy={busy}
        onStay={() => blocker.reset?.()}
        onLeave={() => blocker.proceed?.()}
        onSave={async () => { if (await save()) blocker.proceed?.(); else blocker.reset?.(); }} />
    </FlowScreen>
  );
}

/** 저장된 것을 고치다 나갈 때 — 저장하고 나가기 · 고친 채로 두고 나가기 · 계속 고치기 */
function LeaveDialog({ open, changes, busy, onStay, onLeave, onSave }: { open: boolean; changes: number; busy: string | null; onStay: () => void; onLeave: () => void; onSave: () => void }) {
  return (
    <Modal open={open} onClose={onStay} width={460} ariaLabel="저장하지 않은 고친 곳"
      footer={<div className="cd-leavefoot">
        <button type="button" className="wm-btn wm-btn--h40" onClick={onStay}>계속 고치기</button>
        <button type="button" className="wm-btn wm-btn--h40" onClick={onLeave}>고친 채로 두고 나가기</button>
        <button type="button" className="wm-btn wm-btn--primary wm-btn--h40" onClick={onSave} disabled={!!busy}>{busy === 'save' ? '저장하는 중…' : '저장하고 나가기'}</button>
      </div>}>
      <div className="cd-leave"><b>고친 곳 {changes}개를 아직 저장하지 않았어요</b>
        <span>저장해야 연결된 Storyboard에 반영돼요. 그대로 두고 나가면 다음에 이 화면을 열 때 「고치는 중」으로 이어져요.</span></div>
    </Modal>
  );
}

// ── 인라인 편집 조각 ─────────────────────────────────

/** AI 추가기능 버튼(✦ · 파란 테두리) — 보드 cd-aib */
export function AiButton({ children, onClick, busy, size = 32, disabled }: { children: ReactNode; onClick?: () => void; busy?: boolean; size?: 28 | 32 | 36; disabled?: boolean }) {
  return (
    <button type="button" className={cx('cd-aib', `cd-aib--${size}`)} onClick={onClick} disabled={disabled || busy} aria-busy={busy || undefined}>
      <svg width={12} height={12} viewBox="0 0 24 24" fill="currentColor" aria-hidden><path d="M12 2.5l1.9 5.6 5.6 1.9-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.9z" /></svg>
      {busy ? 'AI가 찾는 중…' : children}
    </button>
  );
}

/** 점선(AI 추천)을 한꺼번에 — 「AI 추천 n개 — 점선은 수락해야 들어가요」 · 모두 지우기 · 모두 수락 */
export function PendingBar({ count, text, onAcceptAll, onClearAll }: { count: number; text?: string; onAcceptAll?: () => void; onClearAll?: () => void }) {
  if (count <= 0) return null;
  return (
    <div className="cd-pendbar" role="status">
      <svg width={13} height={13} viewBox="0 0 24 24" fill="currentColor" aria-hidden><path d="M12 2.5l1.9 5.6 5.6 1.9-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.9z" /></svg>
      <span>{text ?? `AI 추천 ${count}개 — 점선은 수락해야 들어가요 · 하나씩 수락하거나 ×로 지워요`}</span>
      {onClearAll && <button type="button" className="cd-pendbar__clear" onClick={onClearAll}>모두 지우기</button>}
      {onAcceptAll && <button type="button" className="cd-ok cd-ok--28" onClick={onAcceptAll}>모두 수락</button>}
    </div>
  );
}

/** 그 자리에서 고치는 글 칸 — 바뀔 때마다 부르지 않고 칸을 떠날 때(또는 Enter) 한 번 저장한다. Esc 는 고치기 전 값으로 되돌리고 칸을 떠난다(저장 안 함).
 *  `required` 면 비운 채 떠날 때 저장하지 않고 원래 값으로 돌아간다. `multiline` + `autosize` 면 글 높이만큼 자란다(Enter 는 줄바꿈 · Ctrl/⌘+Enter 저장). */
export function InlineInput({ value, onCommit, placeholder, className, changed, label, multiline, autosize, maxLength = 300, disabled, required, id, inputRef, onKeyDown, inputMode, autoFocus }: {
  value: string; onCommit: (v: string) => unknown; placeholder?: string; className?: string; changed?: boolean; label: string; multiline?: boolean; autosize?: boolean; maxLength?: number; disabled?: boolean;
  required?: boolean; id?: string; inputRef?: Ref<HTMLInputElement | HTMLTextAreaElement>; onKeyDown?: (e: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
  inputMode?: HTMLAttributes<HTMLInputElement>['inputMode']; autoFocus?: boolean;
}) {
  const [v, setV] = useState(value);
  const skip = useRef(false);
  const own = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null);
  useEffect(() => { setV(value); }, [value]);
  const fit = () => { const el = own.current; if (multiline && autosize && el) { el.style.height = 'auto'; el.style.height = `${el.scrollHeight + 2}px`; } };
  useLayoutEffect(fit, [v, multiline, autosize]);
  const setRef = (el: HTMLInputElement | HTMLTextAreaElement | null) => {
    own.current = el;
    if (typeof inputRef === 'function') inputRef(el);
    else if (inputRef) (inputRef as MutableRefObject<HTMLInputElement | HTMLTextAreaElement | null>).current = el;
  };
  const commit = (e: FocusEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    if (skip.current) { skip.current = false; return; }
    const t = e.currentTarget.value.trim();
    if (required && !t) { setV(value); return; }
    if (t !== value.trim()) void onCommit(t);
  };
  const keys = (e: KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    onKeyDown?.(e);
    if (e.defaultPrevented || e.nativeEvent.isComposing) return;
    const el = e.currentTarget;
    if (e.key === 'Escape') { e.preventDefault(); skip.current = true; setV(value); el.blur(); return; }
    if (e.key === 'Enter' && (!multiline || e.metaKey || e.ctrlKey)) { e.preventDefault(); el.blur(); }
  };
  const common = { id, className: cx('cd-in', changed && 'cd-in--chg', className), 'aria-label': label, value: v, placeholder, maxLength, disabled, autoFocus,
    onChange: (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setV(e.target.value), onBlur: commit, onKeyDown: keys };
  if (multiline) return <textarea ref={setRef} rows={autosize ? 1 : undefined} {...common} />;
  return <input ref={setRef} inputMode={inputMode} {...common} />;
}
