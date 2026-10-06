/**
 * 유관 사례 검색 팝오버(00-shell §5.6, 보드 HomeCase) — 780×730.
 * 필터 칩 4(업종 · 제품 · 지역 · 기간+건수) · `유사도 순` · 사례 카드(사진 3 · 태그 · 요약 · 제품 칩 · URL · 원문 열기) · 푸터.
 */
import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import { useQueries } from '@tanstack/react-query';
import { Button, CaseCard, Chip, ItemAddButton, Skeleton, displayUrl, formatDate, useActiveDrag, useDragSource } from '@/ui';
import { imageAlt, imageSrc, kb, parseRef, ref, useCaseSearchPages, useCategories, useKbMeta, useSolutions, useVerticals } from '../kb';
import type { KbCaseCard } from '../kbTypes';
import { useShellRuntime } from '../runtime';
import { useShellUrl } from '../urlState';
import {
  ADD_FAIL_TEXT, AddAllButton, DragHint, NoTaskFooter, PopoverFrame, PopSearch, useAddRunner, useAddState, useDebounced, usePopMemory, usePopoverEscape, type TrayEntry,
} from './common';

type Period = 'all' | '1y' | '3y' | '5y';
const PERIODS: Array<{ v: Period; label: string }> = [{ v: 'all', label: '전체 기간' }, { v: '1y', label: '최근 1년' }, { v: '3y', label: '최근 3년' }, { v: '5y', label: '최근 5년' }];
interface VerticalSel { mode: 'auto' | 'all' | 'pick'; id?: string; name?: string }
interface Mem { vertical: VerticalSel; target: { value: string; label: string } | null; period: Period; tray: TrayEntry[] }

interface MenuItem { key: string; label: string; checked: boolean; indent?: boolean; onSelect: () => void }

/** 칩 + 아래로 열리는 메뉴 */
function FilterMenu({ label, on, items, onOpen, testId }: { label: ReactNode; on?: boolean; items: MenuItem[]; onOpen?: () => void; testId: string }) {
  const [open, setOpen] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => { if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [open]);
  const onKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape' && open) { e.preventDefault(); e.stopPropagation(); setOpen(false); }
  };
  return (
    <div ref={wrap} style={{ position: 'relative' }} onKeyDown={onKey} data-filter={testId}>
      <Chip tight on={on} caret aria-haspopup="menu" aria-expanded={open} onClick={() => { if (!open) onOpen?.(); setOpen(!open); }}>{label}</Chip>
      {open && (
        <div className="wm-menu" role="menu" style={{ top: 'calc(100% + 4px)', left: 0 }}>
          {items.map((it) => (
            <button key={it.key} type="button" role="menuitemradio" aria-checked={it.checked} className={it.indent ? 'wm-menu__item wm-menu__item--indent' : 'wm-menu__item'}
              onClick={() => { it.onSelect(); setOpen(false); }}>{it.label}</button>
          ))}
        </div>
      )}
    </div>
  );
}

function CaseItem({ c, inTray, onToggle }: { c: KbCaseCard; inTray: boolean; onToggle: () => void }) {
  const rt = useShellRuntime();
  const active = useActiveDrag();
  const stateOf = useAddState('case');
  const r = ref.case(c.id);
  const st = stateOf(r, inTray);
  const canDrag = rt.canDrag('case') && st !== 'added';
  const year = c.date ? c.date.slice(0, 4) : '';
  const drag = useDragSource(canDrag ? { type: 'case', ref: r, label: c.title, sub: ['유관 사례', c.vertical?.name, year].filter(Boolean).join(' · ') } : null);
  const photos = (c.photos?.items ?? []).slice(0, 3).map((p) => ({ src: imageSrc(p), alt: imageAlt(p, c.title), focal: p.focal }));
  return (
    <CaseCard title={c.title} date={formatDate(c.date)} url={c.url} urlDisplay={c.url_display || displayUrl(c.url)}
      tag={c.vertical ? `${c.vertical.name}${c.tag_detail ? ` · ${c.tag_detail}` : ''}` : c.tag_detail}
      summary={c.summary} quote={c.quote} products={(c.products ?? []).map((p) => p.label).slice(0, 3)} matchTerms={c.match?.terms ?? []} photos={photos}
      photoCount={c.photos?.count ?? photos.length} selected={st === 'sel'} grip={canDrag} dragging={active?.ref === r} dragProps={drag}
      action={<ItemAddButton state={st} name={c.title} offReason={rt.offReason('case')} onToggle={onToggle} />} />
  );
}

export function CasePopover({ onClose, hidden }: { onClose: () => void; hidden?: boolean }) {
  const rt = useShellRuntime();
  const url = useShellUrl();
  const activeDrag = useActiveDrag();
  const [mem, setMem] = usePopMemory<Mem>('case', () => ({ vertical: { mode: 'auto' }, target: null, period: 'all', tray: [] }));
  const [qInput, setQInput] = useState(url.q);
  const q = useDebounced(qInput.trim(), 300);
  const { update } = url;
  useEffect(() => { update({ q: q || null }); }, [q, update]);
  useEffect(() => { rt.remember('case', { ...mem, q }); }, [mem, q, rt]);
  usePopoverEscape(onClose, !hidden);

  const tc = rt.page.taskContext;
  const vParams = mem.vertical.mode === 'pick' ? { vertical_id: mem.vertical.id }
    : mem.vertical.mode === 'all' ? { infer_vertical: false }
      : tc?.verticalId ? { vertical_id: tc.verticalId, vertical_from: 'task' as const } : { infer_vertical: true };
  const enabled = !!q || mem.vertical.mode === 'pick' || !!mem.target || (mem.vertical.mode === 'auto' && !!tc?.verticalId);
  const search = useCaseSearchPages({ q: q || undefined, ...vParams, target: mem.target?.value, period: mem.period === 'all' ? undefined : mem.period }, enabled);
  const first = search.data?.pages[0];
  const meta = useKbMeta();

  // 메뉴 데이터
  const [wantMenus, setWantMenus] = useState(false);
  const verticals = useVerticals(wantMenus);
  const sols = useSolutions({});
  const top = useCategories(null, wantMenus);
  const l2 = useQueries({
    queries: (wantMenus ? top.data?.items ?? [] : []).map((t) => ({
      queryKey: ['kb', 'categories', t.id], queryFn: ({ signal }: { signal: AbortSignal }) => kb.categories(t.id, signal), staleTime: 300_000,
    })),
  });

  const applied = first?.applied?.vertical ?? null;
  const vLabel = applied?.name ?? (mem.vertical.mode === 'pick' ? mem.vertical.name : mem.vertical.mode === 'auto' && tc?.verticalName ? tc.verticalName : '전체');
  const vOn = !!applied || mem.vertical.mode === 'pick';
  const vItems: MenuItem[] = useMemo(() => {
    const list = verticals.data?.items ?? [];
    const parents = list.filter((v) => !v.parent_id);
    const out: MenuItem[] = [{ key: 'all', label: '전체', checked: !vOn, onSelect: () => setMem({ vertical: { mode: 'all' } }) }];
    for (const p of parents) {
      out.push({ key: p.id, label: p.name, checked: (applied?.id ?? mem.vertical.id) === p.id, onSelect: () => setMem({ vertical: { mode: 'pick', id: p.id, name: p.name } }) });
      for (const ch of list.filter((v) => v.parent_id === p.id)) {
        out.push({ key: ch.id, label: ch.name, indent: true, checked: (applied?.id ?? mem.vertical.id) === ch.id, onSelect: () => setMem({ vertical: { mode: 'pick', id: ch.id, name: ch.name } }) });
      }
    }
    return out;
  }, [verticals.data, vOn, applied, mem.vertical.id, setMem]);

  const toTarget = (r: string): string | null => {
    const p = parseRef(r);
    if (p.kind === 'family' || p.kind === 'category' || p.kind === 'model') return `${p.kind}:${p.id}`;
    if (p.kind === 'solution') {
      if (p.id.startsWith('sol_')) return `solution:${p.id}`;
      const kbId = sols.data?.items.find((s) => s.id === p.id)?.kb_id;
      return kbId ? `solution:${kbId}` : null;
    }
    return null;
  };
  const pItems: MenuItem[] = [{ key: 'all', label: '전체', checked: !mem.target, onSelect: () => setMem({ target: null }) }];
  for (const t of tc?.products ?? []) {
    const v = toTarget(t.ref);
    if (v) pItems.push({ key: v, label: t.label, checked: mem.target?.value === v, onSelect: () => setMem({ target: { value: v, label: t.label } }) });
  }
  l2.forEach((res) => (res.data?.items ?? []).forEach((c) => {
    const v = `category:${c.id}`;
    pItems.push({ key: v, label: c.name, checked: mem.target?.value === v, onSelect: () => setMem({ target: { value: v, label: c.name } }) });
  }));

  const corpusN = first?.corpus?.count ?? (mem.period === 'all' ? meta.data?.counts?.case_pages : undefined);
  const periodLabel = PERIODS.find((p) => p.v === mem.period)?.label ?? '전체 기간';

  const tray = mem.tray;
  const toggleTray = (e: TrayEntry) => setMem({ tray: tray.some((t) => t.ref === e.ref) ? tray.filter((t) => t.ref !== e.ref) : [...tray, e] });
  const runner = useAddRunner('case', tray, () => setMem({ tray: [] }));
  const items = (search.data?.pages ?? []).flatMap((pg) => pg.items);

  let body: ReactNode;
  if (!enabled) body = <div className="sh-state">고객 · 업종 · 용도로 검색해 보세요.</div>;
  else if (search.isError && !search.data) {
    body = <div className="sh-state" role="alert"><span>도입사례를 불러오지 못했어요.<br /><Button h={28} onClick={() => search.refetch()} style={{ marginTop: 8 }}>다시 시도</Button></span></div>;
  } else if (search.isLoading && !search.data) body = [0, 1, 2].map((i) => <Skeleton key={i} h={150} r={10} />);
  else if (!items.length) body = <div className="sh-state">조건에 맞는 도입사례가 없어요. 필터를 줄여 보세요.</div>;
  else {
    body = (
      <>
        {items.map((c) => <CaseItem key={c.id} c={c} inTray={tray.some((t) => t.ref === ref.case(c.id))} onToggle={() => toggleTray({ ref: ref.case(c.id), label: c.title })} />)}
        {search.hasNextPage && (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '4px 0 8px', flexShrink: 0 }}>
            <Button h={32} loading={search.isFetchingNextPage} onClick={() => search.fetchNextPage()} data-more="">
              사례 더 보기 · {items.length} / {first?.total ?? '…'}
            </Button>
          </div>
        )}
      </>
    );
  }

  return (
    <PopoverFrame kind="case" hidden={hidden} dragging={!!activeDrag && activeDrag.type === 'case'}>
      <PopSearch label="사례 검색" placeholder="고객 · 업종 · 용도로 검색" value={qInput} onChange={setQInput} onClose={onClose} />
      <div className="sh-pop__bar" style={{ fontSize: 12, zIndex: 3 }} role="group" aria-label="사례 필터">
        <FilterMenu testId="vertical" label={`업종: ${vLabel}`} on={vOn} items={vItems} onOpen={() => setWantMenus(true)} />
        <FilterMenu testId="product" label={`제품: ${mem.target?.label ?? '전체'}`} on={!!mem.target} items={pItems} onOpen={() => setWantMenus(true)} />
        <FilterMenu testId="region" label="지역: 전체" items={[{ key: 'all', label: '전체', checked: true, onSelect: () => undefined }]} />
        <FilterMenu testId="period" label={`${periodLabel} · 삼성 도입사례 ${corpusN ?? '…'}건`} on={mem.period !== 'all'}
          items={PERIODS.map((p) => ({ key: p.v, label: p.label, checked: mem.period === p.v, onSelect: () => setMem({ period: p.v }) }))} />
        <span style={{ flex: 1 }} />
        {rt.canDrag('case') ? <DragHint /> : <span style={{ color: 'var(--wm-text-muted)', whiteSpace: 'nowrap' }}>유사도 순</span>}
      </div>
      <div className="sh-pop__list" style={{ gap: 8 }} aria-label="사례 결과">{body}</div>
      {rt.hasTask ? (
        <div className="sh-pop__foot" data-footer="task" style={{ justifyContent: 'space-between' }}>
          <span className={runner.failed ? 'sh-pop__foot-text sh-pop__foot-text--err' : 'sh-pop__foot-text'} role={runner.failed ? 'alert' : undefined}>
            {runner.failed ? ADD_FAIL_TEXT : `선택 ${tray.length}`}
          </span>
          <AddAllButton n={tray.length} busy={runner.busy} onClick={runner.run} disabledReason={rt.canAdd('case') ? undefined : rt.offReason('case', 'footer')} />
        </div>
      ) : <NoTaskFooter text="진행 중인 작업이 없어 탐색만 할 수 있어요. 원문 열기는 계속 가능합니다." />}
    </PopoverFrame>
  );
}
