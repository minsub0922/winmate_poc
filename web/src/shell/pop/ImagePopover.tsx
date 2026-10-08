/**
 * 이미지 검색 팝오버(00-shell §5.5, 보드 HomeImage) — 820×560.
 * 탭 5(전체 · 제품 이미지 · 유관 사례 이미지 · 내 생성 이미지 · 사내 자산) · `출처 확인된 이미지만` · 3열 그리드 · 이미지 정보 패널 · 푸터.
 * 타일 클릭 = 포커스(패널), 체크 원/Space = 선택(작업 있음).
 */
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  Button, Img, ImageTile, MetaRows, Skeleton, Toggle, Tabs, formatDate, formatMediaSize, shortFileUrl, useActiveDrag, useDragSource, type MetaRow,
} from '@/ui';
import { imageAlt, imageKindLabel, imageSrc, kb, ref, useImageMeta, useImageSearchPages, useMyImageInfo, useMyImages, usageNotePopover } from '../kb';
import type { GeneratedImage, KbImageCard, KbImageMeta } from '../kbTypes';
import { useShellRuntime } from '../runtime';
import { useAssetUsage, usageText } from '../workspace';
import { useShellUrl } from '../urlState';
import {
  ADD_FAIL_TEXT, AddAllButton, DragHint, NoTaskFooter, PopoverFrame, PopSearch, useAddRunner, useDebounced, usePopMemory, usePopoverEscape,
  errorReason,
} from './common';

type Tab = 'all' | 'official' | 'case' | 'mine' | 'internal';
interface Sel { ref: string; label: string; id: string; generated?: boolean }
interface Mem { tab: Tab; verifiedOnly: boolean; selected: Sel[] }
interface Item { key: string; ref: string; id: string; title: string; kind: string; src: string | null; fit: 'cover' | 'contain'; focal: KbImageCard['focal'];
  meta: string; aria: string; card?: KbImageCard; gen?: GeneratedImage }

const OFFICIAL = new Set(['product', 'solution', 'industry']);

function toItem(c: KbImageCard): Item {
  const kind = imageKindLabel(c.kind);
  const domain = c.source_domain || 'samsung.com';
  const size = c.original?.width && c.original?.height ? `${c.original.width}×${c.original.height}` : null;
  return {
    key: c.id, ref: ref.image(c.id), id: c.id, title: imageAlt({ alt: c.title, title: c.alt }, '이미지'), kind, src: imageSrc(c), fit: c.kind === 'product' ? 'contain' : 'cover', focal: c.focal,
    meta: [kind, size, domain].filter(Boolean).join(' · '), aria: `${imageAlt({ alt: c.title, title: c.alt }, '이미지')} — ${kind} 이미지, 출처 ${domain}`, card: c,
  };
}
function genItem(g: GeneratedImage): Item {
  const title = g.title || '생성 이미지';
  return {
    key: `gen:${g.id}`, ref: ref.generated(g.id), id: g.id, title, kind: '생성', src: g.thumb_url ?? null, fit: 'cover', focal: null,
    meta: ['생성', g.width && g.height ? `${g.width}×${g.height}` : null, 'Winmate'].filter(Boolean).join(' · '), aria: `${title} — 생성 이미지, 출처 Winmate`, gen: g,
  };
}

function InfoPanel({ item }: { item: Item | null }) {
  const meta = useImageMeta(item?.card ? item.id : null);
  const usage = useAssetUsage(item ? [item.ref] : []);
  // 내 생성 이미지는 image 서비스 정보 행(출처 · 원본 · 저장본 · 생성 · 사용 조건 · 사용 이력)을 그대로 — 못 받으면 셸이 아는 값으로
  const genInfo = useMyImageInfo(item?.gen ? item.id : null);
  if (!item) return <aside className="sh-imginfo" aria-label="이미지 정보"><span className="sh-imginfo__head">이미지 정보</span></aside>;
  const m: KbImageMeta | undefined = meta.data;
  const rows: MetaRow[] = [];
  if (item.card) {
    const posted = m?.posted?.date ? ` · 출처 게시 ${m.posted.date}` : '';
    const orig = formatMediaSize(m?.original ?? item.card.original);
    const stored = formatMediaSize(m?.stored);
    const shrunk = m?.stored && m?.original && (m.stored.width < m.original.width || m.stored.height < m.original.height) ? ' · 긴 변 축소' : '';
    rows.push(
      { k: '출처 페이지', v: m?.source_page?.label || m?.source_page?.title || (m ? '[확인 필요]' : '…'), href: m?.source_page?.url ?? null },
      { k: '원본 파일', v: m?.original_url ? shortFileUrl(m.original_url) : (m ? '[확인 필요]' : '…'), href: m?.original_url ?? null, title: m?.original_url ?? undefined },
      { k: '원본', v: `${orig || '[확인 필요]'}${posted}` },
      { k: '저장본', v: stored ? `${stored}${shrunk}` : (m ? '[확인 필요]' : '…') },
      { k: '수집', v: m?.collected_at ? `${formatDate(m.collected_at)} · 공식 페이지에서 수집` : (m ? '[확인 필요]' : '…') },
      { k: '사용 조건', v: m?.usage_note_short || usageNotePopover(m?.rights ?? item.card.rights) },
      { k: '사용 이력', v: usageText(usage.data, item.ref, usage.isLoading) },
    );
  } else if (item.gen && genInfo.data?.rows?.length) {
    rows.push(...genInfo.data.rows.map((r) => ({ k: r.k, v: r.v, href: r.href ?? null })));
  } else if (item.gen) {
    rows.push(
      { k: '출처', v: 'Winmate 이미지 생성' },
      { k: '원본', v: formatMediaSize(item.gen.width && item.gen.height ? { width: item.gen.width, height: item.gen.height, format: item.gen.format ?? '', bytes: item.gen.bytes ?? 0 } : null) || '[확인 필요]' },
      { k: '생성', v: formatDate(item.gen.created_at) || '[확인 필요]' },
      { k: '사용 조건', v: '대외 사용 범위 확인 필요' },
      { k: '사용 이력', v: usageText(usage.data, item.ref, usage.isLoading) },
    );
  }
  return (
    <aside className="sh-imginfo" aria-label="이미지 정보">
      <span className="sh-imginfo__head">이미지 정보</span>
      <span className="sh-imginfo__img"><Img src={item.card ? imageSrc(item.card, 'stored') : item.src} alt={item.title} focal={item.focal} /></span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0 }}>
        <span className="wm-badge wm-badge--darksm">{item.kind}</span>
        <span className="sh-ell" style={{ fontSize: 12.5, fontWeight: 700 }} title={item.title}>{item.title}</span>
      </div>
      {(item.card && meta.isLoading) || (item.gen && genInfo.isLoading) ? [0, 1, 2, 3].map((i) => <Skeleton key={i} h={26} r={6} />) : <MetaRows rows={rows} />}
    </aside>
  );
}

function Tile({ it, focused, selected, selectable, onFocus, onToggle }: { it: Item; focused: boolean; selected: boolean; selectable: boolean; onFocus: () => void; onToggle: () => void }) {
  const rt = useShellRuntime();
  const active = useActiveDrag();
  const canDrag = rt.canDrag('image') && !rt.isAdded(it.ref);
  const drag = useDragSource(canDrag ? { type: 'image', ref: it.ref, label: it.title, sub: `이미지 · ${it.kind}` } : null);
  const tone = OFFICIAL.has(it.card?.kind ?? '') ? 'product' : 'photo';
  return (
    <ImageTile src={it.src} title={it.title} meta={it.meta} kind={{ label: it.kind, tone }} fit={it.fit} focal={it.focal} focused={focused}
      selected={selected} selectable={selectable} onSelectToggle={onToggle} onClick={onFocus} ariaLabel={it.aria} dragProps={drag} grip={canDrag}
      dragging={active?.ref === it.ref} />
  );
}

export function ImagePopover({ onClose, hidden }: { onClose: () => void; hidden?: boolean }) {
  const rt = useShellRuntime();
  const url = useShellUrl();
  const qc = useQueryClient();
  const activeDrag = useActiveDrag();
  const [mem, setMem] = usePopMemory<Mem>('image', () => ({ tab: 'all', verifiedOnly: true, selected: [] }));
  const [qInput, setQInput] = useState(url.q);
  const q = useDebounced(qInput.trim(), 300);
  const { update } = url;
  useEffect(() => { update({ q: q || null }); }, [q, update]);
  useEffect(() => { rt.remember('image', { ...mem, q }); }, [mem, q, rt]);
  usePopoverEscape(onClose, !hidden);

  const source = mem.tab === 'official' ? 'official' : mem.tab === 'case' ? 'case' : 'all';
  const search = useImageSearchPages({ q, source, verified_only: mem.verifiedOnly });
  const mine = useMyImages(q);
  const pages = search.data?.pages;
  const counts: Partial<NonNullable<typeof pages>[number]['counts']> = pages?.[0]?.counts ?? {};
  const nOfficial = counts.official ?? 0;
  const nCase = counts.case ?? 0;
  const nMine = mine.data?.items.length ?? 0;
  const nInternal = 0;

  const items: Item[] = useMemo(() => {
    if (mem.tab === 'mine') return (mine.data?.items ?? []).map(genItem);
    if (mem.tab === 'internal') return [];
    const kbItems = (pages ?? []).flatMap((pg) => pg.items).map(toItem);
    return mem.tab === 'all' ? [...kbItems, ...(mine.data?.items ?? []).map(genItem)] : kbItems;
  }, [mem.tab, pages, mine.data]);

  // 새 결과면 첫 타일에 포커스, `더 보기` 로 뒤에 붙으면 그대로
  const [focusKey, setFocusKey] = useState<string | null>(null);
  const firstKey = items[0]?.key ?? null;
  useEffect(() => { setFocusKey(firstKey); }, [firstKey, q, mem.tab, mem.verifiedOnly]);
  const focused = items.find((i) => i.key === focusKey) ?? items[0] ?? null;

  const selectable = rt.hasTask;
  const sel = mem.selected;
  const toggleSel = (it: Item) => setMem({ selected: sel.some((s) => s.ref === it.ref) ? sel.filter((s) => s.ref !== it.ref) : [...sel, { ref: it.ref, label: it.title, id: it.id, generated: !!it.gen }] });
  const runner = useAddRunner('image', sel, () => setMem({ selected: [] }));
  const [attachState, setAttachState] = useState<'idle' | 'busy' | 'failed'>('idle');
  const canAttach = !!rt.page.onAttach && rt.hasTask;
  const attach = async () => {
    if (!sel.length || !rt.page.onAttach) return;
    setAttachState('busy');
    try {
      const metas = await Promise.all(sel.map(async (s) => {
        if (s.generated) return { id: s.id, ref: s.ref, kind: 'generated', title: s.label, usage_note: '대외 사용 범위 확인 필요' } as Record<string, unknown>;
        const m = await qc.fetchQuery({ queryKey: ['kb', 'image', s.id], queryFn: ({ signal }) => kb.image(s.id, signal), staleTime: 300_000 });
        return { ...m, ref: s.ref, usage_note: m.usage_note || usageNotePopover(m.rights) } as Record<string, unknown>;
      }));
      await rt.page.onAttach(metas);
      setAttachState('idle');
      setMem({ selected: [] });
    } catch {
      setAttachState('failed');
    }
  };

  const tabs = [
    { value: 'all' as Tab, label: '전체', count: nOfficial + nCase + nMine + nInternal },
    { value: 'official' as Tab, label: '제품 이미지', count: nOfficial },
    { value: 'case' as Tab, label: '유관 사례 이미지', count: nCase },
    { value: 'mine' as Tab, label: '내 생성 이미지', count: nMine },
    { value: 'internal' as Tab, label: '사내 자산', count: nInternal },
  ];

  let grid: ReactNode;
  if (!q) grid = <div className="sh-state" style={{ gridColumn: '1 / -1' }}>장면 · 공간 · 제품으로 검색해 보세요.</div>;
  else if (search.isError && !search.data && mem.tab !== 'mine') {
    grid = <div className="sh-state" style={{ gridColumn: '1 / -1' }} role="alert"><span>이미지를 불러오지 못했어요.<br /><span className="sh-state__why">{errorReason(search.error)}</span><Button h={28} onClick={() => search.refetch()} style={{ marginTop: 8 }}>다시 시도</Button></span></div>;
  } else if ((search.isLoading && !search.data && mem.tab !== 'mine') || (mem.tab === 'mine' && mine.isLoading)) {
    grid = Array.from({ length: 6 }, (_, i) => <Skeleton key={i} h={160} r={10} />);
  } else if (!items.length) {
    grid = <div className="sh-state" style={{ gridColumn: '1 / -1' }}>{mem.tab === 'mine' ? '아직 만든 이미지가 없어요.' : mem.tab === 'internal' ? '등록된 사내 자산이 없어요.' : `‘${q}’에 맞는 이미지가 없어요.`}</div>;
  } else {
    const kbTotal = mem.tab === 'official' ? nOfficial : mem.tab === 'case' ? nCase : nOfficial + nCase;
    const kbShown = (pages ?? []).reduce((a, pg) => a + pg.items.length, 0);
    grid = (
      <>
        {items.map((it) => (
          <Tile key={it.key} it={it} focused={focused?.key === it.key} selected={sel.some((s) => s.ref === it.ref)} selectable={selectable}
            onFocus={() => setFocusKey(it.key)} onToggle={() => toggleSel(it)} />
        ))}
        {mem.tab !== 'mine' && search.hasNextPage && (
          <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'center', padding: '4px 0 8px' }}>
            <Button h={32} loading={search.isFetchingNextPage} onClick={() => search.fetchNextPage()} data-more="">
              이미지 더 보기 · {kbShown} / {kbTotal}
            </Button>
          </div>
        )}
      </>
    );
  }

  const footLeft = runner.failed ? ADD_FAIL_TEXT : attachState === 'failed' ? '첨부하지 못했어요. 다시 시도해 주세요.' : `선택 ${sel.length} · 출처 정보가 함께 붙습니다`;
  return (
    <PopoverFrame kind="image" hidden={hidden} dragging={!!activeDrag && activeDrag.type === 'image'}>
      <PopSearch label="이미지 검색" placeholder="장면 · 공간 · 제품으로 검색" value={qInput} onChange={setQInput} onClose={onClose} />
      <div className="sh-pop__bar sh-pop__bar--tabs">
        <Tabs variant="pop" ariaLabel="이미지 출처" value={mem.tab} onChange={(t) => setMem({ tab: t })} items={tabs} />
        {rt.canDrag('image') ? <DragHint /> : <Toggle checked={mem.verifiedOnly} onChange={(v) => setMem({ verifiedOnly: v })}>출처 확인된 이미지만</Toggle>}
      </div>
      <div style={{ flex: 1, minHeight: 0, display: 'flex' }}>
        <div className="sh-imggrid" role="list" aria-label="이미지 결과">{grid}</div>
        <InfoPanel item={q && items.length ? focused : null} />
      </div>
      {rt.hasTask ? (
        <div className="sh-pop__foot" data-footer="task" style={{ justifyContent: 'space-between' }}>
          <span className={runner.failed || attachState === 'failed' ? 'sh-pop__foot-text sh-pop__foot-text--err' : 'sh-pop__foot-text'}>{footLeft}</span>
          <div style={{ display: 'flex', gap: 6 }}>
            <Button h={32} disabled={!sel.length || !canAttach} loading={attachState === 'busy'} onClick={attach}
              disabledReason={!canAttach ? '이 화면에는 첨부할 대화가 없습니다' : '먼저 첨부할 이미지를 고르세요'}>대화에 첨부</Button>
            <AddAllButton n={sel.length} busy={runner.busy} onClick={runner.run} disabledReason={rt.canAdd('image') ? undefined : rt.offReason('image', 'footer')} />
          </div>
        </div>
      ) : <NoTaskFooter text="진행 중인 작업이 없어 탐색만 할 수 있어요." buttons={['대화에 첨부', '현재 작업에 추가']} />}
    </PopoverFrame>
  );
}

