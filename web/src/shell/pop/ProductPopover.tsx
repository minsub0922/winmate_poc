/**
 * 제품 탐색 팝오버(00-shell §5.3, 보드 HomeProduct · SP1Product) — 700×540.
 * 검색 줄 · 경로 줄 · 트리(L1 › L2 › 시리즈) · 모델 표(열은 API columns) · 푸터(선택 트레이).
 */
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { Link } from 'react-router';
import { Button, FolderIcon, Grip, Img, ItemAddButton, Skeleton, TrayChip, useActiveDrag, useDragSource, type DragPayload } from '@/ui';
import { imageSrc, modelName, parseRef, ref, seriesFrontAlt, useCategories, useFamilies, useModels } from '../kb';
import type { KbCategory, KbColumn, KbFamily, KbModelRow } from '../kbTypes';
import { useShellRuntime } from '../runtime';
import { detailSearch, useShellUrl } from '../urlState';
import {
  ADD_FAIL_TEXT, AddAllButton, DragHint, NoTaskFooter, PopoverFrame, PopSearch, useAddRunner, useAddState, useDebounced, usePopMemory, usePopoverEscape, type TrayEntry,
} from './common';
import { familyLabel, nodeKind, registerCategories, registerFamilies, useAncestry } from './productTree';

const DEFAULT_COLUMNS: KbColumn[] = [{ key: 'size', label: '크기' }, { key: 'brightness', label: '밝기' }, { key: 'resolution', label: '해상도' }];
const NO_TASK_TEXT = '진행 중인 작업이 없어 탐색만 할 수 있어요. 작업을 시작하면 제품을 추가할 수 있습니다.';

interface Mem { expanded: string[]; collapsed: string[]; tray: TrayEntry[] }

function gridFor(n: number) {
  const vals = n === 3 ? '0.5fr 0.7fr 0.8fr' : `repeat(${n}, minmax(0, 0.7fr))`;
  return `10px 56px 1.1fr ${vals} 44px 76px`;
}

function TreeRow({ id, label, depth, active, open, onSelect, onToggle }:
  { id: string; label: string; depth: number; active: boolean; open: boolean; onSelect: () => void; onToggle: () => void }) {
  const leaf = nodeKind(id) === 'fam';
  return (
    <button type="button" className={active ? 'sh-tree__row sh-tree__row--active' : 'sh-tree__row'} style={{ paddingLeft: 6 + depth * 14 }}
      onClick={onSelect} aria-current={active || undefined} aria-expanded={leaf ? undefined : open} data-node={id} title={label}>
      <span className="sh-tree__chev" onClick={(e) => { e.stopPropagation(); if (!leaf) onToggle(); else onSelect(); }} aria-hidden="true">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke={active ? 'var(--wm-brand)' : 'var(--wm-text-subtle)'} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d={open && !leaf ? 'M6 9l6 6 6-6' : 'M9 6l6 6-6 6'} />
        </svg>
      </span>
      <FolderIcon open={open || active} />
      <span className="sh-tree__label">{label}</span>
    </button>
  );
}

function SkeletonRows({ n, depth }: { n: number; depth: number }) {
  return <>{Array.from({ length: n }, (_, i) => <Skeleton key={i} h={28} r={6} style={{ marginLeft: depth * 14, width: `calc(100% - ${depth * 14}px)` }} />)}</>;
}

function FamilyChildren({ catId, depth, ctx }: { catId: string; depth: number; ctx: TreeCtx }) {
  const fams = useFamilies(catId);
  useEffect(() => { registerFamilies(fams.data?.items, catId); }, [fams.data, catId]);
  if (fams.isLoading) return <SkeletonRows n={3} depth={depth} />;
  return <>{(fams.data?.items ?? []).map((f: KbFamily) => (
    <TreeRow key={f.id} id={f.id} label={familyLabel(f)} depth={depth} active={ctx.active === f.id} open={false} onSelect={() => ctx.select(f.id)} onToggle={() => undefined} />
  ))}</>;
}

function CategoryChildren({ parentId, depth, ctx }: { parentId: string; depth: number; ctx: TreeCtx }) {
  const cats = useCategories(parentId);
  useEffect(() => { registerCategories(cats.data?.items, parentId); }, [cats.data, parentId]);
  if (cats.isLoading) return <SkeletonRows n={2} depth={depth} />;
  return <>{(cats.data?.items ?? []).map((c: KbCategory) => <CategoryNode key={c.id} c={c} depth={depth} ctx={ctx} />)}</>;
}

interface TreeCtx { active: string | null; isOpen: (id: string) => boolean; select: (id: string) => void; toggle: (id: string) => void }

function CategoryNode({ c, depth, ctx }: { c: KbCategory; depth: number; ctx: TreeCtx }) {
  const open = ctx.isOpen(c.id);
  return (
    <>
      <TreeRow id={c.id} label={c.name} depth={depth} active={ctx.active === c.id} open={open} onSelect={() => ctx.select(c.id)} onToggle={() => ctx.toggle(c.id)} />
      {open && (depth === 0 ? <CategoryChildren parentId={c.id} depth={depth + 1} ctx={ctx} /> : <FamilyChildren catId={c.id} depth={depth + 1} ctx={ctx} />)}
    </>
  );
}

function ModelRow({ row, columns, grid, showSeries, repName, tray, toggleTray, search }:
  { row: KbModelRow; columns: KbColumn[]; grid: string; showSeries: boolean; repName: string; tray: TrayEntry[]; toggleTray: (e: TrayEntry) => void; search: URLSearchParams }) {
  const rt = useShellRuntime();
  const active = useActiveDrag();
  const stateOf = useAddState('product');
  const r = ref.model(row.id);
  const name = modelName(row);
  const inTray = tray.some((t) => t.ref === r);
  const st = stateOf(r, inTray);
  const canDrag = rt.canDrag('product') && st !== 'added';
  const size = row.values?.size?.display;
  const payload: DragPayload | null = canDrag ? { type: 'product', ref: r, label: name, sub: `제품 · ${row.family.name}${size && size !== '—' ? ` ${size}` : ''}` } : null;
  const drag = useDragSource(payload);
  const dragging = active?.ref === r;
  const cls = ['sh-mrow', st === 'sel' && 'sh-mrow--sel', canDrag && 'wm-grab', dragging && 'wm-dragging'].filter(Boolean).join(' ');
  return (
    <div className={cls} style={{ gridTemplateColumns: grid }} {...drag} data-model={row.model_code} role="row">
      <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{canDrag && <Grip />}</span>
      <span className="sh-mthumb"><Img src={imageSrc(row.thumb)} alt={seriesFrontAlt(row.family, repName)} fit="contain" /></span>
      <span className="sh-mname" role="cell">
        <span>{name}</span>
        {showSeries && <small className="sh-ell">{familyLabel(row.family)}</small>}
      </span>
      {columns.map((c) => <span key={c.key} className="sh-mval" role="cell" data-col={c.key}>{row.values?.[c.key]?.display ?? '—'}</span>)}
      <Link className="sh-detailbtn" to={{ search: detailSearch('product', row.model_code, 'spec', search) }} replace
        aria-label={`${name} 상세 보기 — 스펙 · 이미지 · 활용 사례`}>상세</Link>
      <ItemAddButton state={st} name={name} offReason={rt.offReason('product')} onToggle={() => toggleTray({ ref: r, label: name })} />
    </div>
  );
}

export function ProductPopover({ onClose, hidden }: { onClose: () => void; hidden?: boolean }) {
  const rt = useShellRuntime();
  const url = useShellUrl();
  const activeDrag = useActiveDrag();
  const [mem, setMem] = usePopMemory<Mem>('product', () => ({ expanded: [], collapsed: [], tray: [] }));
  const [qInput, setQInput] = useState(url.q);
  const q = useDebounced(qInput.trim(), 200);
  usePopoverEscape(onClose, !hidden);

  // 검색어 → URL(q) · 기억
  const { update } = url;
  useEffect(() => { update({ q: q || null }); }, [q, update]);

  const top = useCategories(null);
  useEffect(() => { registerCategories(top.data?.items, null); }, [top.data]);
  const taskFamily = (rt.page.added ?? []).map(parseRef).find((p) => p.kind === 'family')?.id;
  const activeNode = url.node ?? taskFamily ?? top.data?.items?.[0]?.id ?? null;
  const chain = useAncestry(activeNode);
  useEffect(() => { rt.remember('product', { ...mem, q, node: url.node }); }, [mem, q, url.node, rt]);

  const ancestors = useMemo(() => {
    const ids = chain.map((n) => n.id);
    if (activeNode && nodeKind(activeNode) !== 'fam' && !ids.includes(activeNode)) ids.push(activeNode);
    return ids;
  }, [chain, activeNode]);
  const isOpen = (id: string) => !mem.collapsed.includes(id) && (mem.expanded.includes(id) || (ancestors.includes(id) && nodeKind(id) !== 'fam'));
  const select = (id: string) => {
    setMem((s) => ({ expanded: s.expanded.includes(id) ? s.expanded : [...s.expanded, id], collapsed: s.collapsed.filter((x) => x !== id) }));
    if (qInput) setQInput('');
    update({ node: id, q: null });
  };
  const toggle = (id: string) => {
    const open = isOpen(id);
    setMem((s) => open
      ? { expanded: s.expanded.filter((x) => x !== id), collapsed: [...s.collapsed.filter((x) => x !== id), id] }
      : { expanded: [...s.expanded.filter((x) => x !== id), id], collapsed: s.collapsed.filter((x) => x !== id) });
  };
  const ctx: TreeCtx = { active: q ? null : activeNode, isOpen, select, toggle };

  // 모델 표
  const searching = q.length > 0;
  const kind = activeNode ? nodeKind(activeNode) : null;
  const params = searching ? { q } : kind === 'fam' ? { family_id: activeNode! } : activeNode ? { category_id: activeNode } : {};
  const models = useModels(params, searching || !!activeNode);
  const columns = models.data?.columns?.length ? models.data.columns : DEFAULT_COLUMNS;
  const rows = useMemo(() => {
    const list = models.data?.items ?? [];
    if (!searching && kind === 'fam') {
      const inch = (r: KbModelRow) => Number((r.values?.size as { inch?: number } | undefined)?.inch ?? NaN);
      return [...list].sort((a, b) => (Number.isNaN(inch(a)) || Number.isNaN(inch(b)) ? 0 : inch(a) - inch(b)));
    }
    return list;
  }, [models.data, searching, kind]);
  const repOf = (famId: string) => {
    const fam = rows.filter((r) => r.family.id === famId);
    const rep = fam.find((r) => r.is_family_default) ?? fam[0];
    return rep ? modelName(rep) : '';
  };
  const grid = gridFor(columns.length);
  const showSeries = searching || kind !== 'fam';

  const tray = mem.tray;
  const setTray = (t: TrayEntry[]) => setMem({ tray: t });
  const toggleTray = (e: TrayEntry) => setTray(tray.some((t) => t.ref === e.ref) ? tray.filter((t) => t.ref !== e.ref) : [...tray, e]);
  const runner = useAddRunner('product', tray, () => setTray([]));

  // 경로 줄
  const pathParts: ReactNode[] = [];
  if (searching) {
    pathParts.push(<button key="all" type="button" onClick={() => setQInput('')}>전체</button>, <span key="s1">›</span>, <span key="sr" className="sh-path__last">검색 결과</span>);
  } else {
    pathParts.push(<span key="all">전체</span>);
    chain.forEach((n, i) => {
      pathParts.push(<span key={`s${i}`}>›</span>);
      pathParts.push(i === chain.length - 1
        ? <span key={n.id} className="sh-path__last">{n.name}</span>
        : <button key={n.id} type="button" onClick={() => select(n.id)}>{n.name}</button>);
    });
  }

  let body: ReactNode;
  if (models.isError && !models.data) {
    body = <div className="sh-state" role="alert"><span>제품 목록을 불러오지 못했어요.<br /><Button h={28} onClick={() => models.refetch()} style={{ marginTop: 8 }}>다시 시도</Button></span></div>;
  } else if ((models.isLoading || (!searching && !activeNode && top.isLoading)) && !models.data) {
    body = <div style={{ display: 'flex', flexDirection: 'column' }}>{Array.from({ length: 6 }, (_, i) => <div key={i} className="sh-mrow" style={{ gridTemplateColumns: grid }}><span /><Skeleton w={56} h={38} r={6} /><Skeleton h={12} w="70%" /><Skeleton h={10} /><Skeleton h={10} /><Skeleton h={10} /><span /><span /></div>)}</div>;
  } else if (!rows.length) {
    body = <div className="sh-state">{searching ? `‘${q}’에 맞는 제품이 없어요. 제품명이나 모델코드 일부로 찾아보세요.` : '이 분류에는 아직 모델이 없어요.'}</div>;
  } else {
    body = (
      <>
        {rows.map((m) => <ModelRow key={m.id} row={m} columns={columns} grid={grid} showSeries={showSeries} repName={repOf(m.family.id)} tray={tray} toggleTray={toggleTray} search={url.sp} />)}
        {models.data?.next_cursor && <div className="sh-state" style={{ flex: 'none', padding: 12 }}>더 많은 모델이 있어요 · 검색으로 좁혀 보세요</div>}
      </>
    );
  }

  return (
    <PopoverFrame kind="product" hidden={hidden} dragging={!!activeDrag && activeDrag.type === 'product'}>
      <PopSearch label="제품 검색" placeholder="제품명 · 모델명 검색" value={qInput} onChange={setQInput} onClose={onClose} />
      <div className="sh-pop__bar sh-pop__bar--path">
        <div className="sh-path" aria-label="경로">{pathParts}</div>
        {rt.canDrag('product') ? <DragHint /> : <span style={{ whiteSpace: 'nowrap', flexShrink: 0 }}>'상세'에서 스펙 · 이미지 · 활용 사례를 모두 볼 수 있어요</span>}
      </div>
      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        <nav className="sh-tree" aria-label="제품 분류">
          {top.isLoading && <SkeletonRows n={8} depth={0} />}
          {top.isError && <div className="sh-state" style={{ padding: 8 }}>분류를 불러오지 못했어요.<br /><Button h={26} onClick={() => top.refetch()} style={{ marginTop: 6 }}>다시 시도</Button></div>}
          {(top.data?.items ?? []).map((c) => <CategoryNode key={c.id} c={c} depth={0} ctx={ctx} />)}
        </nav>
        <div className="sh-mcol" role="table" aria-label="모델 목록">
          <div className="sh-mhead" style={{ gridTemplateColumns: grid }} role="row">
            <span /><span style={{ gridColumn: 'span 2' }} role="columnheader">모델</span>
            {columns.map((c) => <span key={c.key} role="columnheader">{c.label}</span>)}
            <span /><span />
          </div>
          <div className="sh-mbody">{body}</div>
          {rt.hasTask ? (
            <div className="sh-pop__foot" data-footer="task">
              <span className={runner.failed ? 'sh-pop__foot-text sh-pop__foot-text--err' : 'sh-pop__foot-text'} role={runner.failed ? 'alert' : undefined}>
                {runner.failed ? ADD_FAIL_TEXT : `선택 ${tray.length}`}
              </span>
              <div style={{ display: 'flex', gap: 6, flex: 1, overflow: 'hidden', minWidth: 0 }} aria-label="선택한 제품">
                {tray.map((t) => <TrayChip key={t.ref} label={t.label} onRemove={() => toggleTray(t)} />)}
              </div>
              <AddAllButton n={tray.length} busy={runner.busy} onClick={runner.run} disabledReason={rt.canAdd('product') ? undefined : rt.offReason('product', 'footer')} />
            </div>
          ) : <NoTaskFooter text={NO_TASK_TEXT} />}
        </div>
      </div>
    </PopoverFrame>
  );
}

