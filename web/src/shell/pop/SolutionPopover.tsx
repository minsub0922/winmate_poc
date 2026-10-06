/**
 * 솔루션 탐색 팝오버(00-shell §5.4, 보드 HomeSolution) — 600×500.
 * 검색 · 업종 칩 5(단일 선택 필터 [제안]) · 솔루션 11(목록 카드) · 푸터 `선택 {n} · {이름들|없음}`.
 */
import { useEffect, useState, type ReactNode } from 'react';
import { Link } from 'react-router';
import { Button, Chip, Grip, ItemAddButton, PathIcon, Skeleton, useActiveDrag, useDragSource } from '@/ui';
import { ref, useSolutions } from '../kb';
import type { KbSolution } from '../kbTypes';
import { solutionIconPath } from '../icons';
import { useShellRuntime } from '../runtime';
import { detailSearch, useShellUrl } from '../urlState';
import {
  ADD_FAIL_TEXT, AddAllButton, DragHint, NoTaskFooter, PopoverFrame, PopSearch, useAddRunner, useAddState, useDebounced, usePopMemory, usePopoverEscape, type TrayEntry,
} from './common';

export const INDUSTRY_CHIPS: Array<{ id: string; label: string }> = [
  { id: 'retail', label: '리테일' }, { id: 'hospitality', label: '호스피탈리티' }, { id: 'education', label: '교육' },
  { id: 'healthcare', label: '헬스케어' }, { id: 'office', label: '오피스' },
];

interface Mem { industry: string | null; tray: TrayEntry[] }

function SolutionRow({ s, inTray, onToggle, search }: { s: KbSolution; inTray: boolean; onToggle: () => void; search: URLSearchParams }) {
  const rt = useShellRuntime();
  const active = useActiveDrag();
  const stateOf = useAddState('solution');
  const r = ref.solution(s.id);
  const st = stateOf(r, inTray);
  const canDrag = rt.canDrag('solution') && st !== 'added';
  const domain = s.domain || (s.desc ?? '').split(' · ')[0];
  const drag = useDragSource(canDrag ? { type: 'solution', ref: r, label: s.name, sub: `솔루션 · ${domain}` } : null);
  const sel = st === 'sel';
  return (
    <div className={['wm-listcard', 'sh-solrow', sel && 'wm-listcard--sel', canDrag && 'wm-grab', active?.ref === r && 'wm-dragging'].filter(Boolean).join(' ')} {...drag} data-solution={s.id}>
      <span className="sh-gripcol">{canDrag && <Grip />}</span>
      <span className="sh-solicon"><PathIcon d={solutionIconPath(s.id, s.icon)} size={16} color={sel ? 'var(--wm-brand)' : 'var(--wm-text-muted)'} /></span>
      <span style={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1, minWidth: 0 }}>
        <span style={{ fontSize: 13.5, fontWeight: 600 }} data-name="">{s.name}</span>
        <span className="sh-ell" style={{ fontSize: 12, color: 'var(--wm-text-muted)' }} title={s.desc ?? undefined} data-desc="">{s.desc}</span>
      </span>
      <Link className="sh-detailbtn" to={{ search: detailSearch('solution', s.id, 'overview', search) }} replace aria-label={`${s.name} 상세 보기 — 개요 · 이미지 · 활용 사례`}>상세</Link>
      <ItemAddButton state={st} name={s.name} offReason={rt.offReason('solution')} onToggle={onToggle} />
    </div>
  );
}

export function SolutionPopover({ onClose, hidden }: { onClose: () => void; hidden?: boolean }) {
  const rt = useShellRuntime();
  const url = useShellUrl();
  const activeDrag = useActiveDrag();
  const [mem, setMem] = usePopMemory<Mem>('solution', () => ({ industry: null, tray: [] }));
  const [qInput, setQInput] = useState(url.q);
  const q = useDebounced(qInput.trim(), 200);
  const { update } = url;
  useEffect(() => { update({ q: q || null }); }, [q, update]);
  useEffect(() => { rt.remember('solution', { ...mem, q }); }, [mem, q, rt]);
  usePopoverEscape(onClose, !hidden);

  const sols = useSolutions({ q: q || undefined, industry: mem.industry ?? undefined });
  const list = sols.data?.items ?? [];
  const tray = mem.tray;
  const toggleTray = (e: TrayEntry) => setMem({ tray: tray.some((t) => t.ref === e.ref) ? tray.filter((t) => t.ref !== e.ref) : [...tray, e] });
  const runner = useAddRunner('solution', tray, () => setMem({ tray: [] }));

  let body: ReactNode;
  if (sols.isError && !sols.data) {
    body = <div className="sh-state" role="alert"><span>솔루션 목록을 불러오지 못했어요.<br /><Button h={28} onClick={() => sols.refetch()} style={{ marginTop: 8 }}>다시 시도</Button></span></div>;
  } else if (sols.isLoading && !sols.data) {
    body = Array.from({ length: 6 }, (_, i) => <Skeleton key={i} h={56} r={10} />);
  } else if (!list.length) {
    body = <div className="sh-state">{q ? `‘${q}’에 맞는 솔루션이 없어요.` : '이 업종에 맞는 솔루션이 없어요.'}</div>;
  } else {
    body = list.map((s) => <SolutionRow key={s.id} s={s} inTray={tray.some((t) => t.ref === ref.solution(s.id))} search={url.sp}
      onToggle={() => toggleTray({ ref: ref.solution(s.id), label: s.name })} />);
  }

  return (
    <PopoverFrame kind="solution" hidden={hidden} dragging={!!activeDrag && activeDrag.type === 'solution'}>
      <PopSearch label="솔루션 검색" placeholder="솔루션명 · 해결 과제로 검색 (예: 원격 콘텐츠 관리)" value={qInput} onChange={setQInput} onClose={onClose} />
      <div className="sh-pop__bar" role="group" aria-label="업종">
        {INDUSTRY_CHIPS.map((c) => (
          <Chip key={c.id} on={mem.industry === c.id} onClick={() => setMem({ industry: mem.industry === c.id ? null : c.id })}>{c.label}</Chip>
        ))}
        <span style={{ flex: 1 }} />
        {rt.canDrag('solution') && <DragHint />}
      </div>
      <div className="sh-pop__list" style={{ gap: 6 }}>{body}</div>
      {rt.hasTask ? (
        <div className="sh-pop__foot" data-footer="task" style={{ justifyContent: 'space-between' }}>
          <span className={runner.failed ? 'sh-pop__foot-text sh-pop__foot-text--err' : 'sh-pop__foot-text sh-ell'} style={{ flexShrink: 1 }} role={runner.failed ? 'alert' : undefined}>
            {runner.failed ? ADD_FAIL_TEXT : `선택 ${tray.length} · ${tray.map((t) => t.label).join(', ') || '없음'}`}
          </span>
          <AddAllButton n={tray.length} busy={runner.busy} onClick={runner.run} disabledReason={rt.canAdd('solution') ? undefined : rt.offReason('solution', 'footer')} />
        </div>
      ) : <NoTaskFooter text="진행 중인 작업이 없어 탐색만 할 수 있어요." />}
    </PopoverFrame>
  );
}
